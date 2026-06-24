# University Experiment Report Review Skill

本地分析大学实验报告，自动选择领域适配包，并生成结构化交付物：彩色批注报告、独立行动清单、质量报告和环回 Dashboard。空白模板生成执行指导；部分完成或已完成报告生成证据化修改建议。原始 DOCX 不覆盖，不调用外部模型 API、远程 OCR 或云端文档处理。

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

## Domain Profiles

内置软件测试、计算机网络、数据库、操作系统/程序设计、物理/电子/其他理工五个本地适配包。低置信度时回退到通用审阅，不强行分类。

```bash
python scripts/domain_router.py --input "<准备目录>/document.txt"
```

## Render QA

流水线依次尝试 `EXPERIMENT_REPORT_RENDERER`、LibreOffice 和 Windows Word COM。成功时生成 PDF、逐页 PNG 与预览图；全部不可用时质量报告明确写入 `unavailable`。需要强制渲染时使用 `--require-render`。

## Feedback Loop

Dashboard 可更新行动状态、填写修正事实并导出 `<job_id>.feedback.json`。该 JSON 不调用模型，只作为下一次 Codex、Claude Code 或 OpenClaw 审阅的用户证据。

## Quality Gates

- 没有教师量表或用户明确要求时，不允许生成数值评分。
- 长执行步骤必须使用列表、复选清单或表格，不能堆成长段落。
- 默认严格匹配锚点；找不到位置时生成失败，不产生“未定位内容”。
- 输出后自动检查 DOCX 可打开、原图保留、标签齐全、无超长段落；检测到 LibreOffice 时额外渲染 PDF。
- Dashboard 展示提交判断、优先级、行动项与质量状态，并提供多个文件下载。

## Validation

```bash
python -m unittest discover -s tests -v
python scripts/run_evals.py --validate
python scripts/agent_compat.py --platform all
python scripts/validate_plan.py assets/execution-plan.example.json
python scripts/validate_plan.py assets/revision-plan.example.json
```

## License

MIT
