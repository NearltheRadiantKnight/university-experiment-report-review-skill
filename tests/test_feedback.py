"""Tests for loopback feedback, preferences, lifecycle records, and render retry."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from dashboard_server import create_app
from feedback_lifecycle import append_event
from skill_improvement_queue import claim_next, finish


class FeedbackTests(unittest.TestCase):
    def create_job(self, root: Path, job: str = "20260623-120000-123456"):
        report = root / f"{job}.docx"
        report.write_bytes(b"docx")
        metadata = {
            "job_id": job,
            "generated_name": report.name,
            "generated_files": [{"kind": "annotated", "label": "Report", "name": report.name}],
            "report_label": "Annotated report",
            "source_name": "source-report.docx",
            "actions": [
                {"label": "CFG evidence", "priority": "high", "category": "suggestion"},
                {"label": "Coverage screenshot", "priority": "blocker", "category": "issue"},
            ],
            "strengths": [],
        }
        (root / f"{job}.metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        return job, create_app(root).test_client()

    def save_one_feedback(self, client, job: str, index: int = 0, text: str = "Reusable correction"):
        payload = client.get(f"/api/reports/{job}/feedback").get_json()
        payload["actions"][index]["correction"] = text
        response = client.post(f"/api/reports/{job}/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_feedback_save_creates_active_records_and_events(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            saved = self.save_one_feedback(client, job, 1, "The coverage proof is enough.")
            self.assertEqual(saved["learning_status"], "recorded")

            visible = client.get("/api/feedback").get_json()["feedback"]
            pool = client.get("/api/feedback-pool").get_json()["feedback"]
            interpretations = client.get("/api/feedback-interpretations").get_json()["interpretations"]
            events = client.get("/api/feedback-lifecycle").get_json()["events"]

            self.assertEqual(len(visible), 1)
            self.assertEqual(len(pool), 1)
            self.assertEqual(pool[0]["status"], "active")
            self.assertEqual(interpretations[0]["status"], "drafted")
            self.assertEqual([event["type"] for event in events], ["feedback_saved", "interpretation_drafted"])

    def test_empty_feedback_is_not_written_to_feedback_pool(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            payload = client.get(f"/api/reports/{job}/feedback").get_json()
            saved = client.post(f"/api/reports/{job}/feedback", json=payload)
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(saved.get_json()["learning_status"], "not-needed")
            self.assertFalse((root / f"{job}.feedback.json").exists())
            self.assertEqual(client.get("/api/feedback").get_json()["feedback"], [])
            self.assertEqual(client.get("/api/feedback-pool").get_json()["feedback"], [])

    def test_withdraw_purges_feedback_interpretations_modifications_events_and_flat_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            self.save_one_feedback(client, job, 0, "Do not treat ordered CFG screenshots as a problem.")
            feedback = client.get("/api/feedback-pool").get_json()["feedback"][0]
            feedback_id = feedback["feedback_id"]
            interpretation = client.get("/api/feedback-interpretations").get_json()["interpretations"][0]
            mod_dir = root / "skill-modifications"
            mod_dir.mkdir()
            modification = {
                "modification_id": "mod-cfg-order",
                "source_feedback_id": feedback_id,
                "interpretation_id": interpretation["interpretation_id"],
                "status": "applied",
                "target_files": ["SKILL.md"],
                "before_behavior": "flag ordered CFG screenshots",
                "after_behavior": "ignore ordered CFG screenshots",
            }
            (mod_dir / "mod-cfg-order.modification.json").write_text(json.dumps(modification), encoding="utf-8")
            append_event(root, "modification_applied", feedback_id=feedback_id, modification_id="mod-cfg-order", job_id=job)

            deleted = client.delete(f"/api/feedback/{feedback_id}")
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(deleted.get_json()["learning_status"], "purged")
            self.assertFalse((root / f"{job}.feedback.json").exists())
            self.assertEqual(client.get("/api/feedback").get_json()["feedback"], [])
            self.assertEqual(client.get("/api/feedback-pool").get_json()["feedback"], [])
            self.assertEqual(client.get("/api/feedback-interpretations").get_json()["interpretations"], [])
            self.assertEqual(client.get("/api/skill-modifications").get_json()["modifications"], [])
            self.assertEqual(client.get("/api/feedback-lifecycle").get_json()["events"], [])

    def test_withdraw_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            self.save_one_feedback(client, job, 0)
            feedback_id = client.get("/api/feedback-pool").get_json()["feedback"][0]["feedback_id"]
            first = client.delete(f"/api/feedback/{feedback_id}")
            second = client.delete(f"/api/feedback/{feedback_id}")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(second.get_json()["lifecycle"]["purged_count"], 0)

    def test_hidden_action_is_restored_after_withdraw_without_reclassification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            self.save_one_feedback(client, job, 0, "This front-end issue is wrong.")
            report = client.get("/api/reports").get_json()["reports"][0]
            self.assertEqual([item.get("category") for item in report["actions"]], ["suggestion", "issue"])
            self.assertTrue(report["actions"][0]["hidden_by_active_feedback"])
            self.assertFalse(report["actions"][1]["hidden_by_active_feedback"])
            self.assertEqual(report["strengths"], [])

            cleared = client.delete(f"/api/reports/{job}/feedback")
            self.assertEqual(cleared.status_code, 200)
            restored = client.get("/api/reports").get_json()["reports"][0]
            self.assertFalse(any(item.get("hidden_by_active_feedback") for item in restored["actions"]))
            self.assertEqual([item.get("category") for item in restored["actions"]], ["suggestion", "issue"])

    def test_history_survives_flat_json_loss_until_withdraw(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            self.save_one_feedback(client, job, 0, "Teacher did not require CFG order notes.")
            feedback_id = client.get("/api/feedback-pool").get_json()["feedback"][0]["feedback_id"]
            (root / f"{job}.feedback.json").unlink()
            history = client.get("/api/feedback").get_json()["feedback"]
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["history_source"], "feedback-pool")
            self.assertEqual(history[0]["actions"][0]["status"], "drafted")
            deleted = client.delete(f"/api/feedback/{feedback_id}")
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(client.get("/api/feedback").get_json()["feedback"], [])

    def test_personal_memory_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _job, client = self.create_job(root)
            self.assertEqual(client.get("/api/personal-memory").get_json()["notes"], "")
            notes = "student: Liu; course: software testing"
            saved = client.put("/api/personal-memory", json={"notes": notes})
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(saved.get_json()["notes"], notes)
            self.assertTrue((root / "personal-memory.json").is_file())

    def test_preferences_and_lifecycle_queue_wrapper(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            self.save_one_feedback(client, job, 0, "All screenshots need concrete retake instructions.")
            preferences = {"time_budget": "1h", "review_depth": "deep", "review_focus": "screenshots", "output_mode": "single_docx"}
            self.assertEqual(client.put("/api/generation-preferences", json=preferences).status_code, 200)
            queued = client.post("/api/skill-improvement-requests", json={"job_ids": [job]})
            self.assertEqual(queued.status_code, 200)
            claimed = claim_next(root / "skill-improvement-queue", "agent")
            self.assertEqual(claimed["status"], "processed")
            completed = finish(root / "skill-improvement-queue", claimed["request_id"], "processed", "validated")
            self.assertEqual(completed["status"], "processed")

    def test_render_retry_and_preview(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            preview = root / "preview.jpg"
            preview.write_bytes(b"jpg")
            result = {"status": "passed", "backend": "test", "attempts": [], "pdf": None, "pages": [], "preview": preview.name}
            with patch("dashboard_server.render_report", return_value=result):
                response = client.post(f"/api/reports/{job}/render")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["quality"]["render_status"], "passed")
            preview_response = client.get(f"/api/reports/{job}/render-preview")
            self.assertEqual(preview_response.status_code, 200)
            preview_response.close()
            with patch("dashboard_server.render_report", side_effect=RuntimeError("renderer crashed")):
                failed = client.post(f"/api/reports/{job}/render")
            self.assertEqual(failed.status_code, 200)
            self.assertEqual(failed.get_json()["quality"]["render_status"], "failed")

    def test_dashboard_button_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job, client = self.create_job(root)
            self.assertEqual(client.get("/api/reports").status_code, 200)
            self.assertEqual(client.get("/api/generation-preferences").status_code, 200)
            self.save_one_feedback(client, job, 0)
            self.assertEqual(len(client.get("/api/feedback").get_json()["feedback"]), 1)
            self.assertEqual(client.get("/api/feedback-pool").status_code, 200)
            self.assertEqual(client.get("/api/feedback-interpretations").status_code, 200)
            self.assertEqual(client.get("/api/skill-modifications").status_code, 200)
            self.assertEqual(client.get("/api/feedback-lifecycle").status_code, 200)
            download = client.get(f"/api/reports/{job}/download/annotated")
            self.assertEqual(download.status_code, 200)
            download.close()
            with patch("dashboard_server.render_report", return_value={"status": "unavailable", "backend": None, "attempts": [], "pdf": None, "pages": [], "preview": None}):
                self.assertEqual(client.post(f"/api/reports/{job}/render").status_code, 200)
            cleared = client.post(f"/api/reports/{job}/feedback/clear")
            self.assertEqual(cleared.status_code, 200)
            self.assertEqual(cleared.get_json()["learning_status"], "purged")
            self.assertEqual(client.delete(f"/api/reports/{job}/feedback").status_code, 200)


if __name__ == "__main__":
    unittest.main()