"""
EduPlatform Orchestrator — autonomous Claude Code executor.

Parses phase docs, breaks them into tasks, executes via Claude Code CLI,
runs tests, commits atomically. Tracks token budget, pauses when exhausted,
resumes from saved state. Graceful shutdown on Ctrl+C / SIGTERM.

Usage:
    # Run all remaining phases (2.4 → 3.6):
    ./run.sh

    # Run a specific phase:
    ./run.sh --phase 2.4

    # Dry run (show tasks, don't execute):
    ./run.sh --phase 2.4 --dry-run

    # Resume after pause/crash:
    ./run.sh --resume

    # Stop gracefully:
    Ctrl+C  (saves state, can resume later)
    touch tools/orchestrator/.stop  (stops after current task)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent  # monorepo root
STATE_DIR = ROOT / "tools" / "orchestrator" / ".state"
LOG_DIR = ROOT / "tools" / "orchestrator" / ".logs"
STOP_FILE = ROOT / "tools" / "orchestrator" / ".stop"

MAX_RETRIES = 2
CLAUDE_TIMEOUT = 900  # 15 min per task

# Token budget: approximate chars as proxy (1 token ~ 4 chars)
# Conservative: pause after ~800K output chars per window (~200K tokens)
TOKEN_BUDGET_CHARS = 800_000
BUDGET_WINDOW_HOURS = 5
BUDGET_PAUSE_HOURS = 5

# Phase execution order
PHASE_ORDER = ["2.4", "2.5", "3.1", "3.2", "3.3", "3.4", "3.5"]

# Test commands by service scope
TEST_COMMANDS: dict[str, str] = {
    "identity": "cd services/py/identity && uv run --package identity pytest tests/ -v",
    "course": "cd services/py/course && uv run --package course pytest tests/ -v",
    "enrollment": "cd services/py/enrollment && uv run --package enrollment pytest tests/ -v",
    "payment": "cd services/py/payment && uv run --package payment pytest tests/ -v",
    "notification": "cd services/py/notification && uv run --package notification pytest tests/ -v",
    "ai": "cd services/py/ai && uv run --package ai pytest tests/ -v",
    "learning": "cd services/py/learning && uv run --package learning pytest tests/ -v",
    "buyer": "cd apps/buyer && pnpm build",
    "seller": "cd apps/buyer && pnpm build",  # seller uses buyer build for now
}

log = logging.getLogger("orchestrator")

# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum: int, frame: object) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    print("\n  SHUTDOWN requested. Finishing current task...")


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Load .env from monorepo root."""
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


def _should_stop() -> bool:
    """Check if we should stop (signal or stop file)."""
    if _shutdown_requested:
        return True
    if STOP_FILE.exists():
        STOP_FILE.unlink()
        return True
    return False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: int
    title: str
    scope: str  # e.g. "backend:learning", "frontend:buyer", "infra", "docs"
    prompt: str
    test_command: str | None = None
    depends_on: list[int] = field(default_factory=list)
    status: str = "pending"  # pending | running | passed | failed | skipped
    attempts: int = 0
    output_chars: int = 0
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


