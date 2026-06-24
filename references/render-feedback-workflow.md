# Render QA and Feedback Continuation

## Render backends

`qa_report.py` tries these backends in order:

1. `EXPERIMENT_REPORT_RENDERER`: path to a compatible local `render_docx.py`-style script.
2. LibreOffice/soffice on PATH.
3. Windows Word COM through PowerShell.

A successful backend produces a PDF, page PNGs, and a contact-sheet preview. Structural checks and render checks are separate. `unavailable` means no backend completed; it is not a pass or a document defect. Use `--require-render` only when the environment is known to provide a renderer.

The reviewing agent must inspect every rendered page image when status is `passed`. The deterministic script cannot decide aesthetics, overlap meaning, or screenshot legibility by itself.

## Feedback

The Dashboard GET/POST route `/api/reports/<job_id>/feedback` accepts only bounded JSON on loopback. Actions support `open`, `done`, `needs-review`, and `skipped`. Confirmed context and corrections become a downloadable feedback JSON.

On a later turn:

1. Read the original report, latest metadata, and feedback JSON.
2. Treat confirmed context as user evidence.
3. Re-check only affected findings and any dependencies.
4. Produce a new immutable job; never overwrite the old report or metadata.