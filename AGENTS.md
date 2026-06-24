# university-experiment-report-review-skill

## Purpose

Analyze university laboratory-report files and screenshots locally. Classify each report as blank, partial, or completed; guide blank templates; review completed work; generate structured DOCX deliverables from the original; run quality gates; open a local dashboard; and provide annotated-report, action-checklist, and quality-report downloads across AgentSkills-compatible agents, with local domain routing, render-state QA, and feedback continuation.

## Activation

Use for explicit `/university-experiment-report-review-skill` invocations and experiment-report requests involving blank templates, execution guidance, completed-report review, screenshots, downloadable DOCX generation, local frontend display, original font preservation, or colored revisions. Do not activate for unrelated education or general writing questions.

## Usage

Read `SKILL.md` completely. Treat teacher rubrics and experiment instructions as authoritative. Use `scripts/inspect_report.py` to prepare text, image contexts, and the contact sheet. After semantic review, write a structured plan matching `assets/generation-plan.schema.json`, validate it, then run `scripts/run_pipeline.py` once to generate the DOCX and open the local download page. Never call an external model API or remote OCR service.

## Required Behavior

- Read all supplied files before judging.
- Inspect important screenshots visually and separate observed, inferred, and unreadable content.
- Never fabricate execution, results, commands, data, screenshots, citations, or requirements.
- Give actionable, located revisions; say “可以提交” when no material issue remains.
- Keep student documents local and avoid repeating sensitive credentials.
- Preserve original DOCX runs and styles; add only clearly marked colored Codex content.
- Use `execution` for blank templates and `revision` for partial or completed reports.

## Files

- `SKILL.md`: complete workflow and output contract.
- `scripts/inspect_report.py`: local text, image, contact-sheet, and domain-routing preparation.
- `scripts/domain_router.py`: selects one of five local domain profiles.
- `scripts/qa_report.py`: structural QA plus optional DOCX render QA.
- `scripts/agent_compat.py`: Codex, Claude Code, and OpenClaw contract/runtime smoke checks.
- `scripts/build_report.py`: style-preserving DOCX annotation engine.
- `scripts/run_pipeline.py`: one-command generation and dashboard delivery.
- `scripts/dashboard_server.py`: loopback-only frontend and downloads.
- `assets/generation-plan.schema.json`: contract for Codex-authored changes.
- `references/generated-document-workflow.md`: generation methodology and boundaries.
- `evals/`: regression criteria and representative cases.

## Cross-Agent Paths

- Claude Code: `~/.claude/skills/university-experiment-report-review-skill`
- Codex and universal AgentSkills: `~/.agents/skills/university-experiment-report-review-skill`
- OpenClaw shared: `~/.openclaw/skills/university-experiment-report-review-skill`
- OpenClaw workspace: `<workspace>/skills/university-experiment-report-review-skill`

OpenClaw loads higher-precedence workspace skills before shared managed skills. Use a new session after changing eligibility or allowlists.