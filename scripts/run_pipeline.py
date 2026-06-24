#!/usr/bin/env python3
"""Single entry point for generation, QA, metadata, and optional dashboard delivery."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from typing import Any
from build_report import ReportBuildError,build_report
from dashboard_launcher import launch_dashboard
from qa_report import ReportQualityError,check_report

def run_pipeline(source:Path,plan:Path,output_dir:Path,port:int=8765,open_browser:bool=True,launch_dashboard_server:bool=True,require_render:bool=False)->dict[str,Any]:
 generated,metadata_path=build_report(source,plan,output_dir)
 quality,quality_path=check_report(source,generated,metadata_path,require_render=require_render)
 metadata=json.loads(metadata_path.read_text(encoding="utf-8")); metadata["quality"]=quality; files=metadata.setdefault("generated_files",[])
 files.append({"kind":"quality","label":"质量报告","name":quality_path.name})
 render=quality.get("render",{})
 if render.get("pdf"): files.append({"kind":"rendered-pdf","label":"渲染 PDF","name":render["pdf"]})
 if render.get("preview"): files.append({"kind":"render-preview","label":"页面预览","name":render["preview"]})
 metadata_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
 url=launch_dashboard(output_dir,port,open_browser) if launch_dashboard_server else None
 return {"generated_report":str(generated),"generated_files":files,"metadata":str(metadata_path),"quality_report":str(quality_path),"render_status":render.get("status","unknown"),"dashboard_url":url,"local_only":True}

def main()->int:
 parser=argparse.ArgumentParser(description="Generate, quality-check, and publish report deliverables.")
 parser.add_argument("--source",type=Path,required=True); parser.add_argument("--plan",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True)
 parser.add_argument("--port",type=int,default=8765); parser.add_argument("--no-open",action="store_true"); parser.add_argument("--no-dashboard",action="store_true"); parser.add_argument("--require-render",action="store_true"); args=parser.parse_args()
 try: result=run_pipeline(args.source.resolve(),args.plan.resolve(),args.output_dir.resolve(),args.port,not args.no_open,not args.no_dashboard,args.require_render)
 except (ValueError,ReportBuildError,ReportQualityError,RuntimeError,OSError) as exc:
  print(json.dumps({"error":str(exc),"error_type":"runtime","hint":"Check source, plan gates, anchors, renderer, output path, and port."},ensure_ascii=False),file=sys.stderr); return 1
 print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())