# university-experiment-report-review-skill

## Purpose

Analyze university laboratory-report files and screenshots locally. Classify each report as blank, partial, or completed; guide blank templates; review completed work for completeness, requirement alignment, technical correctness, reproducibility, evidence, screenshot quality, analysis, conclusions, and writing; and state clearly when it is ready to submit.

## Activation

Use for explicit `/university-experiment-report-review-skill` invocations and requests involving 实验报告、空白模板、怎么做实验、怎么写、检查报告、完成度、匹配度、正确性、截图、运行结果、修改建议 or 能不能提交. Do not activate for unrelated general education or writing questions.

## Usage

Read `SKILL.md` in this directory completely before reviewing a report. Treat teacher rubrics and experiment instructions as authoritative. Use `scripts/inspect_report.py` only to prepare local document text and images; the current Codex model must perform the semantic and visual review itself. Never call an external model API or remote OCR service.

## Required Behavior

- Read all supplied files before judging.
- Inspect important screenshots visually and separate observed, inferred, and unreadable content.
- Never fabricate execution, results, commands, data, screenshots, citations, or requirements.
- Give actionable, located revisions; say “可以提交” when no material issue remains.
- Keep student documents local and avoid repeating sensitive credentials.

## Files

- `SKILL.md`: complete workflow and output contract.
- `scripts/inspect_report.py`: local text/image preparation.
- `references/`: detailed review, screenshot, and output methodology.
- `assets/review-rubric.json`: default rubric used only when no teacher rubric exists.
- `evals/`: regression criteria and representative cases.
