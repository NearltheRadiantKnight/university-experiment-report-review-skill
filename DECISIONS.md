# Architecture Decisions

## Simple Skill

The package is a single simple skill because blank-template guidance, partial-report completion, completed-report review, and screenshot analysis share one evidence pipeline and one user outcome: submission-ready experiment reports. A suite would create unnecessary routing and duplicated methodology.

## Local-Only Design

No external model, OCR, storage, or analysis API is used. `scripts/inspect_report.py` performs deterministic local preparation. Codex itself reads the extracted text, views relevant images, and performs the semantic review. This satisfies the privacy requirement and avoids managing model credentials.

## Visual Evidence

DOCX media is extracted from the local archive. PDF pages and embedded images are rendered locally with PyMuPDF. The skill requires visual inspection and forbids treating OCR, captions, or extracted text as proof of what a screenshot shows.

## Scoring

The default rubric organizes review but does not claim to predict a teacher's grade. Teacher rubrics override it. Submission readiness and dimension statuses are preferred when course-specific weights are unavailable.

## Interactive Boundary

There is no deterministic semantic `run_pipeline.py`: final classification and review require Codex judgment and may branch by report state. The local preparation script is independently testable, while the eval spec uses semantic checklist criteria.
