"""Task tools: TaskCreate, TaskUpdate, TaskGet, TaskList — registered into tool_registry."""
from __future__ import annotations

import time
from typing import Any

from tool_registry import ToolDef, register_tool
from . import store as task_store
from .store import create_task, get_task, list_tasks, update_task, delete_task
from .types import TaskStatus


# ── Schemas ───────────────────────────────────────────────────────────────────

_TASK_CREATE_SCHEMA = {
    "name": "TaskCreate",
    "description": (
        "Create a new task in the task list. "
        "Use this to track work items, to-dos, and multi-step plans. "
        "Returns the new task's ID and subject."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "A brief title for the task",
            },
            "description": {
                "type": "string",
                "description": "What needs to be done",
            },
            "active_form": {
                "type": "string",
                "description": (
                    "Present-continuous label shown while in_progress "
                    "(e.g. 'Running tests', 'Writing docs')"
                ),
            },
            "metadata": {
                "type": "object",
                "description": "Arbitrary key-value metadata to attach to the task",
            },
            "expected_value": {
                "type": "number",
                "description": "Expected absolute value (EV), default 100.0",
            },
            "p_success": {
                "type": "number",
                "description": "Success probability in [0.0, 1.0], default 1.0",
            },
            "duration_hours": {
                "type": "number",
                "description": "Estimated task duration in hours, default 1.0",
            },
            "sunk_cost_hours": {
                "type": "number",
                "description": "Already invested sunk cost in hours, default 0.0",
            },
            "deadline_timestamp": {
                "type": "number",
                "description": "Absolute deadline as Unix timestamp",
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Predecessor task IDs that must finish before this task",
            },
        },
        "required": ["subject", "description"],
    },
}

_TASK_UPDATE_SCHEMA = {
    "name": "TaskUpdate",
    "description": (
        "Update an existing task. Can change subject, description, status, owner, "
        "dependency edges (blocks / blocked_by), and metadata. "
        "Set status='deleted' to remove the task. "
        "Valid statuses: pending, in_progress, completed, cancelled, deleted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The ID of the task to update",
            },
            "subject": {
                "type": "string",
                "description": "New title for the task",
            },
            "description": {
                "type": "string",
                "description": "New description for the task",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "completed", "cancelled", "deleted"],
                "description": "New status ('deleted' removes the task)",
            },
            "active_form": {
                "type": "string",
                "description": "Present-continuous label while in_progress",
            },
            "owner": {
                "type": "string",
                "description": "Agent/user responsible for this task",
            },
            "add_blocks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Task IDs that this task now blocks",
            },
            "add_blocked_by": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Task IDs that block this task",
            },
            "metadata": {
                "type": "object",
                "description": "Keys to merge into task metadata (null value = delete key)",
            },
            "expected_value": {
                "type": "number",
                "description": "Expected absolute value (EV)",
            },
            "p_success": {
                "type": "number",
                "description": "Success probability in [0.0, 1.0]",
            },
            "duration_hours": {
                "type": "number",
                "description": "Estimated duration in hours",
            },
            "sunk_cost_hours": {
                "type": "number",
                "description": "Already invested sunk cost in hours",
            },
            "deadline_timestamp": {
                "type": "number",
                "description": "Absolute deadline as Unix timestamp",
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Predecessor task IDs",
            },
        },
        "required": ["task_id"],
    },
}

_TASK_GET_SCHEMA = {
    "name": "TaskGet",
    "description": "Retrieve a single task by ID. Returns full task details.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The ID of the task to retrieve",
            },
        },
        "required": ["task_id"],
    },
}

