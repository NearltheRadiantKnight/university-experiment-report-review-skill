#!/usr/bin/env python3
"""Serve a local-only dashboard for generated experiment reports.

The Flask app binds to loopback, reads trusted metadata emitted by the local
pipeline, and exposes only registered generated DOCX files for download.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template, send_file

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "assets" / "dashboard" / "templates"
STATIC_DIR = ROOT / "assets" / "dashboard" / "static"


def _metadata_records(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not output_dir.is_dir():
        return records
    for metadata_path in sorted(output_dir.glob("*.metadata.json"), reverse=True):
        try:
            record = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        generated_name = str(record.get("generated_name", ""))
        generated_path = output_dir / generated_name
        if not generated_name or not generated_path.is_file():
            continue
        record["download_url"] = f"/api/reports/{record.get('job_id', '')}/download"
        records.append(record)
    return records


def _resolve_registered_report(output_dir: Path, job_id: str) -> tuple[dict[str, Any], Path]:
    if not re_full_job_id(job_id):
        abort(404)
    metadata_path = output_dir / f"{job_id}.metadata.json"
    if not metadata_path.is_file():
        abort(404)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        abort(404)
    generated_name = str(metadata.get("generated_name", ""))
    if Path(generated_name).name != generated_name:
        abort(404)
    generated_path = (output_dir / generated_name).resolve()
    output_root = output_dir.resolve()
    if generated_path.parent != output_root or not generated_path.is_file():
        abort(404)
    return metadata, generated_path


def re_full_job_id(job_id: str) -> bool:
    """Validate the timestamp-based identifier accepted by download routes."""
    import re

    return re.fullmatch(r"\d{8}-\d{6}-\d{6}", job_id) is not None


def create_app(output_dir: Path) -> Flask:
    """Create a loopback dashboard app backed by one output directory."""
    resolved_output = output_dir.resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/health")
    def health() -> Any:
        return jsonify({"ok": True, "local_only": True})

    @app.get("/api/reports")
    def reports() -> Any:
        return jsonify({"reports": _metadata_records(resolved_output)})

    @app.get("/api/reports/<job_id>/metadata")
    def report_metadata(job_id: str) -> Any:
        metadata, _ = _resolve_registered_report(resolved_output, job_id)
        return jsonify(metadata)

    @app.get("/api/reports/<job_id>/download")
    def download(job_id: str) -> Any:
        metadata, generated_path = _resolve_registered_report(resolved_output, job_id)
        return send_file(
            generated_path,
            as_attachment=True,
            download_name=str(metadata["generated_name"]),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    return app


def main() -> int:
    """Run the local dashboard server on loopback only."""
    parser = argparse.ArgumentParser(description="Serve generated experiment reports locally.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated report directory.")
    parser.add_argument("--port", type=int, default=8765, help="Loopback TCP port.")
    args = parser.parse_args()
    if args.port < 1024 or args.port > 65535:
        parser.error("--port must be between 1024 and 65535")
    app = create_app(args.output_dir)
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
