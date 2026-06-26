# Render QA and Feedback Continuation

## Render backends

`qa_report.py` tries these backends in order:

1. `EXPERIMENT_REPORT_RENDERER`: path to a compatible local `render_docx.py`-style script.
2. LibreOffice/soffice on PATH.
3. Windows Word COM through PowerShell.

A successful backend produces a PDF, page PNGs, and a contact-sheet preview. Structural checks and render checks are separate. `unavailable` means no backend completed; it is not a pass or a document defect. Use `--require-render` only when the environment is known to provide a renderer.

The reviewing agent must inspect every rendered page image when status is `passed`. The deterministic script cannot decide aesthetics, overlap meaning, or screenshot legibility by itself.

## Feedback and Personal Memory

The Dashboard has two separate user inputs:

- Report feedback: action-level corrections for the current generated report.
- Personal memory: cross-document notes such as student information, course names, teacher requirements, software versions, and account ownership.

Report feedback follows a three-layer lifecycle:

1. Feedback pool: raw feedback stores the user's exact words only while the feedback is still effective. Empty temporary inputs are not written.
2. AI interpretation layer: the next agent run converts active feedback into structured meaning. Scopes are `report_specific`, `reusable_skill_rule`, `personal_preference`, and `needs_clarification`.
3. Modification records: generated only for reusable skill rules. Valid statuses are `drafted`, `needs_revision`, `validated`, and `applied`. They never use a failed terminal status; validation problems move the record to a revision state.

Skill files change only through validated modification records. Every feedback save or update writes deterministic local lifecycle records and events. The Dashboard must not call an external model or silently edit skill files. The next agent run scans active feedback, completes interpretation, generates or revises modification records, validates, and installs automatically. If user confirmation or elevated permission is required, the agent asks in that same session.

Withdrawing feedback is an irreversible purge. The Dashboard removes the raw feedback, interpretation records, modification records, related lifecycle events, and matching flat `*.feedback.json` action content. History must not show revoked/reverted placeholders. If an applied feedback already changed skill files, the agent must first remove or reverse the actual skill effect and validate the result, then purge local lifecycle JSON.