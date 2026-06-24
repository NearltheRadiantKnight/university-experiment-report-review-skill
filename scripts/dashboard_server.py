#!/usr/bin/env python3
"""Serve loopback-only report deliverables, QA state, and local review feedback."""
from __future__ import annotations
import argparse,hashlib,json,mimetypes,re
from datetime import datetime
from pathlib import Path
from typing import Any
from flask import Flask,abort,jsonify,render_template,request,send_file
ROOT=Path(__file__).resolve().parents[1]; TEMPLATE_DIR=ROOT/"assets"/"dashboard"/"templates"; STATIC_DIR=ROOT/"assets"/"dashboard"/"static"
DASHBOARD_API_VERSION=2
PRIORITY_LABELS={"blocker":"阻塞","high":"高","medium":"中","low":"低","optional":"可选"}

def _output_dir_id(output_dir:Path)->str:
 return hashlib.sha256(str(output_dir.resolve()).casefold().encode("utf-8")).hexdigest()[:16]

def re_full_job_id(job_id:str)->bool: return re.fullmatch(r"\d{8}-\d{6}-\d{6}",job_id) is not None

def _files(record:dict[str,Any],output_dir:Path)->list[dict[str,Any]]:
 raw=record.get("generated_files") or [{"kind":"annotated","label":record.get("report_label","DOCX"),"name":record.get("generated_name","")}]; files=[]
 for item in raw:
  name=str(item.get("name","")); kind=str(item.get("kind","file"))
  if Path(name).name!=name or not (output_dir/name).is_file(): continue
  entry=dict(item); entry["download_url"]=f"/api/reports/{record.get('job_id','')}/download/{kind}"; files.append(entry)
 return files

def _load_metadata(output_dir:Path,job_id:str)->dict[str,Any]:
 if not re_full_job_id(job_id): abort(404)
 path=output_dir/f"{job_id}.metadata.json"
 if not path.is_file(): abort(404)
 try: metadata=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): abort(404)
 return metadata

def _save_metadata(output_dir:Path,metadata:dict[str,Any])->None:
 path=output_dir/f"{metadata['job_id']}.metadata.json"; temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)

def _metadata_records(output_dir:Path)->list[dict[str,Any]]:
 records=[]
 if not output_dir.is_dir(): return records
 for path in sorted(output_dir.glob("*.metadata.json"),reverse=True):
  try: record=json.loads(path.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError): continue
  if not isinstance(record,dict): continue
  record["files"]=_files(record,output_dir)
  if not record["files"]: continue
  record["download_url"]=next((f["download_url"] for f in record["files"] if f["kind"]=="annotated"),record["files"][0]["download_url"]); records.append(record)
 return records

def _resolve_file(output_dir:Path,job_id:str,kind:str)->tuple[dict[str,Any],Path]:
 metadata=_load_metadata(output_dir,job_id); matches=[item for item in _files(metadata,output_dir) if item["kind"]==kind]
 if not matches: abort(404)
 path=(output_dir/str(matches[0]["name"])).resolve()
 if path.parent!=output_dir.resolve() or not path.is_file(): abort(404)
 return metadata,path

def _feedback_path(output_dir:Path,job_id:str)->Path: return output_dir/f"{job_id}.feedback.json"

def _feedback_records(output_dir:Path)->list[dict[str,Any]]:
 records=[]
 if not output_dir.is_dir(): return records
 for path in sorted(output_dir.glob("*.feedback.json"),reverse=True):
  try: data=json.loads(path.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError): continue
  if not isinstance(data,dict): continue
  records.append(data)
 return records

def _default_feedback(metadata:dict[str,Any])->dict[str,Any]:
 actions=[]
 for index,action in enumerate(metadata.get("actions",[]),1): actions.append({"action_id":index,"label":str(action.get("label",f"行动 {index}")),"priority":str(action.get("priority","medium")),"priority_label":str(action.get("priority_label",PRIORITY_LABELS.get(str(action.get("priority","medium")),"中"))),"status":"open","note":"","correction":""})
 return {"job_id":metadata["job_id"],"source_name":metadata.get("source_name"),"updated_at":None,"confirmed_context":{},"actions":actions}

def _load_feedback(output_dir:Path,metadata:dict[str,Any])->dict[str,Any]:
 path=_feedback_path(output_dir,str(metadata["job_id"]))
 if not path.is_file(): return _default_feedback(metadata)
 try: data=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): return _default_feedback(metadata)
 return data if isinstance(data,dict) else _default_feedback(metadata)

