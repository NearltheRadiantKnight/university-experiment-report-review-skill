# University Experiment Report Review Skill

本地分析大学生实验报告。它能区分空白模板、部分完成和已完成报告：对空白模板给出实验执行、证据保留和章节写作方案；对已完成报告审阅完成度、任务匹配度、技术正确性、可复现性、截图证据、分析、结论与格式，并在足够好时明确提示可以提交。

## Privacy and Model Use

本 skill 不接入任何外部模型 API、远程 OCR 或上传服务。文档准备脚本只读取本地文件并导出本地文本与图片；语义和视觉分析由当前 Codex 会话完成。

## Installation

### Codex

把整个目录复制到：

```text
~/.codex/skills/university-experiment-report-review-skill/
```

或使用通用路径：

```text
~/.agents/skills/university-experiment-report-review-skill/
```

安装后重启 Codex，使其重新扫描 skills。

### Other SKILL.md Hosts

可以运行：

```bash
chmod +x install.sh
./install.sh --platform codex
./install.sh --all
./install.sh --dry-run
```

## Local Preparation Script

DOCX、PDF、文本和图片可以先在本地整理：

```powershell
python scripts/inspect_report.py --input "C:\path\report.docx" --output-dir "C:\tmp\report-review"
python scripts/inspect_report.py --input "C:\path\report.pdf" --output-dir "C:\tmp\report-review"
python scripts/inspect_report.py --check-prereqs
python scripts/inspect_report.py --diagnostics
```

脚本生成 `manifest.json`、`document.txt` 和 `images/`。Codex 随后读取文字并实际查看相关图片。脚本本身不评价报告。

## Usage

```text
/university-experiment-report-review-skill 这是初始空白报告，请告诉我怎么做、怎么截图、每节怎么写
/university-experiment-report-review-skill 检查这份已完成报告，重点看正确性和截图是否能证明结果
/university-experiment-report-review-skill 按教师评分表审阅，确认是否可以提交
```

支持计算机网络、数据库、编程、操作系统、软件工程、电子电路、物理、化学及其他大学实验课程。教师任务书和评分标准优先于默认量表。

## Supported Files

- `.docx`
- `.pdf`（本地脚本需要 PyMuPDF）
- `.txt`、`.md`
- `.png`、`.jpg`、`.jpeg`、`.bmp`、`.webp`

旧版 `.doc` 请先在本地另存为 `.docx` 或 `.pdf`。

## Evals

验证评测规范：

```powershell
python scripts/run_evals.py --validate
```

评测位于 `evals/university-experiment-report-review-skill.eval.md`。由于最终审阅依赖 Codex 对语义和图片的判断，六项标准使用 `llm-judge`，运行器会把它们打印为人工检查清单。

## Troubleshooting

- PDF 无法提取：确认安装 `PyMuPDF>=1.24,<2.0`，或让 Codex 直接查看 PDF 页面。
- PDF 文本为空：它可能是扫描件，必须查看 `images/page-*.png`，不能判定为空白。
- DOCX 没有图片：确认图片是真正嵌入文档，而不是已失效的外部链接。
- 截图太模糊：使用原始图片或重新截图关键区域，保留窗口标题、参数和结果上下文。
- 找不到课程要求：同时提供实验指导书、任务书或评分表；skill 仍可按通用标准审阅，但会标注不确定性。

## License

MIT
