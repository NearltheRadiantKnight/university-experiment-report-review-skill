# Changelog

## 1.1.0 — 2026-06-23

- Add style-preserving DOCX generation based on the uploaded original file.
- Generate an experiment execution report for blank templates and a modification report for partial or completed work.
- Mark Codex-added content with explicit labels, distinct fonts, and category colors while leaving original runs untouched.
- Add a loopback-only frontend that opens automatically and downloads generated DOCX files.
- Add a single delivery pipeline, generation-plan schema, examples, dashboard assets, and tests.

## 1.0.0 — 2026-06-23

- Add blank, partial, and completed experiment-report classification.
- Add local DOCX, PDF, text, Markdown, and image preparation.
- Add screenshot and visual-evidence review rules.
- Add completeness, alignment, correctness, reproducibility, evidence, analysis, conclusion, and writing review dimensions.
- Add explicit ready-to-submit decisions and no-forced-criticism behavior.
- Add six eval criteria and three representative golden inputs.
- Keep all model reasoning local to the current Codex session with no external API.
