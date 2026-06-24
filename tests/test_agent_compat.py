"""Tests for AgentSkills contract smoke checks."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from agent_compat import run
class AgentCompatTests(unittest.TestCase):
 def test_contract_passes_without_installed_external_agents(self):
  result=run(ROOT,["claude-code","openclaw"]); self.assertTrue(result["contract_ok"]); self.assertTrue(all(item["status"] in {"passed","failed","blocked","not-installed"} for item in result["runtime"]))
if __name__=="__main__": unittest.main()