#!/usr/bin/env python3
"""Build structured, style-safe experiment report deliverables from a local DOCX."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph
from validate_plan import PlanValidationError, load_and_validate

SKILL_NAME="university-experiment-report-review-skill"
VERSION="1.3.2"
DEFAULT_FONT="Microsoft YaHei"
CATEGORY_STYLES={
 "guidance":("2F75B5","执行指导"),"evidence":("008C95","证据要求"),"writing":("7030A0","写作建议"),
 "warning":("C65911","注意事项"),"issue":("C00000","发现问题"),"suggestion":("1F4E79","修改建议"),
 "example":("548235","参考写法"),"praise":("8064A2","保留优点"),"summary":("44546A","总结")}
PRIORITY_LABELS={"blocker":"阻塞","high":"高","medium":"中","low":"低","optional":"可选"}

class ReportBuildError(RuntimeError): pass

def _error_payload(message:str,error_type:str,hint:str)->None:
 print(json.dumps({"error":message,"error_type":error_type,"hint":hint},ensure_ascii=False),file=sys.stderr)

def _sha256(path:Path)->str:
 digest=hashlib.sha256()
 with path.open("rb") as stream:
  for block in iter(lambda:stream.read(1024*1024),b""): digest.update(block)
 return digest.hexdigest()

def _safe_stem(text:str)->str:
 return re.sub(r'[\\/:*?"<>|]+',"-",text).strip(" .-") or "experiment-report"

def _unique_path(path:Path,job_id:str)->Path:
 return path if not path.exists() else path.with_name(f"{path.stem}-{job_id}{path.suffix}")

def _all_paragraphs(document:Document)->list[Paragraph]:
 paragraphs=list(document.paragraphs)
 for table in document.tables:
  for row in table.rows:
   for cell in row.cells: paragraphs.extend(cell.paragraphs)
 return paragraphs

def _ensure_styles(document:Document)->None:
 styles=document.styles
 if "Codex Added" not in styles:
  style=styles.add_style("Codex Added",WD_STYLE_TYPE.PARAGRAPH)
  style.base_style=styles["Normal"]
  style.paragraph_format.space_before=Pt(4); style.paragraph_format.space_after=Pt(4)
 if "Codex Item" not in styles:
  style=styles.add_style("Codex Item",WD_STYLE_TYPE.PARAGRAPH)
  style.base_style=styles["Codex Added"]
  style.paragraph_format.left_indent=Pt(18); style.paragraph_format.first_line_indent=Pt(-12)

def _insert_after(paragraph:Paragraph,style_name:str="Codex Added")->Paragraph:
 element=OxmlElement("w:p"); paragraph._p.addnext(element); inserted=Paragraph(element,paragraph._parent)
 try: inserted.style=style_name
 except KeyError: pass
 return inserted

def _set_run_font(run:Any,font_name:str,color_hex:str,size_pt:float,bold:bool=False)->None:
 run.font.name=font_name; run.font.color.rgb=RGBColor.from_string(color_hex); run.font.size=Pt(size_pt); run.bold=bold
 rpr=run._element.get_or_add_rPr(); fonts=rpr.rFonts
 if fonts is None: fonts=OxmlElement("w:rFonts"); rpr.insert(0,fonts)
 for key in ("w:ascii","w:hAnsi","w:eastAsia"): fonts.set(qn(key),font_name)

def _add_runs(paragraph:Paragraph,addition:dict[str,Any],label_override:str|None=None,text_override:str|None=None)->None:
 category=str(addition.get("category","suggestion")); color,default_label=CATEGORY_STYLES.get(category,CATEGORY_STYLES["suggestion"])
 label=label_override or str(addition.get("label",default_label)).strip() or default_label
 text=str(addition.get("text","") if text_override is None else text_override).strip()
 font=str(addition.get("font_name",DEFAULT_FONT)).strip() or DEFAULT_FONT; size=float(addition.get("font_size_pt",10.5))
 label_run=paragraph.add_run(f"【Codex 新增·{label}】"); _set_run_font(label_run,font,color,size,True)
 if text:
  body=paragraph.add_run(text); _set_run_font(body,font,color,size)

def _apply_table_style(table: Any) -> None:
 try:
  table.style="Table Grid"
 except KeyError:
  pass
def _item_text(addition:dict[str,Any],item:Any,checklist:bool)->str:
 return f"{'☐' if checklist else '•'} {str(item).strip()}"

def _render_after(document:Document,anchor:Paragraph,addition:dict[str,Any])->Paragraph:
 block=str(addition.get("block_type","paragraph")); current=_insert_after(anchor); _add_runs(current,addition)
 if block in {"bullets","checklist"}:
  for item in addition.get("items",[]):
   current=_insert_after(current,"Codex Item")
   category=str(addition.get("category","suggestion")); color=CATEGORY_STYLES.get(category,CATEGORY_STYLES["suggestion"])[0]
   run=current.add_run(_item_text(addition,item,block=="checklist")); _set_run_font(run,str(addition.get("font_name",DEFAULT_FONT)),color,float(addition.get("font_size_pt",10.5)))
 elif block=="table":
  tail=_insert_after(current); table=document.add_table(rows=1,cols=len(addition["columns"])); _apply_table_style(table)
  for index,value in enumerate(addition["columns"]):
   cell=table.rows[0].cells[index]; cell.text=str(value)
   for run in cell.paragraphs[0].runs: _set_run_font(run,DEFAULT_FONT,"44546A",9,True)
  for values in addition.get("rows",[]):
   cells=table.add_row().cells
   for index,value in enumerate(values):
    cells[index].text="" if value is None else str(value)
    for run in cells[index].paragraphs[0].runs: _set_run_font(run,DEFAULT_FONT,"1F1F1F",9)
  tail._p.addprevious(table._tbl); current=tail
 return current

def _render_append(document:Document,addition:dict[str,Any])->None:
 block=str(addition.get("block_type","paragraph")); paragraph=document.add_paragraph(style="Codex Added"); _add_runs(paragraph,addition)
 if block in {"bullets","checklist"}:
  for item in addition.get("items",[]):
   row=document.add_paragraph(style="Codex Item"); color=CATEGORY_STYLES.get(str(addition.get("category")),CATEGORY_STYLES["suggestion"])[0]
   run=row.add_run(_item_text(addition,item,block=="checklist")); _set_run_font(run,DEFAULT_FONT,color,float(addition.get("font_size_pt",10.5)))
 elif block=="table":
  table=document.add_table(rows=1,cols=len(addition["columns"])); _apply_table_style(table)
  for index,value in enumerate(addition["columns"]): table.rows[0].cells[index].text=str(value)
  for values in addition.get("rows",[]):
   cells=table.add_row().cells
   for index,value in enumerate(values): cells[index].text="" if value is None else str(value)

def _find_anchor(paragraphs:list[Paragraph],addition:dict[str,Any])->Paragraph|None:
 if "paragraph_index" in addition:
  index=int(addition["paragraph_index"])
  if index<0 or index>=len(paragraphs): raise ReportBuildError(f"paragraph_index {index} is outside the source document.")
  return paragraphs[index]
 text=str(addition.get("anchor_text","")).strip(); occurrence=int(addition.get("occurrence",1))
 if not text: return None
 matches=[paragraph for paragraph in paragraphs if text in paragraph.text]
 return matches[occurrence-1] if len(matches)>=occurrence else None

def _append_summary(document:Document,plan:dict[str,Any])->None:
 if not plan.get("include_summary_appendix"): return
 paragraph=document.add_paragraph(); paragraph.add_run().add_break(WD_BREAK.PAGE)
 _render_append(document,{"category":"summary","label":"提交判断","text":str(plan.get("verdict",""))})
 _render_append(document,{"category":"summary","label":"整体说明","text":str(plan.get("summary",""))})

def _addition_plain_text(addition:dict[str,Any])->str:
 block=str(addition.get("block_type","paragraph")); text=str(addition.get("text","")).strip()
 if block in {"bullets","checklist"}: return "；".join(([text] if text else [])+[str(x) for x in addition.get("items",[])])
 if block=="table": return f"表格：{', '.join(str(x) for x in addition.get('columns',[]))}（{len(addition.get('rows',[]))} 行）"
 return text

def _build_companion(source:Path,plan:dict[str,Any],output_dir:Path,job_id:str)->Path:
 document=Document(); _ensure_styles(document)
 label="实验执行清单" if plan["report_kind"]=="execution" else "报告修改清单"
 document.add_heading(label,0); document.add_paragraph(f"来源文件：{source.name}")
 document.add_heading("提交判断",level=1); document.add_paragraph(str(plan.get("verdict","")))
 document.add_heading("整体说明",level=1); document.add_paragraph(str(plan.get("summary","")))
 document.add_heading("行动项目",level=1)
 table=document.add_table(rows=1,cols=5); _apply_table_style(table)
 for cell,value in zip(table.rows[0].cells,["完成","优先级","类别","依据","行动"]): cell.text=value
 for addition in plan.get("additions",[]):
  cells=table.add_row().cells; category=str(addition.get("category","suggestion")); default=CATEGORY_STYLES.get(category,CATEGORY_STYLES["suggestion"])[1]
  values=["☐",PRIORITY_LABELS.get(str(addition.get("priority","medium")),"中"),str(addition.get("label",default)),str(addition.get("evidence_basis","未标注")),_addition_plain_text(addition)]
  for index,value in enumerate(values): cells[index].text=value
 path=_unique_path(output_dir/f"{_safe_stem(source.stem)}-{label}.docx",job_id); document.save(path); return path

def build_report(source:Path,plan_path:Path,output_dir:Path)->tuple[Path,Path]:
 if not source.is_file(): raise ValueError(f"Source file does not exist: {source}")
 if source.suffix.lower()!=".docx": raise ValueError("Style-preserving generated reports require a .docx source file.")
 try: plan,warnings=load_and_validate(plan_path)
 except PlanValidationError as exc: raise ReportBuildError(str(exc)) from exc
 try: document=Document(str(source))
 except Exception as exc: raise ReportBuildError(f"DOCX could not be opened: {exc}") from exc
 _ensure_styles(document); original_paragraphs=_all_paragraphs(document); last_by_anchor={}; appendix=[]; applied=[]
 strict=bool(plan.get("strict_anchors",True))
 for index,addition in enumerate(plan.get("additions",[]),1):
  position=str(addition.get("position","after")); anchor=_find_anchor(original_paragraphs,addition)
  if position=="append":
   appendix.append(addition); applied.append({"index":index,"location":"appendix","anchor_found":True}); continue
  if anchor is None:
   if strict or str(addition.get("on_anchor_missing","error"))=="error":
    raise ReportBuildError(f"Addition {index} anchor was not found. Fix the plan instead of creating an unlocated section.")
   appendix.append(addition); applied.append({"index":index,"location":"appendix-fallback","anchor_found":False}); continue
  key=id(anchor._p); insertion=last_by_anchor.get(key,anchor); last_by_anchor[key]=_render_after(document,insertion,addition)
  applied.append({"index":index,"location":"after-anchor","anchor_found":True,"anchor_text":anchor.text[:120]})
 if appendix:
  document.add_heading(str(plan.get("appendix_title","行动清单")),level=1)
  for addition in appendix: _render_append(document,addition)
 _append_summary(document,plan)
 output_dir.mkdir(parents=True,exist_ok=True); job_id=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
 report_label="实验执行报告" if plan["report_kind"]=="execution" else "修改报告"
 output_path=_unique_path(output_dir/f"{_safe_stem(source.stem)}-{report_label}.docx",job_id); document.save(output_path)
 companion=None
 if plan.get("generate_companion",True): companion=_build_companion(source,plan,output_dir,job_id)
 generated_files=[{"kind":"annotated","label":report_label,"name":output_path.name,"sha256":_sha256(output_path)}]
 if companion: generated_files.append({"kind":"companion","label":"行动清单","name":companion.name,"sha256":_sha256(companion)})
 counts=Counter(str(item.get("priority","medium")) for item in plan.get("additions",[]))
 actions=[]
 for item in plan.get("additions",[]):
  category=str(item.get("category","suggestion")); priority=str(item.get("priority","medium")); default=CATEGORY_STYLES.get(category,CATEGORY_STYLES["suggestion"])[1]
  actions.append({"label":str(item.get("label",default)),"priority":priority,"priority_label":PRIORITY_LABELS.get(priority,"中"),"category":category,"evidence_basis":str(item.get("evidence_basis","unverified")),"text":_addition_plain_text(item)[:240]})
 metadata={"job_id":job_id,"skill":SKILL_NAME,"version":VERSION,"created_at":datetime.now().astimezone().isoformat(timespec="seconds"),
  "report_kind":plan["report_kind"],"report_label":report_label,"source_state":plan["source_state"],"source_name":source.name,
  "domain_profile":plan.get("domain_profile"),"domain_confidence":plan.get("domain_confidence"),"domain_profile_basis":plan.get("domain_profile_basis"),
  "source_sha256":_sha256(source),"generated_name":output_path.name,"generated_sha256":_sha256(output_path),"generated_files":generated_files,
  "summary":str(plan.get("summary","")).strip(),"verdict":str(plan.get("verdict","")).strip(),"addition_count":len(plan.get("additions",[])),
  "priority_counts":dict(counts),"actions":actions,"plan_warnings":warnings,"applied":applied,
  "style_policy":{"original_content":"preserved","generated_content":"structured, labeled, and category-colored"},"local_only":True}
 metadata_path=output_dir/f"{job_id}.metadata.json"; metadata_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
 return output_path,metadata_path

def diagnostics()->dict[str,Any]:
 return {"skill":SKILL_NAME,"version":VERSION,"commands":["build-report","diagnostics"],"features":{"structured_blocks":True,"strict_anchors":True,"numeric_score_gate":True,"companion_checklist":True,"external_model_api":False}}

def main()->int:
 parser=argparse.ArgumentParser(description="Build structured experiment-report deliverables."); parser.add_argument("--source",type=Path); parser.add_argument("--plan",type=Path); parser.add_argument("--output-dir",type=Path); parser.add_argument("--diagnostics",action="store_true"); args=parser.parse_args()
 if args.diagnostics: print(json.dumps(diagnostics(),ensure_ascii=False,indent=2)); return 0
 if None in (args.source,args.plan,args.output_dir): _error_payload("--source, --plan, and --output-dir are required.","validation","Supply all paths."); return 1
 try: output,metadata=build_report(args.source.resolve(),args.plan.resolve(),args.output_dir.resolve())
 except (ValueError,ReportBuildError,OSError) as exc: _error_payload(str(exc),"runtime","Check paths, plan quality gates, anchors, and open files."); return 1
 print(json.dumps({"ok":True,"output":str(output),"metadata":str(metadata)},ensure_ascii=False)); return 0
if __name__=="__main__": raise SystemExit(main())