# Changelog

## 1.3.2 - 2026-06-23

- Restore report download buttons when an older dashboard exposes only the legacy top-level `download_url`.
- Allow feedback entry on legacy dashboards without a feedback API.
- Persist legacy feedback in browser local storage and download a portable feedback JSON on save.

## 1.3.1 - 2026-06-23

- Prevent reuse of stale dashboard processes that point at another output directory or expose an older API.
- Select the next available loopback port automatically when the requested port belongs to a stale instance.
- Show every generated report in local history, including the latest result and its download actions.
- Detect HTML responses on JSON endpoints and explain how to recover from a stale local page.

## 1.2.0 - 2026-06-23

- Added structured paragraph, bullet, checklist, and table blocks.
- Added strict anchor and numeric-score quality gates.
- Removed default duplicate summary appendix and accidental unlocated-content sections.
- Added companion action-checklist DOCX and deterministic quality JSON.
- Added image context mapping and local contact sheets.
- Expanded the Dashboard with priorities, actions, QA status, and multi-file downloads.
- Added native Claude Code, Codex, and OpenClaw installation contracts.
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
