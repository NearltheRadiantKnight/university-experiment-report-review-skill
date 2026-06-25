# University Experiment Report Review Skill

本地分析大学实验报告，自动选择领域适配包，并生成一份整合交付物：保留原格式的彩色批注 DOCX，以及仅展示必要信息的环回 Dashboard。空白模板生成执行指导；部分完成或已完成报告生成证据化修改建议。原始 DOCX 不覆盖，不调用外部模型 API、远程 OCR 或云端文档处理。

## Agent Compatibility

该仓库使用 AgentSkills `SKILL.md` 和 `AGENTS.md`，支持 Claude Code、Codex CLI、OpenClaw，以及其他兼容 AgentSkills 的客户端。

### Claude Code

```bash
./install.sh --platform claude-code
# Windows
.\install.ps1 -Platform claude-code
```

安装位置：`~/.claude/skills/university-experiment-report-review-skill`。

### Codex CLI

```bash
./install.sh --platform codex
# Windows
.\install.ps1 -Platform codex
```

安装位置：`~/.agents/skills/university-experiment-report-review-skill`。Codex Desktop 也可安装到 `$CODEX_HOME/skills`。

### OpenClaw

```bash
./install.sh --platform openclaw
# Windows
.\install.ps1 -Platform openclaw
```

共享安装位置：`~/.openclaw/skills/university-experiment-report-review-skill`；项目安装使用 `<workspace>/skills/university-experiment-report-review-skill`。更新后开启新会话，必要时运行 `openclaw gateway restart`，并用 `openclaw skills list` 检查。

### All Detected Agents

```bash
./install.sh --all
# Windows
.\install.ps1 -All
```

## Usage

```text
/university-experiment-report-review-skill 请告诉我这份空白实验报告怎么执行、截图和填写
/university-experiment-report-review-skill 检查这份完成报告，给出修改意见并生成 DOCX
```

Agent 先运行：

```bash
python scripts/inspect_report.py --input "<报告>" --output-dir "<准备目录>"
```

读取文字、图片上下文、`contact-sheet.jpg` 和 `domain_routing` 后，加载匹配的 `assets/domain-profiles/*.json`，再生成符合 `assets/generation-plan.schema.json` 的计划，再只运行：

```bash
python scripts/run_pipeline.py --source "<报告.docx>" --plan "<计划.json>" --output-dir "<输出目录>"
```

## Generation Framework

生成前由 Agent 与 Dashboard 共同确认时间预算、审阅深度、审阅重点和输出方式。Dashboard 首屏只显示红绿灯、五项以内的预算行动和主 DOCX 下载；截图证据、伪完成、污染检查、质量状态和历史反馈按需展开。最终 DOCX 的综合附录统一承载这些内容，避免重复文件。
## Domain Profiles

内置软件测试、计算机网络、数据库、操作系统/程序设计、物理/电子/其他理工五个本地适配包。低置信度时回退到通用审阅，不强行分类。

```bash
python scripts/domain_router.py --input "<准备目录>/document.txt"
```

## Render QA

流水线依次尝试 `EXPERIMENT_REPORT_RENDERER`、LibreOffice 和 Windows Word COM。成功时生成内部 PDF、逐页 PNG 与预览图；普通用户只下载整合 DOCX。桌面 COM 被沙箱阻止时显示 `permission-required` 与处理方法，其他渲染器均不可用时显示 `unavailable`。

## Feedback Loop

当前反馈保留在结果页；历史反馈通过弹窗查看。两者都可修改状态、删除行动、删除整份记录和保存。点击“用反馈改进 Skill”会创建本地智能体任务队列；Agent 使用 agent-skill-creator 仅吸收可复用问题，并在验证后更新本机 Skill。

## Quality Gates

- 没有教师量表或用户明确要求时，不允许生成数值评分。
- 长执行步骤必须使用列表、复选清单或表格，不能堆成长段落。
- 默认严格匹配锚点；找不到位置时生成失败，不产生“未定位内容”。
- 输出后自动检查 DOCX 可打开、原图保留、标签齐全、无超长段落；检测到 LibreOffice 时额外渲染 PDF。
- Dashboard 展示提交判断、优先级、行动项与质量状态，并提供主 DOCX 下载、渲染预览和重试。

## Validation

```bash
python -m unittest discover -s tests -v
python scripts/run_evals.py --validate
python scripts/agent_compat.py --platform all
python scripts/validate_plan.py assets/execution-plan.example.json
python scripts/validate_plan.py assets/revision-plan.example.json
```