_TASK_LIST_SCHEMA = {
    "name": "TaskList",
    "description": (
        "List all tasks. Returns id, subject, status, owner, and pending blockers. "
        "Use this to review the current plan or find the next available task."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

_TASK_BATCH_ANALYZE_SCHEMA = {
    "name": "batch_analyze_and_schedule_tasks",
    "description": (
        "当用户用自然语言陈述一堆日常杂事、待办和截止时间，不知道先做什么时调用。"
        "将输入批量拆解为带依赖关系的 DAG 任务，并基于运筹学常识估算 EV 与耗时后排序。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "description": "任务列表，每个元素由大模型估算 EV/耗时/依赖后给出",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "任务标题（用于依赖映射）"},
                        "description": {"type": "string", "description": "任务细节说明"},
                        "expected_value": {
                            "type": "number",
                            "description": "预估收益（1-1000）",
                        },
                        "duration_hours": {
                            "type": "number",
                            "description": "预估耗时（小时）",
                        },
                        "deadline_timestamp": {
                            "type": ["number", "null"],
                            "description": "若提及截止时间则转换为 Unix 时间戳，否则为 null",
                        },
                        "dependencies": {
                            "type": "array",
                            "description": "前置任务标题列表（title，而非 task_id）",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["title", "description", "expected_value", "duration_hours"],
                },
            },
        },
        "required": ["tasks"],
    },
}


# ── Implementations ────────────────────────────────────────────────────────────

def _normalize_subject(subject: str) -> str:
    return " ".join(str(subject).strip().split()).lower()


def _find_active_task_by_subject(subject: str):
    normalized = _normalize_subject(subject)
    if not normalized:
        return None

    candidates = [
        task for task in list_tasks()
        if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        and _normalize_subject(task.subject) == normalized
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda task: int(task.id) if task.id.isdigit() else 10**9)
    return candidates[0]


def _create_or_reuse_task(
    subject: str,
    description: str,
    active_form: str = "",
    metadata: dict[str, Any] | None = None,
    expected_value: float = 100.0,
    p_success: float = 1.0,
    duration_hours: float = 1.0,
    sunk_cost_hours: float = 0.0,
    deadline_timestamp: float | None = None,
    dependencies: list[str] | None = None,
):
    existing = _find_active_task_by_subject(subject)
    if existing is None:
        task = create_task(
            subject,
            description,
            active_form=active_form,
            metadata=metadata,
            expected_value=expected_value,
            p_success=p_success,
            duration_hours=duration_hours,
            sunk_cost_hours=sunk_cost_hours,
            deadline_timestamp=deadline_timestamp,
            dependencies=dependencies,
        )
        return task, True

    update_task(
        existing.id,
        description=description,
        active_form=active_form if active_form else None,
        expected_value=expected_value,
        p_success=p_success,
        duration_hours=duration_hours,
        sunk_cost_hours=sunk_cost_hours,
        deadline_timestamp=deadline_timestamp,
        dependencies=dependencies,
        metadata=metadata if metadata is not None else None,
    )
    refreshed = get_task(existing.id)
    return (refreshed or existing), False

def _task_create(
    subject: str,
    description: str,
    active_form: str = "",
    metadata: dict[str, Any] | None = None,
    expected_value: float = 100.0,
    p_success: float = 1.0,
    duration_hours: float = 1.0,
    sunk_cost_hours: float = 0.0,
    deadline_timestamp: float | None = None,
    dependencies: list[str] | None = None,
) -> str:
    try:
        task, created = _create_or_reuse_task(
            subject,
            description,
            active_form=active_form,
            metadata=metadata,
            expected_value=expected_value,
            p_success=p_success,
            duration_hours=duration_hours,
            sunk_cost_hours=sunk_cost_hours,
            deadline_timestamp=deadline_timestamp,
            dependencies=dependencies,
        )
    except ValueError as exc:
        return f"Error: {exc}"
    if not created:
        return f"Task #{task.id} reused (deduplicated): {task.subject}"
    return f"Task #{task.id} created: {task.subject}"


def _task_update(
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
) -> str:
    # Handle deletion
    if status == "deleted":
        ok = delete_task(task_id)
        if ok:
            return f"Task #{task_id} deleted."
        return f"Error: task #{task_id} not found."

    try:
        task, updated_fields = update_task(
            task_id,
            subject=subject,
            description=description,
            status=status,
            active_form=active_form,
            owner=owner,
            expected_value=expected_value,
            p_success=p_success,
            duration_hours=duration_hours,
            sunk_cost_hours=sunk_cost_hours,
            deadline_timestamp=deadline_timestamp,
            dependencies=dependencies,
            add_blocks=add_blocks or [],
            add_blocked_by=add_blocked_by or [],
            metadata=metadata,
        )
    except ValueError as exc:
        return f"Error: {exc}"

    if task is None:
        return f"Error: task #{task_id} not found."
    if not updated_fields:
        return f"Task #{task_id}: no changes (fields already match)."
    return f"Task #{task_id} updated — changed: {', '.join(updated_fields)}."


