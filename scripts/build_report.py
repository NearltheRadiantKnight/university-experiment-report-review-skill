#!/usr/bin/env python3
"""Build an annotated experiment report from an original DOCX and Codex plan.

The generator preserves all original paragraphs, runs, tables, images, and styles
while inserting clearly marked colored content supplied by the current Codex run.
It performs no model call, OCR request, upload, or network operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph

SKILL_NAME = "university-experiment-report-review-skill"
VERSION = "1.1.0"
REPORT_KINDS = {"execution", "revision"}
DEFAULT_FONT = "Microsoft YaHei"
CATEGORY_STYLES = {
    "guidance": ("2F75B5", "执行指导"),
    "evidence": ("008C95", "证据要求"),
    "writing": ("7030A0", "写作建议"),
    "warning": ("C65911", "注意事项"),
    "issue": ("C00000", "发现问题"),
    "suggestion": ("1F4E79", "修改建议"),
    "example": ("548235", "参考写法"),
    "praise": ("8064A2", "保留优点"),
    "summary": ("44546A", "Codex 总结"),
}


class ReportBuildError(RuntimeError):
    """Raised when a generation plan cannot be applied safely."""


def _error_payload(message: str, error_type: str, hint: str) -> None:
    payload = {"error": message, "error_type": error_type, "hint": hint}
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for block in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_stem(text: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", text).strip(" .-")
    return cleaned or "experiment-report"


def _all_paragraphs(document: Document) -> list[Paragraph]:
    paragraphs = list(document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    return paragraphs


def _insert_after(paragraph: Paragraph) -> Paragraph:
    new_element = OxmlElement("w:p")
    paragraph._p.addnext(new_element)
    inserted = Paragraph(new_element, paragraph._parent)
    if paragraph.style is not None:
        inserted.style = paragraph.style
    return inserted


def _set_run_font(run: Any, font_name: str, color_hex: str, size_pt: float, bold: bool) -> None:
    run.font.name = font_name
    run.font.color.rgb = RGBColor.from_string(color_hex)
    run.font.size = Pt(size_pt)
    run.bold = bold
    run_properties = run._element.get_or_add_rPr()
    run_fonts = run_properties.rFonts
    if run_fonts is None:
        run_fonts = OxmlElement("w:rFonts")
        run_properties.insert(0, run_fonts)
    run_fonts.set(qn("w:ascii"), font_name)
    run_fonts.set(qn("w:hAnsi"), font_name)
    run_fonts.set(qn("w:eastAsia"), font_name)


def _add_marked_content(paragraph: Paragraph, addition: dict[str, Any]) -> None:
    category = str(addition.get("category", "suggestion")).strip().lower()
    color_hex, default_label = CATEGORY_STYLES.get(category, CATEGORY_STYLES["suggestion"])
    label = str(addition.get("label", default_label)).strip() or default_label
    text = str(addition.get("text", "")).strip()
    if not text:
        raise ReportBuildError("Every addition must contain non-empty text.")

    font_name = str(addition.get("font_name", DEFAULT_FONT)).strip() or DEFAULT_FONT
    size_value = addition.get("font_size_pt", 10.5)
    try:
        size_pt = float(size_value)
    except (TypeError, ValueError) as exc:
        raise ReportBuildError(f"Invalid font_size_pt: {size_value}") from exc
    if size_pt < 8 or size_pt > 30:
        raise ReportBuildError("font_size_pt must be between 8 and 30.")

    label_run = paragraph.add_run(f"【Codex 新增·{label}】")
    _set_run_font(label_run, font_name, color_hex, size_pt, True)
    text_run = paragraph.add_run(text)
    _set_run_font(text_run, font_name, color_hex, size_pt, False)


def _find_anchor(paragraphs: list[Paragraph], addition: dict[str, Any]) -> Paragraph | None:
    if "paragraph_index" in addition:
        try:
            index = int(addition["paragraph_index"])
        except (TypeError, ValueError) as exc:
            raise ReportBuildError("paragraph_index must be an integer.") from exc
        if index < 0 or index >= len(paragraphs):
            raise ReportBuildError(f"paragraph_index {index} is outside 0..{len(paragraphs) - 1}.")
        return paragraphs[index]

    anchor_text = str(addition.get("anchor_text", "")).strip()
    if not anchor_text:
        return None
    occurrence_value = addition.get("occurrence", 1)
    try:
        occurrence = int(occurrence_value)
    except (TypeError, ValueError) as exc:
        raise ReportBuildError("occurrence must be an integer.") from exc
    if occurrence < 1:
        raise ReportBuildError("occurrence must be at least 1.")

    matches = [paragraph for paragraph in paragraphs if anchor_text in paragraph.text]
    return matches[occurrence - 1] if len(matches) >= occurrence else None


def _validate_plan(plan: dict[str, Any]) -> None:
    report_kind = str(plan.get("report_kind", "")).strip().lower()
    if report_kind not in REPORT_KINDS:
        raise ReportBuildError("report_kind must be 'execution' or 'revision'.")
    additions = plan.get("additions", [])
    if not isinstance(additions, list):
        raise ReportBuildError("additions must be a JSON array.")
    if not additions and not str(plan.get("summary", "")).strip():
        raise ReportBuildError("The plan must contain at least one addition or a summary.")
    for addition in additions:
        if not isinstance(addition, dict):
            raise ReportBuildError("Each additions item must be an object.")
        if str(addition.get("position", "after")).lower() not in {"after", "append"}:
            raise ReportBuildError("position must be 'after' or 'append'.")


def _append_summary(document: Document, plan: dict[str, Any]) -> None:
    summary = str(plan.get("summary", "")).strip()
    verdict = str(plan.get("verdict", "")).strip()
    if not summary and not verdict:
        return

    break_paragraph = document.add_paragraph()
    break_paragraph.add_run().add_break(WD_BREAK.PAGE)
    heading = document.add_paragraph()
    _add_marked_content(
        heading,
        {
            "category": "summary",
            "label": "生成说明",
            "text": "以下内容由当前 Codex 会话基于原文生成，原文内容和样式保留在前文。",
            "font_size_pt": 12,
        },
    )
    if verdict:
        verdict_paragraph = document.add_paragraph()
        _add_marked_content(
            verdict_paragraph,
            {"category": "summary", "label": "提交判断", "text": verdict},
        )
    if summary:
        summary_paragraph = document.add_paragraph()
        _add_marked_content(
            summary_paragraph,
            {"category": "summary", "label": "整体说明", "text": summary},
        )


def build_report(source: Path, plan_path: Path, output_dir: Path) -> tuple[Path, Path]:
    """Apply a Codex-authored plan to a copy of the source DOCX.

    Args:
        source: Existing DOCX report supplied by the user.
        plan_path: JSON plan authored by the current Codex session.
        output_dir: Directory for the generated report and metadata.

    Returns:
        Tuple of generated DOCX path and metadata JSON path.

    Raises:
        ValueError: If a required path or extension is invalid.
        ReportBuildError: If the plan is malformed or cannot be applied.
    """
    if not source.is_file():
        raise ValueError(f"Source file does not exist: {source}")
    if source.suffix.lower() != ".docx":
        raise ValueError("Style-preserving generated reports require a .docx source file.")
    if not plan_path.is_file():
        raise ValueError(f"Plan file does not exist: {plan_path}")

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportBuildError(f"Plan JSON is invalid: {exc}") from exc
    if not isinstance(plan, dict):
        raise ReportBuildError("Plan root must be a JSON object.")
    _validate_plan(plan)

    try:
        document = Document(str(source))
    except Exception as exc:
        raise ReportBuildError(f"DOCX could not be opened: {exc}") from exc

    original_paragraphs = _all_paragraphs(document)
    last_inserted_by_anchor: dict[int, Paragraph] = {}
    unanchored: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []

    for addition_index, addition in enumerate(plan.get("additions", []), start=1):
        position = str(addition.get("position", "after")).lower()
        anchor = _find_anchor(original_paragraphs, addition)
        if position == "append" or anchor is None:
            unanchored.append(addition)
            applied.append({"index": addition_index, "location": "appendix", "anchor_found": False})
            continue

        anchor_key = id(anchor._p)
        insertion_point = last_inserted_by_anchor.get(anchor_key, anchor)
        inserted = _insert_after(insertion_point)
        _add_marked_content(inserted, addition)
        last_inserted_by_anchor[anchor_key] = inserted
        applied.append(
            {
                "index": addition_index,
                "location": "after-anchor",
                "anchor_found": True,
                "anchor_text": anchor.text[:120],
            }
        )

    if unanchored:
        document.add_paragraph()
        appendix_heading = document.add_paragraph()
        _add_marked_content(
            appendix_heading,
            {
                "category": "summary",
                "label": "未定位内容",
                "text": "以下新增内容未匹配到原文锚点，已集中放在文末供人工放置。",
            },
        )
        for addition in unanchored:
            paragraph = document.add_paragraph()
            _add_marked_content(paragraph, addition)

    _append_summary(document, plan)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_kind = str(plan["report_kind"]).lower()
    suffix = "实验执行报告" if report_kind == "execution" else "修改报告"
    base_name = f"{_safe_stem(source.stem)}-{suffix}"
    output_path = output_dir / f"{base_name}.docx"
    job_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    if output_path.exists():
        output_path = output_dir / f"{base_name}-{job_id}.docx"

    try:
        document.save(output_path)
    except PermissionError as exc:
        raise ReportBuildError(f"Output is open or not writable: {output_path}") from exc

    metadata = {
        "job_id": job_id,
        "skill": SKILL_NAME,
        "version": VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "report_kind": report_kind,
        "report_label": suffix,
        "source_state": str(plan.get("source_state", "unknown")),
        "source_name": source.name,
        "source_sha256": _sha256(source),
        "generated_name": output_path.name,
        "generated_sha256": _sha256(output_path),
        "summary": str(plan.get("summary", "")).strip(),
        "verdict": str(plan.get("verdict", "")).strip(),
        "addition_count": len(plan.get("additions", [])),
        "applied": applied,
        "style_policy": {
            "original_content": "preserved",
            "generated_content": "marked with a Codex label, distinct font settings, and category color",
        },
        "local_only": True,
    }
    metadata_path = output_dir / f"{job_id}.metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path, metadata_path


def diagnostics() -> dict[str, Any]:
    """Return generator capabilities for automated readiness checks."""
    return {
        "skill": SKILL_NAME,
        "version": VERSION,
        "commands": ["build-report", "diagnostics"],
        "features": {
            "source_docx_required": True,
            "original_style_preservation": True,
            "colored_generated_content": True,
            "external_model_api": False,
        },
    }


def main() -> int:
    """Build one report or print diagnostics."""
    parser = argparse.ArgumentParser(description="Build a colored annotated DOCX from an original report.")
    parser.add_argument("--source", type=Path, help="Original .docx report.")
    parser.add_argument("--plan", type=Path, help="Codex-authored generation plan JSON.")
    parser.add_argument("--output-dir", type=Path, help="Directory for report and metadata.")
    parser.add_argument("--diagnostics", action="store_true", help="Print generator capabilities as JSON.")
    args = parser.parse_args()

    if args.diagnostics:
        print(json.dumps(diagnostics(), ensure_ascii=False, indent=2))
        return 0
    if args.source is None or args.plan is None or args.output_dir is None:
        _error_payload(
            "--source, --plan, and --output-dir are required.",
            "validation",
            "Supply an original DOCX and a Codex-authored plan JSON.",
        )
        return 1

    try:
        output_path, metadata_path = build_report(
            args.source.resolve(), args.plan.resolve(), args.output_dir.resolve()
        )
    except ValueError as exc:
        _error_payload(str(exc), "validation", "Check source format and file paths.")
        return 1
    except ReportBuildError as exc:
        _error_payload(str(exc), "runtime", "Validate the plan schema and close any open output document.")
        return 1
    except OSError as exc:
        _error_payload(str(exc), "runtime", "Check local permissions and disk space.")
        return 1

    print(
        json.dumps(
            {"ok": True, "output": str(output_path), "metadata": str(metadata_path)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
