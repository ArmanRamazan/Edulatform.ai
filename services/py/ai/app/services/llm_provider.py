"""Abstract LLM provider and concrete implementations (Gemini, self-hosted OpenAI-compatible)."""
from __future__ import annotations

import asyncio
import json
import random
from abc import ABC, abstractmethod

import httpx
import structlog

from common.errors import AppError

logger = structlog.get_logger()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class LLMProvider(ABC):
    """Abstract base for LLM providers. All providers share the same interface."""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        """Generate text from a prompt.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.

        Returns:
            Tuple of (generated_text, tokens_in, tokens_out).
        """
        ...


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, http_client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._http = http_client
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        url = f"{GEMINI_API_URL}/{self._model}:generateContent"

        contents = []
        if system:
            contents.append({"parts": [{"text": system}]})
        contents.append({"parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096,
            },
        }
        params = {"key": self._api_key}

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._http.post(url, json=payload, params=params, timeout=30.0)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = AppError(f"Gemini API error: {resp.status_code}", status_code=502)
                    wait = 2 ** attempt
                    logger.warning("gemini_retry", status_code=resp.status_code, wait_seconds=wait, attempt=attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    raise AppError(f"Gemini API error: {resp.status_code} {resp.text}", status_code=502)

                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                tokens_in = usage.get("promptTokenCount", 0)
                tokens_out = usage.get("candidatesTokenCount", 0)
                return text, tokens_in, tokens_out
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning("gemini_http_error", error=str(exc), wait_seconds=wait)
                await asyncio.sleep(wait)

        raise AppError(f"Gemini API unavailable after 3 retries: {last_exc}", status_code=502)


class SelfHostedProvider(LLMProvider):
    """OpenAI-compatible self-hosted LLM provider (vLLM, Ollama, text-generation-inference)."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str = "default",
        api_key: str | None = None,
    ) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key

    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        url = f"{self._base_url}/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._http.post(url, json=payload, headers=headers, timeout=60.0)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = AppError(f"Self-hosted LLM error: {resp.status_code}", status_code=502)
                    wait = 2 ** attempt
                    logger.warning(
                        "self_hosted_retry",
                        status_code=resp.status_code,
                        wait_seconds=wait,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    raise AppError(
                        f"Self-hosted LLM error: {resp.status_code} {resp.text}",
                        status_code=502,
                    )

                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)
                return text, tokens_in, tokens_out
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning("self_hosted_http_error", error=str(exc), wait_seconds=wait)
                await asyncio.sleep(wait)

        raise AppError(f"Self-hosted LLM unavailable after 3 retries: {last_exc}", status_code=502)


# ---------------------------------------------------------------------------
# Mock data bank — realistic-looking responses for demo / no-API-key mode
# ---------------------------------------------------------------------------

_MOCK_BLUEPRINTS: list[dict] = [
    {
        "concept_name": "Python Closures",
        "difficulty": "intermediate",
        "phases": {
            "recap": (
                "Let's revisit Python functions and variable scopes. "
                "Can you explain the difference between local and global variables?"
            ),
            "reading": (
                "A closure is an inner function that retains access to variables from its "
                "enclosing scope even after that scope has finished executing. Python implements "
                "closures via the `__closure__` attribute, which holds references to the free "
                "variables. This is the mechanism that powers decorators, factories, and "
                "callback-based APIs."
            ),
            "questions": [
                "What does a closure capture from its enclosing scope?",
                "Why are closures useful in Python compared to global variables?",
                "What keyword allows an inner function to reassign an outer variable?",
            ],
            "code_case": (
                "def make_counter():\n"
                "    count = 0\n"
                "    def increment():\n"
                "        nonlocal count\n"
                "        count += 1\n"
                "        return count\n"
                "    return increment\n\n"
                "counter = make_counter()\n"
                "print(counter())  # 1\n"
                "print(counter())  # 2\n"
                "print(counter())  # 3\n"
                "# Each call remembers the previous count — that's the closure at work."
            ),
            "wrap_up": (
                "Closures are inner functions that capture variables from enclosing scopes. "
                "They enable stateful functions without classes, and are the foundation of "
                "Python decorators. Key takeaway: the `nonlocal` keyword allows mutation of "
                "captured variables."
            ),
        },
    },
    {
        "concept_name": "Rust Ownership",
        "difficulty": "advanced",
        "phases": {
            "recap": (
                "Before we start, let's recall how Python handles memory via reference counting. "
                "What happens when no references to an object remain?"
            ),
            "reading": (
                "Rust's ownership system guarantees memory safety at compile time without a "
                "garbage collector. Every value has exactly one owner. When ownership is "
                "transferred (moved), the original binding becomes invalid. References "
                "(&T, &mut T) allow borrowing without ownership transfer, subject to strict "
                "lifetime rules enforced by the borrow checker."
            ),
            "questions": [
                "What does 'ownership is moved' mean in Rust?",
                "What is the difference between a move and a borrow?",
                "Why does Rust disallow two mutable references to the same data?",
            ],
            "code_case": (
                "fn main() {\n"
                "    let s1 = String::from(\"hello\");\n"
                "    let s2 = s1;  // ownership moved: s1 is now invalid\n"
                "    // println!(\"{}\", s1);  // compile error: value used after move\n"
                "    println!(\"{}\", s2);    // works fine\n\n"
                "    let s3 = String::from(\"world\");\n"
                "    let s4 = &s3;  // borrow: s3 is still valid\n"
                "    println!(\"{} {}\", s3, s4);  // both valid\n"
                "}"
            ),
            "wrap_up": (
                "Rust ownership prevents dangling pointers and data races at compile time. "
                "No runtime overhead, no GC pauses. The three rules: each value has one owner, "
                "ownership can be moved or borrowed, and borrows must not outlive the owned value."
            ),
        },
    },
    {
        "concept_name": "TypeScript Generics",
        "difficulty": "intermediate",
        "phases": {
            "recap": (
                "Let's warm up with TypeScript interfaces. How do they differ from `type` "
                "aliases, and when would you reach for `any`?"
            ),
            "reading": (
                "Generics let you write algorithms that are type-safe for any type without "
                "sacrificing type information. Instead of `any` (which erases types), a "
                "generic type parameter `<T>` threads the type through the function signature, "
                "preserving compile-time checks. Generics appear in functions, classes, and "
                "interfaces, and support constraints via `extends`."
            ),
            "questions": [
                "What is the key difference between `any` and a generic type parameter?",
                "How do you constrain a generic to types that have a `.length` property?",
                "When should you prefer generics over union types?",
            ],
            "code_case": (
                "function identity<T>(arg: T): T {\n"
                "    return arg;\n"
                "}\n\n"
                "// TypeScript infers T automatically:\n"
                "const num = identity(42);          // T = number\n"
                "const str = identity('hello');     // T = string\n\n"
                "// With constraint:\n"
                "function getLength<T extends { length: number }>(arg: T): number {\n"
                "    return arg.length;\n"
                "}\n"
                "getLength('hello');  // 5\n"
                "getLength([1, 2, 3]); // 3"
            ),
            "wrap_up": (
                "Generics are TypeScript's mechanism for writing reusable, type-safe code. "
                "Use them when you need a function or data structure that works with multiple "
                "types but must preserve type information. Constraints narrow what types are "
                "accepted while keeping the benefits of type checking."
            ),
        },
    },
]

_MOCK_COACH_RESPONSES: list[str] = [
    (
        "Great question! Let's think about this step by step. "
        "What do you already know about this concept? "
        "Start by telling me what you understand so far, and we'll build from there."
    ),
    (
        "That's a solid attempt — you're definitely on the right track. "
        "Consider this: how does variable scope play a role here? "
        "What would happen if the inner function tried to access a variable that no longer exists?"
    ),
    (
        "Excellent work! You've grasped the core idea. "
        "Now let's push a bit further: can you think of a real-world scenario where this pattern "
        "would be useful? Think about configuration factories or event handlers."
    ),
    (
        "Not quite — but that's exactly why we practice! "
        "The key insight is that functions in Python are first-class objects, meaning they can "
        "be passed around and returned from other functions. "
        "With that in mind, how would you revise your answer?"
    ),
    (
        "We've covered the essentials today — nicely done! "
        "To recap: closures capture variables from their enclosing scope, enabling stateful "
        "behaviour without classes. This is foundational to decorators and callbacks. "
        "Any questions before we wrap up?"
    ),
]

_MOCK_QUIZ_SETS: list[list[dict]] = [
    [
        {
            "question": "What is a Python closure?",
            "options": [
                "A function that is defined inside a class",
                "An inner function that captures variables from its enclosing scope",
                "A function that closes the interpreter",
                "A lambda with default arguments",
            ],
            "correct_answer": "An inner function that captures variables from its enclosing scope",
        },
        {
            "question": "Which keyword allows an inner function to reassign a variable from the enclosing scope?",
            "options": ["global", "outer", "nonlocal", "free"],
            "correct_answer": "nonlocal",
        },
        {
            "question": "What does the `__closure__` attribute of a function contain?",
            "options": [
                "The source code of the function",
                "A tuple of cell objects holding free variable values",
                "The function's return type",
                "References to imported modules",
            ],
            "correct_answer": "A tuple of cell objects holding free variable values",
        },
    ],
    [
        {
            "question": "In Rust, what happens when ownership of a value is moved?",
            "options": [
                "The value is copied to the new owner",
                "Both the old and new bindings remain valid",
                "The original binding becomes invalid",
                "The value is dropped immediately",
            ],
            "correct_answer": "The original binding becomes invalid",
        },
        {
            "question": "What does the Rust borrow checker enforce?",
            "options": [
                "That all functions return a value",
                "That references do not outlive the data they point to",
                "That all variables are mutable",
                "That structs implement Display",
            ],
            "correct_answer": "That references do not outlive the data they point to",
        },
        {
            "question": "How many mutable references to the same data can exist at a time in Rust?",
            "options": ["Unlimited", "Two", "One", "Zero"],
            "correct_answer": "One",
        },
    ],
    [
        {
            "question": "What is the main benefit of TypeScript generics over `any`?",
            "options": [
                "Generics run faster at runtime",
                "Generics preserve type information through function calls",
                "Generics allow any type to be passed without checks",
                "Generics only work with primitive types",
            ],
            "correct_answer": "Generics preserve type information through function calls",
        },
        {
            "question": "How do you constrain a TypeScript generic to types with a `length` property?",
            "options": [
                "<T implements { length: number }>",
                "<T where T.length>",
                "<T extends { length: number }>",
                "<T: Sized>",
            ],
            "correct_answer": "<T extends { length: number }>",
        },
        {
            "question": "Which syntax correctly declares a generic function in TypeScript?",
            "options": [
                "function f(T)(arg: T): T",
                "function f<T>(arg: T): T",
                "function<T> f(arg: T): T",
                "generic function f(arg): auto",
            ],
            "correct_answer": "function f<T>(arg: T): T",
        },
    ],
]

_MOCK_SUMMARIES: list[str] = [
    (
        "This lesson explored closures in Python — inner functions that retain access to "
        "variables from their enclosing scope. Closures are created when an inner function "
        "references a free variable, and they enable stateful behaviour without using classes. "
        "The `nonlocal` keyword allows mutation of captured variables. Closures power "
        "decorators, factories, and callback patterns widely used in Python codebases."
    ),
    (
        "The core concept covered here is lexical scoping and how Python resolves variable "
        "names through the LEGB rule (Local → Enclosing → Global → Built-in). "
        "When a nested function references a variable from an outer scope, Python creates a "
        "closure — bundling the function with its captured environment. This mechanism is "
        "essential for writing composable, functional-style code and implementing the "
        "decorator pattern cleanly."
    ),
]

_MOCK_SEARCH_ROUTING: list[dict] = [
    {"route": "internal", "intent": "concept_lookup", "source": "rag", "confidence": 0.95},
    {"route": "external", "intent": "general_question", "source": "gemini", "confidence": 0.87},
    {"route": "internal", "intent": "code_example", "source": "rag", "confidence": 0.91},
]

_MOCK_GENERIC_RESPONSES: list[str] = [
    (
        "That's a thoughtful question! I'd recommend breaking it into smaller parts: "
        "start with what you already know, identify the knowledge gap, then look for a "
        "concrete example that bridges the two. Experimentation is the fastest path to "
        "understanding in software engineering."
    ),
    (
        "Great inquiry. The answer depends on context, but a reliable heuristic is to "
        "follow the data flow: where does the data come from, how is it transformed, and "
        "where does it end up? Tracing this path usually reveals the answer."
    ),
    (
        "I understand what you're asking. Let me offer a framework: first principles "
        "thinking. Strip away assumptions and ask what fundamentally must be true. "
        "From there, build back up to the specific problem at hand — you'll often find "
        "a simpler solution than you expected."
    ),
]


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for demo/development mode (no API key required).

    Detects request type from prompt keywords and returns realistic pre-defined responses.
    Simulates network latency with a random asyncio.sleep to mirror real provider behaviour.
    """

    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        """Return a mock response based on detected prompt intent.

        Args:
            prompt: The user prompt (used for keyword-based routing).
            system: Ignored — included for interface compatibility.

        Returns:
            Tuple of (response_text, tokens_in, tokens_out) with randomised token counts.
        """
        lower = prompt.lower()

        if "mission" in lower or "blueprint" in lower:
            text = json.dumps(random.choice(_MOCK_BLUEPRINTS))
        elif "coach" in lower or "session" in lower or "socratic" in lower:
            text = random.choice(_MOCK_COACH_RESPONSES)
        elif "quiz" in lower or "question" in lower:
            text = json.dumps(random.choice(_MOCK_QUIZ_SETS))
        elif "summary" in lower or "summarize" in lower:
            text = random.choice(_MOCK_SUMMARIES)
        elif "search" in lower or "route" in lower or "classify" in lower:
            text = json.dumps(random.choice(_MOCK_SEARCH_ROUTING))
        elif "moderate" in lower or "safety" in lower:
            text = json.dumps({"safe": True})
        else:
            text = random.choice(_MOCK_GENERIC_RESPONSES)

        await asyncio.sleep(random.uniform(0.5, 1.5))
        return text, random.randint(200, 800), random.randint(100, 500)
