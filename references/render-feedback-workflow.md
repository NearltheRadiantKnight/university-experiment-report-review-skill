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

Report feedback follows a four-layer lifecycle:

1. Raw feedback stores the user's exact words. Feedback status is only `active` or `revoked`.
2. AI interpretation records convert raw feedback into structured meaning during an Agent run. Scopes are `report_specific`, `reusable_skill_rule`, `personal_preference`, and `needs_clarification`.
3. Modification records are generated only for reusable skill rules. Valid statuses are `drafted`, `needs_revision`, `validated`, `applied`, `revert_drafted`, `revert_needs_revision`, and `reverted`. They never use a failed terminal status; validation problems move the record to a revision state.
4. Skill files change only through validated modification records.

Every feedback save, update, clear, or delete writes deterministic local lifecycle records and events. The Dashboard must not call an external model or silently edit skill files. The next Agent run scans `feedback-lifecycle/events.jsonl`, completes interpretation, generates or revises modification records, validates, installs, or drafts reversions automatically. If user confirmation or elevated permission is required, the Agent asks in that same session.

Clearing or deleting feedback revokes it. If it has not affected skill files, subsequent lifecycle records are revoked. If it has already been applied, the Agent must create and validate a reverse modification record.
