"""Pydantic schemas for strategic option evaluation (PERT)."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PERTEstimate(BaseModel):
    rationale: str = Field(description="强制大模型写出提取该数值的客观依据与思维链")
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
    expected_revenue: PERTEstimate = Field(description="成功后的预期总收益三点估算")
    estimated_cost: float = Field(description="预计付出的确定执行成本")

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
    standalone_values: dict[str, float] = Field(description="每个参与方单干可获得的价值")
    synergy_value: float = Field(description="合作产生的总价值（毛值）")
    cooperation_cost: float = Field(description="合作实施总成本")
    rationale: str = Field(description="协作背景与价值来源说明")

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
        return self
