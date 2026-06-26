#!/usr/bin/env python3
"""Manage local feedback lifecycle records for report review self-iteration."""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
from typing import Any

FEEDBACK_STATUSES={"active"}
INTERPRETATION_STATUSES={"drafted","interpreted","needs_clarification","superseded"}
INTERPRETATION_SCOPES={"report_specific","reusable_skill_rule","personal_preference","needs_clarification",None}
MODIFICATION_STATUSES={"drafted","needs_revision","validated","applied"}

def now()->str: return datetime.now().astimezone().isoformat(timespec="seconds")
def _id(prefix:str,*parts:object)->str:
 raw="\x1f".join(str(part) for part in parts)
 return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"
def _write_json(path:Path,data:dict[str,Any])->None:
 path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(".tmp")
 temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
def _read_json(path:Path)->dict[str,Any]|None:
 try: data=json.loads(path.read_text(encoding="utf-8-sig"))
 except (OSError,json.JSONDecodeError): return None
 return data if isinstance(data,dict) else None
def feedback_dir(root:Path)->Path: return root/"feedback-pool"
def interpretation_dir(root:Path)->Path: return root/"feedback-interpretations"
def modification_dir(root:Path)->Path: return root/"skill-modifications"
def lifecycle_dir(root:Path)->Path: return root/"feedback-lifecycle"
def events_path(root:Path)->Path: return lifecycle_dir(root)/"events.jsonl"
def _feedback_path(root:Path,feedback_id:str)->Path: return feedback_dir(root)/f"{feedback_id}.feedback.json"
def _interpretation_path(root:Path,interpretation_id:str)->Path: return interpretation_dir(root)/f"{interpretation_id}.interpretation.json"
def _modification_path(root:Path,modification_id:str)->Path: return modification_dir(root)/f"{modification_id}.modification.json"

def list_records(directory:Path,suffix:str)->list[dict[str,Any]]:
 if not directory.is_dir(): return []
 records=[]
 for path in sorted(directory.glob(f"*{suffix}")):
  data=_read_json(path)
  if data is not None:
   data.setdefault("path",str(path)); records.append(data)
 return records
def list_feedback(root:Path)->list[dict[str,Any]]: return list_records(feedback_dir(root),".feedback.json")
def list_interpretations(root:Path)->list[dict[str,Any]]: return list_records(interpretation_dir(root),".interpretation.json")
def list_modifications(root:Path)->list[dict[str,Any]]: return list_records(modification_dir(root),".modification.json")
def list_events(root:Path)->list[dict[str,Any]]:
 path=events_path(root)
 if not path.is_file(): return []
 events=[]
 for line in path.read_text(encoding="utf-8-sig").splitlines():
  if not line.strip(): continue
  try: data=json.loads(line)
  except json.JSONDecodeError: continue
  if isinstance(data,dict): events.append(data)
 return events
def append_event(root:Path,event_type:str,**fields:Any)->dict[str,Any]:
 path=events_path(root); path.parent.mkdir(parents=True,exist_ok=True)
 event={"event_id":_id("evt",event_type,fields,now()),"type":event_type,"status":"ready_for_agent","created_at":now(),**fields}
 with path.open("a",encoding="utf-8") as handle: handle.write(json.dumps(event,ensure_ascii=False)+"\n")
 return event

def _blank_interpretation(root:Path,feedback:dict[str,Any])->dict[str,Any]:
 interpretation_id=_id("interp",feedback["feedback_id"])
 return {"interpretation_id":interpretation_id,"feedback_id":feedback["feedback_id"],"status":"drafted","raw_text":feedback.get("raw_text",""),"meaning":None,"scope":None,"confidence":None,"uncertainties":[],"recommended_action":None,"created_at":now(),"updated_at":now()}

def upsert_feedback(root:Path,job_id:str,source_name:str|None,action:dict[str,Any],event_type:str="feedback_saved")->dict[str,Any]|None:
 raw_text=str(action.get("correction") or action.get("note") or "").strip()
 if not raw_text: return None
 action_id=action.get("action_id")
 label=str(action.get("label","")).strip()
 feedback_id=_id("fb",job_id,action_id,label)
 path=_feedback_path(root,feedback_id); previous=_read_json(path) or {}
 record={"feedback_id":feedback_id,"job_id":job_id,"source_name":source_name,"action_id":action_id,"label":label,"raw_text":raw_text,"status":"active","created_at":previous.get("created_at") or now(),"updated_at":now()}
 _write_json(path,record)
 append_event(root,event_type,feedback_id=feedback_id,job_id=job_id)
 interpretation=_blank_interpretation(root,record)
 existing=_read_json(_interpretation_path(root,interpretation["interpretation_id"])) or {}
 if existing.get("raw_text")!=raw_text or existing.get("status") in {None,"superseded"}:
  interpretation["created_at"]=existing.get("created_at") or interpretation["created_at"]
  _write_json(_interpretation_path(root,interpretation["interpretation_id"]),interpretation)
  append_event(root,"interpretation_drafted",feedback_id=feedback_id,interpretation_id=interpretation["interpretation_id"],job_id=job_id)
 return record

