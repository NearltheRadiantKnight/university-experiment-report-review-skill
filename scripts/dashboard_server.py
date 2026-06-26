#!/usr/bin/env python3
"""Serve loopback-only report deliverables, QA state, and local review feedback."""
from __future__ import annotations
import argparse,hashlib,json,mimetypes,re
from datetime import datetime
from pathlib import Path
from typing import Any
from flask import Flask,abort,jsonify,render_template,request,send_file
from feedback_lifecycle import list_events,list_feedback,list_interpretations,list_modifications,purge_feedback,purge_job_feedback,sync_feedback_payload
from output_paths import resolve_output_dir
from qa_report import render_report
ROOT=Path(__file__).resolve().parents[1]; TEMPLATE_DIR=ROOT/"assets"/"dashboard"/"templates"; STATIC_DIR=ROOT/"assets"/"dashboard"/"static"
DASHBOARD_API_VERSION=4
DASHBOARD_ASSET_VERSION="1.5.11"
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

def _public_record(record:dict[str,Any],output_dir:Path)->dict[str,Any]:
 files=[item for item in _files(record,output_dir) if item.get("kind")=="annotated"]
 screenshots=[]
 for index,item in enumerate(record.get("screenshot_evidence",[])):
  entry={key:item.get(key) for key in ("source_ref","claim","observed","readability","matches_text","privacy_risk","retake_instruction")}
  preview_name=str(item.get("preview_name","")).strip()
  if preview_name:
   candidate=(output_dir/preview_name).resolve()
   try: candidate.relative_to(output_dir.resolve())
   except ValueError: candidate=None
   if candidate and candidate.is_file(): entry["preview_url"]=f"/api/reports/{record.get('job_id','')}/screenshots/{index}"
  screenshots.append(entry)
 quality=record.get("quality",{}) if isinstance(record.get("quality"),dict) else {}; render=quality.get("render",{}) if isinstance(quality.get("render"),dict) else {}
 public_quality={"ok":quality.get("ok"),"shipping_ready":quality.get("shipping_ready"),"render_status":render.get("status"),"render_resolution":render.get("resolution")}
 preview=str(render.get("preview","")).strip()
 if preview:
  candidate=(output_dir/preview).resolve()
  try: candidate.relative_to(output_dir.resolve())
  except ValueError: candidate=None
  if candidate and candidate.is_file(): public_quality["preview_url"]=f"/api/reports/{record.get('job_id','')}/render-preview"
 return {key:record.get(key) for key in ("job_id","report_kind","report_label","source_state","source_name","generated_name","created_at","summary","verdict","submission_signal","time_budget","estimated_minutes","priority_counts","strengths","false_completion_findings","contamination_findings")}|{"actions":_annotate_actions_for_feedback(record,output_dir),
  "files":files,"screenshots":screenshots,"quality":public_quality}

def _metadata_records(output_dir:Path)->list[dict[str,Any]]:
 records=[]
 if not output_dir.is_dir(): return records
 for path in sorted(output_dir.glob("*.metadata.json"),reverse=True):
  try: record=json.loads(path.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError): continue
  if not isinstance(record,dict): continue
  public=_public_record(record,output_dir)
  if not public["files"]: continue
  public["download_url"]=public["files"][0]["download_url"]; records.append(public)
 return records

def _resolve_file(output_dir:Path,job_id:str,kind:str)->tuple[dict[str,Any],Path]:
 metadata=_load_metadata(output_dir,job_id); matches=[item for item in _files(metadata,output_dir) if item["kind"]==kind]
 if not matches: abort(404)
 path=(output_dir/str(matches[0]["name"])).resolve()
 if path.parent!=output_dir.resolve() or not path.is_file(): abort(404)
 return metadata,path

def _resolve_screenshot(output_dir:Path,job_id:str,index:int)->Path:
 metadata=_load_metadata(output_dir,job_id); screenshots=metadata.get("screenshot_evidence",[])
 if not isinstance(screenshots,list) or index<0 or index>=len(screenshots): abort(404)
 name=str(screenshots[index].get("preview_name","")).strip(); path=(output_dir/name).resolve()
 try: path.relative_to(output_dir.resolve())
 except ValueError: abort(404)
 if not name or not path.is_file(): abort(404)
 return path

