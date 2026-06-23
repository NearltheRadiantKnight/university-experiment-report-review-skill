# University Experiment Report Review Skill Eval

These checks define whether the skill performs an evidence-based local review. Semantic criteria are intentionally `llm-judge` because classification, technical reasoning, screenshot interpretation, and feedback usefulness require model judgment. The bundled runner validates the contract and prints these checks as a review checklist.

```json
{
  "skill": "university-experiment-report-review-skill",
  "criteria": [
    {
      "id": "evidence-based-state-classification",
      "text": "The output classifies the report as blank, partial, or completed and cites observable evidence rather than relying only on length or filename.",
      "type": "llm-judge"
    },
    {
      "id": "actionable-blank-guidance",
      "text": "For a blank template, the output gives an executable experiment and writing plan with evidence-capture checkpoints and does not fabricate commands, measurements, or results.",
      "type": "llm-judge"
    },
    {
      "id": "complete-finished-review",
      "text": "For partial or completed work, the output covers completeness, requirement alignment, technical correctness, reproducibility, evidence/screenshots, analysis, conclusions, and writing as applicable.",
      "type": "llm-judge"
    },
    {
      "id": "located-revision-actions",
      "text": "Every material issue includes a location or evidence reference, its impact, a concrete revision action, and a completion or verification condition.",
      "type": "llm-judge"
    },
    {
      "id": "honest-visual-claims",
      "text": "Screenshot findings distinguish directly visible content, contextual inference, and unreadable or unverifiable content, without treating OCR or captions as visual proof.",
      "type": "llm-judge"
    },
    {
      "id": "honest-submission-decision",
      "text": "The output prioritizes blockers, states uncertainty, avoids forced criticism, and clearly says the report can be submitted when no material issue remains.",
      "type": "llm-judge"
    }
  ],
  "golden": [
    {
      "id": "blank-template",
      "input": "golden/blank-template/input.md",
      "expected": null,
      "split": "val",
      "expected_status": "pending-first-green"
    },
    {
      "id": "partial-unreadable-screenshot",
      "input": "golden/partial-unreadable-screenshot/input.md",
      "expected": null,
      "split": "val",
      "expected_status": "pending-first-green"
    },
    {
      "id": "strong-completed-report",
      "input": "golden/strong-completed-report/input.md",
      "expected": null,
      "split": "val",
      "expected_status": "pending-first-green"
    }
  ]
}
```
