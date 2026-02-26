"""
EduPlatform Orchestrator — Gemini (brain) + Claude Code (hands).

Gemini holds the full codebase context (1M tokens) and breaks phases
into concrete tasks. Claude Code executes each task in isolation.
Gemini validates the result before moving to the next task.

Usage:
    cd tools/orchestrator
    uv run python orchestrator.py --phase 2.4

    # Dry run (Gemini plans but Claude doesn't execute):
    uv run python orchestrator.py --phase 2.4 --dry-run

    # Resume from a specific task:
    uv run python orchestrator.py --phase 2.4 --resume-from 3
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from google import genai

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent  # monorepo root
CONTEXT_FILES = [
    "CLAUDE.md",
    "STRUCTURE.md",
    "docs/goals/00-ROADMAP.md",
    "docs/architecture/01-SYSTEM-OVERVIEW.md",
    "docs/architecture/02-API-REFERENCE.md",
    "docs/architecture/03-DATABASE-SCHEMAS.md",
    "docs/architecture/04-AUTH-FLOW.md",
    "docs/architecture/05-INFRASTRUCTURE.md",
    "docs/architecture/06-SHARED-LIBRARY.md",
]
MAX_RETRIES = 2
CLAUDE_TIMEOUT = 600  # 10 min per task
STATE_DIR = ROOT / "tools" / "orchestrator" / ".state"

log = logging.getLogger("orchestrator")


def _load_env() -> None:
    """Load .env from monorepo root (simple key=value parser, no extra deps)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not os.environ.get(key):
            os.environ[key] = value


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: int
    title: str
    scope: str  # e.g. "backend:learning", "frontend:buyer", "infra"
    prompt: str  # full prompt for Claude Code
    test_command: str | None = None  # verification command
    depends_on: list[int] = field(default_factory=list)
    status: str = "pending"  # pending | running | passed | failed
    attempts: int = 0
    claude_output: str = ""
    validation: str = ""


