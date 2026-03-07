"""Orchestrator v2 — IMPLEMENT phase with parallel agent execution."""

from __future__ import annotations

import fcntl
import os
import queue
import signal
import subprocess
import threading
import time
from pathlib import Path

from agent_runner import (
    has_git_changes,
    is_shutdown,
    log,
    run_agent,
    run_git,
)
from config import (
    DESIGN_REVIEW_AGENTS,
    DISPATCH_INTERVAL,
    FRONTEND_SCOPES,
    MAX_RETRIES,
    ORCH_DIR,
    ROOT,
    SCOPE_AGENT_MAP,
    TDD_PREAMBLE,
    WORKTREE_DIR,
)
from state import SprintState, Task, _now

_state_lock = threading.Lock()
_merge_lock = threading.Lock()
_MERGE_LOCK_FILE = ORCH_DIR / ".merge.lock"

_SENTINEL = None  # poison pill


# ---------------------------------------------------------------------------
# Worktree management
# ---------------------------------------------------------------------------

def _create_worktree(task_id: str) -> Path:
    wt_path = WORKTREE_DIR / f"task-{task_id}"
    branch = f"orch/task-{task_id}"

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    # Remove stale
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
        raise RuntimeError(f"Worktree creation failed: {result.stderr}")
    return wt_path


def _merge_worktree(task_id: str) -> tuple[bool, str]:
    branch = f"orch/task-{task_id}"
    # Thread lock (intra-process) + file lock (inter-process)
    with _merge_lock:
        _MERGE_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = open(_MERGE_LOCK_FILE, "w")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)

            # Stash any uncommitted changes on main before merge
            stash_result = subprocess.run(
                ["git", "stash", "--include-untracked"],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            stashed = "No local changes" not in stash_result.stdout

            result = subprocess.run(
                ["git", "merge", "--no-ff", "-m", f"merge: task {task_id}", branch],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=str(ROOT), capture_output=True,
                )
                if stashed:
                    subprocess.run(
                        ["git", "stash", "pop"],
                        cwd=str(ROOT), capture_output=True,
                    )
                return False, result.stderr + result.stdout

            # Restore stashed changes after successful merge
            if stashed:
                subprocess.run(
                    ["git", "stash", "pop"],
                    cwd=str(ROOT), capture_output=True,
                )
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
    return True, ""


def _cleanup_worktree(task_id: str) -> None:
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


def prune_worktrees() -> None:
    subprocess.run(["git", "worktree", "prune"], cwd=str(ROOT), capture_output=True)
    if WORKTREE_DIR.exists():
        for entry in WORKTREE_DIR.iterdir():
            if entry.is_dir() and entry.name.startswith("task-"):
                log(f"  Removing stale worktree: {entry.name}")
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(entry)],
                    cwd=str(ROOT), capture_output=True,
                )
                tid = entry.name.removeprefix("task-")
                subprocess.run(
                    ["git", "branch", "-D", f"orch/task-{tid}"],
                    cwd=str(ROOT), capture_output=True,
                )


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def _resolve_agent(scope: str) -> str:
    base_scope = scope.split(":")[0]
    agent = SCOPE_AGENT_MAP.get(base_scope)
    if not agent:
        log(f"  ! Unknown scope '{scope}', falling back to backend-engineer")
        return "backend-engineer"
    return agent


def _is_frontend_scope(scope: str) -> bool:
    base_scope = scope.split(":")[0]
    return base_scope in FRONTEND_SCOPES


def _build_design_review_prompt(task: Task) -> str:
    return (
        f"You are reviewing frontend code just written for task: {task.title}\n\n"
        f"Original requirement: {task.prompt[:1000]}\n\n"
        "Review the code in this worktree and IMPROVE it:\n"
        "- Fix any design system violations (colors, spacing, typography)\n"
        "- Add missing states (loading skeleton, empty, error, partial)\n"
        "- Add micro-interactions (hover, press, mount animations via Framer Motion)\n"
        "- Ensure keyboard accessibility and focus management\n"
        "- Apply Dark Knowledge theme: dark-first, violet accent #7c5cfc, Inter font\n"
        "- Follow Linear/Vercel/Stripe quality standard\n\n"
        "Make direct edits to the files. Do NOT create new files unless absolutely needed.\n"
        "Do NOT rewrite from scratch — refine what exists.\n"
        "Run `cd apps/buyer && pnpm build` to verify your changes compile."
    )