def _validate_feedback(payload:Any,metadata:dict[str,Any])->dict[str,Any]:
 if not isinstance(payload,dict): abort(400,"Feedback must be a JSON object.")
 raw_actions=payload.get("actions",[])
 if not isinstance(raw_actions,list) or len(raw_actions)>100: abort(400,"Invalid actions list.")
 actions=[]
 for item in raw_actions:
  if not isinstance(item,dict): abort(400,"Every action must be an object.")
  status=str(item.get("status","open"))
  if status not in {"open","done","skipped","needs-review"}: abort(400,"Invalid action status.")
  note=str(item.get("note","")).strip(); correction=str(item.get("correction","")).strip()
  if len(note)>1000 or len(correction)>2000: abort(400,"Feedback text is too long.")
  actions.append({"action_id":int(item.get("action_id",len(actions)+1)),"label":str(item.get("label",""))[:160],"priority":str(item.get("priority","medium"))[:20],"priority_label":str(item.get("priority_label","")),"status":status,"note":note,"correction":correction})
 context=payload.get("confirmed_context",{})
 if not isinstance(context,dict) or len(context)>30: abort(400,"Invalid confirmed_context.")
 clean_context={str(key)[:80]:str(value)[:1000] for key,value in context.items()}
 return {"job_id":metadata["job_id"],"source_name":metadata.get("source_name"),"updated_at":datetime.now().astimezone().isoformat(timespec="seconds"),"confirmed_context":clean_context,"actions":actions}

def create_app(output_dir:Path)->Flask:
 resolved=output_dir.resolve(); resolved.mkdir(parents=True,exist_ok=True); app=Flask(__name__,template_folder=str(TEMPLATE_DIR),static_folder=str(STATIC_DIR)); app.config["MAX_CONTENT_LENGTH"]=64*1024
 @app.get("/")
 def index()->str: return render_template("index.html")
 @app.get("/api/health")
 def health()->Any: return jsonify({"ok":True,"service":"university-experiment-report-dashboard","api_version":DASHBOARD_API_VERSION,"output_dir_id":_output_dir_id(resolved),"local_only":True,"external_model_api":False})
 @app.get("/api/reports")
 def reports()->Any: return jsonify({"reports":_metadata_records(resolved)})
 @app.get("/api/feedback")
 def feedback_list()->Any: return jsonify({"feedback":_feedback_records(resolved)})
 @app.get("/api/reports/<job_id>/metadata")
 def report_metadata(job_id:str)->Any: return jsonify(_load_metadata(resolved,job_id))
 @app.get("/api/reports/<job_id>/download")
 def download_legacy(job_id:str)->Any:
  _,path=_resolve_file(resolved,job_id,"annotated"); return send_file(path,as_attachment=True,download_name=path.name,mimetype=mimetypes.guess_type(path.name)[0])
 @app.get("/api/reports/<job_id>/download/<kind>")
 def download(job_id:str,kind:str)->Any:
  _,path=_resolve_file(resolved,job_id,kind); return send_file(path,as_attachment=True,download_name=path.name,mimetype=mimetypes.guess_type(path.name)[0])
 @app.get("/api/reports/<job_id>/feedback")
 def get_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); return jsonify(_load_feedback(resolved,metadata))
 @app.post("/api/reports/<job_id>/feedback")
 def save_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); feedback=_validate_feedback(request.get_json(silent=True),metadata); path=_feedback_path(resolved,job_id); temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
  files=metadata.setdefault("generated_files",[])
  if not any(item.get("kind")=="feedback" for item in files): files.append({"kind":"feedback","label":"反馈 JSON","name":path.name})
  _save_metadata(resolved,metadata); return jsonify({"ok":True,"feedback":feedback,"download_url":f"/api/reports/{job_id}/download/feedback"})
 @app.put("/api/reports/<job_id>/feedback")
 def replace_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); feedback=_validate_feedback(request.get_json(silent=True),metadata); path=_feedback_path(resolved,job_id); temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
  files=metadata.setdefault("generated_files",[])
  if not any(item.get("kind")=="feedback" for item in files): files.append({"kind":"feedback","label":"反馈 JSON","name":path.name})
  _save_metadata(resolved,metadata); return jsonify({"ok":True,"feedback":feedback})
 return app

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path,required=True); parser.add_argument("--port",type=int,default=8765); args=parser.parse_args()
 if args.port<1024 or args.port>65535: parser.error("--port must be between 1024 and 65535")
 create_app(args.output_dir).run(host="127.0.0.1",port=args.port,debug=False,use_reloader=False); return 0
if __name__=="__main__": raise SystemExit(main())