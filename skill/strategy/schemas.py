"""Pydantic schemas for strategic option evaluation (PERT)."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PERTEstimate(BaseModel):
    rationale: str = Field(
        description=(
            "强制写出该数值的客观依据与换算逻辑。"
            "当场景不是纯金钱时，必须把时间、情绪价值、健康提升、精力消耗等"
            "定性因素换算为通用效用点数（UP），例如 1小时=100UP、极度痛苦=-500UP。"
        )
    )
    min_val: float = Field(description="极端悲观估计值")
    mode_val: float = Field(description="最可能估计值")
    max_val: float = Field(description="极端乐观估计值")

    @model_validator(mode="after")
    def validate_order(self) -> "PERTEstimate":
        if not (self.min_val <= self.mode_val <= self.max_val):
            raise ValueError("必须满足 min_val <= mode_val <= max_val")
        return self


class DecisionOption(BaseModel):
    option_name: str
    success_prob: PERTEstimate = Field(description="成功率的三点估算，约束 0.0 到 1.0")
    expected_revenue: PERTEstimate = Field(
        description=(
            "期望综合收益的三点估算。"
            "不局限于金钱，在日常生活中代表通用效用点数（UP）。"
            "需在 rationale 中说明将时间节省、情绪价值、多巴胺、健康提升等转化为 UP 的逻辑。"
        )
    )
    estimated_cost: float = Field(
        description=(
            "预计付出的综合成本。"
            "不局限于现金成本，可包含时间投入、机会成本、精力损耗等 UP 折算值。"
        )
    )

    @model_validator(mode="after")
    def validate_success_prob_range(self) -> "DecisionOption":
        values = (self.success_prob.min_val, self.success_prob.mode_val, self.success_prob.max_val)
        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError("success_prob 的 min/mode/max 必须在 [0.0, 1.0] 区间内")
        return self


class DecisionContext(BaseModel):
    goal: str = Field(description="决策目标")
    options: list[DecisionOption]


class CooperationContext(BaseModel):
    players: list[str] = Field(description="合作参与方名称列表，至少两方")
    standalone_values: dict[str, float] = Field(
        description="每个参与方单干可获得的价值（通用效用点数，UP）"
    )
    synergy_value: float = Field(
        description="合作产生的总价值（毛值，通用效用点数 UP）"
    )
    cooperation_cost: float = Field(description="合作实施总成本")
    rationale: str = Field(description="协作背景与价值来源说明")
    proposed_project_rationale: str = Field(
        description="基于双方资源与能力互补性，推演出的具体合作项目或商业模式的详细脑暴过程。"
    )

    @model_validator(mode="after")
    def validate_players_and_values(self) -> "CooperationContext":
        if len(self.players) < 2:
            raise ValueError("players 至少包含 2 个参与方")

        unique_players = list(dict.fromkeys(self.players))
        if len(unique_players) != len(self.players):
            raise ValueError("players 不能包含重复参与方")

        player_set = set(self.players)
        value_keys = set(self.standalone_values.keys())
        if player_set != value_keys:
            raise ValueError("standalone_values 的 key 必须与 players 完全一致")

        if any(value < 0 for value in self.standalone_values.values()):
            raise ValueError("standalone_values 不能为负")

        if self.synergy_value < 0:
            raise ValueError("synergy_value 不能为负")
        if self.cooperation_cost < 0:
            raise ValueError("cooperation_cost 不能为负")
        if not self.proposed_project_rationale.strip():
            raise ValueError("proposed_project_rationale 不能为空")
        return self
