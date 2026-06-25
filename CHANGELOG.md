## 1.5.7 - 2026-06-25
- ? DOCX ????????????? `????`??????? `??????`?
- ???????????????????/????????????????????????
- ????????????????????????????????????????????????????????? skill ?????
- ??????????????????????????

## 1.5.6 - 2026-06-25
- ???????? unknown?????????????? yes/no/partial ????????
- ????? `personal-memory.json` ?????????????????????????
- ???????????????????????????????
- ???????????????????????????

## 1.5.5 - 2026-06-25
- ?? Dashboard ?????? Skill?????
- ????????????????????????
- ?????????????????????

## 1.5.0 - 2026-06-24

- Restored editable and deletable current/history feedback workflows.
- Added local AgentSkills improvement requests driven by saved feedback evidence.
- Added Dashboard generation settings for budget, depth, focus, and output mode.
- Added explicit render-state explanations, local preview, and retry actions.
## 1.5.5 - 2026-06-25
- ?? Dashboard ???????? Skill????
- ?????????????????????????
- ??????????????? Skill ???????

## 1.5.4 - 2026-06-25
- ?? Dashboard ???????????????? `.modal-overlay[hidden]` ??????
- ????? `role=dialog` ? `aria-modal=true`????????????????

## 1.5.3 - 2026-06-25
- 修复 Dashboard 弹窗关闭按钮的可点击区域与无障碍标签。
- 修复反馈行动行布局冲突，删除按钮改为稳定单行按钮。
- 默认隐藏无渲染器时的页面预览警告，避免把 DOCX 可下载状态误报成失败。
- 增加前端按钮与渲染状态回归测试。

## 1.4.0 - 2026-06-24

- Added time-budgeted rescue modes and green/yellow/red submission signals.
- Consolidated user delivery into one annotated DOCX with review and automatic-QA appendices.
- Added local false-completion, contamination, screenshot-dimension, and retake evidence signals.
- Rebuilt the dashboard as a progressive workbench without background refresh or unsafe HTML insertion.
- Added safe registered screenshot previews and kept machine JSON/render artifacts out of normal downloads.
# Changelog

## 1.5.2 - 2026-06-24

- Audit all Dashboard buttons and align their UI behavior with local API routes.
- Hide ineffective render retry when no renderer is installed.
- Track unsaved state per feedback editor so saving one record does not clear another.
- Make clipboard failures non-fatal after a Skill improvement task is queued.
- Require saved feedback before creating a Skill improvement request and show the activation command in a modal.
- Bump frontend asset version to prevent stale browser JavaScript.

## 1.5.1 - 2026-06-24

- Disable Microsoft Word COM rendering by default to prevent Windows sandbox and registry popups.
- Add explicit `--allow-word-com` opt-in for host sessions that can safely render through Word.
- Preserve the local Dashboard in normal delivery and write its URL to `dashboard-url.txt`.
- Avoid Codex Desktop local-image helpers that trigger sandbox setup; use registered Dashboard screenshots instead.
- Make QA tables compatible with localized Word templates that lack the `Table Grid` style.

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
