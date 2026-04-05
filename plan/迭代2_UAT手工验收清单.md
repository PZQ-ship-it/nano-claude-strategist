# 迁移迭代2：HITL + PERT 手工验收清单（UAT）

> 目标：验证 `evaluate_strategic_options` 工具、Textual 拦截器、Pydantic 双重校验、EU 计算闭环是否按预期工作。

## 0. 启动命令（每轮测试前）

1. 激活环境：
   - `source activate nano-claude`
2. 进入项目：
   - `cd /d/nano-claude-strategist/nano-claude-strategist`
3. 启动主程序：
   - `python nano_claude.py`

---

## 1) 正向触发：必须调用工具并弹出 Textual

### 输入指令

```text
我有1万块，方案A做独立开发，方案B买基金。请帮我评估预期效用，必须调用工具做三点估算。
```

### 预期行为

- LLM 立即调用 `evaluate_strategic_options`。
- CLI 暂停交互。
- 终端进入全屏 Textual 界面，展示 JSON 参数（`goal/options/success_prob/expected_revenue/estimated_cost`）。

### 验证核心点

- 模型没有先输出长篇主观结论，而是优先发起 Tool 调用。
- Textual 接管成功，布局正常（Header + JSON编辑区 + Footer）。
- JSON 初稿字段完整，具备三点估算结构（`min_val/mode_val/max_val`）。

---

## 2) 防呆阻断：JSON语法错误 / 业务校验错误不放行

### 操作步骤

在 Textual 编辑区任选其一：

1. 业务错误：把方案 A 的 `min_val` 改成大于 `max_val`。
2. 语法错误：删除一个双引号或逗号，制造非法 JSON。

然后按：`Ctrl+S`

### 预期行为

- TUI **不会退出**。
- 右下角/角落出现错误通知（如 JSON 语法错误或 ValidationError）。
- 脏数据不进入计算流程。

### 验证核心点

- `json.loads` 语法校验生效。
- `Pydantic model_validate_json` 业务规则校验生效。
- 双重防线都能阻断放行。

---

## 3) 一票否决：ESC 驳回

### 操作步骤

在 TUI 中按：`ESC`

### 预期行为

- TUI 立即关闭，回到 CLI。
- LLM 收到类似：`Action aborted by human: 人类专家驳回了参数注入，执行中止。`
- 模型会道歉或询问你如何调整参数后再试。

### 验证核心点

- `InterruptedError` 被上层工具逻辑正确捕获。
- 驳回路径没有崩溃，没有卡死。
- 对话流恢复正常，模型可继续交互（具备自愈反思）。

---

## 4) 完美放行：Ctrl+S 通过后输出 EU 表格

### 操作步骤

重新发送同类问题（可重复第1条输入）。
在 TUI 不改错或修正后，按：`Ctrl+S`

### 预期行为

- TUI 平滑退出，回到 CLI。
- 模型输出 Markdown 表格，至少包含：
  - `Option`
  - `Rationale (Summary)`
  - `Success Mean`
  - `Revenue Mean`
  - `Cost`
  - `Expected Utility (EU)`
- 方案按 EU 降序排列，并给出专业建议。

### 验证核心点

- Beta-PERT 期望均值计算链路生效：
  - `Mean = (min + 4*mode + max) / 6`
- `EU = revenue_mean * prob_mean - cost` 计算正确。
- 排序逻辑正确（EU 高的在前）。
- Textual 退出后终端显示无乱码、无残屏。

---

## 5) 建议记录模板（可复制）

```text
[UAT记录]
日期：
环境：nano-claude / python版本
场景1 正向触发：通过/失败（备注）
场景2 防呆阻断：通过/失败（备注）
场景3 ESC驳回：通过/失败（备注）
场景4 完美放行：通过/失败（备注）
终端渲染是否正常：是/否
结论：可发布 / 需修复
```
