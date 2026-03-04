"""
EduPlatform Orchestrator v2 — Claude Code task runner.

Reads YAML task files, executes via Claude Code CLI, runs tests, commits.
Graceful shutdown on SIGINT/SIGTERM/SIGHUP (terminal close).

Usage:
    ./run.sh tasks/phase-2.5.yaml              # run a task file
    ./run.sh tasks/phase-2.5.yaml --dry-run    # preview tasks
    ./run.sh tasks/phase-2.5.yaml --workers 3  # parallel mode (3 workers)
    ./run.sh tasks/phase-2.5.yaml --multi-agent  # multi-agent mode (wave-based)
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
import queue
import signal
import subprocess
import sys
import threading
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
WORKTREE_DIR = ROOT / ".claude" / "worktrees"

MAX_RETRIES = 2
CLAUDE_TIMEOUT = 900  # 15 min per task
TEST_TIMEOUT = 300    # 5 min per test
DISPATCH_INTERVAL = 2  # seconds between queue scans

# Quota retry config
QUOTA_RETRY_INTERVAL = 1800  # 30 min between retries
QUOTA_MAX_RETRIES = 12       # 12 retries = 6 hours max wait
_QUOTA_PATTERNS = [
    "rate limit", "rate_limit", "ratelimit",
    "too many request", "429",
    "overloaded", "over capacity",
    "quota exceeded", "quota limit",
    "request limit", "usage limit",
    "capacity", "throttl",
]

# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

_child_procs: dict[str, subprocess.Popen] = {}
_child_procs_lock = threading.Lock()
_shutdown_requested = False

# Locks for parallel mode
_state_lock = threading.Lock()
_merge_lock = threading.Lock()
_print_lock = threading.Lock()


def _handle_signal(signum: int, _frame: object) -> None:
    """Handle SIGINT/SIGTERM/SIGHUP — request graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    name = signal.Signals(signum).name
    _p(f"\n  [{name}] Shutdown requested. Finishing current tasks...")


for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    try:
        signal.signal(sig, _handle_signal)
    except OSError:
        pass  # SIGHUP not available on Windows


def _kill_child(task_id: str | None = None) -> None:
    """Kill a child process by task_id, or all if None."""
    with _child_procs_lock:
        if task_id is not None:
            proc = _child_procs.get(task_id)
            if proc is None or proc.poll() is not None:
                _child_procs.pop(task_id, None)
                return
            targets = [(task_id, proc)]
        else:
            targets = [(tid, p) for tid, p in _child_procs.items()
                        if p.poll() is None]

    for tid, proc in targets:
        _p(f"  Killing child process (task {tid})...")
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass
        with _child_procs_lock:
            _child_procs.pop(tid, None)


def _cleanup() -> None:
    """atexit handler: kill all children, remove PID file."""
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

