"""Tool registration for Utility Points mapping management."""
from __future__ import annotations

from tool_registry import ToolDef, register_tool

from .store import delete_rule, list_rules_with_source, reset_rules, set_rule


def _up_rule_list(params: dict, config: dict) -> str:
    rows = list_rules_with_source()
    if not rows:
        return "No UP mapping rules found."

    lines = [
        "## Utility Points Mapping",
        "",
        "| Key | UP Value | Source |",
        "|---|---:|---|",
    ]
    for key, value, source in rows:
        lines.append(f"| {key} | {value:.2f} | {source} |")
    return "\n".join(lines)


def _up_rule_set(params: dict, config: dict) -> str:
    key = params["key"]
    value = float(params["value"])
    norm_key, final_value, is_new = set_rule(key, value)
    action = "created" if is_new else "updated"
    return f"UP rule {action}: {norm_key} = {final_value:.2f}"


def _up_rule_delete(params: dict, config: dict) -> str:
    key = params["key"]
    removed, fallback_default = delete_rule(key)
    if removed and fallback_default:
        return f"UP user override removed: {key}. Fallback to default rule is active."
    if removed:
        return f"UP rule deleted: {key}"
    if fallback_default:
        return f"UP rule '{key}' is a default rule and has no user override to delete."
    return f"UP rule not found: {key}"


def _up_rule_reset(params: dict, config: dict) -> str:
    reset_rules()
    return "UP mapping reset: all user overrides cleared; defaults remain active."


register_tool(ToolDef(
    name="UPRuleList",
    schema={
        "name": "UPRuleList",
        "description": "List current Utility Points (UP) mapping rules including source (default/user).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    func=_up_rule_list,
    read_only=True,
    concurrent_safe=True,
))

register_tool(ToolDef(
    name="UPRuleSet",
    schema={
        "name": "UPRuleSet",
        "description": "Create or update a Utility Points mapping rule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Rule key, e.g. hour_saved"},
                "value": {"type": "number", "description": "UP value for the key"},
            },
            "required": ["key", "value"],
        },
    },
    func=_up_rule_set,
    read_only=False,
    concurrent_safe=False,
))

register_tool(ToolDef(
    name="UPRuleDelete",
    schema={
        "name": "UPRuleDelete",
        "description": "Delete a user override UP rule by key.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Rule key to delete"},
            },
            "required": ["key"],
        },
    },
    func=_up_rule_delete,
    read_only=False,
    concurrent_safe=False,
))

register_tool(ToolDef(
    name="UPRuleReset",
    schema={
        "name": "UPRuleReset",
        "description": "Reset UP mapping to defaults by clearing all user overrides.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    func=_up_rule_reset,
    read_only=False,
    concurrent_safe=False,
))
