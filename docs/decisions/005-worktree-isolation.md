# ADR-005: Git Worktree Isolation for Multi-Agent Orchestration

**Status:** Accepted
**Date:** 2026-03-05
**Decision makers:** Core team

## Context
Orchestrator runs multiple Claude Code agents in parallel. Each agent modifies files. Without isolation, agents overwrite each other's work.

## Decision
Each task runs in an isolated git worktree:

```
~/.claude/worktrees/
├── task-api-auth/        # Agent 1 workspace
├── task-frontend-dash/   # Agent 2 workspace
└── task-rag-ingest/      # Agent 3 workspace
```

Workflow:
1. Create worktree: `git worktree add <path> -b orch/task-<id> HEAD`
2. Agent works in worktree (full repo copy, shared .git)
3. Commit in worktree
4. Merge to main: `git merge --no-ff orch/task-<id>`
5. Cleanup: `git worktree remove` + `git branch -D`

Merge serialization: `fcntl.flock` file lock for cross-process safety.

## Consequences
**Positive:**
- Full isolation — agents can't corrupt each other's work
- Standard git workflow — no custom VCS needed
- Parallel execution scales to N agents
- Easy debugging — each worktree is inspectable

**Negative:**
- Disk space: each worktree = full working copy
- Merge conflicts between parallel tasks
- Stale worktree cleanup needed (prune_worktrees)
- WSL2 file system performance impact

## Alternatives considered
1. **Sequential execution** — no conflicts, but 4x slower
2. **Feature branches without worktrees** — requires git checkout (blocks other agents)
3. **Separate repos** — too complex, no shared history
4. **Patch files** — fragile, hard to debug
