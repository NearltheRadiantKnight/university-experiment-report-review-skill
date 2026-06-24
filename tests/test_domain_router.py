"""Tests for local domain routing."""
from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from domain_router import route_domain
class DomainRouterTests(unittest.TestCase):
 def test_qtp_routes_to_software_testing(self): self.assertEqual(route_domain("QTP 等价类 边界值 测试用例")["selected"]["id"],"software-testing")
 def test_wireshark_routes_to_networking(self): self.assertEqual(route_domain("Wireshark 抓包 TCP ping 路由")["selected"]["id"],"networking")
 def test_ambiguous_text_has_low_confidence(self): self.assertEqual(route_domain("实验目的 实验步骤 实验心得")["confidence"],"low")
if __name__=="__main__": unittest.main()