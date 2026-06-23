#!/usr/bin/env python3
"""Start the local report dashboard when needed and open it in a browser."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "scripts" / "dashboard_server.py"


def _healthy(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def launch_dashboard(output_dir: Path, port: int = 8765, open_browser: bool = True) -> str:
    """Ensure the dashboard is running and optionally open the default browser."""
    if port < 1024 or port > 65535:
        raise ValueError("port must be between 1024 and 65535")
    output_dir.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{port}"

    if not _healthy(url):
        command = [
            sys.executable,
            str(SERVER_SCRIPT),
            "--output-dir",
            str(output_dir.resolve()),
            "--port",
            str(port),
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            close_fds=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if _healthy(url):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Dashboard did not become ready within 10 seconds.")

    if open_browser:
        webbrowser.open(url, new=2)
    return url


def main() -> int:
    """Launch the local dashboard and print its URL as JSON."""
    parser = argparse.ArgumentParser(description="Launch the local report download dashboard.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="Start without opening a browser.")
    args = parser.parse_args()
    try:
        url = launch_dashboard(args.output_dir, args.port, not args.no_open)
    except (ValueError, RuntimeError, OSError) as exc:
        print(
            json.dumps(
                {"error": str(exc), "error_type": "runtime", "hint": "Try another local port."},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"ok": True, "url": url}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
