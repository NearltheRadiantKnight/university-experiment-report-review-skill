#!/usr/bin/env python3
"""Manage local skill-improvement requests created by the dashboard."""
from __future__ import annotations
import argparse,json
from datetime import datetime
from pathlib import Path
from typing import Any

def _records(queue_dir:Path)->list[tuple[Path,dict[str,Any]]]:
 records=[]
 if not queue_dir.is_dir(): return records
 for path in sorted(queue_dir.glob("*.skill-improvement.json")):
  try: data=json.loads(path.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError): continue
  if isinstance(data,dict): records.append((path,data))
 return records

def _write(path:Path,data:dict[str,Any])->None:
 temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)

def claim_next(queue_dir:Path,agent:str)->dict[str,Any]|None:
 for path,data in _records(queue_dir):
  if data.get("status")!="pending-agent": continue
  data["status"]="in-progress"; data["claimed_by"]=agent; data["claimed_at"]=datetime.now().astimezone().isoformat(timespec="seconds"); _write(path,data); data["path"]=str(path); return data
 return None

def finish(queue_dir:Path,request_id:str,status:str,summary:str)->dict[str,Any]:
 path=queue_dir/f"{request_id}.skill-improvement.json"
 if not path.is_file(): raise ValueError("Request not found.")
 data=json.loads(path.read_text(encoding="utf-8")); data["status"]=status; data["completed_at"]=datetime.now().astimezone().isoformat(timespec="seconds"); data["result_summary"]=summary[:2000]; _write(path,data); return data

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--queue-dir",type=Path,required=True); parser.add_argument("--list",action="store_true"); parser.add_argument("--claim-next"); parser.add_argument("--complete"); parser.add_argument("--fail"); parser.add_argument("--summary",default=""); args=parser.parse_args()
 if args.list: print(json.dumps([data|{"path":str(path)} for path,data in _records(args.queue_dir)],ensure_ascii=False,indent=2)); return 0
 if args.claim_next: print(json.dumps(claim_next(args.queue_dir,args.claim_next),ensure_ascii=False,indent=2)); return 0
 request_id=args.complete or args.fail
 if request_id: print(json.dumps(finish(args.queue_dir,request_id,"completed" if args.complete else "failed",args.summary),ensure_ascii=False,indent=2)); return 0
 parser.error("Choose --list, --claim-next, --complete, or --fail.")
 return 2
if __name__=="__main__": raise SystemExit(main())
