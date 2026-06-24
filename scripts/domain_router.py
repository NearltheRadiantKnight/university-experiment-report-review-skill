#!/usr/bin/env python3
"""Route extracted report text to local domain-specific review profiles."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_PROFILES=ROOT/"assets"/"domain-profiles"

class DomainRoutingError(ValueError): pass

def load_profiles(profile_dir:Path=DEFAULT_PROFILES)->list[dict[str,Any]]:
 profiles=[]
 for path in sorted(profile_dir.glob("*.json")):
  data=json.loads(path.read_text(encoding="utf-8"))
  if not isinstance(data,dict) or not data.get("id") or not isinstance(data.get("keywords"),dict):
   raise DomainRoutingError(f"Invalid domain profile: {path}")
  data["profile_path"]=str(path)
  profiles.append(data)
 if not profiles: raise DomainRoutingError(f"No domain profiles found in {profile_dir}")
 return profiles

def route_domain(text:str,profiles:list[dict[str,Any]]|None=None)->dict[str,Any]:
 profiles=profiles or load_profiles(); normalized=text.casefold(); results=[]
 for profile in profiles:
  matches=[]; score=0
  for keyword,weight in profile["keywords"].items():
   count=normalized.count(str(keyword).casefold())
   if count:
    contribution=min(count,4)*int(weight); score+=contribution; matches.append({"keyword":keyword,"count":count,"score":contribution})
  results.append({"id":profile["id"],"name":profile.get("name",profile["id"]),"score":score,"matches":matches,"profile_path":profile["profile_path"]})
 results.sort(key=lambda item:(-item["score"],item["id"])); top=results[0]; total=sum(item["score"] for item in results)
 if top["score"]==0:
  return {"selected":None,"confidence":"low","reason":"No domain keywords matched.","candidates":results[:3]}
 second=results[1]["score"] if len(results)>1 else 0; share=top["score"]/max(total,1); gap=top["score"]-second
 confidence="high" if share>=0.62 and gap>=8 else "medium" if share>=0.45 and gap>=3 else "low"
 return {"selected":top,"confidence":confidence,"reason":f"Matched {len(top['matches'])} weighted keyword groups.","candidates":results[:3]}

def main()->int:
 parser=argparse.ArgumentParser(description="Select a local experiment-report domain profile."); parser.add_argument("--input",type=Path); parser.add_argument("--text"); parser.add_argument("--profiles",type=Path,default=DEFAULT_PROFILES); parser.add_argument("--output",type=Path); args=parser.parse_args()
 if bool(args.input)==bool(args.text): parser.error("Provide exactly one of --input or --text")
 try:
  text=args.input.read_text(encoding="utf-8-sig") if args.input else str(args.text); result=route_domain(text,load_profiles(args.profiles))
 except (OSError,json.JSONDecodeError,DomainRoutingError) as exc:
  print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr); return 1
 payload={"ok":True,**result}; rendered=json.dumps(payload,ensure_ascii=False,indent=2)
 if args.output: args.output.write_text(rendered,encoding="utf-8")
 print(rendered); return 0
if __name__=="__main__": raise SystemExit(main())