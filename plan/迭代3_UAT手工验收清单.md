# 迁移迭代3：Monte Carlo + Shapley 手工验收清单（UAT）

> 目标：验证 `evaluate_strategic_options`（蒙特卡洛风控）与 `evaluate_cooperation_synergy`（夏普利分配）在 **工具必调、TUI拦截、数学正确、边界稳健** 四个维度均符合预期。

## 0. 启动命令（每轮测试前）

1. 激活环境（Git Bash）：
   - `source activate nano-claude`
2. 进入项目：
   - `cd /d/nano-claude-strategist/nano-claude-strategist`
3. 启动主程序：
   - `python nano_claude.py`

---

## 1) 场景一：蒙特卡洛风控模拟

### 输入指令

```text
我在考虑两个创业方案。A方案稳扎稳打，B方案高风险高回报。请调用工具做三点估算和期望效用评估。
```

### 预期行为

- LLM 触发 `evaluate_strategic_options` 工具（而非先主观拍结论）。
- 终端进入全屏 TUI，展示 `goal/options/success_prob/expected_revenue/estimated_cost` JSON。
- `Ctrl+S` 放行后，输出报告中出现：
  - “经过万次蒙特卡洛模拟”（或同等含义）
  - 每个方案的 `95% CI Lower / 95% CI Upper`
  - 对高风险方案给出下行亏损警告（若下限 < 0）。

### 验证核心点

1. `numpy` 向量化抽样执行顺畅（无明显卡顿）。
2. 模型是否强调“95%下限”这一防守底线。
3. 表格排序是否按 `EU` 降序。

---

## 2) 场景二：夏普利值博弈分配

### 输入指令

```text
我和朋友合伙开公司。我自己干能赚100万，他自己干赚80万。我们合作预计能做大到300万，但有20万的磨合成本。请用工具计算最公平的分润比例，严禁五五开。
```

### 预期行为

- LLM 触发 `evaluate_cooperation_synergy`。
- TUI 弹出并展示：`players / standalone_values / synergy_value / cooperation_cost / rationale`。
- `Ctrl+S` 放行后，输出 Shapley 分配结果：
  - 净合作价值：$300-20=280$ 万
  - 协同增量：$280-(100+80)=100$ 万
  - 预期分配金额：A=150 万，B=130 万（非五五开）
- 输出中解释“协同增量”来源。

### 验证核心点

1. `CooperationContext` 的 Schema 解析与校验是否正确。
2. `v_func` 构造与 Shapley 计算逻辑是否正确。
3. 模型是否明确拒绝“拍脑袋平分”。

---

## 3) 场景三：负协同效应边界防御

### 操作步骤

- 复用场景二请求。
- 在 TUI 中将 `cooperation_cost` 改为 `150`（万）。
- 按 `Ctrl+S` 放行。

### 预期行为

- 工具给出：
  - 净合作价值：$300-150=150$ 万
  - 协同增量：$150-180=-30$ 万（负数）
- 输出应体现明显风险建议：合作不划算，建议谨慎或放弃。
- 两方 Shapley 金额应加总为 150 万（参考值：A≈85 万，B≈65 万）。

### 验证核心点

1. 负协同时数学仍稳定，分配总和满足效率性。
2. LLM 能遵循“反直觉数学事实”，不硬给乐观结论。

---

## 4) 场景四：确定性参数边界容错

### 操作步骤

- 触发 `evaluate_strategic_options`。
- 在 TUI 中把某方案的 `min_val/mode_val/max_val` 改为相同值（例如都为 `100`）。
- 按 `Ctrl+S` 放行。

### 预期行为

- 工具不崩溃，不出现除零异常。
- 报告可正常生成，EU 与区间结果合理（区间可能收敛）。

### 验证核心点

1. `or_math.py` 对 `min==mode==max` 的边界保护生效。
2. Beta-PERT 抽样流程在确定性输入下稳定运行。

---

## 5) UAT 记录模板（可复制）

```text
[Iteration3-UAT记录]
日期：
环境：OS / Python版本 / 虚拟环境
场景1 蒙特卡洛风控：通过/失败（备注）
场景2 夏普利分配：通过/失败（备注）
场景3 负协同边界：通过/失败（备注）
场景4 确定性容错：通过/失败（备注）
工具调用是否符合预期（必调）：是/否
TUI交互是否稳定（保存/驳回/通知）：是/否
结论：可发布 / 需修复
```
