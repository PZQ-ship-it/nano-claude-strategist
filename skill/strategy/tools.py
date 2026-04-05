"""Strategic OR tools with mandatory Textual HITL checkpoint."""
from __future__ import annotations

from typing import cast

from tool_registry import ToolDef, register_tool

from .or_math import calculate_shapley_value, run_monte_carlo_eu
from .schemas import CooperationContext, DecisionContext, PERTEstimate
from .tui_editor import require_human_approval_via_tui


def _pert_mean(estimate: PERTEstimate) -> float:
    return (estimate.min_val + (4.0 * estimate.mode_val) + estimate.max_val) / 6.0


def execute_strategic_options(**kwargs) -> str:
    try:
        approved_context = cast(DecisionContext, require_human_approval_via_tui(DecisionContext, kwargs))
    except InterruptedError as error:
        return f"Action aborted by human: {error}"
    except Exception as error:
        return f"Action failed in HITL checkpoint: {error}"

    rows: list[dict[str, float | str]] = []
    for option in approved_context.options:
        simulation = run_monte_carlo_eu(
            min_p=option.success_prob.min_val,
            mode_p=option.success_prob.mode_val,
            max_p=option.success_prob.max_val,
            min_rev=option.expected_revenue.min_val,
            mode_rev=option.expected_revenue.mode_val,
            max_rev=option.expected_revenue.max_val,
            cost=option.estimated_cost,
            num_simulations=10000,
        )
        prob_mean = _pert_mean(option.success_prob)
        revenue_mean = _pert_mean(option.expected_revenue)
        rationale = option.success_prob.rationale.strip().replace("\n", " ")
        rows.append(
            {
                "option": option.option_name,
                "rationale": rationale[:80] + ("…" if len(rationale) > 80 else ""),
                "prob_mean": prob_mean,
                "revenue_mean": revenue_mean,
                "cost": option.estimated_cost,
                "eu": simulation["mean_eu"],
                "ci_lower": simulation["ci_95_lower"],
                "ci_upper": simulation["ci_95_upper"],
            }
        )

    rows.sort(key=lambda item: cast(float, item["eu"]), reverse=True)
    has_negative_downside = any(cast(float, row["ci_lower"]) < 0 for row in rows)

    lines = [
        "## Strategic Option Evaluation",
        "",
        f"Goal: {approved_context.goal}",
        "",
        "| Option | Rationale (Summary) | Success Mean | Revenue Mean | Cost | Expected Utility (EU) | 95% CI Lower | 95% CI Upper |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['option']} | {row['rationale']} | {cast(float, row['prob_mean']):.4f} | "
            f"{cast(float, row['revenue_mean']):.2f} | {cast(float, row['cost']):.2f} | {cast(float, row['eu']):.2f} | "
            f"{cast(float, row['ci_lower']):.2f} | {cast(float, row['ci_upper']):.2f} |"
        )
    lines.append("")
    lines.append("请向用户强调 95% 置信区间下限；若下限为负，必须明确警告亏损风险。")
    if has_negative_downside:
        lines.append("⚠️ 风险提示：至少一个方案在 95% 置信区间下限小于 0，存在实际亏损可能。")
    return "\n".join(lines)


def execute_cooperation_synergy(**kwargs) -> str:
    try:
        approved_context = cast(CooperationContext, require_human_approval_via_tui(CooperationContext, kwargs))
    except InterruptedError as error:
        return f"Action aborted by human: {error}"
    except Exception as error:
        return f"Action failed in HITL checkpoint: {error}"

    players = approved_context.players
    coop_total = approved_context.synergy_value - approved_context.cooperation_cost
    v_func: dict[tuple[str, ...], float] = {tuple(): 0.0}
    for player in players:
        v_func[(player,)] = approved_context.standalone_values[player]
    v_func[tuple(sorted(players))] = coop_total

    shapley = calculate_shapley_value(players, v_func)
    total_allocation = sum(shapley.values()) or 1.0
    synergy_surplus = round(
        coop_total - sum(approved_context.standalone_values[player] for player in players),
        2,
    )

    lines = [
        "## Cooperation Synergy Evaluation",
        "",
        f"Context: {approved_context.rationale}",
        f"Proposed project rationale: {approved_context.proposed_project_rationale}",
        f"Cooperation gross value: {approved_context.synergy_value:.2f}",
        f"Cooperation cost: {approved_context.cooperation_cost:.2f}",
        f"Net cooperative value: {coop_total:.2f}",
        f"Synergy surplus: {synergy_surplus:.2f}",
        "",
        "| Participant | Standalone Baseline | Shapley Allocation | Allocation Ratio |",
        "|---|---:|---:|---:|",
    ]
    for player in players:
        baseline = approved_context.standalone_values[player]
        allocation = shapley[player]
        ratio = (allocation / total_allocation) * 100.0
        lines.append(f"| {player} | {baseline:.2f} | {allocation:.2f} | {ratio:.2f}% |")
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


_COOPERATION_TOOL_SCHEMA = {
    "name": "evaluate_cooperation_synergy",
    "description": (
        "当面临多方合作、收益分配或合资谈判时，绝对禁止拍脑袋给比例。"
        "你必须调用此工具，基于协同收益和成本做 Shapley 分配。"
    ),
    "input_schema": CooperationContext.model_json_schema(),
}


COOPERATION_TOOL_DEF = ToolDef(
    name="evaluate_cooperation_synergy",
    schema=_COOPERATION_TOOL_SCHEMA,
    func=lambda p, c: execute_cooperation_synergy(**p),
    read_only=True,
    concurrent_safe=False,
)


def _register() -> None:
    register_tool(STRATEGY_TOOL_DEF)
    register_tool(COOPERATION_TOOL_DEF)


_register()