def _task_get(task_id: str) -> str:
    task = get_task(task_id)
    if task is None:
        return f"Task #{task_id} not found."
    lines = [
        f"Task #{task.id}: {task.subject}",
        f"Status:      {task.status.value}",
        f"Description: {task.description}",
    ]
    if task.owner:
        lines.append(f"Owner:       {task.owner}")
    if task.active_form:
        lines.append(f"Active form: {task.active_form}")
    if task.blocked_by:
        lines.append(f"Blocked by:  #{', #'.join(task.blocked_by)}")
    if task.blocks:
        lines.append(f"Blocks:      #{', #'.join(task.blocks)}")
    if task.metadata:
        lines.append(f"Metadata:    {task.metadata}")
    lines.append(f"Created:     {task.created_at[:19]}")
    lines.append(f"Updated:     {task.updated_at[:19]}")
    return "\n".join(lines)


def _task_list() -> str:
    tasks = list_tasks()
    if not tasks:
        return "No tasks."

    current_timestamp = time.time()
    task_by_id = {task.id: task for task in tasks}

    ready_rows: list[tuple] = []
    blocked_rows: list[tuple] = []
    done_rows: list[tuple] = []

    for task in tasks:
        is_done = task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        predecessor_ids = list(task_store.dag.predecessors(task.id)) if task_store.dag.has_node(task.id) else []
        has_unfinished_predecessor = any(
            task_by_id.get(pred_id) is not None and task_by_id[pred_id].status != TaskStatus.COMPLETED
            for pred_id in predecessor_ids
        )
        is_blocked = (not is_done) and has_unfinished_predecessor

        score = 0.0
        if (not is_done) and (not is_blocked):
            score = task.calculate_dynamic_score(current_timestamp)

        laxity_hours = task.calculate_laxity_hours(current_timestamp)
        laxity_display = "-" if laxity_hours is None else f"{laxity_hours:.2f}"
        status_display = "[BLOCKED]" if is_blocked else f"[{task.status.value}]"

        row = (
            task.id,
            status_display,
            f"{score:.2f}",
            f"{task.expected_value:.2f}",
            f"{task.duration_hours:.2f}",
            laxity_display,
            task.subject,
            score,
        )

        if is_done:
            done_rows.append(row)
        elif is_blocked:
            blocked_rows.append(row)
        else:
            ready_rows.append(row)

    ready_rows.sort(key=lambda item: item[7], reverse=True)
    blocked_rows.sort(key=lambda item: item[0])
    done_rows.sort(key=lambda item: item[0])

    ordered_rows = ready_rows + blocked_rows + done_rows
    lines = [
        "| ID | Status | Score | EV | Dur(h) | Laxity(h) | Title |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in ordered_rows:
        lines.append(
            f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]} |"
        )
    return "\n".join(lines)


def _normalize_title(title: str) -> str:
    return " ".join(str(title).strip().split()).lower()