def sync_feedback_payload(root:Path,feedback:dict[str,Any],event_type:str="feedback_saved")->dict[str,Any]:
 job_id=str(feedback.get("job_id","")); source_name=feedback.get("source_name")
 saved=[]
 for action in feedback.get("actions",[]):
  if isinstance(action,dict):
   record=upsert_feedback(root,job_id,source_name,action,event_type)
   if record: saved.append(record)
 return {"ok":True,"saved":saved,"saved_count":len(saved),"lifecycle_status":"recorded" if saved else "not-needed"}

def _rewrite_events_without(root:Path,feedback_ids:set[str],modification_ids:set[str])->int:
 path=events_path(root)
 if not path.is_file(): return 0
 kept=[]; removed=0
 for line in path.read_text(encoding="utf-8-sig").splitlines():
  if not line.strip(): continue
  try: event=json.loads(line)
  except json.JSONDecodeError:
   kept.append(line); continue
  if not isinstance(event,dict):
   kept.append(line); continue
  feedback_match=str(event.get("feedback_id","") or "") in feedback_ids
  modification_match=str(event.get("modification_id","") or "") in modification_ids or str(event.get("reverts_modification_id","") or "") in modification_ids
  if feedback_match or modification_match: removed+=1
  else: kept.append(json.dumps(event,ensure_ascii=False))
 if kept: path.write_text("\n".join(kept)+"\n",encoding="utf-8")
 else: path.unlink(missing_ok=True)
 return removed

def purge_feedback(root:Path,feedback_id:str,reason:str="user_purged")->dict[str,Any]:
 feedback_ids={str(feedback_id)}; modification_ids=set(); removed={"feedback":0,"interpretations":0,"modifications":0,"events":0}; job_ids=set()
 path=_feedback_path(root,feedback_id); feedback=_read_json(path)
 if feedback and feedback.get("job_id") is not None: job_ids.add(str(feedback.get("job_id")))
 if path.is_file(): path.unlink(); removed["feedback"]+=1
 for interpretation in list_interpretations(root):
  if str(interpretation.get("feedback_id")) in feedback_ids:
   _interpretation_path(root,str(interpretation.get("interpretation_id"))).unlink(missing_ok=True); removed["interpretations"]+=1
 for modification in list_modifications(root):
  if str(modification.get("source_feedback_id")) in feedback_ids:
   modification_id=str(modification.get("modification_id"))
   modification_ids.add(modification_id)
   _modification_path(root,modification_id).unlink(missing_ok=True); removed["modifications"]+=1
 if modification_ids:
  for modification in list_modifications(root):
   if str(modification.get("reverts_modification_id")) in modification_ids:
    modification_id=str(modification.get("modification_id"))
    modification_ids.add(modification_id)
    _modification_path(root,modification_id).unlink(missing_ok=True); removed["modifications"]+=1
 removed["events"]=_rewrite_events_without(root,feedback_ids,modification_ids)
 return {"ok":True,"purged":removed,"purged_count":sum(removed.values()),"feedback_id":feedback_id,"job_ids":sorted(job_ids),"reason":reason}

def purge_job_feedback(root:Path,job_id:str,reason:str="user_purged")->dict[str,Any]:
 feedback_ids=[str(feedback["feedback_id"]) for feedback in list_feedback(root) if str(feedback.get("job_id"))==str(job_id)]
 results=[purge_feedback(root,feedback_id,reason) for feedback_id in feedback_ids]
 return {"ok":True,"job_id":str(job_id),"purged_feedback_ids":feedback_ids,"purged_count":sum(item.get("purged_count",0) for item in results),"results":results}
def run_deterministic(root:Path)->dict[str,Any]:
 return {"ok":True,"feedback":len(list_feedback(root)),"interpretations":len(list_interpretations(root)),"modifications":len(list_modifications(root)),"events":len(list_events(root))}

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,required=True)
 group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument("--list-feedback",action="store_true"); group.add_argument("--list-interpretations",action="store_true"); group.add_argument("--list-modifications",action="store_true"); group.add_argument("--list-events",action="store_true"); group.add_argument("--run",action="store_true"); group.add_argument("--run-agent"); group.add_argument("--purge-feedback")
 args=parser.parse_args(); root=args.root.resolve()
 if args.list_feedback: data=list_feedback(root)
 elif args.list_interpretations: data=list_interpretations(root)
 elif args.list_modifications: data=list_modifications(root)
 elif args.list_events: data=list_events(root)
 elif args.run or args.run_agent: data=run_deterministic(root)|({"agent":args.run_agent} if args.run_agent else {})
 elif args.purge_feedback: data=purge_feedback(root,args.purge_feedback)
 else: data={}
 print(json.dumps(data,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
