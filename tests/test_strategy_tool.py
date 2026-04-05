"""Tests for strategy PERT schemas and strategic evaluation tool."""
from __future__ import annotations

import pytest

try:
    import pydantic  # noqa: F401
    HAS_PYDANTIC = True
except ModuleNotFoundError as exc:  # pragma: no cover - environment compatibility
    HAS_PYDANTIC = False
    _IMPORT_ERROR = str(exc)

if HAS_PYDANTIC:
    from tool_registry import get_tool
    from skill.strategy.schemas import DecisionContext, DecisionOption, PERTEstimate
    import skill.strategy.tools as strategy_tools


@pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic is required for strategy tool tests")
class TestStrategySchemas:
    def test_pert_estimate_order_validation(self):
        ok = PERTEstimate(rationale="x", min_val=1.0, mode_val=2.0, max_val=3.0)
        assert ok.mode_val == 2.0

        with pytest.raises(ValueError, match="min_val <= mode_val <= max_val"):
            PERTEstimate(rationale="bad", min_val=3.0, mode_val=2.0, max_val=1.0)

    def test_success_probability_range_validation(self):
        with pytest.raises(ValueError, match=r"\[0.0, 1.0\]"):
            DecisionOption(
                option_name="A",
                success_prob=PERTEstimate(rationale="bad prob", min_val=-0.1, mode_val=0.5, max_val=1.2),
                expected_revenue=PERTEstimate(rationale="rev", min_val=100.0, mode_val=120.0, max_val=150.0),
                estimated_cost=20.0,
            )


@pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic is required for strategy tool tests")
class TestStrategicTool:
    def test_tool_registered(self):
        tool = get_tool("evaluate_strategic_options")
        assert tool is not None
        assert tool.name == "evaluate_strategic_options"

    def test_execute_returns_abort_message_when_human_rejects(self, monkeypatch):
        def _reject(_model_class, _initial_data):
            raise InterruptedError("人类专家驳回了参数注入，执行中止。")

        monkeypatch.setattr(strategy_tools, "require_human_approval_via_tui", _reject)

        result = strategy_tools.execute_strategic_options(goal="x", options=[])
        assert "Action aborted by human" in result

    def test_execute_sorts_by_eu_desc_and_renders_markdown(self, monkeypatch):
        payload = {
            "goal": "选择最高效方案",
            "options": [
                {
                    "option_name": "LowEU",
                    "success_prob": {"rationale": "保守", "min_val": 0.1, "mode_val": 0.2, "max_val": 0.3},
                    "expected_revenue": {"rationale": "收益低", "min_val": 1000.0, "mode_val": 1100.0, "max_val": 1200.0},
                    "estimated_cost": 500.0,
                },
                {
                    "option_name": "HighEU",
                    "success_prob": {"rationale": "积极", "min_val": 0.4, "mode_val": 0.6, "max_val": 0.8},
                    "expected_revenue": {"rationale": "收益高", "min_val": 1500.0, "mode_val": 2000.0, "max_val": 2600.0},
                    "estimated_cost": 300.0,
                },
            ],
        }

        def _approve(_model_class, initial_data):
            return DecisionContext.model_validate(initial_data)

        monkeypatch.setattr(strategy_tools, "require_human_approval_via_tui", _approve)

        result = strategy_tools.execute_strategic_options(**payload)

        assert result.startswith("## Strategic Option Evaluation")
        assert "| Option | Rationale (Summary) | Success Mean | Revenue Mean | Cost | Expected Utility (EU) |" in result

        rows = [line for line in result.splitlines() if line.startswith("| ") and not line.startswith("| Option ") and not line.startswith("|---")]
        assert rows, result
        assert rows[0].startswith("| HighEU |"), result

    def test_private_pert_mean_formula(self):
        estimate = PERTEstimate(rationale="", min_val=1.0, mode_val=2.0, max_val=7.0)
        assert strategy_tools._pert_mean(estimate) == pytest.approx(2.6666666667)


def test_strategy_test_environment_probe():
    """Ensure this file always has at least one runnable test in minimal envs."""
    if HAS_PYDANTIC:
        assert True
    else:
        assert isinstance(_IMPORT_ERROR, str)
