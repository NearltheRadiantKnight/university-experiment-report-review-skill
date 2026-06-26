"""Tests for canonical output directory handling."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from output_paths import default_output_dir, resolve_output_dir


class OutputPathTests(unittest.TestCase):
    def test_default_output_dir_is_fixed_under_skill_outputs(self) -> None:
        expected = ROOT / "outputs" / "dashboard"
        self.assertEqual(default_output_dir(), expected)
        self.assertEqual(resolve_output_dir(None), expected.resolve())

    def test_custom_output_dir_requires_explicit_allowance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custom = Path(temp) / "custom-output"
            with self.assertRaises(ValueError):
                resolve_output_dir(custom)
            self.assertEqual(resolve_output_dir(custom, allow_custom=True), custom.resolve())

    def test_environment_can_allow_custom_output_for_ci(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custom = Path(temp) / "ci-output"
            previous = os.environ.get("EXPERIMENT_REPORT_ALLOW_CUSTOM_OUTPUT_DIR")
            os.environ["EXPERIMENT_REPORT_ALLOW_CUSTOM_OUTPUT_DIR"] = "1"
            try:
                self.assertEqual(resolve_output_dir(custom), custom.resolve())
            finally:
                if previous is None:
                    os.environ.pop("EXPERIMENT_REPORT_ALLOW_CUSTOM_OUTPUT_DIR", None)
                else:
                    os.environ["EXPERIMENT_REPORT_ALLOW_CUSTOM_OUTPUT_DIR"] = previous


    def test_generation_requires_conversational_confirmation_in_docs(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        workflow = (ROOT / "references" / "generated-document-workflow.md").read_text(encoding="utf-8")
        self.assertIn("user-confirmed", skill)
        self.assertIn("Dashboard saved settings are preferences only", skill)
        self.assertIn("missing user confirmation never writes `generation-plan.json`", skill)
        self.assertNotIn("directory.## Core Workflow", skill)
        self.assertIn("| user-confirmed |", workflow)
        self.assertIn("Dashboard preferences saved but no conversational confirmation", workflow)
        self.assertIn("saved `generation-preferences.json`", workflow)
        self.assertNotIn("mismatch." + "\n" + "Blocked edges", workflow)
    def test_cli_entries_expose_custom_output_override(self) -> None:
        for script in ("inspect_report.py", "run_pipeline.py", "dashboard_launcher.py", "dashboard_server.py"):
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script), "--help"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("--allow-custom-output-dir", completed.stdout)


if __name__ == "__main__":
    unittest.main()