def _feedback_path(output_dir:Path,job_id:str)->Path: return output_dir/f"{job_id}.feedback.json"


def _active_feedback_records(output_dir:Path)->list[dict[str,Any]]:
 return [item for item in list_feedback(output_dir) if item.get("status","active")=="active"]

def _remove_flat_feedback(output_dir:Path,job_id:Any,feedback:dict[str,Any]|None=None)->dict[str,Any]:
 path=_feedback_path(output_dir,str(job_id))
 if not path.is_file(): return {"removed_file":False,"removed_actions":0}
 if feedback is None:
  path.unlink(missing_ok=True); return {"removed_file":True,"removed_actions":"all"}
 try: data=json.loads(path.read_text(encoding="utf-8-sig"))
 except (OSError,json.JSONDecodeError):
  path.unlink(missing_ok=True); return {"removed_file":True,"removed_actions":"unreadable"}
 actions=data.get("actions",[]) if isinstance(data,dict) else []
 action_id=str(feedback.get("action_id","")).strip(); label=str(feedback.get("label","")).strip(); raw=str(feedback.get("raw_text","")).strip()
 kept=[]; removed=0
 for action in actions:
  if not isinstance(action,dict): continue
  same_id=action_id and str(action.get("action_id","")).strip()==action_id
  same_label=label and str(action.get("label","")).strip()==label
  same_text=raw and str(action.get("correction") or action.get("note") or "").strip()==raw
  if same_id and (same_label or same_text or not label): removed+=1
  elif same_label and same_text: removed+=1
  else:
   if str(action.get("correction") or action.get("note") or "").strip(): kept.append(action)
 if kept:
  data["actions"]=kept; path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
 else:
  path.unlink(missing_ok=True)
 return {"removed_file":not bool(kept),"removed_actions":removed}
def _active_feedback_by_action(output_dir:Path,job_id:Any)->dict[tuple[str,str],dict[str,Any]]:
 matches={}
 for feedback in _active_feedback_records(output_dir):
  if str(feedback.get("job_id"))!=str(job_id): continue
  action_id=str(feedback.get("action_id","")).strip(); label=str(feedback.get("label","")).strip()
  if action_id: matches[("id",action_id)]=feedback
  if label: matches[("label",label)]=feedback
 return matches

def _annotate_actions_for_feedback(record:dict[str,Any],output_dir:Path)->list[dict[str,Any]]:
 active=_active_feedback_by_action(output_dir,record.get("job_id"))
 actions=[]
 for index,item in enumerate(record.get("actions",[]) or [],1):
  action=dict(item)
  label=str(action.get("label","")).strip()
  feedback=active.get(("label",label)) if label else active.get(("id",str(index)))
  if feedback:
   action["hidden_by_active_feedback"]=True
   action["feedback_id"]=feedback.get("feedback_id")
   action["feedback_status"]=feedback.get("status")
  else:
   action["hidden_by_active_feedback"]=False
  actions.append(action)
 return actions

def _personal_memory_path(output_dir:Path)->Path: return output_dir/"personal-memory.json"

def _load_personal_memory(output_dir:Path)->dict[str,Any]:
 path=_personal_memory_path(output_dir)
 if not path.is_file(): return {"notes":"","updated_at":None}
 try: data=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): return {"notes":"","updated_at":None}
 if not isinstance(data,dict): return {"notes":"","updated_at":None}
 notes=str(data.get("notes","")).strip()
 return {"notes":notes,"updated_at":data.get("updated_at")}

def _save_personal_memory(output_dir:Path,payload:Any)->dict[str,Any]:
 if not isinstance(payload,dict): abort(400,"Personal memory must be an object.")
 notes=str(payload.get("notes","")).strip()
 if len(notes)>4000: abort(400,"Personal memory is too long.")
 record={"notes":notes,"updated_at":datetime.now().astimezone().isoformat(timespec="seconds")}
 path=_personal_memory_path(output_dir); temp=path.with_suffix(".tmp")
 temp.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
 return record

def _preferences_path(output_dir:Path)->Path: return output_dir/"generation-preferences.json"

