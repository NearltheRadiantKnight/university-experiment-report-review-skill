#!/usr/bin/env python3
"""Resolve stable local output paths for report review runs."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "dashboard"


def default_output_dir() -> Path:
    """Return the canonical output directory for normal interactive runs."""
    return DEFAULT_OUTPUT_DIR


def custom_output_allowed() -> bool:
    """Return whether this process may write outside the canonical output dir."""
    return os.environ.get("EXPERIMENT_REPORT_ALLOW_CUSTOM_OUTPUT_DIR") == "1" or os.environ.get("CI") == "1"


def resolve_output_dir(path: Path | None, *, allow_custom: bool = False) -> Path:
    """Resolve and validate the output directory.

    Normal skill runs use one stable output directory so generated DOCX files,
    metadata, feedback lifecycle records, and Dashboard state stay together.
    Tests, CI, and explicitly approved maintenance commands may override it.
    """
    default = default_output_dir().resolve()
    if path is None:
        return default
    resolved = path.resolve()
    if resolved == default:
        return resolved
    if allow_custom or custom_output_allowed():
        return resolved
    raise ValueError(
        "Custom output directories are disabled for normal runs. "
        f"Use the fixed output directory {default}, or pass --allow-custom-output-dir "
        "for tests/CI/explicit maintenance."
    )
