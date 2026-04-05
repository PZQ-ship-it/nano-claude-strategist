"""Tests for strategy OR math helpers (Monte Carlo + Shapley)."""
from __future__ import annotations

import pytest

try:
    import numpy  # noqa: F401
    HAS_NUMERIC_DEPS = True
except ModuleNotFoundError as exc:  # pragma: no cover - environment compatibility
    HAS_NUMERIC_DEPS = False
    _IMPORT_ERROR = str(exc)

if HAS_NUMERIC_DEPS:
    from skill.strategy.or_math import calculate_shapley_value, run_monte_carlo_eu


@pytest.mark.skipif(not HAS_NUMERIC_DEPS, reason="numpy is required for OR math tests")
class TestStrategyOrMath:
    def test_monte_carlo_output_shape_and_order(self):
        result = run_monte_carlo_eu(
            min_p=0.2,
            mode_p=0.5,
            max_p=0.8,
            min_rev=100.0,
            mode_rev=200.0,
            max_rev=400.0,
            cost=30.0,
            num_simulations=3000,
        )

        assert set(result.keys()) == {"mean_eu", "ci_95_lower", "ci_95_upper"}
        assert result["ci_95_lower"] <= result["mean_eu"] <= result["ci_95_upper"]

    def test_shapley_efficiency_two_player_case(self):
        players = ["A", "B"]
        v_func = {
            tuple(): 0.0,
            ("A",): 40.0,
            ("B",): 20.0,
            ("A", "B"): 100.0,
        }

        result = calculate_shapley_value(players, v_func)
        assert pytest.approx(sum(result.values()), rel=1e-6) == 100.0

    def test_shapley_symmetry_identical_players(self):
        players = ["甲", "乙"]
        v_func = {
            tuple(): 0.0,
            ("甲",): 10.0,
            ("乙",): 10.0,
            ("乙", "甲"): 30.0,
        }

        result = calculate_shapley_value(players, v_func)
        assert result["甲"] == pytest.approx(result["乙"], abs=0.01)


def test_or_math_test_environment_probe():
    """Ensure this file always has at least one runnable test in minimal envs."""
    if HAS_NUMERIC_DEPS:
        assert True
    else:
        assert isinstance(_IMPORT_ERROR, str)
