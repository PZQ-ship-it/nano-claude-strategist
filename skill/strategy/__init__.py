"""strategy package — strategic OR tools with mandatory HITL approval."""

from .or_math import calculate_shapley_value, run_monte_carlo_eu  # noqa: F401

try:
	from .schemas import CooperationContext, DecisionContext, DecisionOption, PERTEstimate  # noqa: F401
	from .tools import (  # noqa: F401
		COOPERATION_TOOL_DEF,
		STRATEGY_TOOL_DEF,
		execute_cooperation_synergy,
		execute_strategic_options,
	)
except ModuleNotFoundError:
	# Allow importing math helpers even in minimal envs without pydantic/textual.
	pass
