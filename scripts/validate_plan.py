#!/usr/bin/env python3
"""Validate generation plans before they can modify a DOCX."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

VALID_REPORT_KINDS={"execution","revision"}
VALID_SOURCE_STATES={"blank","partial","completed"}
VALID_CATEGORIES={"guidance","evidence","writing","warning","issue","suggestion","example","praise","summary"}
VALID_BLOCK_TYPES={"paragraph","bullets","checklist","table"}
VALID_DOMAINS={"software-testing","networking","database","os-programming","physical-science"}
SCORE_PATTERN=re.compile(r"(?<!\d)(?:100|[0-9]{1,2})(?:\.\d+)?\s*(?:/\s*100|分|%)(?!\d)")

class PlanValidationError(ValueError):
    """Raised when a generation plan violates a quality gate."""

def _addition_text(addition: dict[str,Any])->str:
    parts=[str(addition.get("label","")),str(addition.get("text",""))]
    parts.extend(str(item) for item in addition.get("items",[]))
    for row in addition.get("rows",[]): parts.extend(str(cell) for cell in row)
    return " ".join(parts)

def validate_generation_plan(plan: dict[str,Any])->list[str]:
    if plan.get("report_kind") not in VALID_REPORT_KINDS: raise PlanValidationError("report_kind must be execution or revision.")
    if plan.get("source_state") not in VALID_SOURCE_STATES: raise PlanValidationError("source_state must be blank, partial, or completed.")
    domain=plan.get("domain_profile")
    if domain is not None and domain not in VALID_DOMAINS: raise PlanValidationError("domain_profile is not recognized.")
    if domain and not str(plan.get("domain_profile_basis","")).strip(): warnings=["domain_profile_basis is missing."]
    else: warnings=[]
    additions=plan.get("additions")
    if not isinstance(additions,list): raise PlanValidationError("additions must be an array.")
    if len(additions)>24: raise PlanValidationError("A plan may contain at most 24 additions.")
    score_allowed=bool(plan.get("rubric_provided") or plan.get("score_requested"))
    score_text=" ".join([str(plan.get("summary","")),str(plan.get("verdict",""))]+[_addition_text(x) for x in additions if isinstance(x,dict)])
    if SCORE_PATTERN.search(score_text) and not score_allowed:
        raise PlanValidationError("Numeric scores require rubric_provided=true or score_requested=true. Use submission readiness instead.")
    if score_allowed and not str(plan.get("scoring_basis","")).strip():
        raise PlanValidationError("scoring_basis is required when a numeric score is used.")
    for index,addition in enumerate(additions,1):
        if not isinstance(addition,dict): raise PlanValidationError(f"Addition {index} must be an object.")
        if str(addition.get("category","")) not in VALID_CATEGORIES: raise PlanValidationError(f"Addition {index} has an invalid category.")
        block_type=str(addition.get("block_type","paragraph"))
        if block_type not in VALID_BLOCK_TYPES: raise PlanValidationError(f"Addition {index} has an invalid block_type.")
        position=str(addition.get("position","after"))
        if position!="append" and "anchor_text" not in addition and "paragraph_index" not in addition:
            raise PlanValidationError(f"Addition {index} needs an anchor or position=append.")
        text=str(addition.get("text","")).strip(); items=addition.get("items",[])
        if block_type=="paragraph":
            if not text: raise PlanValidationError(f"Paragraph addition {index} needs text.")
            if len(text)>420: raise PlanValidationError(f"Paragraph addition {index} is too long ({len(text)} chars); use bullets, checklist, or table.")
        elif block_type in {"bullets","checklist"}:
            if not isinstance(items,list) or not items: raise PlanValidationError(f"{block_type} addition {index} needs items.")
            if any(not str(item).strip() or len(str(item))>350 for item in items): raise PlanValidationError(f"Addition {index} contains an empty or overlong item.")
        else:
            columns=addition.get("columns",[]); rows=addition.get("rows",[])
            if not isinstance(columns,list) or not columns: raise PlanValidationError(f"Table addition {index} needs columns.")
            if not isinstance(rows,list): raise PlanValidationError(f"Table addition {index} needs rows.")
            if any(not isinstance(row,list) or len(row)!=len(columns) for row in rows): raise PlanValidationError(f"Table addition {index} rows must match column count.")
        if not addition.get("evidence_basis"): warnings.append(f"Addition {index} has no evidence_basis.")
    return warnings

def load_and_validate(path:Path)->tuple[dict[str,Any],list[str]]:
    try: data=json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,json.JSONDecodeError) as exc: raise PlanValidationError(f"Plan JSON is invalid: {exc}") from exc
    if not isinstance(data,dict): raise PlanValidationError("Plan root must be an object.")
    return data,validate_generation_plan(data)

def main()->int:
    parser=argparse.ArgumentParser(description="Validate an experiment report generation plan."); parser.add_argument("plan",type=Path); args=parser.parse_args()
    try: _,warnings=load_and_validate(args.plan)
    except PlanValidationError as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr); return 1
    print(json.dumps({"ok":True,"warnings":warnings},ensure_ascii=False,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
