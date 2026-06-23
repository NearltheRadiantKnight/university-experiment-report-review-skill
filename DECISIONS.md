# Architecture Decisions

## Simple Skill

The package remains one skill because blank-template guidance, completed-report review, DOCX annotation, and result delivery share one evidence pipeline and one user outcome.

## Local-Only Design

No external model, OCR, storage, or analysis API is used. Codex performs semantic and visual review in the active conversation. Python performs deterministic local extraction, DOCX insertion, metadata registration, and browser delivery.

## Visual Evidence

DOCX media is extracted locally. PDF pages and embedded images are rendered locally with PyMuPDF. OCR, captions, and extracted text never replace actual screenshot inspection.

## Generated Documents and Dashboard

Version 1.1 separates semantic planning from deterministic delivery. Codex writes a generation plan after review. `run_pipeline.py` applies it to the original DOCX, registers metadata, starts a loopback-only Flask dashboard, and opens the browser.

The server has no upload or model endpoint and only downloads files registered by metadata in the selected output directory. It binds to `127.0.0.1` and is not exposed to the local network.

## Style Preservation

The original DOCX is never overwritten. Existing runs, fonts, colors, images, tables, and paragraph styles are not reset. New runs carry a `Codex 新增` label, an explicit font, and a category color. Editable style preservation is promised only for DOCX; PDF remains an analysis input unless locally converted first.

## Interactive Boundary

Semantic classification and plan authorship require Codex judgment. Delivery after the plan exists is deterministic and uses one command. This boundary avoids pretending a local Flask app can invoke Codex without an API.

## Scoring

Teacher rubrics override the default rubric. Without course-specific weights, submission readiness and evidence-based dimension states are preferred over false-precision scores.
