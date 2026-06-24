#!/usr/bin/env python3
"""Derive conservative local review signals without remote OCR or model APIs."""
from __future__ import annotations
import re
from collections import Counter
from typing import Any

PLACEHOLDER_PATTERNS=(r"请(?:在此)?填写",r"待补充",r"TODO",r"TBD",r"占位符",r"示例文字",r"点击此处输入")
AI_TRACE_PATTERNS=(r"作为(?:一个)?AI",r"ChatGPT",r"以下是.{0,20}(?:报告|内容|建议)",r"希望(?:以上|这些).{0,20}对你有帮助")
PROCESS_WORDS=("实验步骤","操作步骤","实验过程","配置过程")
RESULT_WORDS=("实验结果","运行结果","测试结果","输出结果","测量结果")
CONCLUSION_WORDS=("实验结论","结论","实验总结")
EVIDENCE_WORDS=("截图","输出","日志","数据","结果如图","运行成功","测试通过")

def _contains_any(text:str,words:tuple[str,...])->bool:
 return any(word in text for word in words)

def _finding(location:str,issue:str,evidence:str,action:str,severity:str)->dict[str,str]:
 return {"location":location,"issue":issue,"evidence":evidence,"action":action,"severity":severity}

def detect_contamination(text:str)->list[dict[str,str]]:
 findings=[]
 for pattern in PLACEHOLDER_PATTERNS:
  matches=list(re.finditer(pattern,text,re.IGNORECASE))
  if matches: findings.append(_finding("正文","仍含模板占位内容",f"匹配 {pattern}，共 {len(matches)} 处","删除占位语并替换为本次实验的真实内容。","high"))
 for pattern in AI_TRACE_PATTERNS:
  matches=list(re.finditer(pattern,text,re.IGNORECASE))
  if matches: findings.append(_finding("正文","存在 AI 对话式痕迹",f"匹配 {pattern}，共 {len(matches)} 处","改为学生自己的实验陈述，并核对其中事实是否真实执行。","medium"))
 headings=[line.strip() for line in text.splitlines() if 2<=len(line.strip())<=40 and (line.strip().endswith("：") or re.match(r"^(?:第?[一二三四五六七八九十0-9]+[.、章节]|#+\s)",line.strip()))]
 repeated=[heading for heading,count in Counter(headings).items() if count>1]
 if repeated: findings.append(_finding("章节结构","存在重复标题",f"重复：{'、'.join(repeated[:5])}","合并重复章节，保留与本次实验相关且证据完整的一份。","low"))
 return findings

def detect_false_completion(text:str,visual_count:int)->list[dict[str,str]]:
 findings=[]; has_process=_contains_any(text,PROCESS_WORDS); has_result=_contains_any(text,RESULT_WORDS); has_conclusion=_contains_any(text,CONCLUSION_WORDS); has_evidence=_contains_any(text,EVIDENCE_WORDS)
 if has_process and has_conclusion and not has_result: findings.append(_finding("实验结果","文字结构看似完整，但缺少结果章节","检测到步骤和结论，未检测到结果章节","补充真实运行结果、关键参数和对应证据后再判断完成。","high"))
 if has_result and visual_count==0 and not has_evidence: findings.append(_finding("实验结果","结果缺少可核验依据","有结果描述，但未发现图片或明确输出/数据证据","补充可复核的输出、数据表或结果截图。","high"))
 if has_conclusion and not (has_result or has_evidence): findings.append(_finding("实验结论","结论缺少前文证据支撑","存在结论，但未找到结果或证据线索","让每条结论对应前文的结果、数据或截图。","medium"))
 return findings

def classify_report_signals(text:str,visual_count:int)->dict[str,Any]:
 clean=text.strip(); contamination=detect_contamination(clean); false_completion=detect_false_completion(clean,visual_count)
 if (contamination and len(clean)<120) or (len(clean)<120 and not _contains_any(clean,PROCESS_WORDS+RESULT_WORDS+CONCLUSION_WORDS)): state="blank"
 elif false_completion or not (_contains_any(clean,PROCESS_WORDS) and _contains_any(clean,RESULT_WORDS) and _contains_any(clean,CONCLUSION_WORDS)): state="partial"
 else: state="completed"
 return {"suggested_state":state,"contamination_findings":contamination,"false_completion_findings":false_completion,"semantic_review_required":True}
