"""OR math primitives for strategic evaluation (Monte Carlo + Shapley)."""
from __future__ import annotations

import math
from itertools import combinations
from typing import Dict, Tuple

import numpy as np  # type: ignore[import-untyped]


def _generate_pert_samples(a: float, m: float, b: float, size: int) -> np.ndarray:
    if a == m == b:
        return np.full(size, a, dtype=float)

    if a > b:
        a, b = b, a
    m = min(max(m, a), b)

    if a == b:
        return np.full(size, a, dtype=float)

    mu = (a + (4.0 * m) + b) / 6.0
    sigma = max((b - a) / 6.0, 1e-9)

    variance_term = ((mu - a) * (b - mu) / (sigma**2)) - 1
    alpha = ((mu - a) / (b - a)) * variance_term if (b - a) != 0 else 1.0
    beta_param = alpha * ((b - mu) / (mu - a)) if (mu - a) != 0 else 1.0

    if alpha <= 0 or beta_param <= 0:
        alpha, beta_param = 1.0, 1.0

    return (np.random.beta(alpha, beta_param, size=size) * (b - a)) + a


def run_monte_carlo_eu(
    min_p: float,
    mode_p: float,
    max_p: float,
    min_rev: float,
    mode_rev: float,
    max_rev: float,
    cost: float,
    num_simulations: int = 10000,
) -> Dict[str, float]:
    """Estimate expected utility mean and 95% CI via Beta-PERT Monte Carlo."""
    n = max(1, int(num_simulations))
    prob_samples = _generate_pert_samples(min_p, mode_p, max_p, n)
    rev_samples = _generate_pert_samples(min_rev, mode_rev, max_rev, n)
    eu_array = (prob_samples * rev_samples) - cost

    return {
        "mean_eu": round(float(np.mean(eu_array)), 2),
        "ci_95_lower": round(float(np.percentile(eu_array, 2.5)), 2),
        "ci_95_upper": round(float(np.percentile(eu_array, 97.5)), 2),
    }


def calculate_shapley_value(players: list[str], v_func: Dict[Tuple[str, ...], float]) -> Dict[str, float]:
    """Calculate Shapley value for cooperative game with characteristic function v(S)."""
    n = len(players)
    if n == 0:
        return {}

    shapley_values = {player: 0.0 for player in players}

    for i in range(n):
        for subset in combinations(players, i):
            subset_set = set(subset)
            subset_key = tuple(sorted(subset_set))
            for player in players:
                if player in subset_set:
                    continue

                val_without = float(v_func.get(subset_key, 0.0))
                subset_with = subset_set.union({player})
                subset_with_key = tuple(sorted(subset_with))
                val_with = float(v_func.get(subset_with_key, 0.0))

                marginal_contribution = val_with - val_without
                weight = (
                    math.factorial(len(subset_set))
                    * math.factorial(n - len(subset_set) - 1)
                    / math.factorial(n)
                )
                shapley_values[player] += weight * marginal_contribution

    return {key: round(value, 2) for key, value in shapley_values.items()}
