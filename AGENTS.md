# university-experiment-report-review-skill

## Purpose

Analyze university laboratory-report files and screenshots locally. Classify each report as blank, partial, or completed; guide blank templates; review completed work; generate a style-preserving annotated DOCX from the uploaded original; open a local dashboard; and provide downloads.

## Activation

Use for explicit `/university-experiment-report-review-skill` invocations and experiment-report requests involving blank templates, execution guidance, completed-report review, screenshots, downloadable DOCX generation, local frontend display, original font preservation, or colored revisions. Do not activate for unrelated education or general writing questions.

## Usage

Read `SKILL.md` completely. Treat teacher rubrics and experiment instructions as authoritative. Use `scripts/inspect_report.py` to prepare text and images. After semantic review, write a plan matching `assets/generation-plan.schema.json`, then run `scripts/run_pipeline.py` once to generate the DOCX and open the local download page. Never call an external model API or remote OCR service.

## Required Behavior

- Read all supplied files before judging.
- Inspect important screenshots visually and separate observed, inferred, and unreadable content.
- Never fabricate execution, results, commands, data, screenshots, citations, or requirements.
- Give actionable, located revisions; say “可以提交” when no material issue remains.
- Keep student documents local and avoid repeating sensitive credentials.
- Preserve original DOCX runs and styles; add only clearly marked colored Codex content.
- Use `execution` for blank templates and `revision` for partial or completed reports.

## Files

- `SKILL.md`: complete workflow and output contract.
- `scripts/inspect_report.py`: local text and image preparation.
- `scripts/build_report.py`: style-preserving DOCX annotation engine.
- `scripts/run_pipeline.py`: one-command generation and dashboard delivery.
- `scripts/dashboard_server.py`: loopback-only frontend and downloads.
- `assets/generation-plan.schema.json`: contract for Codex-authored changes.
- `references/generated-document-workflow.md`: generation methodology and boundaries.
- `evals/`: regression criteria and representative cases.