def _load_preferences(output_dir:Path)->dict[str,Any]:
 path=_preferences_path(output_dir)
 if not path.is_file(): return {"time_budget":"full","review_depth":"standard","review_focus":"comprehensive","output_mode":"single_docx","updated_at":None}
 try: data=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): return {"time_budget":"full","review_depth":"standard","review_focus":"comprehensive","output_mode":"single_docx","updated_at":None}
 return data if isinstance(data,dict) else {}

def _validate_preferences(payload:Any)->dict[str,Any]:
 if not isinstance(payload,dict): abort(400,"Preferences must be an object.")
 allowed={"time_budget":{"15m","1h","half_day","full"},"review_depth":{"quick","standard","deep"},"review_focus":{"comprehensive","screenshots","correctness","writing"},"output_mode":{"single_docx","guidance_only"}}
 defaults={"time_budget":"full","review_depth":"standard","review_focus":"comprehensive","output_mode":"single_docx"}; clean={}
 for key,values in allowed.items():
  value=str(payload.get(key,defaults[key]))
  if value not in values: abort(400,f"Invalid {key}.")
  clean[key]=value
 clean["updated_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
 return clean

def _improvement_dir(output_dir:Path)->Path: return output_dir/"skill-improvement-queue"

def _improvement_records(output_dir:Path)->list[dict[str,Any]]:
 return [{"request_id":"feedback-lifecycle","status":"ready_for_agent","mode":"feedback-lifecycle","feedback_count":len(_active_feedback_records(output_dir)),"interpretation_count":len(list_interpretations(output_dir)),"modification_count":len(list_modifications(output_dir)),"event_count":len(list_events(output_dir)),"activation_text":f"process feedback lifecycle in {output_dir}"}]


def _auto_improvement_path(output_dir:Path)->Path: return _improvement_dir(output_dir)/"auto-feedback-learning.skill-improvement.json"

def _record_auto_improvement(output_dir:Path,event_type:str,job_id:str,feedback:dict[str,Any]|None=None,deleted_feedback:dict[str,Any]|None=None)->dict[str,Any]:
 directory=_improvement_dir(output_dir); directory.mkdir(parents=True,exist_ok=True); path=_auto_improvement_path(output_dir); request_id="auto-feedback-learning"
 try: record=json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
 except (OSError,json.JSONDecodeError): record={}
 now=datetime.now().astimezone().isoformat(timespec="seconds")
 events=record.get("events",[]) if isinstance(record.get("events"),list) else []
 event={"type":event_type,"job_id":job_id,"at":now}
 if feedback is not None: event["feedback"]=feedback
 if deleted_feedback is not None: event["deleted_feedback"]=deleted_feedback
 events.append(event); events=events[-100:]
 saved_feedback=_feedback_records(output_dir)
 activation_text=f"/agent-skill-creator process local feedback task {path}"
 record={"request_id":request_id,"status":"ready_for_agent","created_at":record.get("created_at") or now,"updated_at":now,"skill":"university-experiment-report-review-skill","mode":"auto-feedback-learning","preferences":_load_preferences(output_dir),"feedback":saved_feedback,"events":events,"instructions":["Use agent-skill-creator locally.","This file is updated automatically whenever Dashboard feedback is created, edited, or deleted.","Separate report-specific corrections from reusable skill rules.","Modify the skill only for reusable patterns supported by repeated or high-confidence feedback evidence.","Do not call external APIs; validate, security scan, and cross-agent check before installation."],"activation_text":activation_text}
 path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
 prompt_path=directory/f"{request_id}.prompt.md"; prompt_path.write_text("# Auto Feedback Learning Task\n\n"+activation_text+"\n\nRead the adjacent JSON evidence and convert reusable feedback patterns into safe skill improvements.\n",encoding="utf-8")
 record["queue_path"]=str(path); record["prompt_path"]=str(prompt_path)
 return record

def _feedback_action_key(job_id:Any,action:dict[str,Any])->tuple[str,str,str,str]:
 text=str(action.get("correction") or action.get("note") or action.get("raw_text") or "").strip()
 return (str(job_id),str(action.get("action_id")),str(action.get("label","")).strip(),text)

def _feedback_lifecycle_records(output_dir:Path)->list[dict[str,Any]]:
 interpretations={str(item.get("feedback_id")):item for item in list_interpretations(output_dir)}
 modifications:dict[str,dict[str,Any]]={}
 for item in list_modifications(output_dir):
  feedback_id=str(item.get("source_feedback_id") or "")
  if feedback_id: modifications[feedback_id]=item
 records=[]
 for item in _active_feedback_records(output_dir):
  feedback_id=str(item.get("feedback_id"))
  interpretation=interpretations.get(feedback_id,{})
  modification=modifications.get(feedback_id,{})
  status=str(modification.get("status") or interpretation.get("status") or item.get("status") or "active")
  action={"action_id":item.get("action_id"),"label":str(item.get("label","")).strip(),"priority":"medium","note":"","correction":str(item.get("raw_text","")).strip(),"legacy_status":str(item.get("status","")),"status":status,"feedback_id":feedback_id,"interpretation_id":interpretation.get("interpretation_id"),"interpretation_scope":interpretation.get("scope"),"modification_id":modification.get("modification_id"),"modification_status":modification.get("status")}
  records.append({"job_id":item.get("job_id"),"source_name":item.get("source_name"),"updated_at":item.get("updated_at"),"confirmed_context":{},"history_source":"feedback-pool","feedback_id":feedback_id,"actions":[action]})
 return sorted(records,key=lambda record:str(record.get("updated_at") or ""),reverse=True)

def _feedback_records(output_dir:Path)->list[dict[str,Any]]:
 records=[]
 if not output_dir.is_dir(): return records
 lifecycle_records=_feedback_lifecycle_records(output_dir)
 lifecycle_actions={_feedback_action_key(record.get("job_id"),action):action for record in lifecycle_records for action in record.get("actions",[]) if isinstance(action,dict)}
 seen=set()
 inactive_statuses={"revoked","reverted","deleted","purged"}
 for path in sorted(output_dir.glob("*.feedback.json"),reverse=True):
  try: data=json.loads(path.read_text(encoding="utf-8"))
  except (OSError,json.JSONDecodeError): continue
  if not isinstance(data,dict): continue
  visible=[]
  for original in data.get("actions",[]):
   if not isinstance(original,dict): continue
   status=str(original.get("status") or original.get("legacy_status") or "").strip().lower()
   if status in inactive_statuses: continue
   action=dict(original)
   key=_feedback_action_key(data.get("job_id"),action)
   lifecycle=lifecycle_actions.get(key)
   text=str(action.get("correction") or action.get("note") or "").strip()
   if lifecycle:
    for field in ("status","feedback_id","interpretation_id","interpretation_scope","modification_id","modification_status"):
     if lifecycle.get(field) is not None: action[field]=lifecycle.get(field)
   elif not text:
    continue
   visible.append(action); seen.add(key)
  if visible:
   record=dict(data); record["actions"]=visible; records.append(record)
 for record in lifecycle_records:
  action=(record.get("actions") or [{}])[0]
  key=_feedback_action_key(record.get("job_id"),action if isinstance(action,dict) else {})
  if key not in seen:
   records.append(record)
 return records

def _default_feedback(metadata:dict[str,Any])->dict[str,Any]:
 actions=[]
 for index,action in enumerate(metadata.get("actions",[]),1): actions.append({"action_id":index,"label":str(action.get("label",f"行动 {index}")),"priority":str(action.get("priority","medium")),"priority_label":str(action.get("priority_label",PRIORITY_LABELS.get(str(action.get("priority","medium")),"中"))),"note":"","correction":""})
 return {"job_id":metadata["job_id"],"source_name":metadata.get("source_name"),"updated_at":None,"confirmed_context":{},"actions":actions}

def _load_feedback(output_dir:Path,metadata:dict[str,Any])->dict[str,Any]:
 path=_feedback_path(output_dir,str(metadata["job_id"]))
 if not path.is_file(): return _default_feedback(metadata)
 try: data=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError): return _default_feedback(metadata)
 return data if isinstance(data,dict) else _default_feedback(metadata)

