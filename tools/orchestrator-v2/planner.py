"""Orchestrator v2 — PLANNING and DESIGN phases."""

from __future__ import annotations

from agent_runner import log, run_agent
from config import PRODUCT_ANALYST, TECH_LEAD
from state import SprintState, Task


def _build_planning_prompt(state: SprintState) -> str:
    task_summary = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope}, depends_on: {t.depends_on})"
        for t in state.tasks
    )
    return (
        f"You are the tech lead analyzing a sprint for the KnowledgeOS platform.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Tasks:\n{task_summary}\n\n"
        f"## Your job:\n"
        f"1. Analyze task dependencies — are they correct? Any missing?\n"
        f"2. Identify which tasks can run in parallel vs sequential\n"
        f"3. Flag any risks or cross-service concerns\n"
        f"4. Produce an execution plan as structured output:\n\n"
        f"```\n"
        f"EXECUTION PLAN:\n"
        f"Wave 1 (parallel): [task-ids]\n"
        f"Wave 2 (parallel): [task-ids]\n"
        f"...\n"
        f"RISKS: [list any concerns]\n"
        f"CROSS-SERVICE: [list any API contracts needed between tasks]\n"
        f"```\n\n"
        f"Do NOT write any code. Only analyze and produce the plan."
    )


def _build_analyst_prompt(state: SprintState) -> str:
    task_summary = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope})"
        for t in state.tasks
    )
    return (
        f"You are the product analyst providing context for sprint planning.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Tasks:\n{task_summary}\n\n"
        f"## Your job:\n"
        f"1. For each task, note which metrics it might affect (DAU, engagement, etc.)\n"
        f"2. Flag any tasks that touch high-risk areas (payments, auth, data)\n"
        f"3. Suggest monitoring priorities after deployment\n\n"
        f"Output a brief analysis (max 500 words). Do NOT write any code."
    )


def _build_design_prompt(state: SprintState, planning_output: str) -> str:
    task_details = "\n\n".join(
        f"### [{t.id}] {t.title}\nScope: {t.scope}\nPrompt: {t.prompt[:500]}..."
        for t in state.tasks
    )
    return (
        f"You are the tech lead designing contracts for cross-service tasks.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Planning analysis:\n{planning_output[:2000]}\n\n"
        f"## Task details:\n{task_details}\n\n"
        f"## Your job:\n"
        f"1. For tasks that touch multiple services, define API contracts between them\n"
        f"2. For tasks that add new endpoints, specify request/response schemas\n"
        f"3. For tasks that modify DB, specify migration requirements\n"
        f"4. Output structured design context that implementation agents can use\n\n"
        f"Format:\n"
        f"```\n"
        f"DESIGN FOR [task-id]:\n"
        f"  Contracts: [API endpoints, request/response if applicable]\n"
        f"  DB changes: [tables, columns if applicable]\n"
        f"  Dependencies: [other services/libs this touches]\n"
        f"```\n\n"
        f"Do NOT write implementation code. Only define contracts and interfaces."
    )


def run_planning(state: SprintState) -> bool:
    """Phase 1: PLANNING — tech-lead + product-analyst analyze the sprint."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 1: PLANNING")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "PLANNING"
    state.save()

    # Tech lead: execution plan
    prompt = _build_planning_prompt(state)
    code, output = run_agent(TECH_LEAD, prompt, task_id="planning")
    if code != 0:
        log(f"  X PLANNING failed (tech-lead exit={code})")
        return False

    state.planning_output = output
    state.save()

    # Product analyst: metrics context (non-blocking — failure doesn't stop sprint)
    analyst_prompt = _build_analyst_prompt(state)
    a_code, a_output = run_agent(PRODUCT_ANALYST, analyst_prompt, task_id="analyst")
    if a_code == 0:
        state.planning_output += f"\n\n--- ANALYST CONTEXT ---\n{a_output}"
        state.save()
    else:
        log("  ! Product analyst failed (non-critical, continuing)")

    log("  V PLANNING complete")
    return True


def run_design(state: SprintState) -> bool:
    """Phase 2: DESIGN — tech-lead generates contracts for cross-service tasks."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 2: DESIGN")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "DESIGN"
    state.save()

    # Check if any tasks are cross-service
    scopes = {t.scope.split(":")[0] for t in state.tasks}
    if len(scopes) <= 1:
        log("  Single-scope sprint — skipping design phase")
        state.design_output = "Single-scope sprint, no cross-service contracts needed."
        state.save()
        return True

    prompt = _build_design_prompt(state, state.planning_output)
    code, output = run_agent(TECH_LEAD, prompt, task_id="design")
    if code != 0:
        log(f"  X DESIGN failed (exit={code})")
        return False

    state.design_output = output
    state.save()
    log("  V DESIGN complete")
    return True