@dataclass
class OrchestratorState:
    """Persistent state across pauses/resumes."""
    phases: dict[str, list[Task]]  # phase -> tasks
    current_phase: str = ""
    current_task_idx: int = 0
    total_output_chars: int = 0
    window_start: str = ""
    paused_at: str = ""

    def save(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = STATE_DIR / "state.json"
        data = {
            "current_phase": self.current_phase,
            "current_task_idx": self.current_task_idx,
            "total_output_chars": self.total_output_chars,
            "window_start": self.window_start,
            "paused_at": self.paused_at,
            "phases": {
                phase: [
                    {
                        "id": t.id,
                        "title": t.title,
                        "scope": t.scope,
                        "prompt": t.prompt,
                        "test_command": t.test_command,
                        "depends_on": t.depends_on,
                        "status": t.status,
                        "attempts": t.attempts,
                        "output_chars": t.output_chars,
                        "started_at": t.started_at,
                        "finished_at": t.finished_at,
                        "error": t.error,
                    }
                    for t in tasks
                ]
                for phase, tasks in self.phases.items()
            },
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls) -> OrchestratorState | None:
        path = STATE_DIR / "state.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        phases = {}
        for phase, task_list in data.get("phases", {}).items():
            phases[phase] = [Task(**t) for t in task_list]
        return cls(
            phases=phases,
            current_phase=data.get("current_phase", ""),
            current_task_idx=data.get("current_task_idx", 0),
            total_output_chars=data.get("total_output_chars", 0),
            window_start=data.get("window_start", ""),
            paused_at=data.get("paused_at", ""),
        )


# ---------------------------------------------------------------------------
# Phase parser — reads docs/phases/ to extract tasks
# ---------------------------------------------------------------------------

def parse_phase_tasks(phase: str) -> list[Task]:
    """Parse a phase doc and generate Claude Code tasks from milestone tables."""
    phase_map = {
        "2.4": ("PHASE-2-LEARNING-INTELLIGENCE.md", "2.4"),
        "2.5": ("PHASE-2-LEARNING-INTELLIGENCE.md", "2.5"),
        "3.1": ("PHASE-3-GROWTH.md", "3.1"),
        "3.2": ("PHASE-3-GROWTH.md", "3.2"),
        "3.3": ("PHASE-3-GROWTH.md", "3.3"),
        "3.4": ("PHASE-3-GROWTH.md", "3.4"),
        "3.5": ("PHASE-3-GROWTH.md", "3.5"),
    }

    if phase not in phase_map:
        log.error("Unknown phase: %s", phase)
        return []

    filename, milestone = phase_map[phase]
    doc_path = ROOT / "docs" / "phases" / filename
    if not doc_path.exists():
        log.error("Phase doc not found: %s", doc_path)
        return []

    content = doc_path.read_text(errors="replace")

    # Extract the milestone section
    milestone_section = _extract_milestone_section(content, milestone)
    if not milestone_section:
        log.warning("Milestone %s not found in %s", milestone, filename)
        return []

    # Parse task rows from tables in the section
    raw_tasks = _parse_task_table(milestone_section, milestone)

    # Convert to Task objects with proper prompts
    tasks: list[Task] = []
    for i, (title, scope, status) in enumerate(raw_tasks, 1):
        if status in ("✅", "✅ Done", "⏳"):
            continue  # skip done/deferred

        test_cmd = _infer_test_command(scope)
        prompt = _build_prompt(phase, title, scope, milestone_section)

        tasks.append(Task(
            id=i,
            title=title,
            scope=scope,
            prompt=prompt,
            test_command=test_cmd,
        ))

    # Set dependencies: frontend depends on backend tasks
    backend_ids = [t.id for t in tasks if t.scope.startswith("backend")]
    for t in tasks:
        if t.scope.startswith("frontend") and backend_ids:
            t.depends_on = backend_ids.copy()

    return tasks


def _extract_milestone_section(content: str, milestone: str) -> str:
    """Extract text between milestone heading and next milestone heading."""
    # Match patterns like "## Milestone 2.4" or "## 2.4 —" or "## Milestone 3.1"
    major, minor = milestone.split(".")
    patterns = [
        rf"##\s+Milestone\s+{re.escape(milestone)}\b",
        rf"##\s+{re.escape(milestone)}\s*[—–-]",
        rf"##\s+.*{re.escape(milestone)}.*",
    ]

    start = -1
    for pat in patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            start = m.start()
            break

    if start == -1:
        return ""

    # Find next ## heading
    next_heading = re.search(r"\n##\s+", content[start + 1:])
    if next_heading:
        end = start + 1 + next_heading.start()
    else:
        end = len(content)

    return content[start:end]


def _parse_task_table(section: str, milestone: str) -> list[tuple[str, str, str]]:
    """Extract (title, scope, status) from markdown tables in a section.

    Supports two table formats:
      Phase 2: | # | Task title | Status |         → scope inferred from title
      Phase 3: | # | Task title | Scope  | Status | → scope from explicit column
    """
    tasks: list[tuple[str, str, str]] = []

    # Match table rows: | number | title | rest... |
    rows = re.findall(r"\|\s*[\d.]+\s*\|\s*(.+?)\s*\|(.+)\|", section)

    for row_title, rest in rows:
        row_title = row_title.strip()
        # Skip header separator rows and section headers
        if row_title.startswith("---") or row_title.startswith("Задача"):
            continue
        cells = [c.strip() for c in rest.split("|")]
        status = cells[-1] if cells else "🔴"

        # Detect explicit scope column (Phase 3 format: | title | scope | status |)
        # Scope values match pattern "backend:xxx", "frontend:xxx", "infra", "docs"
        explicit_scope = None
        if len(cells) >= 2:
            candidate = cells[0]
            if re.match(r"^(backend|frontend|infra|docs)(:\w+)?$", candidate):
                explicit_scope = candidate

        scope = explicit_scope if explicit_scope else _infer_scope(row_title, milestone)
        tasks.append((row_title, scope, status))

    return tasks


def _infer_scope(title: str, milestone: str) -> str:
    """Infer task scope from title and milestone number."""
    title_lower = title.lower()

    # Frontend indicators
    fe_keywords = ["ui", "страниц", "компонент", "дашборд", "landing", "onboarding",
                   "responsive", "mobile", "seller app", "фронт", "next.js", "react"]
    for kw in fe_keywords:
        if kw in title_lower:
            if "seller" in title_lower:
                return "frontend:seller"
            return "frontend:buyer"

    # Infra indicators
    infra_keywords = ["docker", "ci/cd", "pipeline", "deploy", "k8s", "monitoring",
                      "nginx", "ssl", "cdn"]
    for kw in infra_keywords:
        if kw in title_lower:
            return "infra"

    # Docs indicators
    docs_keywords = ["документ", "readme", "seo", "structured data"]
    for kw in docs_keywords:
        if kw in title_lower:
            return "docs"

    # Backend service detection
    svc_keywords = {
        "identity": ["auth", "регистрац", "jwt", "пароль", "верификац", "пользовател"],
        "course": ["курс", "модул", "урок", "каталог", "категори", "curriculum"],
        "enrollment": ["запис", "enrollment", "прогресс", "completion"],
        "payment": ["оплат", "платёж", "платеж", "stripe", "подписк", "subscription"],
        "notification": ["уведомлен", "email", "notification", "письм"],
        "ai": ["ai", "gemini", "llm", "генерац", "quiz generate", "summary"],
        "learning": ["quiz", "flashcard", "xp", "streak", "badge", "leaderboard",
                     "gamif", "балл", "достижен", "очки", "ачивк", "геймиф",
                     "spaced repetition", "concept", "knowledge graph"],
    }
    for svc, keywords in svc_keywords.items():
        for kw in keywords:
            if kw in title_lower:
                return f"backend:{svc}"

    # Default by milestone
    phase_major = milestone.split(".")[0]
    if phase_major == "2":
        return "backend:learning"
    return "backend:course"


def _infer_test_command(scope: str) -> str | None:
    """Get the test command for a scope."""
    if scope.startswith("frontend:"):
        app = scope.split(":")[1]
        return TEST_COMMANDS.get(app, "cd apps/buyer && pnpm build")
    if scope.startswith("backend:"):
        svc = scope.split(":")[1]
        return TEST_COMMANDS.get(svc)
    return None


def _build_prompt(phase: str, title: str, scope: str, milestone_section: str) -> str:
    """Build a detailed Claude Code prompt for a task."""
    # Read CLAUDE.md rules excerpt for the prompt
    claude_md = ROOT / "CLAUDE.md"
    rules_excerpt = ""
    if claude_md.exists():
        rules_excerpt = (
            "Следуй правилам из CLAUDE.md: Clean Architecture, TDD (red→green→refactor), "
            "type hints, async, YAGNI. Коммит формат: <type>(<scope>): <description>."
        )

    test_note = ""
    test_cmd = _infer_test_command(scope)
    if test_cmd:
        test_note = f"\n\nПосле реализации проверь: `{test_cmd}` — все тесты должны быть зелёными."

    return f"""Задача из Phase {phase}, Milestone: {title}

КОНТЕКСТ MILESTONE:
{milestone_section[:1500]}

ЗАДАЧА: {title}
SCOPE: {scope}

ИНСТРУКЦИИ:
1. Изучи существующий код в проекте (структура описана в CLAUDE.md и STRUCTURE.md)
2. Следуй TDD: сначала напиши failing test, потом минимальную реализацию
3. Используй существующие паттерны (посмотри аналогичные сервисы/компоненты)
4. {rules_excerpt}
5. После реализации создай атомарный git commit

{test_note}

ВАЖНО:
- НЕ создавай файлы "на будущее" (YAGNI)
- НЕ рефактори код не связанный с задачей
- НЕ добавляй зависимости без необходимости
- Обнови документацию если затронуты: API endpoints, DB schemas, новые сервисы
"""


# ---------------------------------------------------------------------------
# Token budget tracker
# ---------------------------------------------------------------------------

class BudgetTracker:
    """Track output chars as proxy for token usage."""

    def __init__(self, state: OrchestratorState, limit: int = TOKEN_BUDGET_CHARS) -> None:
        self._state = state
        self._limit = limit
        if not state.window_start:
            state.window_start = _now()

    @property
    def used_chars(self) -> int:
        return self._state.total_output_chars

    @property
    def remaining_pct(self) -> float:
        if self._limit == 0:
            return 100.0
        return max(0.0, (1 - self.used_chars / self._limit) * 100)

    def add(self, chars: int) -> None:
        self._state.total_output_chars += chars

    def should_pause(self) -> bool:
        return self.remaining_pct < 30

    def reset_window(self) -> None:
        self._state.total_output_chars = 0
        self._state.window_start = _now()


# ---------------------------------------------------------------------------
# Claude Code executor
# ---------------------------------------------------------------------------

def run_claude_code(prompt: str, cwd: Path | None = None) -> tuple[int, str]:
    """Execute a task via Claude Code CLI."""
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
        output = result.stdout
        if result.stderr:
            output += "\n--- STDERR ---\n" + result.stderr
        log.info("Claude Code finished in %.0fs (exit=%d, %d chars)",
                 elapsed, result.returncode, len(output))
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
            timeout=300,
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Test command timed out after 300s"


def run_git_commit(task: Task) -> tuple[int, str]:
    """Create an atomic git commit for a completed task."""
    scope = task.scope.split(":")[-1] if ":" in task.scope else task.scope
    commit_type = "feat"
    msg = f"{commit_type}({scope}): {task.title.lower()}"

    # Stage all changes
    add_result = subprocess.run(
        ["git", "add", "-A"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if add_result.returncode != 0:
        return add_result.returncode, add_result.stderr

    # Check if there's anything to commit
    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(ROOT),
        capture_output=True,
    )
    if status.returncode == 0:
        return 0, "Nothing to commit"

    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Orchestration loop
# ---------------------------------------------------------------------------

def execute(state: OrchestratorState, dry_run: bool = False, budget_limit: int = TOKEN_BUDGET_CHARS) -> None:
    """Main loop: iterate phases → tasks, execute, test, commit."""
    budget = BudgetTracker(state, limit=budget_limit)

    # Find phases to process
    phases_to_run = [p for p in PHASE_ORDER if p in state.phases]
    if state.current_phase:
        # Skip completed phases
        try:
            start_idx = phases_to_run.index(state.current_phase)
            phases_to_run = phases_to_run[start_idx:]
        except ValueError:
            pass

    for phase in phases_to_run:
        tasks = state.phases[phase]
        state.current_phase = phase

        # Skip to current task if resuming
        start_task = state.current_task_idx if phase == phases_to_run[0] else 0

        print(f"\n{'#'*60}")
        print(f"  PHASE {phase} — {len(tasks)} tasks")
        print(f"  Budget remaining: {budget.remaining_pct:.0f}%")
        print(f"{'#'*60}")

        for i in range(start_task, len(tasks)):
            task = tasks[i]
            state.current_task_idx = i

            # --- Pre-checks ---
            if _should_stop():
                print("\n  STOP requested. Saving state...")
                state.paused_at = _now()
                state.save()
                _print_report(state)
                return

            if budget.should_pause():
                print(f"\n  BUDGET PAUSE — used {budget.used_chars:,} chars ({budget.remaining_pct:.0f}% left)")
                print(f"  Sleeping {BUDGET_PAUSE_HOURS}h. Resume with: ./run.sh --resume")
                state.paused_at = _now()
                state.save()
                _print_report(state)

                # Sleep and then reset budget window
                time.sleep(BUDGET_PAUSE_HOURS * 3600)
                budget.reset_window()
                print(f"\n  Waking up! Budget reset. Continuing...")

            if task.status == "passed":
                continue

            # Check dependencies
            deps_ok = True
            for dep_id in task.depends_on:
                dep = next((t for t in tasks if t.id == dep_id), None)
                if dep and dep.status != "passed":
                    log.warning("Task #%d blocked by #%d (%s)", task.id, dep_id, dep.status)
                    task.status = "skipped"
                    task.error = f"Blocked by #{dep_id}"
                    deps_ok = False
                    break
            if not deps_ok:
                continue

            # --- Execute task ---
            print(f"\n{'='*60}")
            print(f"  [{i+1}/{len(tasks)}] Phase {phase} / Task #{task.id}: {task.title}")
            print(f"  Scope: {task.scope} | Budget: {budget.remaining_pct:.0f}%")
            print(f"{'='*60}")

            if dry_run:
                print(f"\n  [DRY RUN] prompt ({len(task.prompt)} chars):")
                print(f"  {task.prompt[:300]}...")
                task.status = "passed"
                continue

            task.started_at = _now()

            for attempt in range(1, MAX_RETRIES + 1):
                task.attempts = attempt
                task.status = "running"
                state.save()

                print(f"\n  Attempt {attempt}/{MAX_RETRIES}...")

                # Run Claude Code
                exit_code, output = run_claude_code(task.prompt)
                task.output_chars = len(output)
                budget.add(len(output))

                # Save output to log file
                _save_task_log(phase, task, output)

                if exit_code != 0 and "TIMEOUT" in output:
                    print("  TIMEOUT — skipping")
                    task.status = "failed"
                    task.error = "Timeout"
                    break

                # Run tests
                test_ok = True
                if task.test_command:
                    print(f"  Testing: {task.test_command}")
                    test_exit, test_out = run_test_command(task.test_command)
                    test_ok = test_exit == 0
                    print(f"  Tests: {'PASSED' if test_ok else 'FAILED'}")
                    if not test_ok:
                        task.error = test_out[-500:]

                if exit_code == 0 and test_ok:
                    # Commit
                    commit_exit, commit_out = run_git_commit(task)
                    if commit_exit == 0:
                        print(f"  Committed: {commit_out.strip().splitlines()[-1] if commit_out.strip() else 'ok'}")
                    task.status = "passed"
                    task.finished_at = _now()
                    state.save()
                    break
                elif attempt < MAX_RETRIES:
                    # Retry with error context
                    print("  Retrying with error context...")
                    task.prompt += f"\n\nПРЕДЫДУЩАЯ ПОПЫТКА ПРОВАЛИЛАСЬ. Ошибка:\n{task.error[:500]}\nИсправь и убедись что тесты проходят."
                else:
                    print("  Max retries. Marking FAILED.")
                    task.status = "failed"
                    task.finished_at = _now()
                    state.save()

            # Progress report
            _print_phase_progress(phase, tasks)

        # Phase complete — move to next
        state.current_task_idx = 0

    # All done
    print(f"\n{'#'*60}")
    print("  ALL PHASES COMPLETE")
    print(f"{'#'*60}")
    _print_report(state)


# ---------------------------------------------------------------------------
# Logging & reports
# ---------------------------------------------------------------------------

def _save_task_log(phase: str, task: Task, output: str) -> None:
    """Save Claude Code output to a log file for debugging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"phase-{phase}-task-{task.id:03d}-attempt-{task.attempts}.log"
    path.write_text(
        f"Task: {task.title}\n"
        f"Scope: {task.scope}\n"
        f"Started: {task.started_at}\n"
        f"{'='*60}\n"
        f"{output}\n"
    )


def _print_phase_progress(phase: str, tasks: list[Task]) -> None:
    passed = sum(1 for t in tasks if t.status == "passed")
    failed = sum(1 for t in tasks if t.status == "failed")
    total = len(tasks)
    print(f"\n  Phase {phase}: {passed}/{total} passed, {failed} failed")


def _print_report(state: OrchestratorState) -> None:
    """Print full status report."""
    print(f"\n{'='*60}")
    print("  STATUS REPORT")
    print(f"{'='*60}")
    for phase, tasks in state.phases.items():
        passed = sum(1 for t in tasks if t.status == "passed")
        failed = sum(1 for t in tasks if t.status == "failed")
        total = len(tasks)
        icon = "✅" if passed == total else ("🔵" if passed > 0 else "⏳")
        print(f"\n  {icon} Phase {phase}: {passed}/{total} passed, {failed} failed")
        for t in tasks:
            t_icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️",
                      "running": "🔄", "pending": "⏳"}.get(t.status, "?")
            extra = f" ({t.attempts} attempts)" if t.attempts > 1 else ""
            err = f" — {t.error[:60]}" if t.error else ""
            print(f"    {t_icon} #{t.id} {t.title}{extra}{err}")

    total_tasks = sum(len(t) for t in state.phases.values())
    total_passed = sum(1 for t in _all_tasks(state) if t.status == "passed")
    print(f"\n  Total: {total_passed}/{total_tasks} tasks passed")
    print(f"  Output: ~{state.total_output_chars:,} chars (~{state.total_output_chars // 4:,} tokens)")
    print(f"{'='*60}\n")


def _all_tasks(state: OrchestratorState) -> list[Task]:
    result: list[Task] = []
    for tasks in state.phases.values():
        result.extend(tasks)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    _load_env()

    parser = argparse.ArgumentParser(
        description="EduPlatform Orchestrator — autonomous Claude Code executor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run.sh                     Run all remaining phases
  ./run.sh --phase 2.4         Run a specific phase
  ./run.sh --phase 2.4 --dry-run  Preview tasks without executing
  ./run.sh --resume            Resume after pause/crash
  ./run.sh --status            Show current status

Stop gracefully:
  Ctrl+C                       Saves state after current task
  touch tools/orchestrator/.stop   Same, but from another terminal
""",
    )
    parser.add_argument("--phase", help="Run a specific phase (e.g. 2.4, 3.1)")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, don't execute")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--budget", type=int, default=TOKEN_BUDGET_CHARS,
                        help=f"Token budget in chars (default: {TOKEN_BUDGET_CHARS:,})")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    budget_chars = args.budget

    # Status mode
    if args.status:
        state = OrchestratorState.load()
        if not state:
            print("  No saved state found.")
            return
        _print_report(state)
        return

    # Resume mode
    if args.resume:
        state = OrchestratorState.load()
        if not state:
            print("  No saved state to resume from.")
            return
        print(f"\n  Resuming from Phase {state.current_phase}, task #{state.current_task_idx + 1}")
        print(f"  Previously paused at: {state.paused_at}")
        execute(state, dry_run=args.dry_run, budget_limit=budget_chars)
        return

    # Normal mode: parse phases and build state
    print(f"\n  EduPlatform Orchestrator")
    print(f"  Root: {ROOT}")
    print(f"  Budget: {budget_chars:,} chars per {BUDGET_WINDOW_HOURS}h window\n")

    phases_to_parse = [args.phase] if args.phase else PHASE_ORDER
    all_phases: dict[str, list[Task]] = {}

    for phase in phases_to_parse:
        print(f"  Parsing Phase {phase}...")
        tasks = parse_phase_tasks(phase)
        if tasks:
            all_phases[phase] = tasks
            print(f"    {len(tasks)} tasks found:")
            for t in tasks:
                deps = f" (after: {t.depends_on})" if t.depends_on else ""
                print(f"      #{t.id} [{t.scope}] {t.title}{deps}")
        else:
            print(f"    No tasks found (all done or unparseable)")

    if not all_phases:
        print("\n  Nothing to do!")
        return

    total = sum(len(t) for t in all_phases.values())
    print(f"\n  Total: {total} tasks across {len(all_phases)} phases")

    if not args.dry_run:
        answer = input("\n  Start execution? [Y/n] ").strip().lower()
        if answer not in ("", "y", "yes"):
            print("  Aborted.")
            return

    state = OrchestratorState(phases=all_phases)
    execute(state, dry_run=args.dry_run, budget_limit=budget_chars)


if __name__ == "__main__":
    main()
