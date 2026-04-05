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
