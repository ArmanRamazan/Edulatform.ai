"""Orchestrator v2 — sprint state persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from config import STATE_DIR

# Allow per-instance state isolation (set by main.py --instance)
_instance_state_dir: Path | None = None


def set_state_dir(path: Path) -> None:
    global _instance_state_dir
    _instance_state_dir = path


def get_state_dir() -> Path:
    return _instance_state_dir or STATE_DIR

try:
    import yaml
except ImportError:
    raise SystemExit("ERROR: PyYAML required. Install: pip install pyyaml")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    id: str
    title: str
    scope: str
    prompt: str
    type: str = "feat"
    test: str | None = None
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    attempts: int = 0
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Sprint file loader
# ---------------------------------------------------------------------------

@dataclass
class SprintFile:
    phase: str
    description: str
    tasks: list[Task]

    @classmethod
    def load(cls, path: Path) -> SprintFile:
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
# Sprint state
# ---------------------------------------------------------------------------

@dataclass
class SprintState:
    source_file: str = ""
    phase: str = ""
    current_pipeline_phase: str = ""
    tasks: list[Task] = field(default_factory=list)
    paused_at: str = ""
    started_at: str = ""
    planning_output: str = ""
    design_output: str = ""
    review_output: str = ""

    def save(self) -> None:
        state_dir = get_state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / "state.json"
        data = {
            "source_file": self.source_file,
            "phase": self.phase,
            "current_pipeline_phase": self.current_pipeline_phase,
            "started_at": self.started_at,
            "paused_at": self.paused_at,
            "planning_output": self.planning_output,
            "design_output": self.design_output,
            "review_output": self.review_output,
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
    def load(cls) -> SprintState | None:
        path = get_state_dir() / "state.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        tasks = [Task(**t) for t in data.get("tasks", [])]
        return cls(
            source_file=data.get("source_file", ""),
            phase=data.get("phase", ""),
            current_pipeline_phase=data.get("current_pipeline_phase", ""),
            tasks=tasks,
            paused_at=data.get("paused_at", ""),
            started_at=data.get("started_at", ""),
            planning_output=data.get("planning_output", ""),
            design_output=data.get("design_output", ""),
            review_output=data.get("review_output", ""),
        )

    @classmethod
    def from_sprint(cls, sprint: SprintFile, source_file: str) -> SprintState:
        return cls(
            source_file=source_file,
            phase=sprint.phase,
            tasks=sprint.tasks,
            started_at=_now(),
        )

    def recover_crashed(self) -> None:
        for t in self.tasks:
            if t.status == "running":
                t.status = "pending"
                t.error = ""