@dataclass
class PhaseState:
    phase: str
    tasks: list[Task]
    current_task: int = 0

    def save(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = STATE_DIR / f"phase-{self.phase}.json"
        data = {
            "phase": self.phase,
            "current_task": self.current_task,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "scope": t.scope,
                    "prompt": t.prompt,
                    "test_command": t.test_command,
                    "depends_on": t.depends_on,
                    "status": t.status,
                    "attempts": t.attempts,
                }
                for t in self.tasks
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        log.info("State saved to %s", path)

    @classmethod
    def load(cls, phase: str) -> PhaseState | None:
        path = STATE_DIR / f"phase-{phase}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        tasks = [Task(**t) for t in data["tasks"]]
        return cls(phase=data["phase"], tasks=tasks, current_task=data["current_task"])


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

class GeminiOperator:
    """Wraps Gemini with the full project context."""

    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not set. Add it to .env or export it.")
            sys.exit(1)
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._context = self._load_context()
        log.info(
            "Gemini context loaded: %d chars (~%d tokens)",
            len(self._context),
            len(self._context) // 4,
        )

    def _load_context(self) -> str:
        """Read all architecture docs + CLAUDE.md into a single context string."""
        parts: list[str] = []
        for rel in CONTEXT_FILES:
            path = ROOT / rel
            if path.exists():
                content = path.read_text(errors="replace")
                parts.append(f"=== FILE: {rel} ===\n{content}\n")
            else:
                log.warning("Context file missing: %s", rel)

        # Also include a tree of Python service files (names only, not content)
        tree_lines: list[str] = []
        for svc_dir in sorted((ROOT / "services" / "py").iterdir()):
            if svc_dir.is_dir():
                for py_file in sorted(svc_dir.rglob("*.py")):
                    tree_lines.append(str(py_file.relative_to(ROOT)))
        parts.append("=== FILE TREE (Python services) ===\n" + "\n".join(tree_lines))

        # Frontend file tree
        buyer_dir = ROOT / "apps" / "buyer"
        if buyer_dir.exists():
            fe_lines: list[str] = []
            for ext in ("*.ts", "*.tsx"):
                for f in sorted(buyer_dir.rglob(ext)):
                    fe_lines.append(str(f.relative_to(ROOT)))
            parts.append("=== FILE TREE (Frontend) ===\n" + "\n".join(fe_lines))

        return "\n\n".join(parts)

    def _call(self, prompt: str) -> str:
        """Send prompt to Gemini with project context. Retries on rate limit."""
        full_prompt = (
            "You are the architect-operator for EduPlatform. "
            "You have the FULL project context below. "
            "Always respond in the exact format requested.\n\n"
            f"{self._context}\n\n"
            f"--- INSTRUCTION ---\n{prompt}"
        )
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=full_prompt,
                )
                return response.text.strip()
            except Exception as e:
                if "429" in str(e) and attempt < max_attempts:
                    wait = 40 * attempt
                    log.warning("Rate limited, waiting %ds (attempt %d/%d)", wait, attempt, max_attempts)
                    time.sleep(wait)
                else:
                    raise

    def _parse_json(self, text: str) -> dict | list:
        """Extract JSON from Gemini response (handles markdown fences)."""
        cleaned = text
        if "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 3:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            for start_char, end_char in [("[", "]"), ("{", "}")]:
                start = text.find(start_char)
                end = text.rfind(end_char)
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(text[start : end + 1])
                    except json.JSONDecodeError:
                        continue
            log.error("Failed to parse JSON from Gemini:\n%s", text[:500])
            raise

    def plan_phase(self, phase: str) -> list[Task]:
        """Ask Gemini to break a roadmap phase into concrete tasks."""
        prompt = f"""
Break down Phase {phase} from the roadmap into concrete implementation tasks.

RULES:
- Each task must be independently executable by Claude Code CLI
- Each task has a SINGLE scope: one service or one frontend feature
- Tasks must follow TDD: write tests first, then implementation
- Tasks must follow the existing patterns in CLAUDE.md
- Include test_command for verification (e.g. "cd services/py/learning && uv run --package learning pytest tests/ -v")
- For frontend tasks, test_command is "cd apps/buyer && pnpm build"
- Order tasks by dependencies (backend before frontend that uses it)
- The prompt field must be a COMPLETE instruction for Claude Code — specific files, patterns, what to create
- Reference existing code patterns (look at file tree above)
- Keep prompts in Russian (as per CLAUDE.md)

Return ONLY a JSON array (no markdown, no explanation):
[
  {{
    "id": 1,
    "title": "Short task title in English",
    "scope": "backend:service-name" or "frontend:buyer" or "infra" or "docs",
    "prompt": "Full detailed prompt for Claude Code in Russian...",
    "test_command": "command to verify" or null,
    "depends_on": []
  }},
  ...
]
"""
        raw = self._call(prompt)
        items = self._parse_json(raw)
        return [Task(**item) for item in items]

    def validate_result(self, task: Task, claude_output: str, test_output: str) -> dict:
        """Ask Gemini to validate what Claude Code produced."""
        prompt = f"""
Validate the implementation of task: "{task.title}" (scope: {task.scope})

TASK PROMPT WAS:
{task.prompt[:2000]}

CLAUDE CODE OUTPUT:
{claude_output[:3000]}

TEST OUTPUT:
{test_output[:2000]}

Check:
1. Did Claude follow the task prompt?
2. Did tests pass?
3. Does it follow CLAUDE.md rules (Clean Architecture, TDD, YAGNI)?
4. Any security concerns?

Return ONLY JSON:
{{
  "approved": true/false,
  "issues": ["list of issues found"],
  "fix_prompt": "If not approved, a specific fix prompt for Claude Code. null if approved."
}}
"""
        raw = self._call(prompt)
        return self._parse_json(raw)


# ---------------------------------------------------------------------------
# Claude Code executor
# ---------------------------------------------------------------------------

def run_claude_code(prompt: str, cwd: Path | None = None) -> tuple[int, str]:
    """Execute a task via Claude Code CLI. Returns (exit_code, output)."""
    work_dir = str(cwd or ROOT)
    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "-p",
        prompt,
    ]

    log.info("Running Claude Code in %s", work_dir)
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
        )
        elapsed = time.time() - start
        output = result.stdout + ("\n--- STDERR ---\n" + result.stderr if result.stderr else "")
        log.info("Claude Code finished in %.0fs (exit=%d)", elapsed, result.returncode)
        return result.returncode, output

    except subprocess.TimeoutExpired:
        log.error("Claude Code timed out after %ds", CLAUDE_TIMEOUT)
        return 1, f"TIMEOUT after {CLAUDE_TIMEOUT}s"

    except FileNotFoundError:
        log.error("'claude' CLI not found. Install: npm install -g @anthropic-ai/claude-code")
        return 1, "claude CLI not found"


