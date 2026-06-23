# University Experiment Report Review Skill

本地分析并生成大学实验报告。空白 DOCX 会生成“实验执行报告”；部分完成或已完成 DOCX 会生成带彩色标注的“修改报告”。原文内容和已有字体样式保留，Codex 新增内容使用独立字体颜色并带明确标签。

## Privacy

不连接任何外部模型 API、远程 OCR、云端文档处理或上传服务。语义和截图分析由当前 Codex 会话完成；Python 只在本地提取、改写和展示文件。

## Installation

```powershell
git clone https://github.com/NearltheRadiantKnight/university-experiment-report-review-skill "$HOME\.codex\skills\university-experiment-report-review-skill"
pip install -r "$HOME\.codex\skills\university-experiment-report-review-skill\requirements.txt"
```

安装或更新后重启 Codex。

## Usage

在 Codex 新对话上传 `.docx`，然后输入：

```text
/university-experiment-report-review-skill
分析这份报告。空白模板生成实验执行报告，已完成报告生成修改报告；保留原字体，新增内容使用彩色字体，并打开下载页面。
```

Codex 会读取文档和截图、生成本地 JSON 计划，然后执行：

```powershell
python scripts/run_pipeline.py --source "<原始报告.docx>" --plan "<generation-plan.json>" --output-dir "<输出目录>"
```

浏览器将自动打开 `http://127.0.0.1:8765`。页面显示最新结果和本地历史，可下载生成的 DOCX。

## Output Rules

- 空白模板：生成“实验执行报告”，新增执行步骤、证据要求和写作指导，不虚构结果。
- 部分完成或已完成：生成“修改报告”，在原文附近插入问题、建议、示例或优点。
- 原始 DOCX 永不覆盖。
- 原文 run 和样式不重设；新增内容带“Codex 新增”标签和分类颜色。
- Dashboard 只绑定 `127.0.0.1`，没有上传和模型接口。

## Supported Inputs

- .docx：完整支持分析、样式保留生成与下载。
- `.pdf`、图片、`.txt`、`.md`：支持分析；要生成保留原字体的可编辑文件，需先本地转换为 DOCX。
- 旧版 `.doc`：先另存为 `.docx`。

## Colors

- 蓝色：执行指导或修改建议。
- 红色：发现的问题。
- 绿色：参考写法。
- 紫色：写作建议或应保留的优点。
- 青色：截图、数据和证据要求。

## Commands

```powershell
python scripts/inspect_report.py --input "<报告>" --output-dir "<准备目录>"
python scripts/build_report.py --source "<报告.docx>" --plan "<计划.json>" --output-dir "<输出目录>"
python scripts/dashboard_launcher.py --output-dir "<输出目录>"
python scripts/run_pipeline.py --source "<报告.docx>" --plan "<计划.json>" --output-dir "<输出目录>"
```

## Validation

```powershell
python -m unittest discover -s tests -v
python scripts/run_evals.py --validate
```

## License

MIT
