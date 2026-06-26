#!/usr/bin/env python3
"""Compatibility wrapper for feedback lifecycle records."""
from __future__ import annotations
import argparse,json,sys
from datetime import datetime
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from feedback_lifecycle import events_path,list_events,list_feedback,list_interpretations,list_modifications,run_deterministic

def _write_events(queue_dir:Path,events:list[dict[str,Any]])->None:
 path=events_path(queue_dir.parent if queue_dir.name=="skill-improvement-queue" else queue_dir)
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text("\n".join(json.dumps(event,ensure_ascii=False) for event in events)+("\n" if events else ""),encoding="utf-8")

def _root(queue_dir:Path)->Path:
 return queue_dir.parent if queue_dir.name=="skill-improvement-queue" else queue_dir

def records(queue_dir:Path)->list[dict[str,Any]]:
 root=_root(queue_dir)
 return [{"request_id":"feedback-lifecycle","status":"ready_for_agent","mode":"feedback-lifecycle","feedback":list_feedback(root),"interpretations":list_interpretations(root),"modifications":list_modifications(root),"events":list_events(root),"path":str(root/"feedback-lifecycle"/"events.jsonl")}]

def claim_next(queue_dir:Path,agent:str)->dict[str,Any]|None:
 root=_root(queue_dir); events=list_events(root)
 for event in events:
  if event.get("status")!="ready_for_agent": continue
  event["status"]="processed"; event["processed_by"]=agent; event["processed_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
  _write_events(queue_dir,events)
  return {"request_id":"feedback-lifecycle","status":"processed","claimed_by":agent,"event":event,"path":str(events_path(root))}
 return None

def finish(queue_dir:Path,request_id:str,status:str,summary:str)->dict[str,Any]:
 root=_root(queue_dir); result=run_deterministic(root)
 result.update({"request_id":request_id,"status":"processed","result_summary":summary[:2000]})
 return result

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--queue-dir",type=Path,required=True); parser.add_argument("--list",action="store_true"); parser.add_argument("--claim-next"); parser.add_argument("--complete"); parser.add_argument("--fail"); parser.add_argument("--summary",default=""); args=parser.parse_args()
 if args.list: print(json.dumps(records(args.queue_dir),ensure_ascii=False,indent=2)); return 0
 if args.claim_next: print(json.dumps(claim_next(args.queue_dir,args.claim_next),ensure_ascii=False,indent=2)); return 0
 request_id=args.complete or args.fail
 if request_id: print(json.dumps(finish(args.queue_dir,request_id,"processed",args.summary),ensure_ascii=False,indent=2)); return 0
 parser.error("Choose --list, --claim-next, --complete, or --fail.")
 return 2
if __name__=="__main__": raise SystemExit(main())