def run_test_command(command: str) -> tuple[int, str]:
    """Run a test/build verification command."""
    log.info("Running: %s", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, "Test command timed out"


# ---------------------------------------------------------------------------
# Orchestration loop
# ---------------------------------------------------------------------------

def execute_phase(
    gemini: GeminiOperator,
    state: PhaseState,
    dry_run: bool = False,
) -> None:
    """Main orchestration loop: plan -> execute -> validate -> repeat."""
    total = len(state.tasks)

    for i in range(state.current_task, total):
        task = state.tasks[i]
        state.current_task = i
        state.save()

        # Check dependencies
        for dep_id in task.depends_on:
            dep_task = next((t for t in state.tasks if t.id == dep_id), None)
            if dep_task and dep_task.status != "passed":
                log.error(
                    "Task #%d depends on #%d which is '%s'. Stopping.",
                    task.id, dep_id, dep_task.status,
                )
                return

        print(f"\n{'='*60}")
        print(f"  [{i+1}/{total}] Task #{task.id}: {task.title}")
        print(f"  Scope: {task.scope}")
        print(f"{'='*60}")

        if dry_run:
            print(f"\n  [DRY RUN] Prompt preview:\n")
            print(f"  {task.prompt[:200]}...")
            task.status = "passed"
            continue

        # Execute with retries
        for attempt in range(1, MAX_RETRIES + 1):
            task.attempts = attempt
            task.status = "running"
            state.save()

            print(f"\n  Attempt {attempt}/{MAX_RETRIES}")
            print("  Sending to Claude Code...")

            # Run Claude Code
            exit_code, claude_output = run_claude_code(task.prompt)
            task.claude_output = claude_output

            if exit_code != 0 and "TIMEOUT" in claude_output:
                print("  TIMEOUT — skipping task")
                task.status = "failed"
                break

            # Run tests if configured
            test_output = ""
            test_passed = True
            if task.test_command:
                print(f"  Running tests: {task.test_command}")
                test_exit, test_output = run_test_command(task.test_command)
                test_passed = test_exit == 0
                if test_passed:
                    print("  Tests PASSED")
                else:
                    print("  Tests FAILED")

            # Gemini validates
            print("  Gemini validating...")
            try:
                validation = gemini.validate_result(task, claude_output, test_output)
            except Exception as e:
                log.warning("Gemini validation failed: %s", e)
                validation = {
                    "approved": test_passed,
                    "issues": [str(e)],
                    "fix_prompt": None,
                }

            task.validation = json.dumps(validation, ensure_ascii=False)
            approved = validation.get("approved", False)
            issues = validation.get("issues", [])

            if approved and test_passed:
                print("  APPROVED")
                task.status = "passed"
                state.save()
                break
            else:
                print(f"  REJECTED — issues: {issues}")
                if attempt < MAX_RETRIES:
                    fix_prompt = validation.get("fix_prompt")
                    if fix_prompt:
                        print("  Retrying with fix prompt from Gemini...")
                        task.prompt = fix_prompt
                    else:
                        print("  Retrying original task...")
                else:
                    print("  Max retries reached. Marking FAILED.")
                    task.status = "failed"
                    state.save()

        # Report after each task
        passed = sum(1 for t in state.tasks if t.status == "passed")
        failed = sum(1 for t in state.tasks if t.status == "failed")
        pending = total - passed - failed
        print(f"\n  Progress: {passed} passed, {failed} failed, {pending} pending")

    # Final report
    print(f"\n{'='*60}")
    print(f"  PHASE {state.phase} COMPLETE")
    print(f"{'='*60}")
    for t in state.tasks:
        icon = {"passed": "✅", "failed": "❌", "pending": "⏳"}.get(t.status, "?")
        print(f"  {icon} #{t.id} {t.title} ({t.attempts} attempts)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    _load_env()

    parser = argparse.ArgumentParser(description="EduPlatform Orchestrator")
    parser.add_argument("--phase", required=True, help="Roadmap phase (e.g. 2.4)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, don't execute")
    parser.add_argument("--resume-from", type=int, default=None, help="Resume from task N")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    print(f"\n  EduPlatform Orchestrator")
    print(f"  Phase: {args.phase}")
    print(f"  Model: {args.model}")
    print(f"  Root:  {ROOT}\n")

    gemini = GeminiOperator(model=args.model)

    # Check for saved state
    state = PhaseState.load(args.phase)
    if state and args.resume_from is None:
        print(f"  Found saved state with {len(state.tasks)} tasks.")
        print(f"  Last completed: #{state.current_task}")
        answer = input("  Resume? [Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            print("  Resuming...")
        else:
            state = None

    if state is None:
        # Ask Gemini to plan
        print("  Gemini is planning tasks...")
        tasks = gemini.plan_phase(args.phase)
        state = PhaseState(phase=args.phase, tasks=tasks)
        state.save()
        print(f"  Planned {len(tasks)} tasks:\n")
        for t in tasks:
            deps = f" (depends: {t.depends_on})" if t.depends_on else ""
            print(f"    #{t.id} [{t.scope}] {t.title}{deps}")
        print()

        if not args.dry_run:
            answer = input("  Start execution? [Y/n] ").strip().lower()
            if answer not in ("", "y", "yes"):
                print("  Aborted.")
                return

    if args.resume_from is not None:
        state.current_task = args.resume_from - 1  # 0-indexed
        if state.current_task < 0:
            state.current_task = 0

    execute_phase(gemini, state, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