def _p(msg: str, task_id: str | None = None) -> None:
    """Print with flush. Thread-safe with optional [task_id] prefix."""
    if task_id:
        msg = f"  [{task_id}] {msg.lstrip()}"
    with _print_lock:
        print(msg, flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _should_stop() -> bool:
    if _shutdown_requested:
        return True
    if STOP_FILE.exists():
        try:
            STOP_FILE.unlink()
        except OSError:
            pass
        return True
    return False


def _has_git_changes(cwd: Path | None = None) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(cwd or ROOT), capture_output=True, text=True,
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


def _is_quota_error(exit_code: int, output: str) -> bool:
    """Detect API quota/rate limit errors in Claude CLI output."""
    if exit_code == 0:
        return False
    output_lower = output.lower()
    return any(p in output_lower for p in _QUOTA_PATTERNS)


def _wait_for_quota(attempt: int) -> bool:
    """Wait for quota reset. Returns False if shutdown requested (Ctrl+C)."""
    minutes = QUOTA_RETRY_INTERVAL // 60
    next_try = time.strftime("%H:%M", time.localtime(time.time() + QUOTA_RETRY_INTERVAL))
    _p(f"\n  {'!' * 50}")
    _p(f"  QUOTA LIMIT HIT — waiting {minutes} min (attempt {attempt}/{QUOTA_MAX_RETRIES})")
    _p(f"  Next retry at {next_try}. Press Ctrl+C to abort.")
    _p(f"  {'!' * 50}\n")

    # Wait in small increments so Ctrl+C is responsive
    elapsed = 0
    while elapsed < QUOTA_RETRY_INTERVAL:
        if _should_stop():
            _p("  Quota wait interrupted by shutdown signal.")
            return False
        time.sleep(10)
        elapsed += 10
        remaining = (QUOTA_RETRY_INTERVAL - elapsed) // 60
        if elapsed % 300 == 0 and remaining > 0:  # log every 5 min
            _p(f"  ... {remaining} min remaining until retry")

    _p(f"  Quota wait done. Retrying...")
    return True


# ---------------------------------------------------------------------------
# YAML task loader
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: str
    title: str
    scope: str
    prompt: str
    type: str = "feat"  # feat | fix | refactor | test | docs | chore | perf
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
                type=t.get("type", "feat"),
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
                    "prompt": t.prompt, "type": t.type, "test": t.test,
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
    task_id: str | None = None,
) -> tuple[int, str]:
    """Run subprocess with real-time streaming. Returns (exit_code, output)."""
    collected: list[str] = []
    start = time.time()

    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, shell=shell, bufsize=1,
            start_new_session=True,  # own process group for clean kill
        )
        proc_key = task_id or "_default"
        with _child_procs_lock:
            _child_procs[proc_key] = proc

        assert proc.stdout is not None
        for line in proc.stdout:
            collected.append(line)
            display = line.rstrip("\n")[:200]
            with _print_lock:
                print(f"{prefix}{display}", flush=True)

            if _shutdown_requested:
                _kill_child(proc_key)
                break

        proc.wait(timeout=timeout)
        elapsed = time.time() - start
        output = "".join(collected)
        with _print_lock:
            print(f"{prefix}--- Done in {elapsed:.0f}s (exit={proc.returncode}) ---", flush=True)
        with _child_procs_lock:
            _child_procs.pop(proc_key, None)
        return proc.returncode, output

    except subprocess.TimeoutExpired:
        proc_key = task_id or "_default"
        _kill_child(proc_key)
        output = "".join(collected)
        return 1, output + f"\nTIMEOUT after {timeout}s"

    except FileNotFoundError:
        proc_key = task_id or "_default"
        with _child_procs_lock:
            _child_procs.pop(proc_key, None)
        return 1, f"Command not found: {cmd[0] if isinstance(cmd, list) else cmd}"


_TDD_PREAMBLE = (
    "\n\nIMPORTANT — CLAUDE.md RULES YOU MUST FOLLOW:\n"
    "1. TDD is mandatory for backend code: write failing tests FIRST, then implement, then refactor.\n"
    "2. All tests must pass before you finish. Run the test command to verify.\n"
    "3. Update documentation files affected by your changes "
    "(see CLAUDE.md 'Closing session' checklist: README.md, STRUCTURE.md, "
    "docs/architecture/*.md, docs/phases/PHASE-*.md as applicable).\n"
    "4. Do NOT add Co-Authored-By or any auto-generated signatures to commits.\n"
    "5. Do NOT create files 'for the future' — only what is needed now (YAGNI).\n"
)


def _augment_prompt(prompt: str, scope: str) -> str:
    """Prepend CLAUDE.md enforcement rules to the task prompt."""
    return prompt + _TDD_PREAMBLE


def run_claude(
    prompt: str,
    cwd: Path | None = None,
    task_id: str | None = None,
    timeout: int | None = None,
) -> tuple[int, str]:
    """Execute task via Claude Code CLI. Auto-retries on quota limits."""
    work_dir = str(cwd or ROOT)
    cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]

    for quota_attempt in range(1, QUOTA_MAX_RETRIES + 1):
        _p("  +-- Claude Code starting...", task_id)
        prefix = f"  [{task_id}] |  " if task_id else "  |  "
        code, output = _stream_process(cmd, work_dir, timeout or CLAUDE_TIMEOUT, prefix=prefix, task_id=task_id)
        _p(f"  +-- Claude Code done (exit={code})", task_id)

        if not _is_quota_error(code, output):
            return code, output

        # Quota hit — wait and retry
        _p(f"  +-- QUOTA ERROR detected in output", task_id)
        if quota_attempt >= QUOTA_MAX_RETRIES:
            _p(f"  +-- Max quota retries ({QUOTA_MAX_RETRIES}) exhausted. Giving up.", task_id)
            return code, output

        if not _wait_for_quota(quota_attempt):
            # Shutdown requested during wait
            return code, output

    return code, output  # unreachable, but satisfies type checker


