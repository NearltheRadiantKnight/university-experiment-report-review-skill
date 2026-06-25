#!/usr/bin/env python3
"""Start the local report dashboard when needed and open it in a browser."""

from __future__ import annotations

import argparse
import json
import os
import hashlib
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "scripts" / "dashboard_server.py"


SERVICE_NAME = "university-experiment-report-dashboard"
API_VERSION = 4
ASSET_VERSION = "1.5.3"


def _output_dir_id(output_dir: Path) -> str:
    return hashlib.sha256(str(output_dir.resolve()).casefold().encode("utf-8")).hexdigest()[:16]


def _health(url: str) -> dict[str, object] | None:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=1.0) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, urllib.error.URLError):
        return None


def _matching_dashboard(url: str, output_dir: Path) -> bool:
    health = _health(url)
    return bool(
        health
        and health.get("service") == SERVICE_NAME
        and health.get("api_version") == API_VERSION
        and health.get("asset_version") == ASSET_VERSION
        and health.get("output_dir_id") == _output_dir_id(output_dir)
    )


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _select_port(output_dir: Path, requested_port: int) -> tuple[int, bool]:
    for port in range(requested_port, min(requested_port + 100, 65536)):
        url = f"http://127.0.0.1:{port}"
        if _matching_dashboard(url, output_dir):
            return port, True
        if _port_available(port):
            return port, False
    raise RuntimeError("No available dashboard port was found.")


def launch_dashboard(output_dir: Path, port: int = 8765, open_browser: bool = True) -> str:
    """Ensure the dashboard is running and optionally open the default browser."""
    if port < 1024 or port > 65535:
        raise ValueError("port must be between 1024 and 65535")
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_port, already_running = _select_port(output_dir, port)
    url = f"http://127.0.0.1:{selected_port}"

    if not already_running:
        command = [
            sys.executable,
            str(SERVER_SCRIPT),
            "--output-dir",
            str(output_dir.resolve()),
            "--port",
            str(selected_port),
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
            if _matching_dashboard(url, output_dir):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Dashboard did not become ready within 10 seconds.")

    if open_browser:
        webbrowser.open(url, new=2)
    (output_dir / "dashboard-url.txt").write_text(url + "\n", encoding="utf-8")
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
