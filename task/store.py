"""Thread-safe task store: in-memory dict persisted to .nano_claude/tasks.json."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from .types import Task, TaskStatus

_lock = threading.Lock()

# Tasks are keyed by ID, stored per session in <cwd>/.nano_claude/tasks.json
# The store is kept in memory; we reload from disk on first access.

_tasks: dict[str, Task] = {}
_dag = nx.DiGraph()
dag = _dag
_loaded = False


# ── persistence ───────────────────────────────────────────────────────────────

def _tasks_file() -> Path:
    return Path.cwd() / ".nano_claude" / "tasks.json"


def _load() -> None:
    global _loaded
    if _loaded:
        return
    f = _tasks_file()
    if f.exists():
        try:
            data = json.loads(f.read_text())
            for item in data.get("tasks", []):
                t = Task.from_dict(item)
                _tasks[t.id] = t
            _sync_dag()
        except Exception:
            pass
    else:
        _sync_dag()
    _loaded = True


def _save() -> None:
    f = _tasks_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    data = {"tasks": [t.to_dict() for t in _tasks.values()]}
    f.write_text(json.dumps(data, indent=2))


def _next_id() -> str:
    """Generate a short sequential numeric ID."""
    if not _tasks:
        return "1"
    max_id = max((int(k) for k in _tasks if k.isdigit()), default=0)
    return str(max_id + 1)


def _snapshot_tasks() -> dict[str, Task]:
    return {task_id: Task.from_dict(task.to_dict()) for task_id, task in _tasks.items()}


def _restore_tasks(snapshot: dict[str, Task]) -> None:
    _tasks.clear()
    _tasks.update(snapshot)
    _sync_dag()


def _sync_dag() -> None:
    """Rebuild runtime DAG from in-memory tasks and enforce acyclic topology."""
    _dag.clear()

    for task in _tasks.values():
        task.dependencies = list(dict.fromkeys(str(dep) for dep in task.dependencies if str(dep)))
        _dag.add_node(task.id, task_obj=task)

    for task in _tasks.values():
        for parent_id in task.dependencies:
            if parent_id not in _tasks:
                raise ValueError(f"依赖任务不存在: {parent_id}")
            _dag.add_edge(parent_id, task.id)

    if not nx.is_directed_acyclic_graph(_dag):
        raise ValueError("检测到循环依赖死锁，拓扑结构不合法")

    for task in _tasks.values():
        task.blocked_by = list(_dag.predecessors(task.id))
        task.blocks = list(_dag.successors(task.id))


# ── public API ────────────────────────────────────────────────────────────────

def create_task(
    subject: str,
    description: str,
    active_form: str = "",
    expected_value: float = 100.0,
    p_success: float = 1.0,
    duration_hours: float = 1.0,
    sunk_cost_hours: float = 0.0,
    deadline_timestamp: float | None = None,
    dependencies: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Task:
    with _lock:
        _load()
        task = Task(
            id=_next_id(),
            subject=subject,
            description=description,
            active_form=active_form,
            expected_value=float(expected_value),
            p_success=max(0.0, min(1.0, float(p_success))),
            duration_hours=max(0.1, float(duration_hours)),
            sunk_cost_hours=max(0.0, float(sunk_cost_hours)),
            deadline_timestamp=deadline_timestamp,
            dependencies=[str(dep) for dep in (dependencies or [])],
            metadata=metadata or {},
        )
        snapshot = _snapshot_tasks()
        _tasks[task.id] = task
        try:
            _sync_dag()
        except ValueError:
            _restore_tasks(snapshot)
            raise
        _save()
        return task


def get_task(task_id: str) -> Task | None:
    with _lock:
        _load()
        return _tasks.get(str(task_id))


def list_tasks() -> list[Task]:
    with _lock:
        _load()
        return list(_tasks.values())


def update_task(
    task_id: str,
    subject: str | None = None,
    description: str | None = None,
    status: str | None = None,
    active_form: str | None = None,
    owner: str | None = None,
    expected_value: float | None = None,
    p_success: float | None = None,
    duration_hours: float | None = None,
    sunk_cost_hours: float | None = None,
    deadline_timestamp: float | None = None,
    dependencies: list[str] | None = None,
    add_blocks: list[str] | None = None,
    add_blocked_by: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[Task | None, list[str]]:
    """Update a task. Returns (updated_task, list_of_updated_fields)."""
    with _lock:
        _load()
        task = _tasks.get(str(task_id))
        if task is None:
            return None, []
        snapshot = _snapshot_tasks()

        updated_fields: list[str] = []

        if subject is not None and subject != task.subject:
            task.subject = subject
            updated_fields.append("subject")

        if description is not None and description != task.description:
            task.description = description
            updated_fields.append("description")

        if active_form is not None and active_form != task.active_form:
            task.active_form = active_form
            updated_fields.append("active_form")

        if owner is not None and owner != task.owner:
            task.owner = owner
            updated_fields.append("owner")

        if expected_value is not None and float(expected_value) != task.expected_value:
            task.expected_value = float(expected_value)
            updated_fields.append("expected_value")

        if p_success is not None:
            normalized = max(0.0, min(1.0, float(p_success)))
            if normalized != task.p_success:
                task.p_success = normalized
                updated_fields.append("p_success")

        if duration_hours is not None:
            normalized = max(0.1, float(duration_hours))
            if normalized != task.duration_hours:
                task.duration_hours = normalized
                updated_fields.append("duration_hours")

        if sunk_cost_hours is not None:
            normalized = max(0.0, float(sunk_cost_hours))
            if normalized != task.sunk_cost_hours:
                task.sunk_cost_hours = normalized
                updated_fields.append("sunk_cost_hours")

        if deadline_timestamp is not None and float(deadline_timestamp) != task.deadline_timestamp:
            task.deadline_timestamp = float(deadline_timestamp)
            updated_fields.append("deadline_timestamp")

        if dependencies is not None:
            new_dependencies = list(dict.fromkeys(str(dep) for dep in dependencies if str(dep)))
            if new_dependencies != task.dependencies:
                task.dependencies = new_dependencies
                updated_fields.append("dependencies")

        if status is not None:
            try:
                new_status = TaskStatus(status)
            except ValueError:
                new_status = None
            if new_status is not None and new_status != task.status:
                task.status = new_status
                updated_fields.append("status")

        if metadata is not None:
            for k, v in metadata.items():
                if v is None:
                    task.metadata.pop(k, None)
                else:
                    task.metadata[k] = v
            updated_fields.append("metadata")

        if add_blocks:
            new_blocks = [str(b) for b in add_blocks if str(b) not in task.blocks]
            if new_blocks:
                for b_id in new_blocks:
                    target = _tasks.get(str(b_id))
                    if target and str(task_id) not in target.dependencies:
                        target.dependencies.append(str(task_id))
                updated_fields.append("blocks")

        if add_blocked_by:
            new_bb = [str(b) for b in add_blocked_by if str(b) not in task.dependencies]
            if new_bb:
                task.dependencies.extend(new_bb)
                updated_fields.append("blocked_by")

        if updated_fields:
            task.updated_at = datetime.now().isoformat()
            try:
                _sync_dag()
            except ValueError:
                _restore_tasks(snapshot)
                raise
            _save()

        return task, updated_fields


def delete_task(task_id: str) -> bool:
    with _lock:
        _load()
        task_id = str(task_id)
        if task_id not in _tasks:
            return False
        snapshot = _snapshot_tasks()
        del _tasks[task_id]
        for task in _tasks.values():
            if task_id in task.dependencies:
                task.dependencies = [dep for dep in task.dependencies if dep != task_id]
                task.updated_at = datetime.now().isoformat()
        try:
            _sync_dag()
        except ValueError:
            _restore_tasks(snapshot)
            return False
        _save()
        return True


def clear_all_tasks() -> None:
    """Remove all tasks (used in tests)."""
    with _lock:
        _tasks.clear()
        _sync_dag()
        _save()


def reload_from_disk() -> None:
    """Force reload from disk (used in tests)."""
    global _loaded
    with _lock:
        _tasks.clear()
        _loaded = False
        _load()


def cascade_ev_decay(root_task_id: str, decay_factor: float = 0.5) -> None:
    with _lock:
        _load()
        root_task_id = str(root_task_id)
        if root_task_id not in _tasks:
            raise KeyError(f"任务不存在: {root_task_id}")
        if not (0.0 <= decay_factor <= 1.0):
            raise ValueError("decay_factor 必须在 [0.0, 1.0] 区间内")

        descendants = nx.descendants(_dag, root_task_id)
        for task_id in descendants:
            task = _tasks.get(task_id)
            if task is None:
                continue
            task.expected_value *= decay_factor
            task.updated_at = datetime.now().isoformat()

        _save()
