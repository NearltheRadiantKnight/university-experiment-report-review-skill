"""Tests for the local experiment-report preparation script."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from inspect_report import prepare_report


class PrepareReportTests(unittest.TestCase):
    """Verify local extraction, validation, and manifest generation."""

    def test_plain_text_manifest(self) -> None:
        """A UTF-8 text report should produce text and a valid manifest."""
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            input_path = temp_dir / "report.txt"
            output_dir = temp_dir / "prepared"
            input_path.write_text("实验目的\n完成任务并分析结果。", encoding="utf-8")

            manifest_path = prepare_report(input_path, output_dir)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertTrue(manifest["local_only"])
            self.assertEqual(manifest["input"]["suffix"], ".txt")
            self.assertIn("实验目的", (output_dir / "document.txt").read_text(encoding="utf-8"))

    def test_docx_text_and_image_extraction(self) -> None:
        """A minimal DOCX archive should expose paragraph text and embedded media."""
        document_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>实验结果正常</w:t></w:r></w:p></w:body></w:document>'
        )
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            input_path = temp_dir / "report.docx"
            output_dir = temp_dir / "prepared"
            with zipfile.ZipFile(input_path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
                archive.writestr("word/media/image1.png", b"not-a-real-png-but-valid-extraction-bytes")

            manifest_path = prepare_report(input_path, output_dir)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["visual_count"], 1)
            self.assertIn("实验结果正常", (output_dir / "document.txt").read_text(encoding="utf-8"))
            self.assertTrue((output_dir / manifest["visuals"][0]["path"]).is_file())

    def test_unsupported_extension_is_rejected(self) -> None:
        """Unsupported legacy formats should fail with a clear validation error."""
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            input_path = temp_dir / "legacy.doc"
            input_path.write_bytes(b"legacy")

            with self.assertRaisesRegex(ValueError, "Unsupported file type"):
                prepare_report(input_path, temp_dir / "prepared")


if __name__ == "__main__":
    unittest.main()
