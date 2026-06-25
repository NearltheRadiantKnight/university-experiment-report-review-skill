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
   root=Path(temp); job,client=self.create_job(root); payload=client.get(f"/api/reports/{job}/feedback").get_json(); self.assertNotIn("status", payload["actions"][0])
   payload["actions"][0]["correction"]="已替换清晰截图"; payload["confirmed_context"]={"teacher_rule":"需要完整窗口"}
   saved=client.post(f"/api/reports/{job}/feedback",json=payload); self.assertEqual(saved.status_code,200); self.assertEqual(saved.get_json()["learning_status"],"queued")
   payload["actions"]=[]; updated=client.put(f"/api/reports/{job}/feedback",json=payload); self.assertEqual(updated.status_code,200); self.assertIsNone(updated.get_json()["learning_request_id"]); self.assertEqual(client.get(f"/api/reports/{job}/feedback").get_json()["actions"],[])
   deleted=client.delete(f"/api/reports/{job}/feedback"); self.assertEqual(deleted.status_code,200); self.assertEqual(deleted.get_json()["learning_status"],"not-needed"); self.assertFalse((root/f"{job}.feedback.json").exists())
   auto=root/"skill-improvement-queue"/"auto-feedback-learning.skill-improvement.json"; self.assertTrue(auto.is_file()); events=json.loads(auto.read_text(encoding="utf-8"))["events"]; self.assertEqual([item["type"] for item in events[-1:]], ["feedback_saved"])

 def test_personal_memory_round_trip(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); _job,client=self.create_job(root)
   empty=client.get("/api/personal-memory")
   self.assertEqual(empty.status_code,200)
   self.assertEqual(empty.get_json()["notes"],"")
   notes="\u5b66\u751f\uff1a\u5218\u601d\u5a55\uff1b\u8bfe\u7a0b\uff1a\u8f6f\u4ef6\u6d4b\u8bd5"
   saved=client.put("/api/personal-memory",json={"notes":notes})
   self.assertEqual(saved.status_code,200)
   self.assertEqual(saved.get_json()["notes"],notes)
   loaded=client.get("/api/personal-memory").get_json()
   self.assertEqual(loaded["notes"],notes)
   self.assertTrue((root/"personal-memory.json").is_file())

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
   queued=client.get("/api/skill-improvement-requests")
   self.assertEqual(queued.status_code,200)
   self.assertFalse(any(item.get("request_id")=="auto-feedback-learning" for item in queued.get_json()["requests"]))
   download=client.get(f"/api/reports/{job}/download/annotated"); self.assertEqual(download.status_code,200); download.close()
   with patch("dashboard_server.render_report",return_value={"status":"unavailable","backend":None,"attempts":[],"pdf":None,"pages":[],"preview":None}):
    self.assertEqual(client.post(f"/api/reports/{job}/render").status_code,200)
   cleared=client.post(f"/api/reports/{job}/feedback/clear")
   self.assertEqual(cleared.status_code,200)
   self.assertEqual(cleared.get_json()["learning_status"],"not-needed")
   self.assertEqual(client.delete(f"/api/reports/{job}/feedback").status_code,200)

if __name__=="__main__": unittest.main()
