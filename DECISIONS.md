# Architecture Decisions

## Simple Skill

The package remains one skill because blank-template guidance, completed-report review, DOCX annotation, and result delivery share one evidence pipeline and one user outcome.

## Local-Only Design

No external model, OCR, storage, or analysis API is used. The agent performs semantic and visual review in the active conversation. Python performs deterministic local extraction, DOCX insertion, metadata registration, and browser delivery.

## Visual Evidence

DOCX media is extracted locally. PDF pages and embedded images are rendered locally with PyMuPDF. OCR, captions, and extracted text never replace actual screenshot inspection.

## Generated Documents and Dashboard

Version 1.1 separates semantic planning from deterministic delivery. The agent writes a generation plan after review. `run_pipeline.py` applies it to the original DOCX, registers metadata, starts a loopback-only Flask dashboard, and opens the browser.

The server has no upload or model endpoint and only downloads files registered by metadata in the selected output directory. It binds to `127.0.0.1` and is not exposed to the local network.

## Style Preservation

The original DOCX is never overwritten. Existing runs, fonts, colors, images, tables, and paragraph styles are not reset. New runs carry a `新增` label, an explicit font, and a category color. Editable style preservation is promised only for DOCX; PDF remains an analysis input unless locally converted first.

## Interactive Boundary

Semantic classification and plan authorship require the agent's judgment. Delivery after the plan exists is deterministic and uses one command. This boundary avoids pretending a local Flask app can invoke a model API.

## Scoring

Teacher rubrics override the default rubric. Without course-specific weights, submission readiness and evidence-based dimension states are preferred over false-precision scores.

## ADR-006: Keep one core skill with local domain profiles

The domains share one document-preparation, plan, generation, QA, dashboard, and privacy pipeline. They are implemented as lazy-loaded JSON profiles rather than independent component skills. This keeps installation and invocation stable while allowing domain-specific evidence rules.

## ADR-007: Render status is evidence, not an assumption

The pipeline tries configured external renderers, LibreOffice, then Windows Word COM. Missing backends produce `unavailable`; they never count as a visual pass. `--require-render` turns this into a hard gate.

## ADR-008: Feedback is local data, not a model endpoint

The Dashboard stores bounded JSON feedback beside job metadata. No uploaded document or prompt is sent to a model. A later AgentSkills session consumes the JSON as explicit user evidence.