def _validate_feedback(payload:Any,metadata:dict[str,Any])->dict[str,Any]:
 if not isinstance(payload,dict): abort(400,"Feedback must be an object.")
 raw_actions=payload.get("actions",[])
 if not isinstance(raw_actions,list) or len(raw_actions)>100: abort(400,"Invalid actions list.")
 actions=[]
 for item in raw_actions:
  if not isinstance(item,dict): abort(400,"Every action must be an object.")
  note=str(item.get("note","")).strip(); correction=str(item.get("correction","")).strip()
  if len(note)>1000 or len(correction)>2000: abort(400,"Feedback text is too long.")
  legacy_status=str(item.get("status","")).strip()
  actions.append({"action_id":item.get("action_id"),"label":str(item.get("label","")).strip()[:160],"priority":str(item.get("priority","medium")),"note":note,"correction":correction,"legacy_status":legacy_status})
 context=payload.get("confirmed_context",{})
 if not isinstance(context,dict) or len(context)>30: abort(400,"Invalid confirmed_context.")
 return {"job_id":metadata["job_id"],"source_name":metadata.get("source_name"),"updated_at":datetime.now().astimezone().isoformat(timespec="seconds"),"confirmed_context":context,"actions":actions}

def _clear_feedback(output_dir:Path,metadata:dict[str,Any])->dict[str,Any]:
 feedback=_default_feedback(metadata)
 feedback["updated_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
 path=_feedback_path(output_dir,str(metadata["job_id"])); temp=path.with_suffix(".tmp")
 temp.write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
 return feedback

def create_app(output_dir:Path)->Flask:
 resolved=output_dir.resolve(); resolved.mkdir(parents=True,exist_ok=True); app=Flask(__name__,template_folder=str(TEMPLATE_DIR),static_folder=str(STATIC_DIR)); app.config["MAX_CONTENT_LENGTH"]=64*1024
 @app.get("/")
 def index()->str: return render_template("index.html")
 @app.get("/api/health")
 def health()->Any: return jsonify({"ok":True,"service":"university-experiment-report-dashboard","api_version":DASHBOARD_API_VERSION,"asset_version":DASHBOARD_ASSET_VERSION,"output_dir_id":_output_dir_id(resolved),"local_only":True,"external_model_api":False})
 @app.get("/api/reports")
 def reports()->Any: return jsonify({"reports":_metadata_records(resolved)})
 @app.get("/api/feedback")
 def feedback_list()->Any: return jsonify({"feedback":_feedback_records(resolved)})
 @app.get("/api/feedback-pool")
 def feedback_pool()->Any: return jsonify({"feedback":_active_feedback_records(resolved)})
 @app.get("/api/feedback-interpretations")
 def feedback_interpretations()->Any: return jsonify({"interpretations":list_interpretations(resolved)})
 @app.get("/api/skill-modifications")
 def skill_modifications()->Any: return jsonify({"modifications":list_modifications(resolved)})
 @app.get("/api/feedback-lifecycle")
 def feedback_lifecycle()->Any: return jsonify({"events":list_events(resolved)})

 @app.get("/api/personal-memory")
 def personal_memory()->Any: return jsonify(_load_personal_memory(resolved))
 @app.post("/api/feedback/<feedback_id>/clear")
 def clear_feedback_record(feedback_id:str)->Any:
  feedback=next((item for item in list_feedback(resolved) if str(item.get("feedback_id"))==str(feedback_id)),None)
  flat=_remove_flat_feedback(resolved,feedback.get("job_id"),feedback) if feedback else {"removed_file":False,"removed_actions":0}
  purge=purge_feedback(resolved,feedback_id,"feedback_cleared")
  return jsonify({"ok":True,"purged":True,"deleted":True,"feedback":{"job_id":feedback.get("job_id") if feedback else None,"source_name":feedback.get("source_name") if feedback else None,"updated_at":None,"confirmed_context":{},"actions":[]},"learning_status":"purged","lifecycle":purge,"flat_feedback":flat})
 @app.delete("/api/feedback/<feedback_id>")
 def delete_feedback_record(feedback_id:str)->Any:
  feedback=next((item for item in list_feedback(resolved) if str(item.get("feedback_id"))==str(feedback_id)),None)
  flat=_remove_flat_feedback(resolved,feedback.get("job_id"),feedback) if feedback else {"removed_file":False,"removed_actions":0}
  purge=purge_feedback(resolved,feedback_id,"feedback_deleted")
  return jsonify({"ok":True,"purged":True,"deleted":True,"feedback":{"job_id":feedback.get("job_id") if feedback else None,"source_name":feedback.get("source_name") if feedback else None,"updated_at":None,"confirmed_context":{},"actions":[]},"learning_status":"purged","lifecycle":purge,"flat_feedback":flat})
 @app.put("/api/personal-memory")
 def save_personal_memory()->Any: return jsonify({"ok":True,**_save_personal_memory(resolved,request.get_json(silent=True))})
 @app.get("/api/generation-preferences")
 def generation_preferences()->Any: return jsonify(_load_preferences(resolved))
 @app.put("/api/generation-preferences")
 def save_generation_preferences()->Any:
  preferences=_validate_preferences(request.get_json(silent=True)); path=_preferences_path(resolved); temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(preferences,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path); return jsonify({"ok":True,"preferences":preferences})
 @app.get("/api/skill-improvement-requests")
 def skill_improvement_requests()->Any: return jsonify({"requests":_improvement_records(resolved)})
 @app.post("/api/skill-improvement-requests")
 def create_skill_improvement_request()->Any:
  payload=request.get_json(silent=True) or {}; requested=payload.get("job_ids",[])
  if not isinstance(requested,list) or len(requested)>50: abort(400,"Invalid job_ids.")
  requested_ids={str(value) for value in requested}; feedback=[item for item in _feedback_records(resolved) if not requested_ids or str(item.get("job_id")) in requested_ids]
  if not feedback: abort(400,"No saved feedback is available.")
  request_id=datetime.now().strftime("%Y%m%d-%H%M%S-%f"); directory=_improvement_dir(resolved); directory.mkdir(parents=True,exist_ok=True)
  activation_text=f"/agent-skill-creator process local feedback task {directory/f'{request_id}.skill-improvement.json'}"
  record={"request_id":request_id,"status":"ready_for_agent","created_at":datetime.now().astimezone().isoformat(timespec="seconds"),"skill":"university-experiment-report-review-skill","preferences":_load_preferences(resolved),"feedback":feedback,"instructions":["Use agent-skill-creator locally.","Separate report-specific corrections from reusable skill rules.","Modify the skill only for reusable patterns supported by feedback evidence.","Run tests, validation, security scan, and cross-agent checks before installation."],"activation_text":activation_text}
  path=directory/f"{request_id}.skill-improvement.json"; path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8"); prompt_path=directory/f"{request_id}.prompt.md"; prompt_path.write_text("# Local Skill Improvement Task\n\n"+activation_text+"\n\nRead the adjacent JSON evidence and process only reusable improvements.\n",encoding="utf-8"); return jsonify({"ok":True,"request":record,"queue_path":str(path),"prompt_path":str(prompt_path),"activation_text":activation_text})
 @app.get("/api/reports/<job_id>/metadata")
 def report_metadata(job_id:str)->Any: return jsonify(_public_record(_load_metadata(resolved,job_id),resolved))
 @app.get("/api/reports/<job_id>/download")
 def download_legacy(job_id:str)->Any:
  _,path=_resolve_file(resolved,job_id,"annotated"); return send_file(path,as_attachment=True,download_name=path.name,mimetype=mimetypes.guess_type(path.name)[0])
 @app.get("/api/reports/<job_id>/download/<kind>")
 def download(job_id:str,kind:str)->Any:
  _,path=_resolve_file(resolved,job_id,kind); return send_file(path,as_attachment=True,download_name=path.name,mimetype=mimetypes.guess_type(path.name)[0])
 @app.get("/api/reports/<job_id>/screenshots/<int:index>")
 def screenshot(job_id:str,index:int)->Any:
  path=_resolve_screenshot(resolved,job_id,index); return send_file(path,as_attachment=False,mimetype=mimetypes.guess_type(path.name)[0])
 @app.get("/api/reports/<job_id>/render-preview")
 def render_preview(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); name=str(metadata.get("quality",{}).get("render",{}).get("preview","")).strip(); path=(resolved/name).resolve()
  try: path.relative_to(resolved)
  except ValueError: abort(404)
  if not name or not path.is_file(): abort(404)
  return send_file(path,as_attachment=False,mimetype=mimetypes.guess_type(path.name)[0])
 @app.post("/api/reports/<job_id>/render")
 def retry_render(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); files=[item for item in _files(metadata,resolved) if item.get("kind")=="annotated"]
  if not files: abort(404)
  generated=(resolved/str(files[0]["name"])).resolve()
  try: result=render_report(generated,job_id)
  except Exception as exc: result={"status":"failed","backend":None,"attempts":[],"pdf":None,"pages":[],"preview":None,"resolution":str(exc)[:1200]}
  quality=metadata.setdefault("quality",{}); quality["render"]=result; quality["shipping_ready"]=bool(quality.get("ok",True)) and result.get("status") in {"passed","unavailable","permission-required"}; _save_metadata(resolved,metadata); return jsonify({"ok":result.get("status")!="failed","quality":_public_record(metadata,resolved)["quality"]})
 @app.get("/api/reports/<job_id>/feedback")
 def get_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); return jsonify(_load_feedback(resolved,metadata))
 @app.post("/api/reports/<job_id>/feedback")
 def save_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); feedback=_validate_feedback(request.get_json(silent=True),metadata); path=_feedback_path(resolved,job_id); temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
  lifecycle=sync_feedback_payload(resolved,feedback,"feedback_saved")
  if not lifecycle.get("saved_count"): _remove_flat_feedback(resolved,job_id)
  return jsonify({"ok":True,"feedback":feedback,"learning_status":lifecycle.get("lifecycle_status"),"lifecycle":lifecycle})
 @app.delete("/api/reports/<job_id>/feedback")
 def delete_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); purge=purge_job_feedback(resolved,job_id,"feedback_deleted"); flat=_remove_flat_feedback(resolved,job_id)
  return jsonify({"ok":True,"deleted":True,"purged":True,"feedback":_default_feedback(metadata),"learning_status":"purged","lifecycle":purge,"flat_feedback":flat})
 @app.post("/api/reports/<job_id>/feedback/clear")
 def clear_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); purge=purge_job_feedback(resolved,job_id,"feedback_cleared"); flat=_remove_flat_feedback(resolved,job_id)
  return jsonify({"ok":True,"deleted":True,"purged":True,"feedback":_default_feedback(metadata),"learning_status":"purged","lifecycle":purge,"flat_feedback":flat})
 @app.get("/api/reports/<job_id>/feedback/download")
 def download_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); path=_feedback_path(resolved,job_id)
  if not path.is_file(): abort(404)
  return send_file(path,as_attachment=True,download_name=path.name,mimetype="application/json")
 @app.put("/api/reports/<job_id>/feedback")
 def replace_feedback(job_id:str)->Any:
  metadata=_load_metadata(resolved,job_id); feedback=_validate_feedback(request.get_json(silent=True),metadata); path=_feedback_path(resolved,job_id); temp=path.with_suffix(".tmp"); temp.write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(path)
  lifecycle=sync_feedback_payload(resolved,feedback,"feedback_updated")
  if not lifecycle.get("saved_count"): purge_job_feedback(resolved,job_id,"feedback_updated_empty"); _remove_flat_feedback(resolved,job_id)
  return jsonify({"ok":True,"feedback":feedback,"learning_status":lifecycle.get("lifecycle_status"),"lifecycle":lifecycle})
 return app

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path); parser.add_argument("--allow-custom-output-dir",action="store_true",help="Allow a non-canonical output directory for tests, CI, or explicit maintenance."); parser.add_argument("--port",type=int,default=8765); args=parser.parse_args()
 if args.port<1024 or args.port>65535: parser.error("--port must be between 1024 and 65535")
 output_dir=resolve_output_dir(args.output_dir,allow_custom=args.allow_custom_output_dir); create_app(output_dir).run(host="127.0.0.1",port=args.port,debug=False,use_reloader=False); return 0
if __name__=="__main__": raise SystemExit(main())
