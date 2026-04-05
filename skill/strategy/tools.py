"""Strategic PERT tool with mandatory Textual HITL checkpoint."""
from __future__ import annotations

from typing import cast

from tool_registry import ToolDef, register_tool

from .schemas import DecisionContext, PERTEstimate
from .tui_editor import require_human_approval_via_tui


def _pert_mean(estimate: PERTEstimate) -> float:
    return (estimate.min_val + (4.0 * estimate.mode_val) + estimate.max_val) / 6.0


def execute_strategic_options(**kwargs) -> str:
    try:
        approved_context = cast(DecisionContext, require_human_approval_via_tui(DecisionContext, kwargs))
    except InterruptedError as error:
        return f"Action aborted by human: {error}"

    rows: list[tuple[str, str, float, float, float, float]] = []
    for option in approved_context.options:
        prob_mean = _pert_mean(option.success_prob)
        revenue_mean = _pert_mean(option.expected_revenue)
        eu = (revenue_mean * prob_mean) - option.estimated_cost
        rationale = option.success_prob.rationale.strip().replace("\n", " ")
        rows.append((
            option.option_name,
            rationale[:80] + ("…" if len(rationale) > 80 else ""),
            prob_mean,
            revenue_mean,
            option.estimated_cost,
            eu,
        ))

    rows.sort(key=lambda item: item[5], reverse=True)

    lines = [
        "## Strategic Option Evaluation",
        "",
        f"Goal: {approved_context.goal}",
        "",
        "| Option | Rationale (Summary) | Success Mean | Revenue Mean | Cost | Expected Utility (EU) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row[0]} | {row[1]} | {row[2]:.4f} | "
            f"{row[3]:.2f} | {row[4]:.2f} | {row[5]:.2f} |"
        )
    return "\n".join(lines)


_STRATEGY_TOOL_SCHEMA = {
    "name": "evaluate_strategic_options",
    "description": (
        "当面临多方案评估、战略取舍或商业预测请求时，绝对禁止直接给出武断结论。"
        "你必须调用此工具。运用费米估算法将现实情况拆解为包含上下界的三点估算。"
    ),
    "input_schema": DecisionContext.model_json_schema(),
}


STRATEGY_TOOL_DEF = ToolDef(
    name="evaluate_strategic_options",
    schema=_STRATEGY_TOOL_SCHEMA,
    func=lambda p, c: execute_strategic_options(**p),
    read_only=True,
    concurrent_safe=False,
)


def _register() -> None:
    register_tool(STRATEGY_TOOL_DEF)


_register()
