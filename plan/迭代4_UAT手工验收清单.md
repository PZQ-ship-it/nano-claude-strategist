# 迁移迭代4：Usability & Life-Strategist 手工验收清单（UAT）

> 目标：验证系统是否能够把非结构化生活输入自动转换为可计算参数（UP），并通过 DAG / Monte Carlo / Shapley 完成可执行、可解释、可审核的闭环决策。

## 0. 启动命令（每轮测试前）

1. 激活环境（Git Bash）：
   - `source /d/Nash-Copilot/Nash-Copilot/venv/Scripts/activate`
2. 进入项目：
   - `cd /d/nano-claude-strategist/nano-claude-strategist`
3. 启动主程序：
   - `python nano_claude.py`

---

## 1) 场景一：日常事项自动统筹（Batch DAG）

### 场景一输入指令示例

```text
我今天下午要打扫卫生、写完项目核心代码（明早要交）、拿快递，还要构思明天的会议发言。帮我排个序。
```

### 场景一预期智能体行为（Agent Behavior）

- LLM 读取当前系统时间（含 Unix Timestamp）作为 DDL 与松弛度计算基准。
- 必须调用 `batch_analyze_and_schedule_tasks`。
- 自动拆解任务并估算：`expected_value`、`duration_hours`、`deadline_timestamp`、`dependencies`。
- 任务“写完项目核心代码（明早要交）”因 DDL 触发高紧迫度，动态 Score 应显著更高。
- 输出 Markdown 科学执行清单，按动态 Score 降序。

### 场景一验证核心点

1. 是否成功触发批量工具，而非循环手动创建多个 Task。
2. 是否正确体现“DDL 驱动优先级跃升”（双曲贴现 + 紧迫度）。
3. 是否识别潜在前置依赖（如“构思会议发言”可依赖“完成核心代码中的结论/进展”）。

---

## 2) 场景二：模糊选择自动估算（UP + Monte Carlo）

### 场景二输入指令示例

```text
十一假期，我是花 5000 块去旅游（开心但累），还是在家看书学习（充实但枯燥），或者去兼职赚 2000 块？
```

### 场景二预期智能体行为（Agent Behavior）

- LLM 必须调用 `evaluate_strategic_options`。
- 自动把金钱、风险、情绪、精力转为 UP 口径，并在 `rationale` 解释换算依据。
- 自动预填 `min/mode/max` 三点估算后进入 TUI。
- 您按 `Ctrl+S` 放行后，底层执行万次 Monte Carlo。
- 输出包含：EU 均值、`95% CI Lower/Upper`，并强调下限（防守底线）最高选项。

### 场景二验证核心点

1. 是否出现明确的 UP 换算逻辑，而非只给主观建议。
2. 是否输出置信区间下限并用于风险提示。
3. 若某方案下限 < 0，是否明确给出亏损/后悔风险警告。

---

## 3) 场景三：合作潜力与分润闭环（Project Brainstorm + Shapley）

### 场景三输入指令示例

```text
我懂 Python 开发，周末有 10 小时；我朋友懂自媒体运营，手里有 5000 粉丝的公众号。评估下我们能怎么合作，以及收益怎么分？
```

### 场景三预期智能体行为（Agent Behavior）

- LLM 必须调用 `evaluate_cooperation_synergy`。
- 在参数中给出 `proposed_project_rationale`（例如“开发小程序并通过公众号变现”）。
- 自动估算双方 `standalone_values` 与 `synergy_value`（均为 UP 口径），并说明估算依据。
- TUI 弹出后您核对参数并 `Ctrl+S` 放行。
- 输出 Shapley 分配金额与比例（例如约 60/40），并拒绝拍脑袋五五开。

### 场景三验证核心点

1. `proposed_project_rationale` 是否存在且内容具体可执行。
2. 分配是否满足数学一致性（各方分配和 = 净合作价值）。
3. 是否解释“协同增量（Synergy Surplus）”来源。

---

## 4) TUI 审核与安全闸门补充检查（通用于场景2/3）

### 操作步骤

- 在 TUI 中故意修改为不合法参数（如 `min_val > max_val`、删除 JSON 引号）。
- 按 `Ctrl+S`。

### 预期行为

- TUI 不退出。
- 报错提示明确（JSON 语法或 Pydantic 校验错误）。
- 仅合法参数可放行进入硬计算。

---

## 5) 场景四：映射表可视化校准（UPRule 工具链）

### 场景四输入指令示例

```text
先把 UP 映射表给我看一下；把 hour_saved 调到 150，再新增 social_anxiety_cost = -280；然后把 social_anxiety_cost 删掉，最后重置为默认映射。
```

### 场景四预期智能体行为（Agent Behavior）

- 按顺序调用并展示结果：
   1. `UPRuleList`（查看当前映射）
   2. `UPRuleSet`（更新 `hour_saved`，新增 `social_anxiety_cost`）
   3. `UPRuleDelete`（删除 `social_anxiety_cost` 用户覆盖）
   4. `UPRuleReset`（清空全部用户覆盖，恢复默认）
- 输出中应可见映射表（Markdown 表格）与 `source`（`default/user`）变化。

### 场景四验证核心点

1. `UPRuleList` 能稳定展示键值与来源，便于人工校准。
2. `UPRuleSet` 更新后能被立即读到（动态调取生效）。
3. `UPRuleDelete` 删除用户覆盖后，对默认键应回退到默认值。
4. `UPRuleReset` 后所有用户覆盖清空，仅保留默认映射。

---

## 6) UAT记录模板（可复制）

```text
[Iteration4-UAT记录]
日期：
环境：OS / Python版本 / 虚拟环境
场景1 日常事项自动统筹：通过/失败（备注）
场景2 模糊选择自动估算：通过/失败（备注）
场景3 合作潜力与分润闭环：通过/失败（备注）
场景4 映射表可视化校准（UPRule）：通过/失败（备注）
TUI 防呆拦截（非法参数阻断）：通过/失败（备注）
工具调用是否符合 SOP（batch/strategic/cooperation/uprule）：是/否
结论：可发布 / 需修复
```
