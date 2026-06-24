"""Tests for dashboard instance and output-directory selection."""
from __future__ import annotations
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
SCRIPTS_DIR=Path(__file__).resolve().parents[1]/"scripts"; sys.path.insert(0,str(SCRIPTS_DIR))
import dashboard_launcher
class DashboardLauncherTests(unittest.TestCase):
 def test_reuses_only_matching_dashboard(self):
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(dashboard_launcher,"_matching_dashboard",side_effect=[True]),patch.object(dashboard_launcher,"_port_available") as available:
    self.assertEqual(dashboard_launcher._select_port(Path(temp),8765),(8765,True)); available.assert_not_called()
 def test_skips_stale_dashboard_port(self):
  with tempfile.TemporaryDirectory() as temp:
   with patch.object(dashboard_launcher,"_matching_dashboard",side_effect=[False,False]),patch.object(dashboard_launcher,"_port_available",side_effect=[False,True]):
    self.assertEqual(dashboard_launcher._select_port(Path(temp),8765),(8766,False))
if __name__=="__main__": unittest.main()
