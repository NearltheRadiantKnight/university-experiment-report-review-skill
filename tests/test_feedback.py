"""Tests for loopback feedback, preferences, improvement queue, and render retry."""
from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
from dashboard_server import create_app
from skill_improvement_queue import claim_next,finish

class FeedbackTests(unittest.TestCase):
 def create_job(self,root:Path)->tuple[str,object]:
  job="20260623-120000-123456"; report=root/"report.docx"; report.write_bytes(b"docx")
  metadata={"job_id":job,"generated_name":report.name,"generated_files":[{"kind":"annotated","label":"报告","name":report.name}],"report_label":"修改报告","source_name":"source.docx","actions":[{"label":"补截图","priority":"high"}]}
  (root/f"{job}.metadata.json").write_text(json.dumps(metadata,ensure_ascii=False),encoding="utf-8")
  return job,create_app(root).test_client()

 def test_feedback_round_trip_edit_and_delete(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); payload=client.get(f"/api/reports/{job}/feedback").get_json(); self.assertEqual(payload["actions"][0]["status"],"open")
   payload["actions"][0]["status"]="done"; payload["actions"][0]["correction"]="已替换清晰截图"; payload["confirmed_context"]={"teacher_rule":"需要完整窗口"}
   saved=client.post(f"/api/reports/{job}/feedback",json=payload); self.assertEqual(saved.status_code,200)
   payload["actions"]=[]; self.assertEqual(client.put(f"/api/reports/{job}/feedback",json=payload).status_code,200); self.assertEqual(client.get(f"/api/reports/{job}/feedback").get_json()["actions"],[])
   self.assertEqual(client.delete(f"/api/reports/{job}/feedback").status_code,200); self.assertFalse((root/f"{job}.feedback.json").exists())

 def test_preferences_and_skill_improvement_queue(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); feedback=client.get(f"/api/reports/{job}/feedback").get_json(); feedback["confirmed_context"]={"user_notes":"所有截图都应给具体重拍指令"}; client.post(f"/api/reports/{job}/feedback",json=feedback)
   preferences={"time_budget":"1h","review_depth":"deep","review_focus":"screenshots","output_mode":"single_docx"}; saved=client.put("/api/generation-preferences",json=preferences); self.assertEqual(saved.status_code,200); self.assertEqual(client.get("/api/generation-preferences").get_json()["review_depth"],"deep")
   queued=client.post("/api/skill-improvement-requests",json={"job_ids":[job]}); self.assertEqual(queued.status_code,200); result=queued.get_json(); queue_path=Path(result["queue_path"]); self.assertTrue(queue_path.is_file()); self.assertTrue(Path(result["prompt_path"]).is_file()); self.assertIn("agent-skill-creator",result["activation_text"])
   claimed=claim_next(queue_path.parent,"codex"); self.assertEqual(claimed["status"],"in-progress"); completed=finish(queue_path.parent,claimed["request_id"],"completed","validated"); self.assertEqual(completed["status"],"completed")

 def test_render_retry_and_preview(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); preview=root/"preview.jpg"; preview.write_bytes(b"jpg")
   result={"status":"passed","backend":"test","attempts":[],"pdf":None,"pages":[],"preview":preview.name}
   with patch("dashboard_server.render_report",return_value=result): response=client.post(f"/api/reports/{job}/render")
   self.assertEqual(response.status_code,200); self.assertEqual(response.get_json()["quality"]["render_status"],"passed")
   preview_response=client.get(f"/api/reports/{job}/render-preview"); self.assertEqual(preview_response.status_code,200); preview_response.close()
   with patch("dashboard_server.render_report",side_effect=RuntimeError("renderer crashed")): failed=client.post(f"/api/reports/{job}/render")
   self.assertEqual(failed.status_code,200); self.assertEqual(failed.get_json()["quality"]["render_status"],"failed")

 def test_dashboard_button_routes(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root)
   self.assertEqual(client.get("/api/reports").status_code,200)
   self.assertEqual(client.get("/api/generation-preferences").status_code,200)
   preferences={"time_budget":"full","review_depth":"deep","review_focus":"comprehensive","output_mode":"single_docx"}
   self.assertEqual(client.put("/api/generation-preferences",json=preferences).status_code,200)
   feedback=client.get(f"/api/reports/{job}/feedback").get_json()
   self.assertEqual(client.post(f"/api/reports/{job}/feedback",json=feedback).status_code,200)
   self.assertEqual(len(client.get("/api/feedback").get_json()["feedback"]),1)
   queued=client.post("/api/skill-improvement-requests",json={"job_ids":[]})
   self.assertEqual(queued.status_code,200)
   self.assertIn("activation_text",queued.get_json())
   download=client.get(f"/api/reports/{job}/download/annotated"); self.assertEqual(download.status_code,200); download.close()
   with patch("dashboard_server.render_report",return_value={"status":"unavailable","backend":None,"attempts":[],"pdf":None,"pages":[],"preview":None}):
    self.assertEqual(client.post(f"/api/reports/{job}/render").status_code,200)
   self.assertEqual(client.delete(f"/api/reports/{job}/feedback").status_code,200)

if __name__=="__main__": unittest.main()
