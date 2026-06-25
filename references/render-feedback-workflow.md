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

- Report feedback: action-level corrections for the current generated report. These records can be edited, deleted, and saved from current or historical feedback dialogs.
- Personal memory: cross-document notes such as student information, course names, teacher requirements, software versions, and account ownership. This is stored separately in `personal-memory.json` and is not evidence that one report already contains that information.

Every feedback save, update, or deletion automatically updates the local skill-improvement queue. The student-facing page should describe this as being recorded for later improvement, and should not show machine file names, debug fields, queue internals, or raw metadata.

When a local maintenance agent consumes the queue, it must separate one-report corrections from reusable skill defects, use `agent-skill-creator` only for reusable changes, and run the full validation suite before installation or publishing.
