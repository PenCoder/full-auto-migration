from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants import DATA_DIR
from src.orchestration.errors import ERR_CHECKPOINT_IO, MigrationError


@dataclass
class CheckpointState:
    run_id: str
    phase: str = "init"
    status: str = "running"
    step_data: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CheckpointManager:
    def __init__(self, run_id: str, checkpoint_dir: Path | None = None) -> None:
        self.run_id = run_id
        self.checkpoint_dir = checkpoint_dir or (DATA_DIR / "checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.checkpoint_dir / f"{run_id}.json"

    def load(self) -> CheckpointState | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise MigrationError(ERR_CHECKPOINT_IO, str(exc)) from exc
        return CheckpointState(
            run_id=raw.get("run_id", self.run_id),
            phase=raw.get("phase", "init"),
            status=raw.get("status", "running"),
            step_data=raw.get("step_data", {}),
            updated_at=raw.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )

    def save(self, state: CheckpointState) -> None:
        state.updated_at = datetime.now(timezone.utc).isoformat()
        try:
            self.path.write_text(json.dumps(state.__dict__, indent=2), encoding="utf-8")
        except OSError as exc:
            raise MigrationError(ERR_CHECKPOINT_IO, str(exc)) from exc

    def mark_phase(self, phase: str, **step_data: Any) -> CheckpointState:
        state = self.load() or CheckpointState(run_id=self.run_id)
        state.phase = phase
        state.step_data.update(step_data)
        self.save(state)
        return state

    def complete(self, **step_data: Any) -> CheckpointState:
        state = self.load() or CheckpointState(run_id=self.run_id)
        state.phase = "completed"
        state.status = "completed"
        state.step_data.update(step_data)
        self.save(state)
        return state
