"""Orchestrator v2 — configuration."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
ORCH_DIR = ROOT / "tools" / "orchestrator-v2"
STATE_DIR = ORCH_DIR / ".state"
LOG_DIR = ORCH_DIR / ".logs"
PID_FILE = ORCH_DIR / ".pid"
STOP_FILE = ORCH_DIR / ".stop"
WORKTREE_DIR = ROOT / ".claude" / "worktrees"
AGENTS_DIR = ROOT / ".claude" / "agents"

# ---------------------------------------------------------------------------
# Timeouts & limits
# ---------------------------------------------------------------------------

CLAUDE_TIMEOUT = 900        # 15 min per agent invocation
TEST_TIMEOUT = 600          # 10 min per test run (WSL2 pnpm build is slow)
MAX_RETRIES = 3             # max retry per phase failure
DISPATCH_INTERVAL = 2       # seconds between queue scans

# Quota retry
QUOTA_RETRY_INTERVAL = 1800  # 30 min
QUOTA_MAX_RETRIES = 12       # 12 × 30 min = 6h max

QUOTA_PATTERNS = [
    "rate limit", "rate_limit", "ratelimit",
    "too many request", "429",
    "overloaded", "over capacity",
    "quota exceeded", "quota limit",
    "request limit", "usage limit",
    "capacity", "throttl",
]

# ---------------------------------------------------------------------------
# Scope → Agent mapping
# ---------------------------------------------------------------------------

SCOPE_AGENT_MAP: dict[str, str] = {
    "backend":     "backend-engineer",
    "frontend":    "frontend-engineer",
    "core":        "core-engineer",
    "ai":          "ml-engineer",
    "ml":          "ml-engineer",
    "infra":       "devops-engineer",
    "devops":      "devops-engineer",
    "ui":          "ui-designer",
    "motion":      "motion-designer",
    "dataviz":     "dataviz-designer",
    "landing":     "landing-designer",
    "interaction": "interaction-designer",
}

# Scopes that trigger a design review pass after implementation
FRONTEND_SCOPES = {"frontend", "ui", "landing", "dataviz", "motion", "interaction"}

# Design agents applied sequentially to frontend tasks after primary agent
DESIGN_REVIEW_AGENTS: list[str] = [
    "ui-designer",
    "interaction-designer",
]

# Agents with fixed roles (not scope-driven)
TECH_LEAD = "tech-lead"
QA_ENGINEER = "qa-engineer"
SECURITY_ENGINEER = "security-engineer"
PRODUCT_ANALYST = "product-analyst"

# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------

PHASES = [
    "PLANNING",
    "DESIGN",
    "IMPLEMENT",
    "TEST",
    "REVIEW",
    "INTEGRATE",
    "DOCUMENT",
]

# Phase → agents involved
PHASE_AGENTS: dict[str, list[str]] = {
    "PLANNING":  [TECH_LEAD, PRODUCT_ANALYST],
    "DESIGN":    [TECH_LEAD],
    "IMPLEMENT": [],  # determined by scope at runtime
    "TEST":      [QA_ENGINEER],
    "REVIEW":    [SECURITY_ENGINEER, TECH_LEAD],
    "INTEGRATE": [],  # no agent — git operations
    "DOCUMENT":  [TECH_LEAD, PRODUCT_ANALYST],
}

# ---------------------------------------------------------------------------
# TDD preamble injected into implementation prompts
# ---------------------------------------------------------------------------

TDD_PREAMBLE = (
    "\n\nIMPORTANT — CLAUDE.md RULES YOU MUST FOLLOW:\n"
    "1. TDD is mandatory for backend code: write failing tests FIRST, then implement, then refactor.\n"
    "2. All tests must pass before you finish. Run the test command to verify.\n"
    "3. Update documentation files affected by your changes "
    "(see CLAUDE.md 'Closing session' checklist).\n"
    "4. Do NOT add Co-Authored-By or any auto-generated signatures to commits.\n"
    "5. Do NOT create files 'for the future' — only what is needed now (YAGNI).\n"
)
