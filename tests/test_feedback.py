"""Tests for loopback feedback, preferences, lifecycle records, and render retry."""
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
  metadata={"job_id":job,"generated_name":report.name,"generated_files":[{"kind":"annotated","label":"报告","name":report.name}],"report_label":"修改报告","source_name":"source.docx","actions":[{"label":"补截图","priority":"high"},{"label":"源码染色截图不达标","priority":"blocker"}]}
  (root/f"{job}.metadata.json").write_text(json.dumps(metadata,ensure_ascii=False),encoding="utf-8")
  return job,create_app(root).test_client()

 def test_feedback_save_creates_raw_feedback_interpretation_and_events(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); payload=client.get(f"/api/reports/{job}/feedback").get_json(); self.assertNotIn("status", payload["actions"][0])
   payload["actions"][1]["correction"]="本实验所用目标方法全绿即可证明"
   saved=client.post(f"/api/reports/{job}/feedback",json=payload)
   self.assertEqual(saved.status_code,200); self.assertEqual(saved.get_json()["learning_status"],"recorded")
   pool=client.get("/api/feedback-pool").get_json()["feedback"]
   self.assertEqual(len(pool),1); self.assertEqual(pool[0]["status"],"active"); self.assertEqual(pool[0]["raw_text"],"本实验所用目标方法全绿即可证明")
   interpretations=client.get("/api/feedback-interpretations").get_json()["interpretations"]
   self.assertEqual(len(interpretations),1); self.assertEqual(interpretations[0]["status"],"drafted"); self.assertIsNone(interpretations[0]["scope"])
   events=client.get("/api/feedback-lifecycle").get_json()["events"]
   self.assertEqual([event["type"] for event in events], ["feedback_saved","interpretation_drafted"])
   queued=client.get("/api/skill-improvement-requests").get_json()["requests"]
   self.assertEqual(queued[0]["status"],"ready_for_agent"); self.assertNotEqual(queued[0]["status"],"pending-agent")

 def test_feedback_clear_and_delete_revoke_lifecycle_records(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); payload=client.get(f"/api/reports/{job}/feedback").get_json(); payload["actions"][0]["correction"]="已替换清晰截图"; client.post(f"/api/reports/{job}/feedback",json=payload)
   cleared=client.post(f"/api/reports/{job}/feedback/clear")
   self.assertEqual(cleared.status_code,200); self.assertEqual(cleared.get_json()["learning_status"],"revoked")
   pool=client.get("/api/feedback-pool").get_json()["feedback"]
   self.assertEqual(pool[0]["status"],"revoked")
   interpretations=client.get("/api/feedback-interpretations").get_json()["interpretations"]
   self.assertEqual(interpretations[0]["status"],"revoked")
   payload=client.get(f"/api/reports/{job}/feedback").get_json(); payload["actions"][0]["correction"]="再次保存"; client.post(f"/api/reports/{job}/feedback",json=payload)
   deleted=client.delete(f"/api/reports/{job}/feedback")
   self.assertEqual(deleted.status_code,200); self.assertEqual(deleted.get_json()["learning_status"],"revoked")

 def test_applied_feedback_revoke_drafts_revert_modification(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); payload=client.get(f"/api/reports/{job}/feedback").get_json(); payload["actions"][0]["correction"]="可复用规则"; client.post(f"/api/reports/{job}/feedback",json=payload)
   feedback_id=client.get("/api/feedback-pool").get_json()["feedback"][0]["feedback_id"]
   interp_id=client.get("/api/feedback-interpretations").get_json()["interpretations"][0]["interpretation_id"]
   mod_dir=root/"skill-modifications"; mod_dir.mkdir()
   applied={"modification_id":"mod-existing","source_feedback_id":feedback_id,"interpretation_id":interp_id,"status":"applied","target_files":["SKILL.md"],"before_behavior":"old","after_behavior":"new","validation_plan":[],"revert_plan":"restore old"}
   (mod_dir/"mod-existing.modification.json").write_text(json.dumps(applied,ensure_ascii=False),encoding="utf-8")
   client.delete(f"/api/reports/{job}/feedback")
   mods=client.get("/api/skill-modifications").get_json()["modifications"]
   self.assertIn("revert_drafted", {item["status"] for item in mods})
   self.assertNotIn("failed", {item["status"] for item in mods})

 def test_feedback_history_keeps_lifecycle_records_after_application(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); payload=client.get(f"/api/reports/{job}/feedback").get_json(); payload["actions"][0]["correction"]="按出现顺序可以判断 CFG 对应方法"; client.post(f"/api/reports/{job}/feedback",json=payload)
   feedback_id=client.get("/api/feedback-pool").get_json()["feedback"][0]["feedback_id"]
   interp_id=client.get("/api/feedback-interpretations").get_json()["interpretations"][0]["interpretation_id"]
   (root/f"{job}.feedback.json").unlink()
   mod_dir=root/"skill-modifications"; mod_dir.mkdir()
   applied={"modification_id":"mod-applied","source_feedback_id":feedback_id,"interpretation_id":interp_id,"status":"applied","target_files":["SKILL.md"],"before_behavior":"old","after_behavior":"new","validation_plan":[],"revert_plan":"restore old"}
   (mod_dir/"mod-applied.modification.json").write_text(json.dumps(applied,ensure_ascii=False),encoding="utf-8")
   history=client.get("/api/feedback").get_json()["feedback"]
   self.assertEqual(len(history),1)
   self.assertEqual(history[0]["history_source"],"feedback-pool")
   self.assertEqual(history[0]["actions"][0]["correction"],"按出现顺序可以判断 CFG 对应方法")
   self.assertEqual(history[0]["actions"][0]["status"],"applied")
   (root/f"{job}.metadata.json").unlink()
   cleared=client.post(f"/api/feedback/{feedback_id}/clear")
   self.assertEqual(cleared.status_code,200)
   self.assertEqual(cleared.get_json()["learning_status"],"revoked")
   mods=client.get("/api/skill-modifications").get_json()["modifications"]
   self.assertIn("revert_drafted", {item["status"] for item in mods})
 def test_personal_memory_round_trip(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); _job,client=self.create_job(root)
   empty=client.get("/api/personal-memory")
   self.assertEqual(empty.status_code,200); self.assertEqual(empty.get_json()["notes"],"")
   notes="学生：刘思婕；课程：软件测试"
   saved=client.put("/api/personal-memory",json={"notes":notes})
   self.assertEqual(saved.status_code,200); self.assertEqual(saved.get_json()["notes"],notes)
   self.assertTrue((root/"personal-memory.json").is_file())

 def test_preferences_and_lifecycle_queue_wrapper(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); job,client=self.create_job(root); feedback=client.get(f"/api/reports/{job}/feedback").get_json(); feedback["actions"][0]["correction"]="所有截图都应给具体重拍指令"; client.post(f"/api/reports/{job}/feedback",json=feedback)
   preferences={"time_budget":"1h","review_depth":"deep","review_focus":"screenshots","output_mode":"single_docx"}; saved=client.put("/api/generation-preferences",json=preferences); self.assertEqual(saved.status_code,200); self.assertEqual(client.get("/api/generation-preferences").get_json()["review_depth"],"deep")
   queued=client.post("/api/skill-improvement-requests",json={"job_ids":[job]}); self.assertEqual(queued.status_code,200); result=queued.get_json(); self.assertEqual(result["request"]["status"],"ready_for_agent")
   claimed=claim_next(root/"skill-improvement-queue","agent"); self.assertEqual(claimed["status"],"processed"); completed=finish(root/"skill-improvement-queue",claimed["request_id"],"processed","validated"); self.assertEqual(completed["status"],"processed")

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
   self.assertEqual(client.get("/api/feedback-pool").status_code,200)
   self.assertEqual(client.get("/api/feedback-interpretations").status_code,200)
   self.assertEqual(client.get("/api/skill-modifications").status_code,200)
   self.assertEqual(client.get("/api/feedback-lifecycle").status_code,200)
   queued=client.get("/api/skill-improvement-requests")
   self.assertEqual(queued.status_code,200)
   self.assertFalse(any(item.get("status")=="pending-agent" for item in queued.get_json()["requests"]))
   download=client.get(f"/api/reports/{job}/download/annotated"); self.assertEqual(download.status_code,200); download.close()
   with patch("dashboard_server.render_report",return_value={"status":"unavailable","backend":None,"attempts":[],"pdf":None,"pages":[],"preview":None}):
    self.assertEqual(client.post(f"/api/reports/{job}/render").status_code,200)
   cleared=client.post(f"/api/reports/{job}/feedback/clear")
   self.assertEqual(cleared.status_code,200); self.assertEqual(cleared.get_json()["learning_status"],"revoked")
   self.assertEqual(client.delete(f"/api/reports/{job}/feedback").status_code,200)

if __name__=="__main__": unittest.main()
