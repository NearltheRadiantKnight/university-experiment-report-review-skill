#!/usr/bin/env python3
"""Single entry point for report generation and local dashboard delivery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from build_report import ReportBuildError, build_report
from dashboard_launcher import launch_dashboard


def run_pipeline(
    source: Path,
    plan: Path,
    output_dir: Path,
    port: int = 8765,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Build an annotated DOCX and publish it through the local dashboard."""
    generated_path, metadata_path = build_report(source, plan, output_dir)
    dashboard_url = launch_dashboard(output_dir, port, open_browser)
    return {
        "generated_report": str(generated_path),
        "metadata": str(metadata_path),
        "dashboard_url": dashboard_url,
        "local_only": True,
    }


def main() -> int:
    """Run the complete deterministic delivery pipeline."""
    parser = argparse.ArgumentParser(description="Generate a report and open its local download page.")
    parser.add_argument("--source", type=Path, required=True, help="Original DOCX report.")
    parser.add_argument("--plan", type=Path, required=True, help="Codex generation plan JSON.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Generated report directory.")
    parser.add_argument("--port", type=int, default=8765, help="Local dashboard port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()
    try:
        result = run_pipeline(
            args.source.resolve(),
            args.plan.resolve(),
            args.output_dir.resolve(),
            args.port,
            not args.no_open,
        )
    except (ValueError, ReportBuildError, RuntimeError, OSError) as exc:
        print(
            json.dumps(
                {"error": str(exc), "error_type": "runtime", "hint": "Check DOCX, plan, output path, and port."},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