def _batch_analyze_and_schedule_tasks(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "Error: tasks 不能为空。"

    normalized_titles: dict[str, str] = {}
    duplicate_titles: list[str] = []
    for item in tasks:
        title = str(item.get("title", "")).strip()
        if not title:
            return "Error: 检测到空 title，无法构建 title -> task_id 映射。"
        normalized = _normalize_title(title)
        if normalized in normalized_titles:
            duplicate_titles.append(title)
        else:
            normalized_titles[normalized] = title

    if duplicate_titles:
        dup = ", ".join(duplicate_titles)
        return f"Error: 检测到重复 title（忽略大小写与多空格）：{dup}"

    created_items: list[tuple[str, str, list[str], bool]] = []
    title_to_task_id: dict[str, str] = {}

    for item in tasks:
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        expected_value = float(item.get("expected_value", 100.0))
        duration_hours = float(item.get("duration_hours", 1.0))

        raw_deadline = item.get("deadline_timestamp")
        deadline_timestamp = float(raw_deadline) if raw_deadline is not None else None

        raw_dependencies = item.get("dependencies") or []
        dependency_titles = [str(dep).strip() for dep in raw_dependencies if str(dep).strip()]

        try:
            task, created = _create_or_reuse_task(
                title,
                description,
                expected_value=expected_value,
                duration_hours=duration_hours,
                deadline_timestamp=deadline_timestamp,
                dependencies=[],
            )
        except ValueError as exc:
            return f"Error: 创建任务 '{title}' 失败: {exc}"

        title_to_task_id[_normalize_title(title)] = task.id
        created_items.append((title, task.id, dependency_titles, created))

    for title, task_id, dependency_titles, _ in created_items:
        mapped_dependencies: list[str] = []
        for dep_title in dependency_titles:
            dep_norm = _normalize_title(dep_title)
            if dep_norm == _normalize_title(title):
                return f"Error: 任务 '{title}' 依赖自身，拓扑结构不合法。"
            dep_task_id = title_to_task_id.get(dep_norm)
            if dep_task_id is None:
                return f"Error: 任务 '{title}' 依赖了未知标题 '{dep_title}'。"
            mapped_dependencies.append(dep_task_id)

        if mapped_dependencies:
            try:
                update_task(task_id, dependencies=list(dict.fromkeys(mapped_dependencies)))
            except ValueError as exc:
                return f"Error: 构建依赖边失败（任务 '{title}'）: {exc}"

    try:
        task_store._sync_dag()
    except ValueError as exc:
        return f"Error: DAG 重建失败: {exc}"

    summary_lines = [
        "## Batch Task Triage Result",
        "",
        "已写入任务（title -> task_id）：",
    ]
    for title, task_id, _, created in created_items:
        action = "created" if created else "reused"
        summary_lines.append(f"- {title} -> #{task_id} ({action})")

    summary_lines.extend([
        "",
        "优化后的今日最佳执行路径：",
        _task_list(),
    ])
    return "\n".join(summary_lines)


# ── Registration ───────────────────────────────────────────────────────────────

def _register() -> None:
    defs = [
        ToolDef(
            name="TaskCreate",
            schema=_TASK_CREATE_SCHEMA,
            func=lambda p, c: _task_create(
                p["subject"],
                p["description"],
                p.get("active_form", ""),
                p.get("metadata"),
                p.get("expected_value", 100.0),
                p.get("p_success", 1.0),
                p.get("duration_hours", 1.0),
                p.get("sunk_cost_hours", 0.0),
                p.get("deadline_timestamp"),
                p.get("dependencies"),
            ),
            read_only=False,
            concurrent_safe=True,
        ),
        ToolDef(
            name="TaskUpdate",
            schema=_TASK_UPDATE_SCHEMA,
            func=lambda p, c: _task_update(
                p["task_id"],
                subject=p.get("subject"),
                description=p.get("description"),
                status=p.get("status"),
                active_form=p.get("active_form"),
                owner=p.get("owner"),
                expected_value=p.get("expected_value"),
                p_success=p.get("p_success"),
                duration_hours=p.get("duration_hours"),
                sunk_cost_hours=p.get("sunk_cost_hours"),
                deadline_timestamp=p.get("deadline_timestamp"),
                dependencies=p.get("dependencies"),
                add_blocks=p.get("add_blocks"),
                add_blocked_by=p.get("add_blocked_by"),
                metadata=p.get("metadata"),
            ),
            read_only=False,
            concurrent_safe=True,
        ),
        ToolDef(
            name="TaskGet",
            schema=_TASK_GET_SCHEMA,
            func=lambda p, c: _task_get(p["task_id"]),
            read_only=True,
            concurrent_safe=True,
        ),
        ToolDef(
            name="TaskList",
            schema=_TASK_LIST_SCHEMA,
            func=lambda p, c: _task_list(),
            read_only=True,
            concurrent_safe=True,
        ),
        ToolDef(
            name="batch_analyze_and_schedule_tasks",
            schema=_TASK_BATCH_ANALYZE_SCHEMA,
            func=lambda p, c: _batch_analyze_and_schedule_tasks(p["tasks"]),
            read_only=False,
            concurrent_safe=True,
        ),
    ]
    for td in defs:
        register_tool(td)


_register()
