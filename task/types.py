"""Task system types: Task dataclass, TaskStatus enum."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"


VALID_STATUSES = {s.value for s in TaskStatus}


@dataclass
class Task:
    id: str
    subject: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    active_form: str = ""          # e.g. "Running tests"
    owner: str = ""
    blocks: list[str] = field(default_factory=list)      # IDs this task blocks
    blocked_by: list[str] = field(default_factory=list)  # IDs that block this task
    expected_value: float = 100.0
    p_success: float = 1.0
    duration_hours: float = 1.0
    sunk_cost_hours: float = 0.0
    deadline_timestamp: float | None = None
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── serialization ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "subject":      self.subject,
            "description":  self.description,
            "status":       self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "active_form":  self.active_form,
            "owner":        self.owner,
            "blocks":       self.blocks,
            "blocked_by":   self.blocked_by,
            "expected_value": self.expected_value,
            "p_success": self.p_success,
            "duration_hours": self.duration_hours,
            "sunk_cost_hours": self.sunk_cost_hours,
            "deadline_timestamp": self.deadline_timestamp,
            "dependencies": self.dependencies,
            "metadata":     self.metadata,
            "created_at":   self.created_at,
            "updated_at":   self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        status_raw = data.get("status", "pending")
        try:
            status = TaskStatus(status_raw)
        except ValueError:
            status = TaskStatus.PENDING
        return cls(
            id=data["id"],
            subject=data.get("subject", ""),
            description=data.get("description", ""),
            status=status,
            active_form=data.get("active_form", ""),
            owner=data.get("owner", ""),
            blocks=data.get("blocks", []),
            blocked_by=data.get("blocked_by", []),
            expected_value=float(data.get("expected_value", 100.0)),
            p_success=max(0.0, min(1.0, float(data.get("p_success", 1.0)))),
            duration_hours=max(0.1, float(data.get("duration_hours", 1.0))),
            sunk_cost_hours=max(0.0, float(data.get("sunk_cost_hours", 0.0))),
            deadline_timestamp=(
                float(data["deadline_timestamp"])
                if data.get("deadline_timestamp") is not None
                else None
            ),
            dependencies=[str(item) for item in data.get("dependencies", [])],
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )

    # ── OR scoring ───────────────────────────────────────────────────────────

    def calculate_laxity_hours(self, current_timestamp: float) -> float | None:
        if self.deadline_timestamp is None:
            return None
        remaining_time = max(0.1, self.duration_hours - self.sunk_cost_hours)
        return (self.deadline_timestamp - current_timestamp) / 3600.0 - remaining_time

    def calculate_dynamic_score(self, current_timestamp: float) -> float:
        if self.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            return 0.0

        remaining_time = max(0.1, self.duration_hours - self.sunk_cost_hours)
        base_roi = (self.expected_value * self.p_success) / remaining_time

        if self.deadline_timestamp is not None:
            laxity_hours = (self.deadline_timestamp - current_timestamp) / 3600.0 - remaining_time
            laxity_hours = max(-20.0, min(50.0, laxity_hours))
            urgency_multiplier = 1.0 + (10.0 / (1.0 + math.exp(0.5 * laxity_hours)))
        else:
            urgency_multiplier = 1.0

        sunk_bonus = self.sunk_cost_hours * 2.0
        return round((base_roi * urgency_multiplier) + sunk_bonus, 2)

    # ── display ────────────────────────────────────────────────────────────────

    def status_icon(self) -> str:
        return {
            TaskStatus.PENDING:     "○",
            TaskStatus.IN_PROGRESS: "●",
            TaskStatus.COMPLETED:   "✓",
            TaskStatus.CANCELLED:   "✗",
        }.get(self.status, "?")

    def one_line(self, resolved_ids: set[str] | None = None) -> str:
        owner_str = f" ({self.owner})" if self.owner else ""
        pending_blockers = [
            b for b in self.blocked_by
            if resolved_ids is None or b not in resolved_ids
        ]
        blocked_str = (
            f" [blocked by #{', #'.join(pending_blockers)}]"
            if pending_blockers else ""
        )
        return f"#{self.id} [{self.status.value}] {self.status_icon()} {self.subject}{owner_str}{blocked_str}"
