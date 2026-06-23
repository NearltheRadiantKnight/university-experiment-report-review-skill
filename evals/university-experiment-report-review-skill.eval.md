# University Experiment Report Review Skill Eval

This contract covers evidence-based review, style-preserving document generation, and local dashboard delivery. Semantic checks remain `llm-judge`; deterministic formatting and download behavior are covered by the Python test suite.

```json
{
  "skill": "university-experiment-report-review-skill",
  "criteria": [
    {"id": "state-classification", "text": "The output classifies the report as blank, partial, or completed and cites observable evidence.", "type": "llm-judge"},
    {"id": "honest-guidance", "text": "Blank-template guidance is executable and does not fabricate commands, measurements, screenshots, or results.", "type": "llm-judge"},
    {"id": "complete-review", "text": "Partial or completed work is reviewed for completeness, alignment, correctness, reproducibility, evidence, analysis, conclusion support, and writing as applicable.", "type": "llm-judge"},
    {"id": "honest-visual-claims", "text": "Screenshot findings distinguish visible content, inference, and unreadable content.", "type": "llm-judge"},
    {"id": "correct-report-kind", "text": "A blank DOCX produces an execution plan/report and a partial or completed DOCX produces a revision plan/report.", "type": "llm-judge"},
    {"id": "source-based-generation", "text": "The generated report is based on the uploaded original document rather than an unrelated replacement document.", "type": "llm-judge"},
    {"id": "style-differentiation", "text": "Original content retains its formatting while every Codex addition is clearly labeled and visually differentiated by font color.", "type": "llm-judge"},
    {"id": "download-delivery", "text": "The response provides the generated file path and local dashboard URL, and the dashboard offers a DOCX download.", "type": "llm-judge"},
    {"id": "local-only-boundary", "text": "No external model API, remote OCR, cloud upload, or public network listener is introduced.", "type": "llm-judge"},
    {"id": "submission-decision", "text": "The output prioritizes blockers and clearly says when the report can be submitted without forced criticism.", "type": "llm-judge"}
  ],
  "golden": [
    {"id": "blank-template", "input": "golden/blank-template/input.md", "expected": null, "split": "val", "expected_status": "pending-first-green"},
    {"id": "partial-unreadable-screenshot", "input": "golden/partial-unreadable-screenshot/input.md", "expected": null, "split": "val", "expected_status": "pending-first-green"},
    {"id": "strong-completed-report", "input": "golden/strong-completed-report/input.md", "expected": null, "split": "val", "expected_status": "pending-first-green"}
  ]
}
```
