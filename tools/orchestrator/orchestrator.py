"""
EduPlatform Orchestrator v2 — Claude Code task runner.

Reads YAML task files, executes via Claude Code CLI, runs tests, commits.
Graceful shutdown on SIGINT/SIGTERM/SIGHUP (terminal close).

Usage:
    ./run.sh tasks/phase-2.5.yaml              # run a task file
    ./run.sh tasks/phase-2.5.yaml --dry-run    # preview tasks
    ./run.sh --resume                          # continue from saved state
    ./run.sh --status                          # show progress
    ./run.sh --reset                           # clear state

Stop gracefully:
    Ctrl+C                                     # saves state after current task
    Close terminal                             # SIGHUP kills children, saves state
    touch tools/orchestrator/.stop             # from another terminal
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Force unbuffered stdout
if not sys.stdout.line_buffering:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
ORCH_DIR = ROOT / "tools" / "orchestrator"
STATE_DIR = ORCH_DIR / ".state"
LOG_DIR = ORCH_DIR / ".logs"
PID_FILE = ORCH_DIR / ".pid"
STOP_FILE = ORCH_DIR / ".stop"

MAX_RETRIES = 2
CLAUDE_TIMEOUT = 900  # 15 min per task
TEST_TIMEOUT = 300    # 5 min per test

# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

_child_proc: subprocess.Popen | None = None
_shutdown_requested = False


def _handle_signal(signum: int, _frame: object) -> None:
    """Handle SIGINT/SIGTERM/SIGHUP — request graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    name = signal.Signals(signum).name
    _p(f"\n  [{name}] Shutdown requested. Finishing current task...")


for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    try:
        signal.signal(sig, _handle_signal)
    except OSError:
        pass  # SIGHUP not available on Windows