def _build_implement_prompt(task: Task, design_context: str) -> str:
    parts = [task.prompt]
    if design_context:
        parts.append(f"\n\n## Design context from tech-lead:\n{design_context[:2000]}")
    parts.append(TDD_PREAMBLE)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Single task execution in worktree
# ---------------------------------------------------------------------------

def _commit_in_worktree(task: Task, wt_path: Path) -> tuple[int, str]:
    if not wt_path.exists():
        return 1, f"Worktree missing: {wt_path}"

    scope = task.scope.split(":")[-1] if ":" in task.scope else task.scope
    commit_type = task.type or "feat"
    msg = f"{commit_type}({scope}): {task.title.lower()}"

    subprocess.run(["git", "add", "-A"], cwd=str(wt_path), capture_output=True)
    check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(wt_path), capture_output=True,
    )
    if check.returncode == 0:
        return 0, "Nothing to commit"

    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=str(wt_path), capture_output=True, text=True,
    )
    return result.returncode, result.stdout + result.stderr


def _execute_task(task: Task, state: SprintState, design_context: str) -> None:
    tid = task.id
    agent_name = _resolve_agent(task.scope)

    # Create worktree
    log(f"Creating worktree...", tid)
    try:
        wt_path = _create_worktree(tid)
    except RuntimeError as e:
        log(f"X Worktree failed: {e}", tid)
        task.status = "failed"
        task.error = str(e)
        task.finished_at = _now()
        with _state_lock:
            state.save()
        return

    log(f"Worktree ready, agent: {agent_name}", tid)
    task.started_at = _now()

    prompt = _build_implement_prompt(task, design_context)

    for attempt in range(1, MAX_RETRIES + 1):
        task.attempts = attempt
        task.status = "running"
        with _state_lock:
            state.save()

        log(f"Attempt {attempt}/{MAX_RETRIES} (agent: {agent_name})...", tid)

        exit_code, output = run_agent(agent_name, prompt, cwd=wt_path, task_id=tid)

        if is_shutdown():
            with _state_lock:
                state.paused_at = _now()
                state.save()
            return

        # Timeout
        if exit_code != 0 and "TIMEOUT" in output:
            log("X TIMEOUT", tid)
            task.status = "failed"
            task.error = "Timeout"
            break

        # No changes (guard: worktree may vanish)
        if not wt_path.exists() or not has_git_changes(wt_path):
            log("X NO CODE CHANGES", tid)
            task.error = "No code changes"
            if attempt < MAX_RETRIES:
                log("Retrying with stronger prompt...", tid)
                prompt += (
                    "\n\nPREVIOUS ATTEMPT PRODUCED NO CODE CHANGES."
                    "\nYou MUST write code. Do not ask questions. Just implement."
                )
                continue
            task.status = "failed"
            task.finished_at = _now()
            with _state_lock:
                state.save()
            break

        # --- Design review pass for frontend tasks ---
        if _is_frontend_scope(task.scope) and agent_name not in DESIGN_REVIEW_AGENTS:
            review_prompt = _build_design_review_prompt(task)
            for designer in DESIGN_REVIEW_AGENTS:
                if is_shutdown():
                    break
                log(f"Design review: {designer}...", tid)
                d_exit, d_output = run_agent(designer, review_prompt, cwd=wt_path, task_id=tid)
                if d_exit != 0:
                    log(f"  ! {designer} exited {d_exit} (non-fatal)", tid)
                else:
                    log(f"  V {designer} done", tid)

        # Guard: worktree may have been removed externally
        if not wt_path.exists():
            log("X Worktree disappeared (external cleanup?)", tid)
            task.status = "failed"
            task.error = "Worktree removed during execution"
            task.finished_at = _now()
            with _state_lock:
                state.save()
            return

        # Commit any uncommitted changes (agent may have already committed)
        _commit_in_worktree(task, wt_path)

        # Merge back
        log("Merging to main...", tid)
        ok, err = _merge_worktree(tid)
        if ok:
            log("V Merged", tid)
            _cleanup_worktree(tid)
            task.status = "passed"
            task.finished_at = _now()
            with _state_lock:
                state.save()
            return
        else:
            log(f"X Merge conflict: {err[:200]}", tid)
            if attempt < MAX_RETRIES:
                log("Retrying after merge conflict...", tid)
                _cleanup_worktree(tid)
                try:
                    wt_path = _create_worktree(tid)
                except RuntimeError as e:
                    log(f"X Worktree recreation failed: {e}", tid)
                    task.status = "failed"
                    task.error = str(e)
                    task.finished_at = _now()
                    with _state_lock:
                        state.save()
                    return
                prompt += f"\n\nPREVIOUS ATTEMPT HAD MERGE CONFLICT:\n{err[:500]}\nFix conflicts."
                continue
            task.status = "failed"
            task.error = f"Merge conflict: {err[:200]}"
            task.finished_at = _now()
            with _state_lock:
                state.save()
            return

    # Fallthrough: failed
    if task.status != "passed":
        _cleanup_worktree(tid)
        task.status = "failed"
        task.finished_at = _now()
        with _state_lock:
            state.save()


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

