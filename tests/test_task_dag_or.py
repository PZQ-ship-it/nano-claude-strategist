"""Iteration 1.1 tests for DAG scheduling + OR scoring behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from task import create_task, get_task, update_task
from task.store import cascade_ev_decay
from task.tools import _task_list
import task.store as _store


@pytest.fixture(autouse=True)
def isolated_store(tmpdir, monkeypatch):
    """Give each test an isolated in-memory and on-disk store."""
    tmp_path = Path(str(tmpdir))
    monkeypatch.setattr(_store, "_tasks", {})
    monkeypatch.setattr(_store, "_loaded", False)
    _store._dag.clear()
    monkeypatch.setattr(_store, "_tasks_file", lambda: tmp_path / ".nano_claude" / "tasks.json")
    yield
    _store._tasks.clear()
    _store._dag.clear()
    _store._loaded = False


def _table_row_by_id(markdown: str, task_id: str) -> list[str]:
    for line in markdown.splitlines():
        if line.startswith(f"| {task_id} |"):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError(f"Row for task id={task_id} not found:\n{markdown}")


def _table_ids_in_order(markdown: str) -> list[str]:
    ids: list[str] = []
    for line in markdown.splitlines():
        if not line.startswith("| "):
            continue
        if line.startswith("| ID ") or line.startswith("| ---"):
            continue
        first_cell = line.split("|", 2)[1].strip()
        ids.append(first_cell)
    return ids


class TestTaskDagOr:
    def test_cycle_detection_raises_and_rolls_back(self):
        a = create_task("A", "root")
        b = create_task("B", "child", dependencies=[a.id])

        with pytest.raises(ValueError, match="循环依赖|拓扑结构"):
            update_task(a.id, dependencies=[b.id])

        # Verify rollback happened: A still has no dependency; B still depends on A.
        a_after = get_task(a.id)
        b_after = get_task(b.id)
        assert a_after is not None and a_after.dependencies == []
        assert b_after is not None and b_after.dependencies == [a.id]

    def test_blocked_status_is_derived_from_unfinished_predecessors(self):
        blocker = create_task("Blocker", "")
        blocked = create_task("Blocked", "", dependencies=[blocker.id])

        table_before = _task_list()
        row_before = _table_row_by_id(table_before, blocked.id)
        assert row_before[1] == "[BLOCKED]"

        update_task(blocker.id, status="completed")

        table_after = _task_list()
        row_after = _table_row_by_id(table_after, blocked.id)
        assert row_after[1] != "[BLOCKED]"

    def test_ready_tasks_sorted_by_score_desc_and_ties_are_stable(self):
        # id=1,2 have same score; id=3 has higher score and must be first.
        t1 = create_task("Tie-1", "", expected_value=100.0, duration_hours=1.0)
        t2 = create_task("Tie-2", "", expected_value=100.0, duration_hours=1.0)
        t3 = create_task("High", "", expected_value=300.0, duration_hours=1.0)

        table = _task_list()
        ids = _table_ids_in_order(table)

        assert ids[0] == t3.id
        # Stable sort expectation for equal scores: insertion order is preserved.
        assert ids.index(t1.id) < ids.index(t2.id)

    def test_cascade_decay_boundary_values_and_invalid_factor(self):
        root = create_task("Root", "", expected_value=100.0)
        b = create_task("B", "", expected_value=80.0, dependencies=[root.id])
        c = create_task("C", "", expected_value=60.0, dependencies=[b.id])
        d = create_task("D", "", expected_value=50.0)  # not descendant

        # decay_factor=1.0 => descendants unchanged
        cascade_ev_decay(root.id, decay_factor=1.0)
        assert get_task(b.id).expected_value == 80.0
        assert get_task(c.id).expected_value == 60.0

        # decay_factor=0.0 => descendants become zero; root and unrelated node unchanged
        cascade_ev_decay(root.id, decay_factor=0.0)
        assert get_task(root.id).expected_value == 100.0
        assert get_task(d.id).expected_value == 50.0
        assert get_task(b.id).expected_value == 0.0
        assert get_task(c.id).expected_value == 0.0

        with pytest.raises(ValueError):
            cascade_ev_decay(root.id, decay_factor=-0.1)
        with pytest.raises(ValueError):
            cascade_ev_decay(root.id, decay_factor=1.1)
