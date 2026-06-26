# university-experiment-report-review-skill

## Purpose（技能用途）

本技能用于在本地分析高校实验报告文件和截图。

支持：

* 判断实验报告状态（空白模板 / 部分完成 / 已完成）
* 指导填写空白实验报告
* 审核已完成实验报告
* 基于原始文档生成结构化 DOCX
* 执行质量检查（QA）
* 启动本地 Dashboard
* 提供一份整合批注 DOCX，并在渐进式 Dashboard 中展示必要信息

适用于 Claude Code、Codex、OpenClaw 等 AgentSkills 兼容环境。

---

## Activation（激活条件）

以下情况应激活本技能：

* 用户显式调用 `/university-experiment-report-review-skill`
* 用户要求分析实验报告
* 用户上传实验报告 DOCX/PDF
* 用户上传实验报告截图
* 用户请求实验指导
* 用户请求实验报告审阅
* 用户要求生成修订版 DOCX
* 用户要求保留原始格式
* 用户要求生成批注或修改建议

以下情况不要激活：

* 普通课程答疑
* 一般写作任务
* 与实验报告无关的教育类问题

---

## Usage（使用流程）

1. 完整阅读 `SKILL.md`
2. 将教师评分标准（Rubric）和实验要求视为最高优先级依据
3. 运行：

```bash
scripts/inspect_report.py
```

用于提取：

* 文本内容
* 图片内容
* Contact Sheet
* 实验领域信息

4. 完成语义分析后：

* 生成符合 `assets/generation-plan.schema.json` 的 Generation Plan
* 执行 Schema 校验

5. 校验通过后仅执行一次：

```bash
scripts/run_pipeline.py
```

正常交付不得添加 `--no-dashboard` 或 `--no-open`。必须返回 Dashboard URL；若浏览器没有自动打开，读取输出目录的 `dashboard-url.txt` 并把地址发给用户。

Windows Codex Desktop 中不要自动尝试 Word COM，也不要调用会触发 `codex-windows-sandbox-setup.exe` 的本地图片查看辅助程序。Word COM 仅在用户明确同意后通过 `--allow-word-com` 启用；截图默认通过本地 Dashboard 查看。

6. 自动完成：

* DOCX 生成
* QA 检查
* Dashboard 启动
* 下载页面展示

禁止：

* 调用外部 LLM API
* 调用远程 OCR 服务
* 上传学生文件到第三方平台

---

## Required Behavior（必须遵守的行为）

### File Review（文件审查）

* 必须读取所有用户提供的文件
* 必须检查关键截图
* 区分：

  * Observed（直接观察到）
  * Inferred（推断得到）
  * Unreadable（无法识别）

### Accuracy（真实性要求）

严禁伪造：

* 实验过程
* 实验结果
* 命令执行记录
* 测试数据
* 截图内容
* 引用来源
* 实验要求

### Review Output（审阅输出）

必须提供：

* 具体修改位置
* 问题原因
* 修改建议

当不存在实质性问题时，明确输出：

> 可以提交

### Privacy（隐私保护）

* 所有学生文档仅允许本地处理
* 不重复输出敏感凭据
* 不泄露认证信息

### DOCX Generation（DOCX 生成）

必须：

* 保留原始段落结构
* 保留原始 Run
* 保留原始样式

仅允许新增：

* 明确标识的 AI 修改内容
* 彩色修订标注

### Mode Selection（模式选择）

根据报告状态自动选择：

| 状态               | 模式        |
| ---------------- | --------- |
| Blank Template   | execution |
| Partial Report   | revision  |
| Completed Report | revision  |

---

## Files（文件说明）

### Core Documents

#### `SKILL.md`

完整工作流说明和输出契约定义。

---

### Scripts

#### `scripts/inspect_report.py`

负责：

* 文本提取
* 图片分析
* Contact Sheet 生成
* Domain Routing 准备

#### `scripts/domain_router.py`

自动识别实验所属领域。

#### `scripts/qa_report.py`

执行：

* 结构检查
* 内容检查
* DOCX 渲染检查（可选）

#### `scripts/agent_compat.py`

执行：

* Claude Code 兼容性检查
* Codex 兼容性检查
* OpenClaw 兼容性检查

#### `scripts/build_report.py`

保留样式的 DOCX 批注生成器。

#### `scripts/run_pipeline.py`

一键执行完整流程。

#### `scripts/dashboard_server.py`

启动仅本地可访问的 Dashboard。

---

### Assets

#### `assets/generation-plan.schema.json`

Generation Plan 的标准 Schema。

---

### References

#### `references/generated-document-workflow.md`

描述：

* 文档生成流程
* 修改边界
* 风险控制原则

---

### Evals

#### `evals/`

包含：

* 回归测试
* 典型案例
* 验收标准

---

## Cross-Agent Paths（跨 Agent 安装路径）

### Claude Code

```text
~/.claude/skills/university-experiment-report-review-skill
```

### Codex / AgentSkills

```text
~/.agents/skills/university-experiment-report-review-skill
```

### OpenClaw Shared Skill

```text
~/.openclaw/skills/university-experiment-report-review-skill
```

### OpenClaw Workspace Skill

```text
<workspace>/skills/university-experiment-report-review-skill
```

---

## OpenClaw Skill Priority（OpenClaw 加载优先级）

加载顺序：

1. Workspace Skills
2. Shared Skills

同名技能时：

* Workspace Skill 覆盖 Shared Skill

修改 Activation、Allowlist 或配置后，建议开启新的 Session 以确保配置重新加载。
0
## v1.4 Delivery Contract

Before generation, confirm one of `15m`, `1h`, `half_day`, or `full`; use `full` only for non-interactive fallback. Produce one user-facing annotated DOCX with a consolidated review appendix. Treat local quality JSON and render assets as machine data. The dashboard defaults to a traffic-light verdict, no more than five budgeted actions, screenshot evidence cards, and the main DOCX download; deeper checks remain collapsed. Review `manifest.json.review_signals` as candidates and visually verify false-completion, contamination, and screenshot retake findings.

## Feedback Lifecycle

Current and historical feedback are editable local records, but they no longer directly form a pending improvement queue. The dashboard writes four-layer lifecycle data: raw feedback (`active` or `revoked`), AI interpretation drafts, modification records, and actual skill files.

On each Agent run, scan `feedback-lifecycle/events.jsonl` and advance every `ready_for_agent` event automatically. Complete AI interpretation, separate report-specific corrections from reusable skill rules, draft modification records only for reusable rules, validate changes, install validated changes, and draft reversions for revoked feedback that already reached `applied`.

Modification records may be `drafted`, `needs_revision`, `validated`, `applied`, `revert_drafted`, `revert_needs_revision`, or `reverted`; do not use a failed terminal state. If validation does not pass, continue revising or ask the user only when confirmation, missing facts, or permission is required. Read `generation-preferences.json` before generation and confirm time budget, review depth, review focus, and output mode with the user.