def _worker(
    task_queue: queue.Queue,
    state: SprintState,
    design_context: str,
) -> None:
    while True:
        item = task_queue.get()
        if item is _SENTINEL:
            task_queue.task_done()
            break

        task: Task = item
        if is_shutdown():
            task_queue.task_done()
            break

        log(f">> Task {task.id}: {task.title} [scope: {task.scope}]", task.id)
        _execute_task(task, state, design_context)
        task_queue.task_done()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_implement(state: SprintState) -> bool:
    """Phase 3: IMPLEMENT — parallel agents execute tasks in worktrees."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 3: IMPLEMENT")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "IMPLEMENT"
    state.save()

    tasks = state.tasks
    total = len(tasks)
    task_map = {t.id: t for t in tasks}
    design_context = state.design_output

    # Determine worker count from independent tasks
    independent = [t for t in tasks if not t.depends_on]
    workers = min(len(independent), 4) if independent else 1
    log(f"  {total} tasks, {workers} workers")

    prune_worktrees()

    task_queue: queue.Queue = queue.Queue()
    enqueued: set[str] = set()

    # Start workers
    threads: list[threading.Thread] = []
    for i in range(workers):
        t = threading.Thread(
            target=_worker,
            args=(task_queue, state, design_context),
            daemon=True,
            name=f"worker-{i}",
        )
        t.start()
        threads.append(t)

    # Dispatcher
    try:
        while True:
            if is_shutdown():
                log("\n  STOP requested.")
                with _state_lock:
                    state.paused_at = _now()
                    state.save()
                break

            dispatched = False
            with _state_lock:
                for task in tasks:
                    if task.id in enqueued or task.status != "pending":
                        continue
                    deps_ok = all(
                        task_map[d].status == "passed"
                        for d in task.depends_on if d in task_map
                    )
                    deps_failed = any(
                        task_map[d].status in ("failed", "skipped")
                        for d in task.depends_on if d in task_map
                    )
                    if deps_failed:
                        task.status = "skipped"
                        task.error = f"Dependency failed: {task.depends_on}"
                        state.save()
                        continue
                    if deps_ok:
                        enqueued.add(task.id)
                        task_queue.put(task)
                        dispatched = True

            # Check completion
            all_done = all(
                t.status in ("passed", "failed", "skipped") for t in tasks
            )
            if all_done:
                break

            if not dispatched:
                time.sleep(DISPATCH_INTERVAL)

    finally:
        # Poison pills
        for _ in threads:
            task_queue.put(_SENTINEL)
        for t in threads:
            t.join(timeout=10)

    passed = sum(1 for t in tasks if t.status == "passed")
    failed = sum(1 for t in tasks if t.status == "failed")
    skipped = sum(1 for t in tasks if t.status == "skipped")
    log(f"\n  IMPLEMENT results: {passed} passed, {failed} failed, {skipped} skipped")

    return failed == 0 and skipped == 0
