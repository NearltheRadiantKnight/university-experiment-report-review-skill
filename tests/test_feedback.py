"""Tests for loopback-only feedback persistence."""
from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from dashboard_server import create_app
class FeedbackTests(unittest.TestCase):
 def test_feedback_round_trip_and_download(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job="20260623-120000-123456"; report=root/"report.docx"; report.write_bytes(b"docx")
   metadata={"job_id":job,"generated_name":report.name,"generated_files":[{"kind":"annotated","label":"报告","name":report.name}],"report_label":"修改报告","source_name":"source.docx","actions":[{"label":"补截图","priority":"high"}]}
   (root/f"{job}.metadata.json").write_text(json.dumps(metadata,ensure_ascii=False),encoding="utf-8"); client=create_app(root).test_client()
   feedback=client.get(f"/api/reports/{job}/feedback"); self.assertEqual(feedback.status_code,200); payload=feedback.get_json(); self.assertEqual(payload["actions"][0]["status"],"open")
   payload["actions"][0]["status"]="done"; payload["actions"][0]["correction"]="已替换清晰截图"; payload["confirmed_context"]={"teacher_rule":"需要完整窗口"}
   saved=client.post(f"/api/reports/{job}/feedback",json=payload); self.assertEqual(saved.status_code,200); download=client.get(saved.get_json()["download_url"]); self.assertEqual(download.status_code,200); self.assertIn("已替换清晰截图".encode("utf-8"),download.data); download.close()
if __name__=="__main__": unittest.main()