def run_tests(command: str, cwd: Path | None = None, task_id: str | None = None) -> tuple[int, str]:
    """Run test/build verification."""
    work_dir = str(cwd or ROOT)
    _p(f"  +-- Tests: {command}", task_id)
    prefix = f"  [{task_id}] |  " if task_id else "  |  "
    code, output = _stream_process(command, work_dir, TEST_TIMEOUT, shell=True, prefix=prefix, task_id=task_id)
    status = "PASSED" if code == 0 else "FAILED"
    _p(f"  +-- Tests {status}", task_id)
    return code, output


def run_commit(task: Task, cwd: Path | None = None) -> tuple[int, str]:
    """Stage all changes and commit."""
    work_dir = str(cwd or ROOT)
    scope = task.scope.split(":")[-1] if ":" in task.scope else task.scope
    commit_type = task.type if task.type else "feat"
    msg = f"{commit_type}({scope}): {task.title.lower()}"

    subprocess.run(["git", "add", "-A"], cwd=work_dir, capture_output=True)

    # Check if anything to commit
    check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work_dir, capture_output=True)
    if check.returncode == 0:
        return 0, "Nothing to commit"

    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=work_dir, capture_output=True, text=True,
    )
    return result.returncode, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Git worktree management
# ---------------------------------------------------------------------------

def _create_worktree(task_id: str) -> Path:
    """Create a git worktree for a task. Returns the worktree path."""
    wt_path = WORKTREE_DIR / f"task-{task_id}"
    branch = f"orch/task-{task_id}"

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale worktree if exists
    if wt_path.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=str(ROOT), capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "-D", branch],
            cwd=str(ROOT), capture_output=True,
        )

    result = subprocess.run(
        ["git", "worktree", "add", str(wt_path), "-b", branch, "HEAD"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create worktree: {result.stderr}")

    return wt_path


def _merge_worktree(task_id: str) -> tuple[bool, str]:
    """Merge worktree branch into main. Returns (success, error_message)."""
    branch = f"orch/task-{task_id}"

    with _merge_lock:
        result = subprocess.run(
            ["git", "merge", "--no-ff", "-m", f"merge: task {task_id}", branch],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        if result.returncode != 0:
            # Conflict — abort
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=str(ROOT), capture_output=True,
            )
            return False, result.stderr + result.stdout

    return True, ""


def _cleanup_worktree(task_id: str) -> None:
    """Remove worktree and delete branch."""
    wt_path = WORKTREE_DIR / f"task-{task_id}"
    branch = f"orch/task-{task_id}"

    subprocess.run(
        ["git", "worktree", "remove", "--force", str(wt_path)],
        cwd=str(ROOT), capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-D", branch],
        cwd=str(ROOT), capture_output=True,
    )


def _prune_worktrees() -> None:
    """Cleanup stale worktrees on startup."""
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=str(ROOT), capture_output=True,
    )
    # Clean up leftover worktree directories
    if WORKTREE_DIR.exists():
        for entry in WORKTREE_DIR.iterdir():
            if entry.is_dir() and entry.name.startswith("task-"):
                _p(f"  Removing stale worktree: {entry.name}")
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(entry)],
                    cwd=str(ROOT), capture_output=True,
                )
                task_id = entry.name.removeprefix("task-")
                subprocess.run(
                    ["git", "branch", "-D", f"orch/task-{task_id}"],
                    cwd=str(ROOT), capture_output=True,
                )


# ---------------------------------------------------------------------------
# Task execution — sequential (workers=1)
# ---------------------------------------------------------------------------

