"""Tests for utility_points persistent mapping and tools."""
from __future__ import annotations

from pathlib import Path

import pytest

import utility_points.store as up_store
from utility_points.store import (
    DEFAULT_RULES,
    delete_rule,
    get_effective_rules,
    list_rules_with_source,
    reset_rules,
    set_rule,
)


@pytest.fixture(autouse=True)
def isolated_up_store(tmpdir, monkeypatch):
    tmp_path = Path(str(tmpdir))
    monkeypatch.setattr(up_store, "_ups_file", lambda: tmp_path / ".nano_claude" / "utility_points.json")
    yield


class TestUtilityPointsStore:
    def test_default_rules_available_without_user_file(self):
        rules = get_effective_rules()
        for key, value in DEFAULT_RULES.items():
            assert key in rules
            assert rules[key] == value

    def test_set_rule_persists_and_marks_user_source(self):
        key, value, is_new = set_rule("hour_saved", 150)
        assert key == "hour_saved"
        assert value == 150.0
        assert is_new is False

        rules = get_effective_rules()
        assert rules["hour_saved"] == 150.0

        rows = list_rules_with_source()
        source = {k: s for k, _, s in rows}
        assert source["hour_saved"] == "user"

    def test_delete_user_override_falls_back_to_default(self):
        set_rule("joy_high", 999)
        removed, fallback_default = delete_rule("joy_high")
        assert removed is True
        assert fallback_default is True
        assert get_effective_rules()["joy_high"] == DEFAULT_RULES["joy_high"]

    def test_reset_rules_clears_user_overrides(self):
        set_rule("new_metric", 321)
        assert get_effective_rules().get("new_metric") == 321.0
        reset_rules()
        assert "new_metric" not in get_effective_rules()


class TestUtilityPointsTools:
    def test_tools_registered(self):
        from tool_registry import get_tool
        import utility_points.tools as _up_tools  # noqa: F401

        for name in ("UPRuleList", "UPRuleSet", "UPRuleDelete", "UPRuleReset"):
            assert get_tool(name) is not None

    def test_global_tool_schemas_exposed(self):
        try:
            from tools import TOOL_SCHEMAS
        except TypeError as exc:
            pytest.skip(f"Skip on legacy interpreter incompatibility: {exc}")

        names = {schema["name"] for schema in TOOL_SCHEMAS}
        for name in ("UPRuleList", "UPRuleSet", "UPRuleDelete", "UPRuleReset"):
            assert name in names

    def test_tool_workflow_set_list_delete(self):
        from utility_points.tools import _up_rule_delete, _up_rule_list, _up_rule_set

        msg = _up_rule_set({"key": "focus_deep_work", "value": 420}, {})
        assert "focus_deep_work" in msg

        table = _up_rule_list({}, {})
        assert "Utility Points Mapping" in table
        assert "focus_deep_work" in table

        deleted = _up_rule_delete({"key": "focus_deep_work"}, {})
        assert "deleted" in deleted.lower() or "removed" in deleted.lower()
