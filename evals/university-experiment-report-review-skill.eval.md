# University Experiment Report Review Skill Eval

This contract covers evidence-based review, domain adaptation, structured delivery, render honesty, feedback continuity, and cross-agent compatibility.

```json
{
  "skill": "university-experiment-report-review-skill",
  "criteria": [
    {"id": "evidence-and-domain", "text": "The output classifies the report from observable evidence and selects or explicitly declines a relevant domain profile.", "type": "llm-judge"},
    {"id": "honest-content", "text": "The output does not fabricate execution, results, requirements, screenshot details, or verification and separates visible, inferred, and unreadable evidence.", "type": "llm-judge"},
    {"id": "structured-actions", "text": "Long workflows use bullets, checklists, or tables; every action has a priority and evidence basis; numeric scores obey the rubric/request gate.", "type": "llm-judge"},
    {"id": "clean-generation", "text": "Generated reports use strict anchors, preserve source content, contain no accidental unlocated section or duplicate summary, and emit an action checklist plus quality metadata.", "type": "llm-judge"},
    {"id": "render-and-feedback", "text": "Render QA is marked passed, failed, or unavailable without pretending; the local dashboard can persist action feedback and export feedback JSON without a model API.", "type": "llm-judge"},
    {"id": "cross-agent-contract", "text": "Codex, Claude Code, and OpenClaw contracts and installers validate; missing or blocked runtimes are reported honestly rather than treated as passed.", "type": "llm-judge"}
  ],
  "golden": [
    {"id": "blank-template", "input": "golden/blank-template/input.md", "expected": "golden/blank-template/expected.md", "split": "val"},
    {"id": "partial-unreadable-screenshot", "input": "golden/partial-unreadable-screenshot/input.md", "expected": "golden/partial-unreadable-screenshot/expected.md", "split": "val"},
    {"id": "strong-completed-report", "input": "golden/strong-completed-report/input.md", "expected": "golden/strong-completed-report/expected.md", "split": "val"},
    {"id": "structured-output-regression", "input": "golden/structured-output-regression/input.md", "expected": "golden/structured-output-regression/expected.md", "split": "val"}
  ]
}
```