def _save_log(task: Task, attempt: int, output: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{task.id}-attempt-{attempt}.log"
    path.write_text(
        f"Task: {task.title}\nScope: {task.scope}\nStarted: {task.started_at}\n"
        f"{'=' * 60}\n{output}\n"
    )


def execute(state: State, dry_run: bool = False) -> None:
    """Main execution loop with multi-pass dependency resolution (sequential)."""
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

                augmented = _augment_prompt(task.prompt, task.scope)
                exit_code, output = run_claude(augmented)
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


# ---------------------------------------------------------------------------
# Task execution — parallel (workers > 1)
# ---------------------------------------------------------------------------

_SENTINEL = None  # poison pill for worker threads


def _execute_task_in_worktree(task: Task, state: State, task_map: dict[str, Task]) -> None:
    """Execute a single task inside a git worktree, then merge back."""
    tid = task.id

    # Create worktree
    _p(f"Creating worktree...", tid)
    try:
        wt_path = _create_worktree(tid)
    except RuntimeError as e:
        _p(f"X Worktree creation failed: {e}", tid)
        task.status = "failed"
        task.error = f"Worktree creation failed: {e}"
        task.finished_at = _now()
        with _state_lock:
            state.save()
        return

    _p(f"Worktree ready: {wt_path}", tid)
    task.started_at = _now()

    for attempt in range(1, MAX_RETRIES + 1):
        task.attempts = attempt
        task.status = "running"
        with _state_lock:
            state.save()

        _p(f"Attempt {attempt}/{MAX_RETRIES}...", tid)

        augmented = _augment_prompt(task.prompt, task.scope)
        exit_code, output = run_claude(augmented, cwd=wt_path, task_id=tid)
        _save_log(task, attempt, output)

        if _shutdown_requested:
            with _state_lock:
                state.paused_at = _now()
                state.save()
            return

        # Timeout
        if exit_code != 0 and "TIMEOUT" in output:
            _p("X TIMEOUT", tid)
            task.status = "failed"
            task.error = "Timeout"
            break

        # No changes produced
        if not _has_git_changes(wt_path):
            _p("X NO CODE CHANGES", tid)
            task.error = "No code changes produced"
            if attempt < MAX_RETRIES:
                _p("Retrying with stronger prompt...", tid)
                task.prompt += (
                    "\n\nPREVIOUS ATTEMPT PRODUCED NO CODE CHANGES."
                    "\nYou MUST write code. Do not ask questions. Just implement."
                )
                continue
            task.status = "failed"
            task.finished_at = _now()
            with _state_lock:
                state.save()
            break

        # Run tests
        test_ok = True
        if task.test:
            test_code, test_out = run_tests(task.test, cwd=wt_path, task_id=tid)
            test_ok = test_code == 0
            if not test_ok:
                task.error = test_out[-500:]

        if exit_code == 0 and test_ok:
            # Commit in worktree
            commit_code, commit_out = run_commit(task, cwd=wt_path)
            if commit_code == 0:
                last_line = commit_out.strip().splitlines()[-1] if commit_out.strip() else "ok"
                _p(f"V Committed: {last_line}", tid)

            # Merge back to main
            _p("Merging to main...", tid)
            ok, err = _merge_worktree(tid)
            if ok:
                _p("V Merged successfully", tid)
                _cleanup_worktree(tid)
                task.status = "passed"
                task.finished_at = _now()
                with _state_lock:
                    state.save()
                return
            else:
                _p(f"X Merge conflict: {err[:200]}", tid)
                task.status = "failed"
                task.error = f"Merge conflict: {err[:200]}"
                task.finished_at = _now()
                _p(f"Worktree preserved at {wt_path}", tid)
                with _state_lock:
                    state.save()
                return

        elif attempt < MAX_RETRIES:
            _p("Retrying with error context...", tid)
            task.prompt += (
                f"\n\nPREVIOUS ATTEMPT FAILED. Error:\n{task.error[:500]}"
                "\nFix it and make sure tests pass."
            )
        else:
            _p("X Max retries. FAILED.", tid)
            task.status = "failed"
            task.finished_at = _now()
            with _state_lock:
                state.save()

    # If we got here via break (timeout/no changes), still save
    if task.status == "failed":
        _cleanup_worktree(tid)
        with _state_lock:
            state.save()


def _worker_loop(
    task_queue: queue.Queue,
    state: State,
    task_map: dict[str, Task],
    dry_run: bool = False,
) -> None:
    """Worker thread: pull tasks from queue, execute in worktrees."""
    while True:
        item = task_queue.get()
        if item is _SENTINEL:
            task_queue.task_done()
            break

        task: Task = item

        if _should_stop():
            task_queue.task_done()
            break

        tid = task.id
        _p(f">> Task {tid}: {task.title} [scope: {task.scope}]", tid)

        if dry_run:
            _p(f"[DRY RUN] prompt ({len(task.prompt)} chars)", tid)
            _p(f"{task.prompt[:300]}...", tid)
            task.status = "passed"
            with _state_lock:
                state.save()
            task_queue.task_done()
            continue

        _execute_task_in_worktree(task, state, task_map)
        task_queue.task_done()


def execute_parallel(state: State, workers: int, dry_run: bool = False) -> None:
    """Parallel execution: dispatch ready tasks to worker threads via worktrees."""
    tasks = state.tasks
    total = len(tasks)
    task_map = {t.id: t for t in tasks}

    _p(f"\n{'#' * 60}")
    _p(f"  Phase {state.phase} — {total} tasks — {workers} workers (parallel)")
    _p(f"{'#' * 60}")

    task_queue: queue.Queue = queue.Queue()
    enqueued: set[str] = set()

    # Start worker threads
    threads: list[threading.Thread] = []
    for i in range(workers):
        t = threading.Thread(
            target=_worker_loop,
            args=(task_queue, state, task_map, dry_run),
            daemon=True,
            name=f"worker-{i}",
        )
        t.start()
        threads.append(t)

    # Dispatcher loop
    try:
        idle_cycles = 0
        while True:
            if _should_stop():
                _p("\n  STOP requested. Saving state...")
                with _state_lock:
                    state.paused_at = _now()
                    state.save()
                break

            dispatched_this_cycle = False

            # Find ready tasks
            with _state_lock:
                for task in tasks:
                    if task.id in enqueued:
                        continue
                    if task.status != "pending":
                        continue
                    # Check deps resolved
                    deps_ok = all(
                        task_map[dep].status == "passed"
                        for dep in task.depends_on
                        if dep in task_map
                    )
                    # Check no dep failed (would block forever)
                    deps_failed = any(
                        task_map[dep].status in ("failed", "skipped")
                        for dep in task.depends_on
                        if dep in task_map
                    )
                    if deps_failed:
                        task.status = "skipped"
                        task.error = f"Dependency failed: {task.depends_on}"
                        state.save()
                        continue
                    if deps_ok:
                        enqueued.add(task.id)
                        task_queue.put(task)
                        dispatched_this_cycle = True
                        _p(f"  Dispatched task {task.id}: {task.title}")

            # Check completion
            with _state_lock:
                pending = sum(1 for t in tasks if t.status == "pending" and t.id not in enqueued)
                running = sum(1 for t in tasks if t.status == "running")
                queued = task_queue.qsize()

            all_terminal = all(t.status in ("passed", "failed", "skipped") for t in tasks)
            if all_terminal:
                break

            if pending == 0 and running == 0 and queued == 0:
                if dispatched_this_cycle:
                    # Just dispatched, give workers time to pick up
                    idle_cycles = 0
                else:
                    idle_cycles += 1

                # Wait a few cycles before declaring deadlock (workers may still be finishing)
                if idle_cycles >= 3:
                    with _state_lock:
                        non_terminal = [t for t in tasks if t.status == "pending"]
                        if non_terminal:
                            _p(f"\n  WARNING: {len(non_terminal)} tasks permanently blocked")
                            for t in non_terminal:
                                t.status = "skipped"
                                t.error = f"Dependencies never resolved: {t.depends_on}"
                            state.save()
                    break
            else:
                idle_cycles = 0

            time.sleep(DISPATCH_INTERVAL)

    finally:
        # Send sentinel to each worker
        for _ in threads:
            task_queue.put(_SENTINEL)

        # Wait for workers to finish (with timeout)
        for t in threads:
            t.join(timeout=30)

    # Final report
    with _state_lock:
        state.save()

    _p(f"\n{'#' * 60}")
    _p("  EXECUTION COMPLETE")
    _p(f"{'#' * 60}")
    _print_report(state)


# ---------------------------------------------------------------------------
# Task execution — multi-agent (Claude dispatches parallel agents per wave)
# ---------------------------------------------------------------------------

MAX_WAVE_TIMEOUT = 3600  # 1 hour cap per wave


def _topological_waves(tasks: list[Task], task_map: dict[str, Task]) -> list[list[Task]]:
    """Group tasks into waves by dependency depth.

    Wave 0: tasks with no deps (or all deps already passed/outside this run).
    Wave N: tasks whose deps are all in waves < N.
    """
    assigned: dict[str, int] = {}  # task_id -> wave number
    waves: list[list[Task]] = []

    # Pre-mark tasks already done
    for t in tasks:
        if t.status in ("passed", "failed", "skipped"):
            assigned[t.id] = -1  # sentinel: already terminal

    max_passes = len(tasks) + 1
    for _ in range(max_passes):
        made_progress = False
        for t in tasks:
            if t.id in assigned:
                continue
            # All deps must be assigned already
            dep_waves: list[int] = []
            all_resolved = True
            for dep_id in t.depends_on:
                if dep_id not in task_map:
                    continue  # external dep, ignore
                if dep_id in assigned:
                    dep_waves.append(assigned[dep_id])
                else:
                    all_resolved = False
                    break
            if not all_resolved:
                continue
            wave_num = max(dep_waves, default=-1) + 1
            assigned[t.id] = wave_num
            made_progress = True
        if not made_progress:
            break

    # Build wave lists (skip terminal tasks)
    wave_nums = sorted(set(w for w in assigned.values() if w >= 0))
    for wn in wave_nums:
        wave = [t for t in tasks if assigned.get(t.id) == wn]
        if wave:
            waves.append(wave)

    # Unassigned tasks (circular deps) go into a final wave
    unassigned = [t for t in tasks if t.id not in assigned]
    if unassigned:
        waves.append(unassigned)

    return waves


def _build_multi_agent_prompt(wave: list[Task]) -> str:
    """Build a single prompt for a wave of tasks using Agent tool dispatch."""
    # Single task — no multi-agent overhead
    if len(wave) == 1:
        return _augment_prompt(wave[0].prompt, wave[0].scope)

    parts: list[str] = []
    parts.append(
        f"You are an orchestrator. Execute these {len(wave)} tasks IN PARALLEL "
        f"using the Agent tool.\n\n"
        f"For EACH task below, launch an Agent with:\n"
        f'- subagent_type: "general-purpose"\n'
        f'- isolation: "worktree"\n'
        f"- The task prompt (provided below) as the agent's prompt\n\n"
        f"Launch ALL agents in a SINGLE message (parallel execution). "
        f"Do NOT run them sequentially.\n\n"
        f"After all agents finish, for each successful agent:\n"
        f"1. Check that the agent reported success\n"
        f"2. If the worktree has changes, they will be on the returned branch\n\n"
        f"IMPORTANT: Do NOT modify any code yourself. Only dispatch agents.\n"
    )

    for i, task in enumerate(wave, 1):
        scope_short = task.scope.split(":")[-1] if ":" in task.scope else task.scope
        commit_msg = f"{task.type}({scope_short}): {task.title.lower()}"
        augmented = _augment_prompt(task.prompt, task.scope)

        parts.append(f"\n{'=' * 40}")
        parts.append(f"== TASK {i}: {task.id} ==")
        parts.append(f"{'=' * 40}")
        parts.append(f"Title: {task.title}")
        parts.append(f"Scope: {task.scope}")
        if task.test:
            parts.append(f"Test command: {task.test}")
        parts.append(f"Commit message: {commit_msg}")
        parts.append(f"\n{augmented}")

    return "\n".join(parts)


def _verify_wave_results(wave: list[Task], state: State) -> None:
    """After Claude finishes a wave, independently verify each task's tests."""
    for task in wave:
        if task.status in ("passed", "failed", "skipped"):
            continue

        _p(f"\n  Verifying task {task.id}: {task.title}")

        # Check if there were git changes (committed by the agent)
        # We verify by running the test command on the current state
        if task.test:
            test_code, test_out = run_tests(task.test)
            if test_code == 0:
                _p(f"  V Task {task.id}: tests PASSED")
                task.status = "passed"
                task.finished_at = _now()
            else:
                _p(f"  X Task {task.id}: tests FAILED")
                task.status = "failed"
                task.error = test_out[-500:]
                task.finished_at = _now()
        else:
            # No test command — mark passed if Claude succeeded
            _p(f"  V Task {task.id}: no test command, marking passed")
            task.status = "passed"
            task.finished_at = _now()

        with _state_lock:
            state.save()


def execute_multi_agent(state: State, dry_run: bool = False) -> None:
    """Multi-agent execution: Claude dispatches parallel agents per wave."""
    tasks = state.tasks
    total = len(tasks)
    task_map = {t.id: t for t in tasks}

    waves = _topological_waves(tasks, task_map)

    _p(f"\n{'#' * 60}")
    _p(f"  Phase {state.phase} — {total} tasks — {len(waves)} waves (multi-agent)")
    _p(f"{'#' * 60}")

    for wave_idx, wave in enumerate(waves):
        # Filter out already-terminal tasks
        active = [t for t in wave if t.status not in ("passed", "failed", "skipped")]
        if not active:
            continue

        if _should_stop():
            _p("\n  STOP requested. Saving state...")
            state.paused_at = _now()
            state.save()
            _print_report(state)
            return

        # Check deps — skip wave if any dep failed
        skip_wave = False
        for task in active:
            deps_failed = any(
                task_map[dep].status in ("failed", "skipped")
                for dep in task.depends_on
                if dep in task_map
            )
            if deps_failed:
                task.status = "skipped"
                task.error = f"Dependency failed: {task.depends_on}"
                with _state_lock:
                    state.save()

        active = [t for t in active if t.status == "pending"]
        if not active:
            continue

        _p(f"\n{'=' * 60}")
        _p(f"  Wave {wave_idx + 1}/{len(waves)}: {len(active)} tasks")
        for t in active:
            _p(f"    {t.id} [{t.scope}] {t.title}")
        _p(f"{'=' * 60}")

        if dry_run:
            prompt = _build_multi_agent_prompt(active)
            _p(f"  [DRY RUN] prompt ({len(prompt)} chars)")
            _p(f"  {prompt[:500]}...")
            for t in active:
                t.status = "passed"
            state.save()
            continue

        # Mark all as running
        for t in active:
            t.started_at = _now()
            t.status = "running"
            t.attempts += 1
        state.save()

        # Build and run the multi-agent prompt
        prompt = _build_multi_agent_prompt(active)
        wave_timeout = min(CLAUDE_TIMEOUT * len(active), MAX_WAVE_TIMEOUT)

        exit_code, output = run_claude(prompt, timeout=wave_timeout)
        _save_log(active[0], active[0].attempts, output)  # log under first task

        if _shutdown_requested:
            state.paused_at = _now()
            state.save()
            _print_report(state)
            return

        if exit_code != 0 and "TIMEOUT" in output:
            _p("  X WAVE TIMEOUT")
            for t in active:
                t.status = "failed"
                t.error = "Wave timeout"
                t.finished_at = _now()
            state.save()
            continue

        # Verify results independently
        _verify_wave_results(active, state)

        # Progress update
        passed = sum(1 for t in tasks if t.status == "passed")
        failed = sum(1 for t in tasks if t.status == "failed")
        _p(f"\n  Progress: {passed}/{total} passed, {failed} failed")

    _p(f"\n{'#' * 60}")
    _p("  EXECUTION COMPLETE")
    _p(f"{'#' * 60}")
    _print_report(state)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

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

def execute_files(
    paths: list[Path],
    dry_run: bool = False,
    workers: int = 1,
    multi_agent: bool = False,
) -> None:
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

        if multi_agent:
            execute_multi_agent(state, dry_run=dry_run)
        elif workers > 1:
            execute_parallel(state, workers=workers, dry_run=dry_run)
        else:
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
  ./run.sh tasks/phase-2.5.yaml --workers 3  Parallel mode (3 workers)
  ./run.sh tasks/phase-2.5.yaml --multi-agent  Multi-agent mode (wave-based)
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
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default: 1 = sequential)")
    parser.add_argument("--multi-agent", action="store_true", help="Multi-agent mode: Claude dispatches parallel agents per wave")
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

    # Startup cleanup: prune stale worktrees
    if args.workers > 1 or args.multi_agent:
        _prune_worktrees()

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
        if args.multi_agent:
            execute_multi_agent(state, dry_run=args.dry_run)
        elif args.workers > 1:
            execute_parallel(state, workers=args.workers, dry_run=args.dry_run)
        else:
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

    if args.multi_agent:
        mode = "multi-agent (wave-based)"
    elif args.workers > 1:
        mode = f"{args.workers} workers (parallel)"
    else:
        mode = "sequential"
    _p(f"\n  EduPlatform Orchestrator v2")
    _p(f"  Root: {ROOT}")
    _p(f"  Mode: {mode}")
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

    execute_files(paths, dry_run=args.dry_run, workers=args.workers, multi_agent=args.multi_agent)


if __name__ == "__main__":
    main()
