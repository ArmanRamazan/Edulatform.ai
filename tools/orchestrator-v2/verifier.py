"""Orchestrator v2 — TEST and REVIEW phases."""

from __future__ import annotations

from agent_runner import log, run_agent, run_tests
from config import QA_ENGINEER, SECURITY_ENGINEER, TECH_LEAD
from state import SprintState, Task


# ---------------------------------------------------------------------------
# Phase 4: TEST
# ---------------------------------------------------------------------------

def _build_test_prompt(state: SprintState) -> str:
    tasks_info = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope}, test: {t.test or 'none'})"
        for t in state.tasks if t.status == "passed"
    )
    return (
        f"You are the QA engineer verifying sprint changes.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Implemented tasks:\n{tasks_info}\n\n"
        f"## Your job:\n"
        f"1. Run tests for EVERY service that was modified:\n"
        f"   - Python: cd services/py/<name> && uv run --package <name> pytest tests/ -v\n"
        f"   - Rust: cd services/rs/<name> && cargo test && cargo clippy -- -D warnings\n"
        f"   - Frontend: cd apps/<name> && pnpm build\n"
        f"2. Report results for each service\n"
        f"3. If tests fail, report EXACTLY which tests failed and why\n\n"
        f"Run the actual test commands. Do NOT just read test files.\n"
        f"Output format:\n"
        f"```\n"
        f"TEST RESULTS:\n"
        f"  [service-name]: PASS (N tests) | FAIL (details)\n"
        f"```"
    )


def run_test_phase(state: SprintState) -> tuple[bool, str]:
    """Phase 4: TEST — qa-engineer runs all affected test suites."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 4: TEST")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "TEST"
    state.save()

    # Run per-task test commands first (fast, specific)
    all_passed = True
    for task in state.tasks:
        if task.status != "passed" or not task.test:
            continue
        log(f"  Running test for [{task.id}]...")
        code, output = run_tests(task.test, task_id=task.id)
        if code != 0:
            all_passed = False
            log(f"  X Test failed for [{task.id}]")

    if not all_passed:
        log("  X Some per-task tests failed")
        return False, "Per-task test failures"

    # Run qa-engineer for broader verification
    prompt = _build_test_prompt(state)
    code, output = run_agent(QA_ENGINEER, prompt, task_id="qa")
    if code != 0:
        log(f"  X QA agent failed (exit={code})")
        return False, output[-500:]

    # Check if QA agent reported failures
    output_lower = output.lower()
    if "fail" in output_lower and "pass" not in output_lower.split("fail")[-1][:50]:
        log("  X QA agent reported test failures")
        return False, output[-500:]

    log("  V TEST complete — all tests passed")
    return True, output


# ---------------------------------------------------------------------------
# Phase 5: REVIEW
# ---------------------------------------------------------------------------

def _build_security_prompt(state: SprintState) -> str:
    tasks_info = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope})"
        for t in state.tasks if t.status == "passed"
    )
    return (
        f"You are the security engineer auditing sprint changes.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Implemented tasks:\n{tasks_info}\n\n"
        f"## Your job:\n"
        f"1. Check for SQL injection (string formatting in queries)\n"
        f"2. Check for auth bypass (missing JWT validation)\n"
        f"3. Check for IDOR (missing ownership checks)\n"
        f"4. Check for hardcoded secrets\n"
        f"5. Check for PII in logs\n"
        f"6. Check for input validation gaps\n\n"
        f"Read the CHANGED files (git diff HEAD~N) and audit them.\n"
        f"Do NOT write code. Report findings.\n\n"
        f"Output format:\n"
        f"```\n"
        f"SECURITY AUDIT:\n"
        f"  CRITICAL: [list or 'none']\n"
        f"  HIGH: [list or 'none']\n"
        f"  MEDIUM: [list or 'none']\n"
        f"  VERDICT: PASS | FAIL\n"
        f"```"
    )


def _build_review_prompt(state: SprintState) -> str:
    tasks_info = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope})"
        for t in state.tasks if t.status == "passed"
    )
    return (
        f"You are the tech lead reviewing sprint code.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Implemented tasks:\n{tasks_info}\n\n"
        f"## Your job:\n"
        f"1. Read changed files (git diff HEAD~N)\n"
        f"2. Check Clean Architecture compliance (dependency direction)\n"
        f"3. Check YAGNI (no unused code, no 'future' abstractions)\n"
        f"4. Check code quality (type hints, error handling, naming)\n"
        f"5. Check test quality (not tautologies, testing behavior)\n\n"
        f"Do NOT write code. Report findings.\n\n"
        f"Output format:\n"
        f"```\n"
        f"CODE REVIEW:\n"
        f"  BLOCKING: [list or 'none']\n"
        f"  SUGGESTIONS: [list or 'none']\n"
        f"  VERDICT: APPROVE | REQUEST_CHANGES\n"
        f"```"
    )


def run_review_phase(state: SprintState) -> tuple[bool, str]:
    """Phase 5: REVIEW — security audit + tech-lead code review."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 5: REVIEW")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "REVIEW"
    state.save()

    results: list[str] = []

    # Security audit
    log("  Running security audit...")
    sec_prompt = _build_security_prompt(state)
    sec_code, sec_output = run_agent(SECURITY_ENGINEER, sec_prompt, task_id="security")

    if sec_code != 0:
        log(f"  X Security agent failed (exit={sec_code})")
        return False, "Security agent failed"

    results.append(f"SECURITY:\n{sec_output[-1000:]}")

    # Check for critical/high findings
    sec_lower = sec_output.lower()
    has_critical = "critical:" in sec_lower and "none" not in sec_lower.split("critical:")[1][:50]
    if has_critical:
        log("  X CRITICAL security findings — failing review")
        return False, sec_output[-500:]

    # Tech lead review
    log("  Running code review...")
    rev_prompt = _build_review_prompt(state)
    rev_code, rev_output = run_agent(TECH_LEAD, rev_prompt, task_id="review")

    if rev_code != 0:
        log(f"  X Review agent failed (exit={rev_code})")
        return False, "Review agent failed"

    results.append(f"CODE REVIEW:\n{rev_output[-1000:]}")

    # Check for blocking issues
    rev_lower = rev_output.lower()
    has_blocking = "request_changes" in rev_lower
    if has_blocking:
        log("  X Code review: REQUEST_CHANGES")
        state.review_output = "\n\n".join(results)
        state.save()
        return False, rev_output[-500:]

    state.review_output = "\n\n".join(results)
    state.save()
    log("  V REVIEW complete — approved")
    return True, state.review_output