def _kill_child() -> None:
    """Kill the child claude process if still running."""
    global _child_proc
    if _child_proc is None or _child_proc.poll() is not None:
        return
    _p("  Killing child process...")
    try:
        pgid = os.getpgid(_child_proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        _child_proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
        try:
            _child_proc.kill()
        except (ProcessLookupError, OSError):
            pass


def _cleanup() -> None:
    """atexit handler: kill child, remove PID file."""
    _kill_child()
    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except OSError:
            pass


atexit.register(_cleanup)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(msg: str) -> None:
    """Print with flush."""
    print(msg, flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _should_stop() -> bool:
    if _shutdown_requested:
        return True
    if STOP_FILE.exists():
        STOP_FILE.unlink()
        return True
    return False


def _has_git_changes() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if not os.environ.get(key.strip()):
            os.environ[key.strip()] = value.strip()


# ---------------------------------------------------------------------------
# YAML task loader
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: str
    title: str
    scope: str
    prompt: str
    test: str | None = None
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | passed | failed | skipped
    attempts: int = 0
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


@dataclass
class TaskFile:
    phase: str
    description: str
    tasks: list[Task]

    @classmethod
    def load(cls, path: Path) -> TaskFile:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        tasks = []
        for t in data.get("tasks", []):
            tasks.append(Task(
                id=str(t["id"]),
                title=t["title"],
                scope=t.get("scope", ""),
                prompt=t["prompt"],
                test=t.get("test"),
                depends_on=[str(d) for d in t.get("depends_on", [])],
            ))
        return cls(
            phase=str(data.get("phase", "")),
            description=data.get("description", ""),
            tasks=tasks,
        )


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

@dataclass
class State:
    source_file: str = ""
    phase: str = ""
    tasks: list[Task] = field(default_factory=list)
    paused_at: str = ""

    def save(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = STATE_DIR / "state.json"
        data = {
            "source_file": self.source_file,
            "phase": self.phase,
            "paused_at": self.paused_at,
            "tasks": [
                {
                    "id": t.id, "title": t.title, "scope": t.scope,
                    "prompt": t.prompt, "test": t.test,
                    "depends_on": t.depends_on, "status": t.status,
                    "attempts": t.attempts, "started_at": t.started_at,
                    "finished_at": t.finished_at, "error": t.error,
                }
                for t in self.tasks
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls) -> State | None:
        path = STATE_DIR / "state.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        tasks = [Task(**t) for t in data.get("tasks", [])]
        return cls(
            source_file=data.get("source_file", ""),
            phase=data.get("phase", ""),
            tasks=tasks,
            paused_at=data.get("paused_at", ""),
        )

    def recover_crashed(self) -> None:
        for t in self.tasks:
            if t.status == "running":
                _p(f"  Recovering crashed task: {t.id} ({t.title})")
                t.status = "pending"
                t.error = ""


# ---------------------------------------------------------------------------
# Subprocess execution
# ---------------------------------------------------------------------------

def _stream_process(
    cmd: list[str] | str,
    cwd: str,
    timeout: int,
    *,
    shell: bool = False,
    prefix: str = "  | ",
) -> tuple[int, str]:
    """Run subprocess with real-time streaming. Returns (exit_code, output)."""
    global _child_proc
    collected: list[str] = []
    start = time.time()

    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, shell=shell, bufsize=1,
            start_new_session=True,  # own process group for clean kill
        )
        _child_proc = proc

        assert proc.stdout is not None
        for line in proc.stdout:
            collected.append(line)
            display = line.rstrip("\n")[:200]
            print(f"{prefix}{display}", flush=True)

            if _shutdown_requested:
                _kill_child()
                break

        proc.wait(timeout=timeout)
        elapsed = time.time() - start
        output = "".join(collected)
        print(f"{prefix}--- Done in {elapsed:.0f}s (exit={proc.returncode}) ---", flush=True)
        _child_proc = None
        return proc.returncode, output

    except subprocess.TimeoutExpired:
        _kill_child()
        output = "".join(collected)
        _child_proc = None
        return 1, output + f"\nTIMEOUT after {timeout}s"

    except FileNotFoundError:
        _child_proc = None
        return 1, f"Command not found: {cmd[0] if isinstance(cmd, list) else cmd}"


def run_claude(prompt: str) -> tuple[int, str]:
    """Execute task via Claude Code CLI."""
    cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]
    _p("  +-- Claude Code starting...")
    code, output = _stream_process(cmd, str(ROOT), CLAUDE_TIMEOUT, prefix="  |  ")
    _p(f"  +-- Claude Code done (exit={code})")
    return code, output


def run_tests(command: str) -> tuple[int, str]:
    """Run test/build verification."""
    _p(f"  +-- Tests: {command}")
    code, output = _stream_process(command, str(ROOT), TEST_TIMEOUT, shell=True, prefix="  |  ")
    status = "PASSED" if code == 0 else "FAILED"
    _p(f"  +-- Tests {status}")
    return code, output


def run_commit(task: Task) -> tuple[int, str]:
    """Stage all changes and commit."""
    scope = task.scope.split(":")[-1] if ":" in task.scope else task.scope
    msg = f"feat({scope}): {task.title.lower()}"

    subprocess.run(["git", "add", "-A"], cwd=str(ROOT), capture_output=True)

    # Check if anything to commit
    check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(ROOT), capture_output=True)
    if check.returncode == 0:
        return 0, "Nothing to commit"

    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Task execution loop
# ---------------------------------------------------------------------------

def _save_log(task: Task, attempt: int, output: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{task.id}-attempt-{attempt}.log"
    path.write_text(
        f"Task: {task.title}\nScope: {task.scope}\nStarted: {task.started_at}\n"
        f"{'=' * 60}\n{output}\n"
    )


def execute(state: State, dry_run: bool = False) -> None:
    """Main execution loop with multi-pass dependency resolution."""
    tasks = state.tasks
    total = len(tasks)
    task_map = {t.id: t for t in tasks}

    _p(f"\n{'#' * 60}")
    _p(f"  Phase {state.phase} — {total} tasks")
    _p(f"{'#' * 60}")

    max_passes = total + 1
    for pass_num in range(1, max_passes + 1):
        made_progress = False

        for task in tasks:
            # --- Pre-checks ---
            if _should_stop():
                _p("\n  STOP requested. Saving state...")
                state.paused_at = _now()
                state.save()
                _print_report(state)
                return

            if task.status in ("passed", "failed", "skipped"):
                continue

            # Check dependencies
            deps_ok = all(
                task_map[dep].status == "passed"
                for dep in task.depends_on
                if dep in task_map
            )
            if not deps_ok:
                if pass_num == 1:
                    _p(f"  ... Task {task.id} deferred (waiting for deps)")
                continue

            # --- Execute ---
            made_progress = True
            _p(f"\n{'=' * 60}")
            _p(f"  >> [{pass_num}] Task {task.id}: {task.title}")
            _p(f"     Scope: {task.scope}")
            _p(f"{'=' * 60}")

            if dry_run:
                _p(f"  [DRY RUN] prompt ({len(task.prompt)} chars)")
                _p(f"  {task.prompt[:300]}...")
                task.status = "passed"
                continue

            task.started_at = _now()

            for attempt in range(1, MAX_RETRIES + 1):
                task.attempts = attempt
                task.status = "running"
                state.save()

                _p(f"\n  Attempt {attempt}/{MAX_RETRIES}...")

                exit_code, output = run_claude(task.prompt)
                _save_log(task, attempt, output)

                if _shutdown_requested:
                    state.paused_at = _now()
                    state.save()
                    _print_report(state)
                    return

                # Timeout
                if exit_code != 0 and "TIMEOUT" in output:
                    _p("  X TIMEOUT")
                    task.status = "failed"
                    task.error = "Timeout"
                    break

                # No changes produced
                if not _has_git_changes():
                    _p("  X NO CODE CHANGES")
                    task.error = "No code changes produced"
                    if attempt < MAX_RETRIES:
                        _p("  Retrying with stronger prompt...")
                        task.prompt += (
                            "\n\nPREVIOUS ATTEMPT PRODUCED NO CODE CHANGES."
                            "\nYou MUST write code. Do not ask questions. Just implement."
                        )
                        continue
                    task.status = "failed"
                    task.finished_at = _now()
                    state.save()
                    break

                # Run tests
                test_ok = True
                if task.test:
                    test_code, test_out = run_tests(task.test)
                    test_ok = test_code == 0
                    if not test_ok:
                        task.error = test_out[-500:]

                if exit_code == 0 and test_ok:
                    commit_code, commit_out = run_commit(task)
                    if commit_code == 0:
                        last_line = commit_out.strip().splitlines()[-1] if commit_out.strip() else "ok"
                        _p(f"  V Committed: {last_line}")
                    task.status = "passed"
                    task.finished_at = _now()
                    state.save()
                    break
                elif attempt < MAX_RETRIES:
                    _p("  Retrying with error context...")
                    task.prompt += (
                        f"\n\nPREVIOUS ATTEMPT FAILED. Error:\n{task.error[:500]}"
                        "\nFix it and make sure tests pass."
                    )
                else:
                    _p("  X Max retries. FAILED.")
                    task.status = "failed"
                    task.finished_at = _now()
                    state.save()

        # Progress check
        passed = sum(1 for t in tasks if t.status == "passed")
        failed = sum(1 for t in tasks if t.status == "failed")
        _p(f"\n  Progress: {passed}/{total} passed, {failed} failed")

        if not made_progress:
            pending = [t for t in tasks if t.status == "pending"]
            if pending:
                _p(f"\n  WARNING: {len(pending)} tasks permanently blocked")
                for t in pending:
                    t.status = "skipped"
                    t.error = f"Dependencies never resolved: {t.depends_on}"
            break

    _p(f"\n{'#' * 60}")
    _p("  EXECUTION COMPLETE")
    _p(f"{'#' * 60}")
    _print_report(state)


def _print_report(state: State) -> None:
    _p(f"\n{'=' * 60}")
    _p(f"  STATUS REPORT — Phase {state.phase}")
    _p(f"{'=' * 60}")
    for t in state.tasks:
        icons = {"passed": "V", "failed": "X", "skipped": ">>",
                 "running": "~", "pending": ".."}
        icon = icons.get(t.status, "?")
        extra = f" ({t.attempts} attempts)" if t.attempts > 1 else ""
        err = f" -- {t.error[:60]}" if t.error else ""
        _p(f"  [{icon}] {t.id} [{t.scope}] {t.title}{extra}{err}")
    passed = sum(1 for t in state.tasks if t.status == "passed")
    _p(f"\n  Total: {passed}/{len(state.tasks)} passed")
    _p(f"{'=' * 60}\n")


# ---------------------------------------------------------------------------
# Multi-file mode: run multiple YAML files sequentially
# ---------------------------------------------------------------------------

def execute_files(paths: list[Path], dry_run: bool = False) -> None:
    """Load and execute multiple YAML task files in order."""
    for path in paths:
        _p(f"\n  Loading: {path.name}")
        tf = TaskFile.load(path)
        _p(f"  Phase {tf.phase}: {tf.description} ({len(tf.tasks)} tasks)")
        for t in tf.tasks:
            deps = f" (after: {t.depends_on})" if t.depends_on else ""
            _p(f"    {t.id} [{t.scope}] {t.title}{deps}")

        state = State(
            source_file=str(path),
            phase=tf.phase,
            tasks=tf.tasks,
        )
        execute(state, dry_run=dry_run)

        # Stop if shutdown requested
        if _shutdown_requested:
            return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    _load_env()

    # Write PID file
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    parser = argparse.ArgumentParser(
        description="EduPlatform Orchestrator v2 — Claude Code task runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./run.sh tasks/phase-2.5.yaml              Run a task file
  ./run.sh tasks/phase-*.yaml                Run multiple files
  ./run.sh tasks/phase-2.5.yaml --dry-run    Preview tasks
  ./run.sh --resume                          Resume from saved state
  ./run.sh --status                          Show progress
  ./run.sh --reset                           Clear state
  ./run.sh --is-running                      Check if running

Stop:
  Ctrl+C                         Saves state after current task
  Close terminal                 SIGHUP kills children, saves state
  touch tools/orchestrator/.stop Same, from another terminal
""",
    )
    parser.add_argument("files", nargs="*", help="YAML task file(s) to execute")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    parser.add_argument("--dry-run", action="store_true", help="Preview, don't execute")
    parser.add_argument("--status", action="store_true", help="Show progress and exit")
    parser.add_argument("--reset", action="store_true", help="Clear saved state")
    parser.add_argument("--is-running", action="store_true", help="Check if orchestrator is running")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    # --is-running
    if args.is_running:
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                _p(f"  Orchestrator is running (PID {pid})")
                sys.exit(0)
            except OSError:
                _p("  Not running (stale PID file)")
                PID_FILE.unlink()
                sys.exit(1)
        else:
            _p("  Not running")
            sys.exit(1)

    # --reset
    if args.reset:
        state_path = STATE_DIR / "state.json"
        if state_path.exists():
            state_path.unlink()
            _p("  State cleared.")
        else:
            _p("  No state to clear.")
        return

    # --status
    if args.status:
        state = State.load()
        if not state:
            _p("  No saved state.")
            return
        _print_report(state)
        return

    # --resume
    if args.resume:
        state = State.load()
        if not state:
            _p("  No saved state to resume from.")
            return
        state.recover_crashed()
        _p(f"\n  Resuming Phase {state.phase}")
        if state.paused_at:
            _p(f"  Paused at: {state.paused_at}")
        execute(state, dry_run=args.dry_run)
        return

    # Normal: run task files
    if not args.files:
        parser.print_help()
        _p("\n  ERROR: Provide YAML task file(s) or use --resume")
        sys.exit(1)

    paths = []
    for f in args.files:
        p = Path(f)
        if not p.is_absolute():
            p = ORCH_DIR / f
        if not p.exists():
            _p(f"  ERROR: File not found: {p}")
            sys.exit(1)
        paths.append(p)

    # Sort by filename for consistent order
    paths.sort(key=lambda p: p.name)

    _p(f"\n  EduPlatform Orchestrator v2")
    _p(f"  Root: {ROOT}")
    _p(f"  Files: {len(paths)}\n")

    # Preview
    total_tasks = 0
    for path in paths:
        tf = TaskFile.load(path)
        _p(f"  {path.name}: Phase {tf.phase} — {len(tf.tasks)} tasks")
        for t in tf.tasks:
            deps = f" (after: {t.depends_on})" if t.depends_on else ""
            _p(f"    {t.id} [{t.scope}] {t.title}{deps}")
        total_tasks += len(tf.tasks)

    _p(f"\n  Total: {total_tasks} tasks across {len(paths)} files")

    if not args.dry_run and not args.yes:
        answer = input("\n  Start execution? [Y/n] ").strip().lower()
        if answer not in ("", "y", "yes"):
            _p("  Aborted.")
            return

    execute_files(paths, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
