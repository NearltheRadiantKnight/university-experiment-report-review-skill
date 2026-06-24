#!/usr/bin/env python3
"""Validate AgentSkills contracts and optionally smoke-test installed agent CLIs."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from typing import Any

PLATFORMS={
 "codex":{"commands":[["codex","--version"]],"paths":[".agents/skills",".codex/skills"]},
 "claude-code":{"commands":[["claude","--version"]],"paths":[".claude/skills"]},
 "openclaw":{"commands":[["openclaw","--version"],["openclaw","skills","list"]],"paths":[".openclaw/skills",".agents/skills","workspace/skills"]},
}

def _frontmatter(skill_md:Path)->dict[str,str]:
 lines=skill_md.read_text(encoding="utf-8").splitlines()
 if not lines or lines[0]!="---": raise ValueError("SKILL.md frontmatter is missing.")
 result={}
 for line in lines[1:]:
  if line=="---": break
  if ":" in line:
   key,value=line.split(":",1); result[key.strip()]=value.strip()
 return result

def validate_contract(skill_dir:Path)->list[dict[str,Any]]:
 skill=skill_dir/"SKILL.md"; agents=skill_dir/"AGENTS.md"; sh=skill_dir/"install.sh"; ps1=skill_dir/"install.ps1"
 checks=[]
 def add(name:str,ok:bool,detail:str)->None: checks.append({"check":name,"ok":ok,"detail":detail})
 if not skill.is_file(): return [{"check":"skill-md","ok":False,"detail":"SKILL.md missing"}]
 front=_frontmatter(skill); body=skill.read_text(encoding="utf-8")
 add("name",front.get("name")==skill_dir.name,front.get("name","missing")); add("description",bool(front.get("description")),"present" if front.get("description") else "missing")
 add("activation",front.get("activation")==f"/{skill_dir.name}",front.get("activation","missing")); add("body-heading",f"# /{skill_dir.name}" in body,"slash heading")
 try: metadata=json.loads(front.get("metadata","")); metadata_ok=isinstance(metadata,dict) and isinstance(metadata.get("openclaw"),dict)
 except json.JSONDecodeError: metadata_ok=False
 add("openclaw-metadata",metadata_ok,"single-line JSON metadata")
 add("agents-md",agents.is_file(),str(agents)); installer_text=(sh.read_text(encoding="utf-8") if sh.is_file() else "")+(ps1.read_text(encoding="utf-8") if ps1.is_file() else "")
 if installer_text:
  for platform,contract in PLATFORMS.items(): add(f"installer-{platform}",platform in installer_text and any(path in installer_text.replace("\\","/") for path in contract["paths"] if path!="workspace/skills"),"source-package installer path contract")
 else:
  installed_contract=(body+(agents.read_text(encoding="utf-8") if agents.is_file() else "")).replace("\\","/").casefold()
  for platform,contract in PLATFORMS.items(): add(f"installed-contract-{platform}",platform.split("-")[0] in installed_contract and any(path in installed_contract for path in contract["paths"]),"installed-package documentation contract")
 return checks

def smoke_platform(platform:str)->dict[str,Any]:
 spec=PLATFORMS[platform]; executable=spec["commands"][0][0]; path=shutil.which(executable)
 if not path: return {"platform":platform,"status":"not-installed","executable":None,"commands":[]}
 results=[]
 for command in spec["commands"]:
  try:
   process=subprocess.run(command,capture_output=True,text=True,timeout=25,check=False); results.append({"command":command,"exit_code":process.returncode,"output":(process.stdout+process.stderr).strip()[-2000:]})
  except PermissionError as exc: results.append({"command":command,"exit_code":"blocked","output":str(exc)})
  except (OSError,subprocess.SubprocessError) as exc: results.append({"command":command,"exit_code":None,"output":str(exc)})
 status="passed" if all(item["exit_code"]==0 for item in results) else "blocked" if any(item["exit_code"]=="blocked" for item in results) else "failed"
 return {"platform":platform,"status":status,"executable":path,"commands":results}

def run(skill_dir:Path,platforms:list[str])->dict[str,Any]:
 checks=validate_contract(skill_dir); return {"skill":skill_dir.name,"contract_ok":all(item["ok"] for item in checks),"checks":checks,"runtime":[smoke_platform(item) for item in platforms]}

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--skill-dir",type=Path,default=Path(__file__).resolve().parents[1]); parser.add_argument("--platform",choices=["all",*PLATFORMS],default="all"); parser.add_argument("--output",type=Path); args=parser.parse_args(); platforms=list(PLATFORMS) if args.platform=="all" else [args.platform]
 try: result=run(args.skill_dir.resolve(),platforms)
 except (OSError,ValueError,json.JSONDecodeError) as exc: print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr); return 1
 rendered=json.dumps({"ok":result["contract_ok"],**result},ensure_ascii=False,indent=2)
 if args.output: args.output.write_text(rendered,encoding="utf-8")
 print(rendered); return 0 if result["contract_ok"] else 1
if __name__=="__main__": raise SystemExit(main())