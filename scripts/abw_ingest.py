import csv
import hashlib
import html
import json
import posixpath
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = (ROOT / "src").resolve()
if SRC_ROOT.exists() and str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
loaded_abw = sys.modules.get("abw")
loaded_abw_file = Path(getattr(loaded_abw, "__file__", "") or ".").resolve() if loaded_abw else None
if SRC_ROOT.exists() and loaded_abw_file and SRC_ROOT not in loaded_abw_file.parents:
    for module_name in list(sys.modules):
        if module_name == "abw" or module_name.startswith("abw."):
            sys.modules.pop(module_name, None)

from abw.conflicts import detect_conflicts, write_conflict_reports
from abw.ocr import preferred_tesseract_language, resolve_tesseract_executable
from abw.providers import execute_provider_chain
from abw.workspace import read_workspace_config


MAX_SUMMARY_CHARS = 500
MAX_KEY_CONCEPTS = 5
MAX_QUERY_SUGGESTIONS = 5
MAX_SEMANTIC_ITEMS = 8
TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".adoc"}
CSV_EXTENSIONS = {".csv"}
HTML_EXTENSIONS = {".html", ".htm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | CSV_EXTENSIONS | HTML_EXTENSIONS | IMAGE_EXTENSIONS | {".docx", ".xlsx", ".pdf", ".pptx"}
ENTERPRISE_PERCEPTION_EXTENSIONS = IMAGE_EXTENSIONS | {".docx", ".xlsx", ".pdf", ".pptx"}
LOW_CONFIDENCE_REVIEW_THRESHOLD = 0.45
AUTO_PROMOTE_THRESHOLD = 0.8
MIN_USEFUL_OCR_TOKENS = 3
LOCAL_OCR_PROVIDERS = ("paddleocr", "tesseract", "binary_text_probe")
VISION_PROVIDERS = ("openai_vision", "claude_vision", "gemini_vision")
PDF_RENDER_PROVIDERS = ("pymupdf", "pdf2image")
VISION_MAX_PAGES_DEFAULT = 3
VISION_MAX_FILE_MB_DEFAULT = 8
OCR_METADATA_MARKERS = {
    "ihdr",
    "idat",
    "iend",
    "srgb",
    "gama",
    "phys",
    "png",
    "pdf",
    "xref",
    "obj",
    "endobj",
    "type",
    "page",
    "pages",
    "catalog",
    "count",
    "eof",
    "resources",
    "subtype",
    "image",
    "kids",
    "xobject",
    "structtreeroot",
    "font",
    "fontdescriptor",
    "metadata",
    "viewerpreferences",
    "stream",
    "endstream",
    "filter",
    "flatedecode",
    "length",
    "trailer",
}
LANGUAGE_HINT_TOKENS = {
    "api",
    "apply",
    "button",
    "cancel",
    "chart",
    "close",
    "data",
    "date",
    "delete",
    "diagram",
    "error",
    "factory",
    "filter",
    "flow",
    "input",
    "label",
    "line",
    "login",
    "menu",
    "output",
    "price",
    "process",
    "quantity",
    "required",
    "save",
    "search",
    "settings",
    "station",
    "status",
    "submit",
    "system",
    "table",
    "total",
    "warning",
}
SEMANTIC_STOPWORDS = {
    "about",
    "after",
    "analysis",
    "and",
    "are",
    "candidate",
    "detected",
    "document",
    "embedded",
    "extracted",
    "from",
    "image",
    "local",
    "metadata",
    "none",
    "page",
    "pages",
    "pdf",
    "provider",
    "raw",
    "recovered",
    "scan",
    "semantic",
    "summary",
    "text",
    "that",
    "the",
    "this",
    "tokens",
    "with",
}
METADATA_LINE_PREFIXES = (
    "cells:",
    "chart text:",
    "comments:",
    "detected buttons/labels:",
    "embedded image metadata/text probe:",
    "embedded media/images:",
    "image artifact detected",
    "layout blocks:",
    "ocr text:",
    "page image candidates:",
    "pdf extraction mode:",
    "pdf pages detected:",
    "provider semantic summary:",
    "slide text:",
    "speaker notes:",
    "text layer blocks:",
)


def supported_perception_providers() -> dict:
    return {
        "local_ocr": list(LOCAL_OCR_PROVIDERS),
        "pdf_render": list(PDF_RENDER_PROVIDERS),
        "cloud_vision": list(VISION_PROVIDERS),
        "notes": "PaddleOCR/Tesseract/cloud vision are optional adapters; binary_text_probe is deterministic fallback.",
    }


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _shorten(text: str, limit: int = 1200) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _extract_xml_text(xml_text: str) -> list[str]:
    values = re.findall(r"<[^>]*t[^>]*>(.*?)</[^>]*t>", str(xml_text or ""), flags=re.IGNORECASE | re.DOTALL)
    cleaned = []
    for item in values:
        text = html.unescape(str(item or "").strip())
        if text:
            cleaned.append(text)
    return cleaned


def _dedupe_text(items: list[str], *, limit: int = 120) -> list[str]:
    deduped = []
    seen = set()
    for item in items:
        text = " ".join(str(item or "").split())
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        deduped.append(text)
        if len(deduped) >= limit:
            break
    return deduped


def _strip_extraction_noise(text: str) -> str:
    cleaned = html.unescape(str(text or ""))
    cleaned = re.sub(r"<[^>\n]{1,120}>", " ", cleaned)
    cleaned = re.sub(r"\b(?:xref|trailer|startxref|endobj|obj|stream|endstream|%%EOF)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"/(?:Type|Page|Pages|Catalog|Resources|Subtype|Image|XObject|Font|Filter|Length|Count|Kids)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:IHDR|IDAT|IEND|sRGB|gAMA|pHYs|PNG)\b", " ", cleaned)
    cleaned = re.sub(r"\b[A-Za-z0-9+/]{48,}={0,2}\b", " ", cleaned)
    cleaned = re.sub(r"\b([A-Za-z0-9])\1{5,}\b", " ", cleaned)
    cleaned = re.sub(r"(?:\b[0-9]+\s+0\s+R\b\s*){2,}", " ", cleaned)
    return cleaned


def _clean_extracted_lines(items: list[str], *, limit: int = 120) -> list[str]:
    cleaned = []
    for item in items:
        text = _strip_extraction_noise(str(item or ""))
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
        text = " ".join(text.split())
        if not text:
            continue
        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
        cjk_tokens = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]{2,}", text)
        marker_words = [word for word in words if word.lower().strip("_-") in OCR_METADATA_MARKERS]
        if words and len(marker_words) / max(1, len(words)) >= 0.8:
            continue
        if not cjk_tokens and len(text) > 180 and len(set(text)) < 12:
            continue
        cleaned.append(text)
    return _dedupe_text(cleaned, limit=limit)


def _clean_content_for_draft(content: str) -> str:
    sections = []
    for block in str(content or "").splitlines():
        stripped = block.strip()
        if not stripped:
            sections.append("")
            continue
        cleaned = _clean_extracted_lines([stripped], limit=1)
        if cleaned:
            sections.append(cleaned[0])
    compact = "\n".join(sections)
    compact = re.sub(r"\n{3,}", "\n\n", compact).strip()
    return compact


def _binary_text_probe(data: bytes, *, min_len: int = 4) -> list[str]:
    decoded = data.decode("utf-8", errors="ignore") + "\n" + data.decode("latin-1", errors="ignore")
    pattern = rf"[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff][A-Za-z0-9\u3040-\u30ff\u3400-\u9fff _.,:;#%()/\\+\-=]{{{min_len - 1},}}"
    candidates = re.findall(pattern, decoded)
    cleaned = [item.strip(" \t\r\n\x00") for item in candidates]
    return _clean_extracted_lines(cleaned, limit=80)


def _text_quality(text_lines: list[str]) -> dict:
    text = " ".join(text_lines)
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    cjk_tokens = re.findall(r"[\u3040-\u30ff\u3400-\u9fff]{2,}", text)
    lowered = [word.lower().strip("_-") for word in words]
    non_metadata = [word for word in lowered if word not in OCR_METADATA_MARKERS]
    if not text or (not words and not cjk_tokens):
        return {
            "alpha_ratio": 0.0,
            "readable_token_score": 0.0,
            "language_token_score": 0.0,
            "metadata_only": True,
            "usable": False,
        }

    alpha_chars = len(re.findall(r"[A-Za-z\u3040-\u30ff\u3400-\u9fff]", text))
    alpha_ratio = alpha_chars / max(1, len(text))
    good_tokens = [
        word
        for word in non_metadata
        if len(word) >= 3
        and not re.search(r"([A-Za-z0-9])\1{3,}", word)
        and (re.search(r"[aeiou]", word) or word in LANGUAGE_HINT_TOKENS)
    ]
    good_tokens.extend(cjk_tokens)
    language_hits = [word for word in good_tokens if word in LANGUAGE_HINT_TOKENS or re.search(r"[aeiou].*[aeiou]", word)]
    language_hits.extend(cjk_tokens)
    token_count = len(words) + len(cjk_tokens)
    readable_token_score = len(good_tokens) / max(1, token_count)
    language_token_score = len(language_hits) / max(1, len(good_tokens))
    metadata_only = bool(words) and not good_tokens
    usable = (
        not metadata_only
        and alpha_ratio >= 0.55
        and readable_token_score >= 0.35
        and language_token_score >= 0.45
        and len(good_tokens) >= 3
    )
    return {
        "alpha_ratio": _clamp(alpha_ratio),
        "readable_token_score": _clamp(readable_token_score),
        "language_token_score": _clamp(language_token_score),
        "metadata_only": metadata_only,
        "usable": usable,
    }


def _filter_metadata_markers(text_lines: list[str]) -> list[str]:
    filtered = []
    for line in text_lines:
        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", line)
        if words and all(word.lower().strip("_-") in OCR_METADATA_MARKERS for word in words):
            continue
        filtered.append(line)
    return filtered


def _image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        data = path.read_bytes()[:32]
    except OSError:
        return None, None
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little")
    if data.startswith(b"BM") and len(data) >= 26:
        return int.from_bytes(data[18:22], "little"), int.from_bytes(data[22:26], "little")
    return None, None


def _run_tesseract(path: Path) -> tuple[list[str], dict]:
    executable = resolve_tesseract_executable()
    if not executable:
        return [], {"provider": "tesseract", "status": "unavailable", "reason": "tesseract executable not found"}
    language = preferred_tesseract_language(executable)
    try:
        completed = subprocess.run(
            [executable, str(path), "stdout", "--psm", "6", "-l", language],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return [], {"provider": "tesseract", "status": "failed", "reason": str(exc)}
    if completed.returncode != 0:
        return [], {"provider": "tesseract", "status": "failed", "reason": completed.stderr.strip()[:200]}
    lines = _dedupe_text([line for line in completed.stdout.splitlines() if line.strip()])
    return lines, {"provider": "tesseract", "status": "success" if lines else "empty", "tokens": len(lines), "path": executable, "language": language}


def _run_paddleocr(path: Path) -> tuple[list[str], dict]:
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return [], {"provider": "paddleocr", "status": "unavailable", "reason": str(exc)}
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        result = ocr.ocr(str(path), cls=True)
    except Exception as exc:  # noqa: BLE001
        return [], {"provider": "paddleocr", "status": "failed", "reason": str(exc)}

    lines = []
    for page in result or []:
        for row in page or []:
            if len(row) >= 2 and isinstance(row[1], (list, tuple)) and row[1]:
                lines.append(str(row[1][0]))
    lines = _dedupe_text(lines)
    return lines, {"provider": "paddleocr", "status": "success" if lines else "empty", "tokens": len(lines)}


def _ocr_candidate(provider: str, lines: list[str], status: dict) -> dict:
    cleaned = _dedupe_text(_clean_extracted_lines(lines), limit=120)
    quality = _text_quality(cleaned)
    noisy = _ocr_noise_score(cleaned)
    confidence = (
        _calibrate_confidence(
            base=0.28,
            text_lines=cleaned,
            structured=bool(_table_region_blocks(_region_blocks(cleaned))),
            noisy=noisy,
            provider_success=True,
            method="real_ocr",
        )
        if status.get("status") == "success" and quality["usable"]
        else 0.08
    )
    return {
        "provider": provider,
        "text_lines": cleaned if quality["usable"] else [],
        "status": status,
        "quality": quality,
        "noise": noisy,
        "confidence": confidence,
        "usable": status.get("status") == "success" and quality["usable"],
    }


def _choose_ocr_candidate(candidates: list[dict]) -> dict:
    if not candidates:
        return _ocr_candidate("none", [], {"provider": "none", "status": "empty", "tokens": 0})
    if not any(candidate.get("usable") for candidate in candidates):
        return _ocr_candidate("none", [], {"provider": "none", "status": "empty", "tokens": 0})
    return sorted(
        candidates,
        key=lambda item: (
            bool(item.get("usable")),
            float(item.get("confidence") or 0.0),
            len(item.get("text_lines") or []),
        ),
        reverse=True,
    )[0]


def _ocr_noise_score(text_lines: list[str]) -> float:
    text = " ".join(text_lines)
    if not text:
        return 1.0
    chars = len(text)
    alpha_num = len(re.findall(r"[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff]", text))
    short_tokens = len([token for token in text.split() if len(token) <= 2])
    tokens = max(1, len(text.split()))
    symbol_ratio = 1.0 - (alpha_num / max(1, chars))
    short_ratio = short_tokens / tokens
    return _clamp((symbol_ratio * 0.7) + (short_ratio * 0.3))


def _calibrate_confidence(
    *,
    base: float,
    text_lines: list[str],
    structured: bool,
    noisy: float,
    provider_success: bool = False,
    method: str = "unknown",
) -> float:
    lines = _clean_extracted_lines(text_lines)
    quality = _text_quality(lines)
    useful_count = len(lines) if quality["usable"] else 0
    method_bonus = {
        "native_text": 0.2,
        "structured_native": 0.18,
        "pdf_text_layer": 0.22,
        "real_ocr": 0.12,
        "binary_probe": 0.0,
        "metadata_probe": -0.08,
    }.get(method, 0.0)
    confidence = base + min(0.24, useful_count * 0.025) + method_bonus
    if structured and useful_count:
        confidence += 0.12
    if quality["metadata_only"] or not useful_count:
        confidence = min(confidence, 0.18)
    confidence -= noisy * 0.28
    return _clamp(confidence, 0.05, 0.9)


def _local_ocr_image(path: Path, *, embedded_bytes: bytes | None = None) -> dict:
    attempts = []
    paddle_lines, paddle_status = _run_paddleocr(path)
    attempts.append(paddle_status)
    tess_lines, tess_status = _run_tesseract(path)
    attempts.append(tess_status)
    candidates = [
        _ocr_candidate("paddleocr", paddle_lines, paddle_status),
        _ocr_candidate("tesseract", tess_lines, tess_status),
    ]
    best = _choose_ocr_candidate(candidates)
    if embedded_bytes is None:
        try:
            embedded_bytes = path.read_bytes()
        except OSError:
            embedded_bytes = b""
    probe_lines = _binary_text_probe(embedded_bytes)
    probe_quality = _text_quality(probe_lines)
    if probe_lines:
        attempts.append(
            {
                "provider": "binary_text_probe",
                "status": "metadata_only",
                "tokens": len(probe_lines),
                "quality": probe_quality,
            }
        )
    else:
        attempts.append({"provider": "binary_text_probe", "status": "empty", "tokens": 0})

    text_lines = best["text_lines"]
    quality = best["quality"]
    noisy = best["noise"]
    confidence = float(best["confidence"])
    return {
        "text_lines": text_lines,
        "metadata_lines": _filter_metadata_markers(probe_lines),
        "attempts": attempts,
        "confidence": confidence,
        "noise": noisy,
        "real_ocr_success": bool(best["usable"]),
        "selected_provider": best["provider"],
        "quality": quality,
        "probe_quality": probe_quality,
        "candidates": candidates,
    }


def _classify_visual_artifact(text_lines: list[str], *, width: int | None = None, height: int | None = None, image_count: int = 0) -> dict:
    text = "\n".join(text_lines)
    lowered = text.lower()
    table_markers = len(re.findall(r"\b(total|qty|quantity|amount|price|date|id|row|column)\b", lowered))
    ui_markers = len(re.findall(r"\b(ok|cancel|save|submit|login|sign in|menu|settings|search|button|filter|tab)\b", lowered))
    window_markers = len(re.findall(r"\b(window|dialog|modal|toolbar|sidebar|navigation|navbar|title bar|status bar|pane|panel|ribbon)\b", lowered))
    diagram_markers = len(re.findall(r"\b(flow|arrow|step|node|input|output|process|system|module|architecture)\b", lowered))
    label_markers = len(re.findall(r"\b(label|status|error|warning|required|enabled|disabled)\b", lowered))
    button_labels = re.findall(r"\b(OK|Cancel|Save|Submit|Login|Search|Filter|Apply|Next|Back|Close)\b", text)
    pipe_rows = len([line for line in text_lines if "|" in line or "\t" in line])
    numeric_grid_rows = len([line for line in text_lines if len(re.findall(r"\b\d+(?:\.\d+)?\b", line)) >= 2])
    aspect = (width / height) if width and height else None
    window_semantics = _software_window_semantics(text_lines, width=width, height=height)

    return {
        "tables": pipe_rows >= 2 or numeric_grid_rows >= 2 or table_markers >= 3,
        "ui_screenshot": ui_markers >= 2 or window_markers >= 1 or (aspect is not None and aspect > 1.2 and ui_markers >= 1),
        "software_window": bool(window_semantics),
        "window_semantics": window_semantics,
        "diagrams": diagram_markers >= 2 or (image_count > 0 and diagram_markers >= 1),
        "labels_buttons": label_markers >= 1 or bool(button_labels),
        "button_labels": _dedupe_text(button_labels, limit=20),
        "signals": {
            "table_markers": table_markers,
            "ui_markers": ui_markers,
            "window_markers": window_markers,
            "diagram_markers": diagram_markers,
            "label_markers": label_markers,
            "pipe_rows": pipe_rows,
            "numeric_grid_rows": numeric_grid_rows,
        },
    }


def _software_window_semantics(text_lines: list[str], *, width: int | None = None, height: int | None = None) -> list[str]:
    text = "\n".join(text_lines)
    lowered = text.lower()
    semantics = []
    patterns = [
        ("dialog_or_modal", r"\b(dialog|modal|popup|confirm|are you sure|close|cancel|ok)\b"),
        ("navigation_or_sidebar", r"\b(nav|navigation|sidebar|menu|home|dashboard|settings)\b"),
        ("toolbar_or_ribbon", r"\b(toolbar|ribbon|tools|filter|search|sort|export|refresh)\b"),
        ("form_or_controls", r"\b(input|field|required|checkbox|dropdown|select|apply|submit|save)\b"),
        ("table_or_grid", r"\b(table|grid|row|column|total|qty|quantity|price|status)\b"),
        ("status_or_alert", r"\b(status|warning|error|failed|success|enabled|disabled)\b"),
    ]
    for name, pattern in patterns:
        if re.search(pattern, lowered):
            semantics.append(name)
    if width and height and width / max(1, height) >= 1.25 and any(item in semantics for item in {"navigation_or_sidebar", "toolbar_or_ribbon", "table_or_grid"}):
        semantics.append("desktop_window_layout")
    return _dedupe_text(semantics, limit=12)


def _region_blocks(text_lines: list[str], *, page: int | None = None, limit: int = 80) -> list[dict]:
    blocks = []
    for index, line in enumerate(_dedupe_text(text_lines, limit=limit), start=1):
        text = " ".join(str(line or "").split())
        if not text:
            continue
        row = {
            "region": f"region-{index:02d}",
            "text": text,
            "order": index,
        }
        if page is not None:
            row["page"] = page
        blocks.append(row)
    return blocks


def _region_ref(row: dict, *, prefix: str) -> str:
    if row.get("page") is not None:
        return f"{prefix}/page-{int(row['page']):03d}/{row['region']}"
    return f"{prefix}/{row['region']}"


def _region_lines(blocks: list[dict], *, prefix: str, limit: int = 80) -> list[str]:
    lines = []
    for row in blocks[:limit]:
        if row.get("page") is not None:
            lines.append(f"- page {row['page']} {row['region']}: {row['text']}")
        else:
            lines.append(f"- {row['region']}: {row['text']}")
    return lines


def _table_region_blocks(blocks: list[dict]) -> list[dict]:
    table_rows = []
    for row in blocks:
        text = row.get("text", "")
        numeric_cells = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
        delimiter_cells = len(re.findall(r"[|\t,]", text))
        header_hits = len(re.findall(r"\b(total|qty|quantity|amount|price|date|id|status|code|name)\b", text, flags=re.IGNORECASE))
        if numeric_cells >= 2 or delimiter_cells >= 2 or header_hits >= 2:
            table_rows.append(row)
    return table_rows


def _semantic_summary_for_visual(kind: str, text_lines: list[str], detections: dict) -> str:
    found = [name for name in ("tables", "ui_screenshot", "software_window", "diagrams", "labels_buttons") if detections.get(name)]
    if not found:
        found = ["visual_artifact"]
    text = "; ".join(text_lines[:12]) if text_lines else "no OCR text recovered"
    return f"{kind} analysis detected {', '.join(found)}. OCR text: {text}"


def _quality_evidence(quality: dict) -> str:
    return (
        f"alpha_ratio={float(quality.get('alpha_ratio', 0.0)):.2f}; "
        f"readable_token_score={float(quality.get('readable_token_score', 0.0)):.2f}; "
        f"language_token_score={float(quality.get('language_token_score', 0.0)):.2f}; "
        f"metadata_only={quality.get('metadata_only')}"
    )


def _provenance(component: str, method: str, confidence: float, evidence: str, *, ref: str | None = None) -> dict:
    row = {"component": component, "method": method, "confidence": confidence, "evidence": evidence}
    if ref:
        row["ref"] = ref
    return row


def _best_component_confidence(provenance: list[dict], components: set[str]) -> float:
    scores = [
        float(row.get("confidence") or 0.0)
        for row in provenance or []
        if str(row.get("component") or "") in components
    ]
    return max(scores, default=0.0)


def _infer_document_type(format_name: str, content: str, provenance: list[dict]) -> dict:
    lowered = str(content or "").lower()
    fmt = str(format_name or "").lower()
    signals = []
    if fmt == "xlsx":
        doc_type = "spreadsheet"
        signals.append("xlsx_container")
    elif fmt == "pptx":
        doc_type = "presentation"
        signals.append("pptx_container")
    elif fmt == "pdf":
        doc_type = "scanned_pdf" if "page image candidates: 0" not in lowered else "pdf_document"
        signals.append("pdf_container")
    elif fmt in IMAGE_EXTENSIONS or fmt in {ext.lstrip(".") for ext in IMAGE_EXTENSIONS}:
        if "ui_screenshot" in lowered:
            doc_type = "ui_screenshot"
        elif "tables" in lowered:
            doc_type = "table_screenshot"
        elif "diagrams" in lowered:
            doc_type = "diagram_image"
        else:
            doc_type = "image"
        signals.append("image_file")
    else:
        doc_type = "text_document"
        signals.append("text_file")

    components = {str(row.get("component") or "") for row in provenance or []}
    for component in sorted(components):
        if component:
            signals.append(component)
    confidence = 0.62 if doc_type != "text_document" else 0.55
    if components:
        confidence += min(0.18, len(components) * 0.03)
    return {"type": doc_type, "confidence": _clamp(confidence, 0.0, 0.9), "signals": signals[:12]}


def _perception_stage_scores(extracted: dict, enriched: dict) -> dict:
    provenance = extracted.get("provenance") or []
    provider = enriched.get("provider") or {}
    return {
        "native_structured": round(
            _best_component_confidence(provenance, {"text", "cells", "comments", "textboxes", "charts", "slides", "notes"}),
            4,
        ),
        "ocr": round(_best_component_confidence(provenance, {"ocr_text", "embedded_images"}), 4),
        "vision_layout": round(
            _best_component_confidence(provenance, {"layout", "tables", "ui_screenshot", "software_window", "diagrams", "labels_buttons", "page_images", "regions", "table_regions"}),
            4,
        ),
        "document_classifier": round(float((extracted.get("document_type") or {}).get("confidence") or 0.0), 4),
        "provider_semantic": round(0.8 if provider.get("used") else 0.0, 4),
    }


def _build_perception_report(extracted: dict, enriched: dict, confidence: float) -> dict:
    doc_type = extracted.get("document_type") or _infer_document_type(
        extracted.get("format"),
        extracted.get("content", ""),
        extracted.get("provenance", []),
    )
    extracted["document_type"] = doc_type
    stage_scores = _perception_stage_scores(extracted, enriched)
    stages = [
        {"stage": "native_structured", "confidence": stage_scores["native_structured"]},
        {"stage": "ocr", "confidence": stage_scores["ocr"]},
        {"stage": "vision_layout", "confidence": stage_scores["vision_layout"]},
        {"stage": "document_classifier", "confidence": stage_scores["document_classifier"]},
        {"stage": "provider_semantic", "confidence": stage_scores["provider_semantic"]},
    ]
    return {
        "version": "enterprise_ingest_perception_v2",
        "document_type": doc_type,
        "stage_scores": stage_scores,
        "stages": stages,
        "confidence": round(float(confidence), 4),
    }


def _review_decision(format_name: str, confidence: float, conflict_reports: list[str]) -> tuple[str, str]:
    if conflict_reports:
        return "review_needed", "conflict_detected"
    if confidence >= AUTO_PROMOTE_THRESHOLD:
        return "candidate_promoted", "high_confidence"
    suffix = "." + str(format_name or "").lower().lstrip(".")
    if suffix in ENTERPRISE_PERCEPTION_EXTENSIONS and confidence >= LOW_CONFIDENCE_REVIEW_THRESHOLD:
        return "candidate_ready", "medium_confidence_enterprise_parse"
    return "review_needed", "low_confidence"


def candidate_path_tokens(task):
    tokens = []
    text = str(task or "").strip()
    match = re.match(r"^\s*(?:ingest|process|review)\s+(.+?)\s*$", text, flags=re.IGNORECASE)
    if match:
        tokens.append(match.group(1))
    pattern = r"(?:raw(?:[\\/][^\r\n]+)?)|(?:[^\s]+\.[A-Za-z0-9]+)"
    tokens.extend(re.findall(pattern, text))
    deduped = []
    seen = set()
    for token in tokens:
        cleaned = str(token).strip("`'\"()[]{}<>.,;:")
        cleaned = re.sub(r"\s+(?:into|to)\s+wiki\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def resolve_raw_target(path_token, workspace="."):
    workspace_root = Path(workspace).resolve()
    token = str(path_token or "").strip().replace("\\", "/")
    if token.lower() in {"raw", "raw/"}:
        token = "raw"

    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        resolved = candidate.resolve()
        relative = resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError("Ingest path must stay inside the current workspace.") from exc

    relative_text = str(relative).replace("\\", "/")
    if relative_text == "raw":
        pass
    elif not relative_text.startswith("raw/"):
        raise ValueError("Ingest path must point to raw/ (file or directory).")

    has_glob = any(char in token for char in "*?[")
    if not resolved.exists() and not has_glob:
        raise FileNotFoundError(
            f"Ingest path not found: {relative_text}. Use: ingest raw/<file> or ingest raw/"
        )
    return relative_text, resolved


def extract_ingest_target(task, workspace="."):
    invalid_error = None
    for token in candidate_path_tokens(task):
        try:
            return resolve_raw_target(token, workspace=workspace)
        except FileNotFoundError:
            raise
        except ValueError as exc:
            invalid_error = exc
            continue
    if invalid_error is not None:
        raise ValueError(str(invalid_error))
    raise FileNotFoundError("No valid ingest path found. Use: ingest raw/<file> or ingest raw/")


def normalized_source_stem(relative_raw_path):
    name = Path(str(relative_raw_path or "").replace("\\", "/")).name.lower()
    for suffix in (".pdf.txt", ".pdf.md", ".pdf"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    else:
        name = Path(name).stem
    normalized = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return normalized or "source"


def deterministic_id(relative_raw_path, content):
    content_hash = hashlib.sha256(str(content or "").encode("utf-8", errors="ignore")).hexdigest()[:16]
    payload = f"{normalized_source_stem(relative_raw_path)}\n{content_hash}".encode("utf-8", errors="ignore")
    return "ingest-" + hashlib.sha256(payload).hexdigest()[:16]


def manifest_path(workspace="."):
    return Path(workspace) / "processed" / "manifest.jsonl"


def _manifest_source_key(relative_raw_path: str) -> tuple[str, str]:
    normalized = str(relative_raw_path or "").replace("\\", "/")
    parent = str(Path(normalized).parent).replace("\\", "/").lower()
    stem = normalized_source_stem(normalized)
    if stem == "source":
        name = Path(normalized).name.lower()
        for suffix in (".pdf.txt", ".pdf.md", ".pdf"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        else:
            name = Path(name).stem
        stem = name or stem
    return parent, stem


def ingest_queue_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_queue.json"


def ingest_runs_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_runs.jsonl"


def ingest_state_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_state.json"


def append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def manifest_source_ids(workspace=".") -> set[str]:
    path = manifest_path(workspace)
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        source_id = str(row.get("id") or "")
        if source_id:
            ids.add(source_id)
    return ids


def draft_aliases_path(workspace="."):
    return Path(workspace) / ".brain" / "draft_aliases.json"


def _draft_alias_candidates(relative_raw_path):
    canonical = draft_relpath(relative_raw_path)
    raw_name = Path(str(relative_raw_path or "").replace("\\", "/")).name
    candidates = {
        f"drafts/{Path(raw_name).stem}_draft.md",
        f"drafts/{Path(raw_name).stem.lower()}_draft.md",
    }
    return [item for item in sorted(candidates) if item and item != canonical]


def _record_draft_aliases(workspace, aliases: list[str], canonical: str):
    if not aliases:
        return
    path = draft_aliases_path(workspace)
    payload = load_json(path, {"aliases": {}, "updated_at": now_iso()})
    alias_map = payload.setdefault("aliases", {})
    for alias in aliases:
        alias_map[alias] = canonical
    payload["updated_at"] = now_iso()
    save_json(path, payload)


def _merge_existing_alias_drafts(workspace, canonical_relpath: str, alias_relpaths: list[str]) -> list[str]:
    workspace_root = Path(workspace)
    canonical_path = workspace_root / canonical_relpath
    merged_aliases: list[str] = []
    for alias_relpath in alias_relpaths:
        alias_path = workspace_root / alias_relpath
        if not alias_path.exists() or not alias_path.is_file():
            continue
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        if not canonical_path.exists():
            alias_path.replace(canonical_path)
        else:
            canonical_text = canonical_path.read_text(encoding="utf-8-sig", errors="ignore")
            alias_text = alias_path.read_text(encoding="utf-8-sig", errors="ignore")
            if alias_text.strip() and alias_text.strip() not in canonical_text:
                canonical_path.write_text(
                    canonical_text.rstrip()
                    + "\n\n## Merged Legacy Draft Alias\n"
                    + f"- alias_file: {alias_relpath}\n\n"
                    + alias_text.strip()
                    + "\n",
                    encoding="utf-8",
                )
            alias_path.unlink()
        merged_aliases.append(alias_relpath)
    _record_draft_aliases(workspace, merged_aliases or alias_relpaths, canonical_relpath)
    return merged_aliases


def summarize_text(content):
    semantic = build_semantic_extraction(content)
    return semantic.get("business_summary") or "No summary could be extracted from the raw file."


def extract_key_concepts(content):
    semantic = build_semantic_extraction(content)
    topics = semantic.get("key_topics") or []
    if topics:
        return topics[:MAX_KEY_CONCEPTS]

    counts = {}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", str(content or "")):
        lowered = token.lower()
        if lowered in SEMANTIC_STOPWORDS:
            continue
        counts[lowered] = counts.get(lowered, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    return [item[0] for item in ranked[:MAX_KEY_CONCEPTS]]


def _semantic_lines(content: str) -> list[str]:
    lines = []
    for raw in str(content or "").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^page\s+\d+\s*:\s*", "", stripped, flags=re.IGNORECASE)
        lowered = stripped.lower()
        if any(lowered.startswith(prefix) for prefix in METADATA_LINE_PREFIXES):
            continue
        if "metadata_only=true" in lowered or "binary_text_probe=metadata_only" in lowered:
            continue
        if "no ocr text recovered" in lowered or "none recovered" in lowered:
            continue
        if len(re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", stripped)) < 2:
            continue
        lines.append(stripped)
    return _dedupe_text(lines, limit=80)


def _rank_business_lines(lines: list[str]) -> list[str]:
    business_terms = {
        "action",
        "approval",
        "blocked",
        "capacity",
        "customer",
        "decision",
        "error",
        "failed",
        "failure",
        "handoff",
        "impact",
        "issue",
        "latency",
        "lead",
        "owner",
        "process",
        "required",
        "risk",
        "sla",
        "status",
        "step",
        "throughput",
        "timeout",
        "trend",
        "workflow",
    }
    scored = []
    for index, line in enumerate(lines):
        lowered = line.lower()
        score = sum(2 for term in business_terms if term in lowered)
        score += min(4, len(re.findall(r"\b[A-Z][A-Za-z0-9_-]{2,}\b", line)))
        score += 1 if re.search(r"\b[A-Z]{2,}\b|\b\d+(?:\.\d+)?%?\b", line) else 0
        score -= 2 if " no " in f" {lowered} " and "recovered" in lowered else 0
        scored.append((score, -index, line))
    return [line for _, _, line in sorted(scored, reverse=True)[:3]]


def detect_document_purpose(content: str, relative_raw_path: str = "", format_name: str = "") -> dict:
    haystack = f"{relative_raw_path} {format_name} {content}".lower()
    patterns = [
        ("meeting_minutes", ("mom", "minutes", "meeting", "attendee", "action item", "decision")),
        ("incident_or_troubleshooting", ("incident", "root cause", "error", "failure", "failed", "timeout", "resolution")),
        ("requirements_or_scope", ("requirement", "acceptance criteria", "scope", "must ", "should ", "user story")),
        ("process_or_workflow", ("process", "workflow", "approval", "handoff", "step", "procedure")),
        ("operations_report", ("kpi", "throughput", "capacity", "trend", "forecast", "q1", "q2", "q3", "q4")),
        ("technical_reference", ("api", "module", "service", "database", "table", "system", "architecture")),
        ("visual_artifact", ("screenshot", "ocr text", "ui_screenshot", "image artifact", "diagram")),
    ]
    best = ("general_knowledge_source", 0, [])
    for purpose, terms in patterns:
        hits = [term.strip() for term in terms if term in haystack]
        if len(hits) > best[1]:
            best = (purpose, len(hits), hits[:5])
    confidence = 0.35 + min(0.5, best[1] * 0.12)
    return {"purpose": best[0], "confidence": round(_clamp(confidence, 0.0, 0.9), 2), "signals": best[2]}


def _extract_topics(lines: list[str]) -> list[str]:
    counts = {}
    for line in lines:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", line):
            lowered = token.lower().strip("_-")
            if lowered in SEMANTIC_STOPWORDS or lowered in OCR_METADATA_MARKERS:
                continue
            counts[lowered] = counts.get(lowered, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    return [token for token, _ in ranked[:MAX_SEMANTIC_ITEMS]]


def _extract_semantic_signals(lines: list[str]) -> dict:
    text = "\n".join(lines)
    entities = _dedupe_text(re.findall(r"\b[A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3}\b", text), limit=MAX_SEMANTIC_ITEMS)
    modules = _dedupe_text(
        re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*(?:API|Service|Module|Queue|Table|DB|Database|Pipeline|Workflow)\b", text)
        + re.findall(r"\b(?:api|service|module|queue|table|database|pipeline|workflow)[-_:/][A-Za-z0-9_.:/-]+\b", text, flags=re.IGNORECASE),
        limit=MAX_SEMANTIC_ITEMS,
    )
    errors = _dedupe_text(
        re.findall(r"\b(?:error|failure|failed|timeout|exception|blocked|warning|E\d{2,}|[45]\d{2})[A-Za-z0-9_:/ -]{0,80}", text, flags=re.IGNORECASE),
        limit=MAX_SEMANTIC_ITEMS,
    )
    processes = _dedupe_text(
        [
            line
            for line in lines
            if re.search(r"\b(action|approve|approval|handoff|process|procedure|review|step|workflow|owner|next)\b", line, flags=re.IGNORECASE)
        ],
        limit=MAX_SEMANTIC_ITEMS,
    )
    return {"entities": entities, "modules": modules, "errors": errors, "processes": processes}


def build_semantic_extraction(content: str, relative_raw_path: str = "", format_name: str = "") -> dict:
    lines = _semantic_lines(content)
    purpose = detect_document_purpose("\n".join(lines) or content, relative_raw_path, format_name)
    topics = _extract_topics(lines)
    signals = _extract_semantic_signals(lines)
    ranked_lines = _rank_business_lines(lines)
    if ranked_lines:
        summary = " ".join(ranked_lines)
        if len(summary) > MAX_SUMMARY_CHARS:
            summary = summary[: MAX_SUMMARY_CHARS - 3].rstrip() + "..."
    else:
        summary = "No summary could be extracted from the raw file."
    return {
        "document_purpose": purpose,
        "key_topics": topics,
        "entities": signals["entities"],
        "modules": signals["modules"],
        "errors": signals["errors"],
        "processes": signals["processes"],
        "business_summary": summary,
    }


def build_possible_queries(concepts, relative_raw_path):
    stem = Path(relative_raw_path).stem.replace("-", " ")
    queries = [f"explain {stem}", f"summarize {stem}"]
    for concept in concepts:
        queries.append(f"what is {concept}")
    deduped = []
    seen = set()
    for query in queries:
        lowered = query.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(query)
        if len(deduped) >= MAX_QUERY_SUGGESTIONS:
            break
    return deduped


def draft_relpath(relative_raw_path):
    stem = normalized_source_stem(relative_raw_path)
    return f"drafts/{stem}_draft.md"


def _resolve_ingest_mode(workspace: str) -> str:
    config, status = read_workspace_config(workspace)
    if status != "ok" or not isinstance(config, dict):
        return "local"
    providers = config.get("providers") if isinstance(config.get("providers"), dict) else {}
    mode = str(providers.get("ingest_mode") or providers.get("ask_mode") or "local").strip().lower()
    if mode not in {"local", "ai", "hybrid"}:
        return "local"
    return mode


def _extract_text_file(path: Path) -> dict:
    content = _clean_content_for_draft(path.read_text(encoding="utf-8-sig", errors="ignore"))
    lines = _clean_extracted_lines(content.splitlines())
    confidence = _calibrate_confidence(base=0.42, text_lines=lines, structured=False, noisy=_ocr_noise_score(lines), method="native_text")
    return {
        "format": path.suffix.lower().lstrip("."),
        "content": content,
        "confidence": confidence,
        "provenance": [
            {
                "component": "text",
                "method": "local_decoder",
                "confidence": confidence,
                "evidence": f"direct UTF-8 text extraction; {len(lines)} readable lines",
            }
        ],
    }


def _extract_csv(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig")
    if "\x00" in raw:
        raise ValueError("CSV contains NUL bytes")
    rows = list(csv.reader(raw.splitlines()))
    rows = [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("CSV has no readable rows")
    lines = [", ".join(cell for cell in row if cell) for row in rows[:80]]
    content = _clean_content_for_draft("\n".join(lines))
    confidence = _calibrate_confidence(base=0.5, text_lines=lines, structured=True, noisy=False, method="csv_parse")
    return {
        "format": "csv",
        "content": content,
        "confidence": confidence,
        "provenance": [
            {
                "component": "text",
                "method": "csv_parse",
                "confidence": confidence,
                "evidence": f"{len(rows)} readable rows",
            }
        ],
    }


class _ReadableHTMLParser(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "caption",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "pre",
        "section",
        "td",
        "th",
        "tr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def _break(self):
        if self._parts and self._parts[-1] != "\n":
            self._parts.append("\n")

    def handle_starttag(self, tag, attrs):
        tag = str(tag or "").lower()
        if tag in {"script", "style", "noscript", "template"}:
            self._skip_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self._break()
        if tag == "a":
            title = ""
            href = ""
            for key, value in attrs or []:
                if str(key).lower() == "title":
                    title = str(value or "").strip()
                elif str(key).lower() == "href":
                    href = str(value or "").strip()
            if title:
                self._parts.append(f" {title} ")
            elif href and not href.startswith(("#", "javascript:", "mailto:")):
                self._parts.append(" ")

    def handle_endtag(self, tag):
        tag = str(tag or "").lower()
        if tag in {"script", "style", "noscript", "template"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in self.BLOCK_TAGS or tag == "a":
            self._break()

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = " ".join(html.unescape(str(data or "")).split())
        if text:
            self._parts.append(f" {text} ")

    def text(self) -> str:
        lines = []
        for line in "".join(self._parts).splitlines():
            cleaned = " ".join(line.split()).strip()
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)


def _extract_html(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8-sig", errors="ignore")
    parser = _ReadableHTMLParser()
    parser.feed(raw)
    parser.close()
    content = _clean_content_for_draft(parser.text())
    lines = _clean_extracted_lines(content.splitlines())
    if not lines:
        raise ValueError("HTML has no readable text")
    confidence = _calibrate_confidence(base=0.5, text_lines=lines, structured=True, noisy=False, method="html_parse")
    return {
        "format": path.suffix.lower().lstrip("."),
        "content": "\n".join(lines),
        "confidence": confidence,
        "provenance": [
            {
                "component": "text",
                "method": "html_parse",
                "confidence": confidence,
                "evidence": f"HTML text extraction; {len(lines)} readable lines",
            }
        ],
    }


def _xml_root_from_zip(archive: zipfile.ZipFile, name: str):
    try:
        data = archive.read(name)
    except KeyError:
        return None
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        return None


def _xml_local_name(tag: str) -> str:
    return str(tag or "").rsplit("}", 1)[-1]


def _xml_attr(element, local_name: str, default: str = "") -> str:
    for key, value in element.attrib.items():
        if _xml_local_name(key) == local_name:
            return str(value or default)
    return default


def _xlsx_safe_text(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    lowered = text.lower()
    if any(marker in lowered for marker in ("xmlns", "<worksheet", "<relationship", "<style", "<theme")):
        return ""
    if re.fullmatch(r"rId\d+", text, flags=re.IGNORECASE):
        return ""
    if re.fullmatch(r"[{(]?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[)}]?", text, flags=re.IGNORECASE):
        return ""
    if re.fullmatch(r"(?:worksheet|sheetdata|row|c|v|is|t|r|si|sst|style|theme|relationships?)", text, flags=re.IGNORECASE):
        return ""
    return text


def _xlsx_text_nodes(element) -> str:
    parts = []
    for node in element.iter():
        if _xml_local_name(node.tag) == "t" and node.text:
            text = _xlsx_safe_text(node.text)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _xlsx_read_relationships(archive: zipfile.ZipFile, rels_path: str) -> dict[str, str]:
    root = _xml_root_from_zip(archive, rels_path)
    if root is None:
        return {}
    base_dir = posixpath.dirname(posixpath.dirname(rels_path))
    relationships = {}
    for rel in root.iter():
        if _xml_local_name(rel.tag) != "Relationship":
            continue
        rel_id = rel.attrib.get("Id", "")
        target = rel.attrib.get("Target", "")
        if not rel_id or not target or "://" in target:
            continue
        relationships[rel_id] = posixpath.normpath(posixpath.join(base_dir, target)).lstrip("/")
    return relationships


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = _xml_root_from_zip(archive, "xl/sharedStrings.xml")
    if root is None:
        return []
    values = []
    for item in root.iter():
        if _xml_local_name(item.tag) == "si":
            values.append(_xlsx_text_nodes(item))
    return values


def _xlsx_workbook_sheets(archive: zipfile.ZipFile) -> list[dict]:
    root = _xml_root_from_zip(archive, "xl/workbook.xml")
    rels = _xlsx_read_relationships(archive, "xl/_rels/workbook.xml.rels")
    sheets = []
    if root is not None:
        for sheet in root.iter():
            if _xml_local_name(sheet.tag) != "sheet":
                continue
            rel_id = _xml_attr(sheet, "id")
            target = rels.get(rel_id, "")
            if target and not target.startswith("xl/"):
                target = f"xl/{target}"
            name = _xlsx_safe_text(sheet.attrib.get("name", "")) or f"Sheet{len(sheets) + 1}"
            sheets.append({"name": name, "path": target, "rel_id": rel_id})
    if sheets:
        return [sheet for sheet in sheets if sheet.get("path")]
    worksheet_paths = sorted(name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name, flags=re.IGNORECASE))
    return [{"name": f"Sheet{index}", "path": name, "rel_id": ""} for index, name in enumerate(worksheet_paths, start=1)]


def _xlsx_cell_text(cell, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return _xlsx_text_nodes(cell)
    value = ""
    for child in cell:
        if _xml_local_name(child.tag) == "v":
            value = child.text or ""
            break
    if cell_type == "s":
        try:
            index = int(str(value).strip())
        except ValueError:
            return ""
        if 0 <= index < len(shared_strings):
            return _xlsx_safe_text(shared_strings[index])
        return ""
    if cell_type == "b":
        return "TRUE" if str(value).strip() == "1" else "FALSE"
    return _xlsx_safe_text(value)


def _xlsx_visible_cells(archive: zipfile.ZipFile, sheets: list[dict], shared_strings: list[str]) -> list[dict]:
    cells = []
    for sheet in sheets:
        root = _xml_root_from_zip(archive, sheet["path"])
        if root is None:
            continue
        hidden_rows = {
            row.attrib.get("r", "")
            for row in root.iter()
            if _xml_local_name(row.tag) == "row" and str(row.attrib.get("hidden", "")).lower() in {"1", "true"}
        }
        for cell in root.iter():
            if _xml_local_name(cell.tag) != "c":
                continue
            ref = cell.attrib.get("r", "")
            row_id = re.sub(r"\D+", "", ref)
            if row_id in hidden_rows:
                continue
            text = _xlsx_cell_text(cell, shared_strings)
            if text:
                cells.append({"sheet": sheet["name"], "cell": ref or "unknown", "text": text})
    return cells


def _xlsx_comments(archive: zipfile.ZipFile) -> list[dict]:
    comments = []
    for name in sorted(archive.namelist()):
        if not re.fullmatch(r"xl/comments\d*\.xml", name, flags=re.IGNORECASE):
            continue
        root = _xml_root_from_zip(archive, name)
        if root is None:
            continue
        for comment in root.iter():
            if _xml_local_name(comment.tag) != "comment":
                continue
            text = _xlsx_text_nodes(comment)
            if text:
                comments.append({"ref": comment.attrib.get("ref", "unknown"), "text": text, "path": name})
    return comments


def _xlsx_drawing_text(archive: zipfile.ZipFile) -> list[dict]:
    textboxes = []
    for name in sorted(archive.namelist()):
        if not re.fullmatch(r"xl/drawings/drawing\d+\.xml", name, flags=re.IGNORECASE):
            continue
        root = _xml_root_from_zip(archive, name)
        if root is None:
            continue
        text = _xlsx_text_nodes(root)
        if text:
            textboxes.append({"path": name, "text": text})
    return textboxes


def _xlsx_chart_titles(archive: zipfile.ZipFile) -> list[dict]:
    charts = []
    for name in sorted(archive.namelist()):
        if not re.fullmatch(r"xl/charts/chart\d+\.xml", name, flags=re.IGNORECASE):
            continue
        root = _xml_root_from_zip(archive, name)
        if root is None:
            continue
        titles = []
        for title in root.iter():
            if _xml_local_name(title.tag) == "title":
                text = _xlsx_text_nodes(title)
                if text:
                    titles.append(text)
        for text in _dedupe_text(titles, limit=5):
            charts.append({"path": name, "text": text})
    return charts


def _extract_xlsx(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheets = _xlsx_workbook_sheets(archive)
        cells = _xlsx_visible_cells(archive, sheets, shared_strings)
        comments = _xlsx_comments(archive)
        textboxes = _xlsx_drawing_text(archive)
        charts = _xlsx_chart_titles(archive)

    sections = []
    if sheets:
        sections.append("Sheets:\n" + "\n".join(f"- {sheet['name']}" for sheet in sheets[:20]))
    if cells:
        sections.append("Cells:\n" + "\n".join(f"- {cell['sheet']}!{cell['cell']}: {cell['text']}" for cell in cells[:60]))
    if comments:
        sections.append("Comments:\n" + "\n".join(f"- {item['ref']}: {item['text']}" for item in comments[:20]))
    if textboxes:
        sections.append("Textboxes:\n" + "\n".join(f"- {item['text']}" for item in textboxes[:20]))
    if charts:
        sections.append("Chart Titles:\n" + "\n".join(f"- {item['text']}" for item in charts[:20]))

    content = "\n\n".join(sections) or "No visible worksheet knowledge extracted from XLSX container."
    value_lines = [item["text"] for item in cells] + [item["text"] for item in comments] + [item["text"] for item in textboxes] + [item["text"] for item in charts] + [sheet["name"] for sheet in sheets]
    structured = bool(cells or textboxes or charts)
    confidence = _calibrate_confidence(
        base=0.52,
        text_lines=value_lines,
        structured=structured,
        noisy=0.05,
        provider_success=bool(cells or textboxes or charts),
        method="structured_native",
    )
    confidence = _clamp(confidence, 0.0, 0.82)

    cell_refs = ", ".join(f"{cell['sheet']}!{cell['cell']}" for cell in cells[:12]) or "none"
    comment_refs = ", ".join(f"{item['ref']}" for item in comments[:12]) or "none"
    return {
        "format": "xlsx",
        "content": content,
        "confidence": confidence,
        "provenance": [
            _provenance("sheets", "xlsx_workbook_parse", 0.72 if sheets else 0.2, f"{len(sheets)} sheet names", ref="xl/workbook.xml"),
            _provenance("cells", "xlsx_visible_cell_parse", 0.78 if cells else 0.2, f"{len(cells)} visible cell values; refs={cell_refs}", ref="xl/worksheets/*.xml"),
            _provenance("comments", "xlsx_comment_parse", 0.7 if comments else 0.2, f"{len(comments)} comments; refs={comment_refs}", ref="xl/comments*.xml"),
            _provenance("textboxes", "xlsx_drawing_text_parse", 0.66 if textboxes else 0.2, f"{len(textboxes)} drawing text blocks", ref="xl/drawings/drawing*.xml"),
            _provenance("charts", "xlsx_chart_title_parse", 0.64 if charts else 0.2, f"{len(charts)} chart titles", ref="xl/charts/chart*.xml"),
        ],
    }


def _docx_text_nodes(element) -> str:
    parts = []
    for node in element.iter():
        if _xml_local_name(node.tag) == "t" and node.text:
            text = _xlsx_safe_text(node.text)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _docx_child(element, local_name: str):
    for child in element:
        if _xml_local_name(child.tag) == local_name:
            return child
    return None


def _docx_paragraph_style(paragraph) -> str:
    props = _docx_child(paragraph, "pPr")
    if props is None:
        return ""
    for child in props:
        if _xml_local_name(child.tag) == "pStyle":
            return _xml_attr(child, "val")
    return ""


def _docx_is_list_paragraph(paragraph) -> bool:
    props = _docx_child(paragraph, "pPr")
    if props is None:
        return False
    style = _docx_paragraph_style(paragraph).lower()
    if "list" in style:
        return True
    return any(_xml_local_name(child.tag) == "numPr" for child in props)


def _docx_is_heading(text: str, style: str) -> bool:
    normalized_style = re.sub(r"\s+", "", str(style or "").lower())
    if normalized_style.startswith("heading") or normalized_style.startswith("title"):
        return True
    return bool(re.match(r"^(?:chapter|chuong|chương)\s+\d+\s*(?:$|[-:–])", str(text or "").strip(), flags=re.IGNORECASE))


def _docx_table_rows(table) -> list[str]:
    rows = []
    for row in table.iter():
        if _xml_local_name(row.tag) != "tr":
            continue
        cells = []
        for cell in row:
            if _xml_local_name(cell.tag) != "tc":
                continue
            text = _docx_text_nodes(cell)
            cells.append(text or "")
        cleaned = [cell for cell in cells if cell]
        if cleaned:
            rows.append(" | ".join(cleaned))
    return rows


def _docx_core_metadata(archive: zipfile.ZipFile) -> dict[str, str]:
    root = _xml_root_from_zip(archive, "docProps/core.xml")
    if root is None:
        return {}
    values = {}
    for node in root.iter():
        key = _xml_local_name(node.tag).lower()
        if key in {"title", "subject", "creator", "description"} and node.text:
            text = _xlsx_safe_text(node.text)
            if text:
                values[key] = text
    return values


def _extract_docx(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            document = _xml_root_from_zip(archive, "word/document.xml")
            metadata = _docx_core_metadata(archive)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"DOCX parser failed for {path.name}: invalid zip container") from exc

    if document is None:
        raise ValueError(f"DOCX parser failed for {path.name}: missing word/document.xml")

    body = None
    for child in document.iter():
        if _xml_local_name(child.tag) == "body":
            body = child
            break
    if body is None:
        raise ValueError(f"DOCX parser failed for {path.name}: missing document body")

    sections = []
    headings = []
    paragraphs = []
    lists = []
    tables = []
    order = 0
    table_index = 0
    chapter_title = metadata.get("title") or path.stem

    for child in body:
        local_name = _xml_local_name(child.tag)
        if local_name == "p":
            text = _docx_text_nodes(child)
            if not text:
                continue
            order += 1
            style = _docx_paragraph_style(child)
            if _docx_is_heading(text, style):
                if not headings:
                    chapter_title = text
                headings.append({"order": order, "text": text, "style": style})
                sections.append(f"Section order {order}: Heading: {text}")
            elif _docx_is_list_paragraph(child):
                lists.append({"order": order, "text": text})
                sections.append(f"Section order {order}: List item: {text}")
            else:
                paragraphs.append({"order": order, "text": text})
                sections.append(f"Section order {order}: Paragraph: {text}")
        elif local_name == "tbl":
            table_rows = _docx_table_rows(child)
            if not table_rows:
                continue
            order += 1
            table_index += 1
            tables.append({"order": order, "rows": table_rows})
            sections.append(f"Section order {order}: Table {table_index}:")
            sections.extend(f"- Table {table_index} row {row_index}: {row_text}" for row_index, row_text in enumerate(table_rows, start=1))

    value_lines = [item["text"] for item in headings + paragraphs + lists]
    for table in tables:
        value_lines.extend(table["rows"])
    if not value_lines:
        raise ValueError(f"DOCX parser failed for {path.name}: no readable text extracted")

    content = "\n".join(
        [
            f"Filename: {path.name}",
            f"Chapter title: {chapter_title}",
            f"Section count: {order}",
            "",
            *sections,
        ]
    )
    confidence = _calibrate_confidence(
        base=0.56,
        text_lines=value_lines,
        structured=bool(headings or tables or lists),
        noisy=0.02,
        provider_success=True,
        method="structured_native",
    )
    signals = ["docx_container", "paragraphs"]
    if headings:
        signals.append("headings")
    if lists:
        signals.append("lists")
    if tables:
        signals.append("tables")
    return {
        "format": "docx",
        "content": content,
        "confidence": _clamp(confidence, 0.0, 0.84),
        "provenance": [
            _provenance("metadata", "docx_core_metadata", 0.72 if metadata else 0.35, f"filename={path.name}; chapter_title={chapter_title}", ref="docProps/core.xml"),
            _provenance("headings", "docx_heading_parse", 0.78 if headings else 0.22, f"{len(headings)} heading blocks", ref="word/document.xml#w:p"),
            _provenance("text", "docx_paragraph_parse", 0.8 if paragraphs else 0.28, f"{len(paragraphs)} paragraph blocks", ref="word/document.xml#w:p"),
            _provenance("lists", "docx_list_parse", 0.74 if lists else 0.22, f"{len(lists)} list items", ref="word/document.xml#w:numPr"),
            _provenance("tables", "docx_table_parse", 0.76 if tables else 0.22, f"{sum(len(table['rows']) for table in tables)} table rows", ref="word/document.xml#w:tbl"),
        ],
        "document_type": {"type": "text_document", "confidence": 0.78, "signals": signals},
    }


def _extract_pptx(path: Path) -> dict:
    slide_text = []
    notes_text = []
    media_count = 0
    with zipfile.ZipFile(path, "r") as archive:
        for name in archive.namelist():
            lowered = name.lower()
            if lowered.startswith("ppt/media/"):
                media_count += 1
                continue
            if not lowered.endswith(".xml"):
                continue
            try:
                xml_text = archive.read(name).decode("utf-8", errors="ignore")
            except KeyError:
                continue
            tokens = _extract_xml_text(xml_text)
            if lowered.startswith("ppt/slides/"):
                slide_text.extend(tokens)
            elif lowered.startswith("ppt/notesslides/"):
                notes_text.extend(tokens)

    sections = []
    if slide_text:
        sections.append("Slide text:\n" + "\n".join(f"- {item}" for item in slide_text[:60]))
    if notes_text:
        sections.append("Speaker notes:\n" + "\n".join(f"- {item}" for item in notes_text[:30]))
    if media_count:
        sections.append(f"Embedded media/images: {media_count}")
    content = "\n\n".join(sections) or "No textual payload extracted from PPTX container."

    confidence = 0.48
    if slide_text:
        confidence += 0.1
    if notes_text:
        confidence += 0.05
    if media_count:
        confidence += 0.03

    return {
        "format": "pptx",
        "content": content,
        "confidence": _clamp(confidence, 0.0, 0.7),
        "provenance": [
            {"component": "slides", "method": "pptx_xml_parse", "confidence": 0.7 if slide_text else 0.2, "evidence": f"{len(slide_text)} slide tokens"},
            {"component": "notes", "method": "pptx_notes_parse", "confidence": 0.62 if notes_text else 0.2, "evidence": f"{len(notes_text)} note tokens"},
            {"component": "embedded_images", "method": "pptx_media_manifest", "confidence": 0.55 if media_count else 0.2, "evidence": f"{media_count} media assets"},
        ],
    }


def _extract_pdf_text_layer(path: Path) -> tuple[list[dict], dict]:
    reader_cls = None
    backend = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_cls = PdfReader
        backend = "pypdf"
    except Exception:  # noqa: BLE001
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_cls = PdfReader
            backend = "PyPDF2"
        except Exception as exc:  # noqa: BLE001
            return [], {"backend": "none", "status": "unavailable", "reason": str(exc)}

    try:
        reader = reader_cls(str(path))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                page_text = ""
            lines = _clean_extracted_lines(page_text.splitlines(), limit=80)
            if lines:
                pages.append({"page": index, "lines": lines})
        return pages, {"backend": backend, "status": "success" if pages else "empty", "pages": len(reader.pages)}
    except Exception as exc:  # noqa: BLE001
        return [], {"backend": backend or "unknown", "status": "failed", "reason": str(exc)}


def _render_pdf_pages(path: Path, output_dir: Path, *, max_pages: int | None = None) -> tuple[list[dict], dict]:
    pages = []
    try:
        import fitz  # type: ignore

        document = fitz.open(str(path))
        page_total = len(document)
        limit = min(page_total, max_pages or page_total)
        for index in range(limit):
            page = document[index]
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            out_path = output_dir / f"page-{index + 1:03d}.png"
            pixmap.save(str(out_path))
            pages.append({"page": index + 1, "path": out_path, "width": pixmap.width, "height": pixmap.height, "backend": "pymupdf"})
        document.close()
        return pages, {"backend": "pymupdf", "status": "success" if pages else "empty", "pages": page_total, "rendered": len(pages)}
    except Exception as pymupdf_exc:  # noqa: BLE001
        pymupdf_error = str(pymupdf_exc)

    try:
        from pdf2image import convert_from_path  # type: ignore

        images = convert_from_path(str(path), dpi=200, first_page=1, last_page=max_pages)
        for index, image in enumerate(images, start=1):
            out_path = output_dir / f"page-{index:03d}.png"
            image.save(str(out_path), "PNG")
            pages.append({"page": index, "path": out_path, "width": image.width, "height": image.height, "backend": "pdf2image"})
        return pages, {"backend": "pdf2image", "status": "success" if pages else "empty", "rendered": len(pages), "pymupdf_error": pymupdf_error}
    except Exception as pdf2image_exc:  # noqa: BLE001
        return [], {"backend": "none", "status": "unavailable", "pymupdf_error": pymupdf_error, "pdf2image_error": str(pdf2image_exc)}


def _vision_limits(workspace: str) -> dict:
    config, status = read_workspace_config(workspace)
    providers = config.get("providers") if status == "ok" and isinstance(config, dict) and isinstance(config.get("providers"), dict) else {}
    return {
        "max_pages": int(providers.get("vision_max_pages") or VISION_MAX_PAGES_DEFAULT),
        "max_file_mb": float(providers.get("vision_max_file_mb") or VISION_MAX_FILE_MB_DEFAULT),
    }


def _provider_vision_allowed(workspace: str, ingest_mode: str, path: Path, page_count: int) -> tuple[bool, str]:
    if ingest_mode not in {"ai", "hybrid"}:
        return False, "provider mode disabled"
    limits = _vision_limits(workspace)
    size_mb = path.stat().st_size / (1024 * 1024) if path.exists() else 0.0
    if size_mb > limits["max_file_mb"]:
        return False, f"file too large for provider vision fallback ({size_mb:.2f}MB > {limits['max_file_mb']:.2f}MB)"
    if page_count > limits["max_pages"]:
        return False, f"too many pages for provider vision fallback ({page_count} > {limits['max_pages']})"
    return True, "allowed"


def _provider_vision_page(workspace: str, image_path: Path, page_no: int, local_lines: list[str]) -> dict:
    prompt = "\n".join(
        [
            "You are assisting ABW scanned PDF page OCR.",
            f"Page image artifact: {image_path}",
            f"Page number: {page_no}",
            "Transcribe visible business text only. Return concise lines, no XML, no metadata.",
            "Local OCR candidate lines:",
            *([f"- {line}" for line in local_lines[:30]] or ["- none"]),
        ]
    )
    execution = execute_provider_chain(
        workspace,
        prompt=prompt,
        task="summarization",
        sensitivity="normal",
        cost_mode="quality",
    )
    text = _clean_content_for_draft(str(execution.get("draft") or ""))
    lines = _clean_extracted_lines(text.splitlines(), limit=60)
    quality = _text_quality(lines)
    used = execution.get("status") == "success" and quality["usable"] and bool(lines)
    confidence = (
        _calibrate_confidence(
            base=0.36,
            text_lines=lines,
            structured=bool(_table_region_blocks(_region_blocks(lines, page=page_no))),
            noisy=_ocr_noise_score(lines),
            provider_success=True,
            method="real_ocr",
        )
        if used
        else 0.0
    )
    return {
        "used": used,
        "status": execution.get("status"),
        "provider": execution.get("provider", ""),
        "lines": lines if used else [],
        "confidence": confidence,
        "quality": quality,
        "attempts": execution.get("attempts", []),
        "fail_count": int(execution.get("fail_count", 0)),
    }


def _extract_scanned_pdf_pages(path: Path, workspace: str, ingest_mode: str, page_count: int, image_refs: list[str]) -> dict | None:
    with tempfile.TemporaryDirectory(prefix="abw_pdf_pages_") as tmp:
        pages, render_status = _render_pdf_pages(path, Path(tmp))
        if not pages:
            return None
        allowed, provider_reason = _provider_vision_allowed(workspace, ingest_mode, path, len(pages))
        all_lines = []
        page_rows = []
        provenance = [
            _provenance("page_images", "pdf_page_render", 0.68, f"{len(pages)} rendered page images via {render_status.get('backend')}", ref="pdf:/pages/*/rendered-images")
        ]
        provider_used = False
        provider_fail_count = 0
        for page in pages:
            ocr = _local_ocr_image(page["path"])
            selected_lines = ocr["text_lines"]
            selected_method = f"local_ocr:{ocr.get('selected_provider', 'unknown')}"
            selected_confidence = float(ocr.get("confidence") or 0.0)
            if selected_confidence < LOW_CONFIDENCE_REVIEW_THRESHOLD and allowed:
                vision = _provider_vision_page(workspace, page["path"], int(page["page"]), selected_lines)
                provider_fail_count += int(vision.get("fail_count", 0))
                if vision["used"] and float(vision["confidence"]) > selected_confidence:
                    selected_lines = vision["lines"]
                    selected_method = f"provider_vision:{vision.get('provider', '')}"
                    selected_confidence = float(vision["confidence"])
                    provider_used = True
            page_rows.append({"page": page["page"], "lines": selected_lines, "method": selected_method, "confidence": selected_confidence, "ocr": ocr})
            all_lines.extend(selected_lines)

        region_blocks = [block for row in page_rows for block in _region_blocks(row["lines"], page=int(row["page"]))]
        table_regions = _table_region_blocks(region_blocks)
        detections = _classify_visual_artifact(all_lines, image_count=len(image_refs))
        noisy = _ocr_noise_score(all_lines)
        confidence = _calibrate_confidence(
            base=0.3,
            text_lines=all_lines,
            structured=bool(table_regions or detections.get("tables")),
            noisy=noisy,
            method="real_ocr" if all_lines else "metadata_probe",
        )
        if provider_used:
            confidence = max(confidence, max((row["confidence"] for row in page_rows), default=confidence))
        content_parts = [
            f"PDF pages detected: {page_count}",
            f"PDF page render mode: {render_status.get('backend')}",
            f"Page image candidates: {len(image_refs)}",
            f"Provider vision fallback: {'used' if provider_used else 'not_used'} ({provider_reason})",
            _semantic_summary_for_visual("PDF page OCR", all_lines, detections),
        ]
        for row in page_rows:
            content_parts.append(f"Page {row['page']} OCR method: {row['method']}; confidence={row['confidence']:.2f}")
            content_parts.extend(f"- page {row['page']}: {line}" for line in row["lines"][:40])
        if region_blocks:
            content_parts.append("OCR/Layout regions:")
            content_parts.extend(_region_lines(region_blocks, prefix="pdf:/pages", limit=120))
        if table_regions:
            content_parts.append("Detected table-like regions:")
            content_parts.extend(_region_lines(table_regions, prefix="pdf:/pages", limit=40))
        if not all_lines:
            content_parts.append("OCR/local text extraction did not recover readable PDF text.")

        provenance.extend(
            [
                _provenance("ocr_text", "pdf_page_local_ocr", max((row["confidence"] for row in page_rows), default=0.08), f"{len(all_lines)} OCR lines across {len(page_rows)} rendered pages; provider_fallback={provider_used}; fail_count={provider_fail_count}", ref="pdf:/pages/*/ocr"),
                _provenance("regions", "pdf_page_ocr_regions", 0.72 if region_blocks else 0.25, f"{len(region_blocks)} ordered page OCR regions", ref="pdf:/pages/*/regions"),
                _provenance("table_regions", "pdf_page_table_region_detector", 0.72 if table_regions else 0.25, f"{len(table_regions)} table-like page regions", ref="pdf:/pages/*/tables"),
                _provenance("provider_vision", "provider_vision_page_ocr", max((row["confidence"] for row in page_rows if str(row["method"]).startswith("provider_vision")), default=0.0), f"provider_used={provider_used}; reason={provider_reason}; fail_count={provider_fail_count}", ref="pdf:/pages/*/provider-vision"),
            ]
        )
        return {
            "format": "pdf",
            "content": "\n".join(content_parts),
            "confidence": confidence if all_lines else 0.08,
            "provenance": provenance,
        }


def _extract_pdf(path: Path, workspace: str = ".", ingest_mode: str = "local") -> dict:
    raw = path.read_bytes()
    decoded = raw.decode("latin-1", errors="ignore")
    page_count = max(1, len(re.findall(r"/Type\s*/Page\b", decoded)) or len(re.findall(r"\bendobj\b", decoded)) // 8)
    image_refs = re.findall(r"/Subtype\s*/Image\b", decoded)
    text_pages, text_status = _extract_pdf_text_layer(path)
    if text_pages:
        text_lines = [line for page in text_pages for line in page["lines"]]
        region_blocks = [block for page in text_pages for block in _region_blocks(page["lines"], page=page["page"])]
        table_regions = _table_region_blocks(region_blocks)
        noisy = _ocr_noise_score(text_lines)
        detections = _classify_visual_artifact(text_lines, image_count=len(image_refs))
        confidence = _calibrate_confidence(
            base=0.44,
            text_lines=text_lines,
            structured=bool(table_regions or detections.get("tables")),
            noisy=noisy,
            method="pdf_text_layer",
        )
        content_parts = [
            f"PDF pages detected: {max(page_count, int(text_status.get('pages') or 0))}",
            f"PDF extraction mode: text_layer ({text_status.get('backend')})",
            f"Page image candidates: {len(image_refs)}",
            "Text layer blocks:",
        ]
        for page in text_pages:
            for line in page["lines"][:40]:
                content_parts.append(f"- page {page['page']}: {line}")
        if region_blocks:
            content_parts.append("OCR/Layout regions:")
            content_parts.extend(_region_lines(region_blocks, prefix="pdf:/pages", limit=80))
        if table_regions:
            content_parts.append("Detected table-like regions:")
            content_parts.extend(_region_lines(table_regions, prefix="pdf:/pages", limit=24))
        return {
            "format": "pdf",
            "content": "\n".join(content_parts),
            "confidence": confidence,
            "provenance": [
                _provenance("text", "pdf_text_layer", confidence, f"{len(text_lines)} readable text lines via {text_status.get('backend')}; noise={noisy:.2f}", ref="pdf:/pages/*/text"),
                _provenance("page_images", "pdf_xobject_scan", 0.35 if image_refs else 0.2, f"{len(image_refs)} image XObject candidates", ref="pdf:/pages/*/images"),
                _provenance("layout", "pdf_text_page_blocks", confidence, f"{len(text_pages)} pages with readable text", ref="pdf:/pages/*/blocks"),
                _provenance("regions", "pdf_ordered_text_regions", min(0.82, confidence + 0.05), f"{len(region_blocks)} ordered text regions", ref="pdf:/pages/*/regions"),
                _provenance("table_regions", "pdf_table_region_detector", 0.72 if table_regions else 0.25, f"{len(table_regions)} table-like regions", ref="pdf:/pages/*/tables"),
            ],
        }

    scanned = _extract_scanned_pdf_pages(path, workspace, ingest_mode, page_count, image_refs)
    if scanned is not None:
        return scanned

    probe_snippets = _binary_text_probe(raw, min_len=8)
    quality = _text_quality(probe_snippets)
    snippets = probe_snippets if quality["usable"] else []
    layout_blocks = []
    for idx, line in enumerate(snippets[:80], start=1):
        page_ref = min(page_count, ((idx - 1) % page_count) + 1)
        layout_blocks.extend(_region_blocks([line], page=page_ref, limit=1))
        if layout_blocks:
            layout_blocks[-1]["region"] = f"region-{idx:02d}"
    table_regions = _table_region_blocks(layout_blocks)
    detections = _classify_visual_artifact(snippets, image_count=len(image_refs))
    summary = _semantic_summary_for_visual("PDF scan", snippets, detections)
    content_parts = [
        f"PDF pages detected: {page_count}",
        f"Page image candidates: {len(image_refs)}",
        summary,
    ]
    if layout_blocks:
        content_parts.append("Layout blocks:\n" + "\n".join(_region_lines(layout_blocks, prefix="pdf:/pages", limit=80)))
    if table_regions:
        content_parts.append("Detected table-like regions:\n" + "\n".join(_region_lines(table_regions, prefix="pdf:/pages", limit=24)))
    else:
        content_parts.append("OCR/local text extraction did not recover readable PDF text.")
    content = "\n\n".join(content_parts)
    noisy = _ocr_noise_score(snippets)
    confidence = _calibrate_confidence(
        base=0.18 if quality["usable"] else 0.1,
        text_lines=snippets,
        structured=False,
        noisy=noisy,
        method="binary_probe" if quality["usable"] else "metadata_probe",
    )
    ocr_method = "pdf_binary_text_probe" if quality["usable"] else "pdf_metadata_probe"
    return {
        "format": "pdf",
        "content": content,
        "confidence": confidence,
        "provenance": [
            _provenance("page_images", "pdf_xobject_scan", 0.55 if image_refs else 0.3, f"{len(image_refs)} image XObject candidates", ref="pdf:/pages/*/images"),
            _provenance(
                "ocr_text",
                ocr_method,
                confidence,
                f"{len(snippets)} readable metadata/text candidates from {len(probe_snippets)} binary tokens; noise={noisy:.2f}; {_quality_evidence(quality)}",
                ref="pdf:/pages/*",
            ),
            _provenance("layout", "pdf_layout_block_scan", 0.58 if layout_blocks else 0.32, f"{len(layout_blocks)} layout blocks across {page_count} pages", ref="pdf:/pages/*/blocks"),
            _provenance("regions", "pdf_estimated_text_regions", 0.58 if layout_blocks else 0.25, f"{len(layout_blocks)} estimated regions across {page_count} pages", ref="pdf:/pages/*/regions"),
            _provenance("table_regions", "pdf_table_region_detector", 0.72 if table_regions else 0.25, f"{len(table_regions)} table-like regions", ref="pdf:/pages/*/tables"),
            _provenance("semantic_summary", "local_visual_classifier", confidence, ", ".join(name for name in ("tables", "ui_screenshot", "software_window", "diagrams", "labels_buttons") if detections.get(name)) or "visual_artifact", ref="pdf:/summary"),
        ],
    }


def _ocr_token_count(lines: list[str]) -> int:
    text = " ".join(str(line or "") for line in lines)
    return len(re.findall(r"[A-Za-z0-9\u3040-\u30ff\u3400-\u9fff]{2,}", text))


def _extract_image(path: Path, *, workspace: str = ".", ingest_mode: str = "local") -> dict:
    size = path.stat().st_size if path.exists() else 0
    width, height = _image_dimensions(path)
    ocr = _local_ocr_image(path)
    text_lines = ocr["text_lines"]
    provider_used = False
    provider_reason = "not needed"
    provider_fail_count = 0
    provider_confidence = 0.0
    token_count = _ocr_token_count(text_lines)
    low_confidence_route = token_count < MIN_USEFUL_OCR_TOKENS
    if low_confidence_route:
        allowed, provider_reason = _provider_vision_allowed(workspace, ingest_mode, path, 1)
        if allowed:
            vision = _provider_vision_page(workspace, path, 1, text_lines)
            provider_fail_count = int(vision.get("fail_count", 0))
            if vision.get("used"):
                text_lines = list(vision.get("lines") or [])
                token_count = _ocr_token_count(text_lines)
                provider_confidence = float(vision.get("confidence") or 0.0)
                provider_used = True
            elif provider_reason == "allowed":
                provider_reason = f"provider attempted but {vision.get('status', 'failed')}"
    region_blocks = _region_blocks(text_lines)
    table_regions = _table_region_blocks(region_blocks)
    detections = _classify_visual_artifact(text_lines, width=width, height=height)
    structured = bool(detections.get("tables") or table_regions)
    confidence = (
        _calibrate_confidence(
            base=ocr["confidence"],
            text_lines=text_lines,
            structured=structured,
            noisy=float(ocr["noise"]),
            provider_success=True,
            method="real_ocr",
        )
        if ocr["real_ocr_success"]
        else min(float(ocr["confidence"]), 0.1)
    )
    if provider_used:
        confidence = max(confidence, provider_confidence)
    dimensions = f"{width}x{height}" if width and height else "unknown dimensions"
    content = "\n".join(
        [
            f"Image artifact detected ({path.name}, {size} bytes, {dimensions}).",
            "OCR confidence routing: "
            + (
                f"low_confidence; provider vision fallback: {'used' if provider_used else 'not_used'} ({provider_reason})"
                if low_confidence_route
                else "local_ocr_sufficient"
            ),
            _semantic_summary_for_visual("Image", text_lines, detections),
            "Detected buttons/labels: " + (", ".join(detections["button_labels"]) if detections["button_labels"] else "none"),
            "Software window semantics: " + (", ".join(detections["window_semantics"]) if detections["window_semantics"] else "none"),
            "OCR text:",
            *([f"- {line}" for line in text_lines[:80]] or ["- none recovered"]),
            "OCR/Layout regions:",
            *(_region_lines(region_blocks, prefix=f"image:{path.name}", limit=80) or ["- none"]),
            "Detected table-like regions:",
            *(_region_lines(table_regions, prefix=f"image:{path.name}", limit=24) or ["- none"]),
        ]
    )
    attempt_evidence = "; ".join(f"{row.get('provider')}={row.get('status')}" for row in ocr["attempts"])
    quality_evidence = _quality_evidence(ocr["quality"])
    return {
        "format": path.suffix.lower().lstrip("."),
        "content": content,
        "confidence": confidence,
        "provenance": [
            _provenance(
                "ocr_text",
                "local_ocr_provider_chain",
                ocr["confidence"],
                f"{len(text_lines)} OCR tokens; {attempt_evidence}; noise={float(ocr['noise']):.2f}; {quality_evidence}",
                ref=f"image:{path.name}",
            ),
            _provenance(
                "provider_vision",
                "provider_vision_image_ocr",
                provider_confidence,
                f"low_confidence_route={low_confidence_route}; provider_used={provider_used}; reason={provider_reason}; fail_count={provider_fail_count}",
                ref=f"image:{path.name}#provider-vision",
            ),
            _provenance("layout", "image_metadata_scan", 0.48 if width and height else 0.28, f"{size} bytes; dimensions={dimensions}", ref=f"image:{path.name}"),
            _provenance("regions", "image_ordered_ocr_regions", 0.76 if region_blocks else 0.25, f"{len(region_blocks)} ordered OCR regions", ref=f"image:{path.name}#regions"),
            _provenance("table_regions", "image_table_region_detector", 0.72 if table_regions else 0.25, f"{len(table_regions)} table-like OCR regions", ref=f"image:{path.name}#tables"),
            _provenance("tables", "visual_table_detector", 0.7 if detections["tables"] else 0.25, str(detections["signals"]), ref=f"image:{path.name}#tables"),
            _provenance("ui_screenshot", "visual_ui_detector", 0.7 if detections["ui_screenshot"] else 0.25, str(detections["signals"]), ref=f"image:{path.name}#ui"),
            _provenance("software_window", "software_window_semantic_detector", 0.74 if detections["software_window"] else 0.25, str(detections["window_semantics"] or detections["signals"]), ref=f"image:{path.name}#window"),
            _provenance("diagrams", "visual_diagram_detector", 0.68 if detections["diagrams"] else 0.25, str(detections["signals"]), ref=f"image:{path.name}#diagram"),
            _provenance("labels_buttons", "visual_label_button_detector", 0.72 if detections["labels_buttons"] else 0.25, str(detections["button_labels"] or detections["signals"]), ref=f"image:{path.name}#labels"),
        ],
    }


def _extract_multimodal_content(raw_path: Path, *, workspace: str = ".", ingest_mode: str = "local") -> dict:
    suffix = raw_path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return _extract_text_file(raw_path)
    if suffix in CSV_EXTENSIONS:
        return _extract_csv(raw_path)
    if suffix in HTML_EXTENSIONS:
        return _extract_html(raw_path)
    if suffix == ".docx":
        return _extract_docx(raw_path)
    if suffix == ".xlsx":
        return _extract_xlsx(raw_path)
    if suffix == ".pptx":
        return _extract_pptx(raw_path)
    if suffix == ".pdf":
        return _extract_pdf(raw_path, workspace=workspace, ingest_mode=ingest_mode)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image(raw_path, workspace=workspace, ingest_mode=ingest_mode)
    raise ValueError(f"Unsupported file extension: {suffix or '<none>'}")


def _provider_semantic_enrichment(workspace: str, relative_raw_path: str, extracted: dict, ingest_mode: str) -> dict:
    extracted_content = _clean_content_for_draft(extracted["content"])
    if ingest_mode == "local":
        return {
            "content": extracted_content,
            "confidence": float(extracted["confidence"]),
            "provider": {"used": False, "mode": "local", "status": "skipped", "fail_count": 0, "vision_adapters": list(VISION_PROVIDERS)},
        }

    prompt = "\n".join(
        [
            "You are assisting ABW ingest summarization.",
            f"Source: {relative_raw_path}",
            f"Format: {extracted.get('format', 'unknown')}",
            "Use the configured cloud vision adapter when the source is image/PDF/XLSX media.",
            f"Supported vision adapters: {', '.join(VISION_PROVIDERS)}.",
            "Generate concise semantic summary, key findings, and possible ambiguities.",
            "Evidence follows:",
            _shorten(extracted_content, limit=3200),
        ]
    )
    execution = execute_provider_chain(
        workspace,
        prompt=prompt,
        task="summarization",
        sensitivity="normal",
        cost_mode="balanced",
    )
    provider = {
        "used": execution.get("status") == "success",
        "mode": ingest_mode,
        "status": execution.get("status"),
        "selected": execution.get("provider", ""),
        "fail_count": int(execution.get("fail_count", 0)),
        "latency_ms": int(execution.get("latency_ms", 0)),
        "token_estimate": int(execution.get("token_estimate", 0)),
        "attempts": execution.get("attempts", []),
        "vision_adapters": list(VISION_PROVIDERS),
    }

    if execution.get("status") != "success":
        return {
            "content": extracted_content,
            "confidence": float(extracted["confidence"]),
            "provider": provider,
        }

    semantic = str(execution.get("draft") or "").strip()
    merged = extracted_content
    if semantic:
        merged += "\n\nProvider semantic summary:\n" + _clean_content_for_draft(semantic)

    return {"content": _clean_content_for_draft(merged), "confidence": float(extracted["confidence"]), "provider": provider}


def write_draft(
    workspace,
    relative_raw_path,
    summary,
    concepts,
    possible_queries,
    source_id,
    *,
    ingest_mode,
    confidence,
    provenance,
    provider,
    promotion_status,
    perception,
    review_reason,
    semantic=None,
    source_excerpt="",
    draft_file=None,
):
    relpath = draft_file or draft_relpath(relative_raw_path)
    alias_candidates = _draft_alias_candidates(relative_raw_path)
    current_relpath = draft_relpath(relative_raw_path)
    if current_relpath != relpath:
        alias_candidates.append(current_relpath)
    _merge_existing_alias_drafts(workspace, relpath, alias_candidates)
    path = Path(workspace) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)

    prov_lines = []
    for row in provenance or []:
        ref = f"; ref={row.get('ref')}" if row.get("ref") else ""
        prov_lines.append(
            f"- {row.get('component', 'unknown')}: method={row.get('method', 'unknown')}; "
            f"confidence={float(row.get('confidence', 0.0)):.2f}; evidence={row.get('evidence', '')}{ref}"
        )

    provider_line = (
        f"used={provider.get('used')}; status={provider.get('status')}; selected={provider.get('selected', '')}; "
        f"fail_count={provider.get('fail_count', 0)}; latency_ms={provider.get('latency_ms', 0)}; "
        f"token_estimate={provider.get('token_estimate', 0)}"
    )
    doc_type = perception.get("document_type") or {}
    semantic = semantic or {}
    purpose = semantic.get("document_purpose") or {}
    stage_lines = []
    for row in perception.get("stages") or []:
        stage_lines.append(f"- {row.get('stage')}: confidence={float(row.get('confidence') or 0.0):.2f}")

    def bullet_lines(items):
        return [f"- {item}" for item in items] if items else ["- none"]

    content = "\n".join(
        [
            f"# Draft Knowledge: {Path(relative_raw_path).stem}",
            "",
            f"- source_id: {source_id}",
            f"- raw_file: {relative_raw_path}",
            f"- status: draft",
            f"- ingest_mode: {ingest_mode}",
            f"- confidence: {confidence:.2f}",
            f"- promotion_status: {promotion_status}",
            f"- review_reason: {review_reason}",
            f"- perception_version: {perception.get('version')}",
            f"- document_type: {doc_type.get('type', 'unknown')}",
            f"- document_purpose: {purpose.get('purpose', 'general_knowledge_source')}",
            "",
            "## Business Summary",
            summary or "No summary could be extracted from the raw file.",
            "",
            "## Document Purpose",
            f"- purpose: {purpose.get('purpose', 'general_knowledge_source')}",
            f"- confidence: {float(purpose.get('confidence') or 0.0):.2f}",
            f"- signals: {', '.join(str(item) for item in purpose.get('signals', [])[:6]) or 'none'}",
            "",
            "## Key Topics",
            *bullet_lines(concepts),
            "",
            "## Extracted Knowledge Signals",
            "### Entities",
            *bullet_lines(semantic.get("entities") or []),
            "",
            "### Modules",
            *bullet_lines(semantic.get("modules") or []),
            "",
            "### Errors",
            *bullet_lines(semantic.get("errors") or []),
            "",
            "### Processes",
            *bullet_lines(semantic.get("processes") or []),
            "",
            "## Perception Pipeline",
            f"- document_type: {doc_type.get('type', 'unknown')}",
            f"- document_type_confidence: {float(doc_type.get('confidence') or 0.0):.2f}",
            f"- signals: {', '.join(str(item) for item in (doc_type.get('signals') or [])[:8]) or 'none'}",
            *(stage_lines or ["- none"]),
            "",
            "## Provider Assistance",
            f"- {provider_line}",
            "",
            "## Possible Queries",
            *([f"- {query}" for query in possible_queries] or ["- none suggested"]),
            "",
            "## Extracted Source Text",
            _shorten(source_excerpt, limit=1600) or "No extracted source text available.",
            "",
            "## Provenance",
            "Raw extraction trace kept separate from business summary.",
            *(prov_lines or ["- none"]),
            "",
            "## Trust Notice",
            "This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return relpath


def append_manifest_entry(
    workspace,
    source_id,
    relative_raw_path,
    *,
    format_name,
    confidence,
    ingest_mode,
    perception,
    queue_status,
    review_reason,
    source_identity=None,
):
    path = manifest_path(workspace)
    source_key = _manifest_source_key(relative_raw_path)
    source_identity = source_identity or {}
    entry = {
        "id": source_id,
        "source": relative_raw_path,
        "status": "processed",
        "format": format_name,
        "confidence": round(float(confidence), 4),
        "ingest_mode": ingest_mode,
        "perception": perception,
        "queue_status": queue_status,
        "review_reason": review_reason,
        "created_at": now_iso(),
    }
    aliases = _source_aliases(source_identity, relative_raw_path)
    lineage = [row for row in (source_identity.get("lineage") or []) if isinstance(row, dict)]
    if aliases:
        entry["aliases"] = aliases
    if lineage:
        entry["lineage"] = lineage
    if source_identity.get("renamed_from"):
        entry["renamed_from"] = source_identity.get("renamed_from")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in _read_manifest_rows(path):
        if isinstance(row, dict):
            if row.get("id") == source_id or row.get("source") == relative_raw_path:
                continue
            if _manifest_source_key(str(row.get("source") or "")) == source_key:
                continue
        rows.append(row)
    rows.append(entry)
    _write_manifest_rows(path, rows)
    return entry


def update_ingest_queue(workspace, source_id, relative_raw_path, draft_file, *, queue_status, confidence, perception, review_reason):
    path = ingest_queue_path(workspace)
    payload = load_json(path, {"items": [], "updated_at": now_iso()})
    item = {
        "id": source_id,
        "raw": relative_raw_path,
        "draft": draft_file,
        "status": queue_status,
        "confidence": round(float(confidence), 4),
        "perception": perception,
        "review_reason": review_reason,
    }
    existing = payload.setdefault("items", [])
    payload["items"] = [row for row in existing if row.get("id") != source_id and row.get("raw") != relative_raw_path]
    payload["items"].append(item)
    payload["updated_at"] = now_iso()
    save_json(path, payload)
    return item


def list_supported_raw_files(raw_target_path):
    target = Path(raw_target_path)
    target_text = str(target)
    if any(char in target_text for char in "*?["):
        parent = target.parent if str(target.parent) not in {"", "."} else Path(".")
        pattern = target.name
        files = [
            candidate
            for candidate in sorted(parent.glob(pattern))
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not files:
            raise FileNotFoundError(
                "No supported files matched ingest glob. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        return _merge_source_siblings(files)
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: {target.suffix or '<none>'}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        return _merge_source_siblings([target])
    if not target.is_dir():
        raise NotADirectoryError(f"Ingest target is not a file or directory: {target}")
    files = []
    for candidate in sorted(target.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(candidate)
    if not files:
        raise FileNotFoundError(
            "No supported files found in directory. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return _merge_source_siblings(files)


def _relative_workspace_path(path: Path, workspace: str) -> str:
    try:
        return str(path.resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _skip_record(path: Path, workspace: str, reason: str, action: str = "skipped", message: str = "") -> dict:
    record = {
        "path": _relative_workspace_path(path, workspace),
        "reason": reason,
        "action": action,
    }
    if message:
        record["message"] = _shorten(message, limit=240)
    return record


def _is_empty_skip_candidate(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size == 0


def _source_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return suffix or "unknown"


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(path: Path, workspace: str, relative_raw_path: str | None = None) -> dict:
    stat = path.stat()
    relative = relative_raw_path or _relative_workspace_path(path, workspace)
    return {
        "path": relative,
        "source_key": "/".join(_manifest_source_key(relative)),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "sha256": _source_sha256(path),
        "type": _source_type(path),
    }


def _active_state_sources(state: dict) -> dict:
    active = {}
    for key, cached in (state.get("sources") or {}).items():
        if not isinstance(cached, dict):
            continue
        if str(cached.get("status") or "active") in {"stale", "deleted"}:
            continue
        active[key] = cached
    return active


def load_ingest_state(workspace=".") -> dict:
    payload = load_json(ingest_state_path(workspace), {"version": 1, "sources": {}, "last_run": None})
    if not isinstance(payload, dict):
        payload = {}
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        sources = {}
    return {
        "version": int(payload.get("version") or 1),
        "sources": sources,
        "last_run": payload.get("last_run") if isinstance(payload.get("last_run"), dict) else None,
    }


def _source_aliases(cached: dict, current_path: str | None = None) -> list[str]:
    aliases: list[str] = []
    for value in cached.get("aliases") or []:
        if isinstance(value, str) and value and value not in aliases:
            aliases.append(value)
    renamed_from = str(cached.get("renamed_from") or "")
    if renamed_from and renamed_from not in aliases:
        aliases.append(renamed_from)
    path = str(current_path or cached.get("path") or cached.get("source") or cached.get("raw") or "")
    if path and path not in aliases:
        aliases.append(path)
    return aliases


def _source_lineage(cached: dict, old_path: str, new_path: str, now: str | None = None) -> list[dict]:
    lineage = [row for row in (cached.get("lineage") or []) if isinstance(row, dict)]
    if not lineage:
        previous = str(cached.get("renamed_from") or "")
        current = str(cached.get("path") or cached.get("source") or cached.get("raw") or "")
        if previous and current and previous != current:
            lineage.append({"from": previous, "to": current})
    if old_path and new_path and old_path != new_path:
        hop = {"from": old_path, "to": new_path}
        if now:
            hop["at"] = now
        if not any(row.get("from") == old_path and row.get("to") == new_path for row in lineage):
            lineage.append(hop)
    return lineage


def _is_unchanged_source(state: dict, fingerprint: dict) -> bool:
    cached = _active_state_sources(state).get(fingerprint["source_key"])
    if not isinstance(cached, dict):
        return False
    return (
        int(cached.get("size") or -1) == fingerprint["size"]
        and str(cached.get("sha256") or "") == fingerprint["sha256"]
    )


def _same_content_signature(row: dict) -> tuple[int, str, str]:
    return (int(row.get("size") or -1), str(row.get("sha256") or ""), str(row.get("type") or ""))


def _detect_renamed_source(active_sources: dict, fingerprint: dict, present_source_keys: set[str]) -> tuple[str, dict] | None:
    signature = _same_content_signature(fingerprint)
    matches = [
        (key, cached)
        for key, cached in active_sources.items()
        if key not in present_source_keys and _same_content_signature(cached) == signature
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _path_in_ingest_scope(relative_path: str, relative_target: str, target_is_dir: bool) -> bool:
    if not target_is_dir:
        return str(relative_path or "") == str(relative_target or "")
    prefix = str(relative_target or "").replace("\\", "/").rstrip("/")
    if not prefix or prefix == ".":
        return True
    relative = str(relative_path or "").replace("\\", "/")
    return relative == prefix or relative.startswith(prefix + "/")


def _read_manifest_rows(path: Path) -> list[dict | str]:
    rows: list[dict | str] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append(line)
    return rows


def _write_manifest_rows(path: Path, rows: list[dict | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = []
    for row in rows:
        if isinstance(row, dict):
            serialized.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
        else:
            serialized.append(str(row))
    path.write_text("\n".join(serialized) + ("\n" if serialized else ""), encoding="utf-8")


def mark_manifest_sources_stale(workspace: str, deleted_sources: list[dict]) -> None:
    if not deleted_sources:
        return
    path = manifest_path(workspace)
    deleted_by_source = {str(row.get("path") or ""): row for row in deleted_sources}
    deleted_by_id = {str(row.get("source_id") or ""): row for row in deleted_sources if row.get("source_id")}
    rows = _read_manifest_rows(path)
    changed = False
    now = now_iso()
    updated = []
    for row in rows:
        if not isinstance(row, dict):
            updated.append(row)
            continue
        source = str(row.get("source") or "")
        source_id = str(row.get("id") or "")
        deleted = deleted_by_source.get(source) or deleted_by_id.get(source_id)
        if deleted:
            row = dict(row)
            row.setdefault("previous_status", row.get("status", "processed"))
            row["status"] = "stale"
            row["stale_reason"] = "source_removed"
            row["stale_at"] = now
            changed = True
        updated.append(row)
    if changed:
        _write_manifest_rows(path, updated)


def update_manifest_source_rename(workspace: str, old_source: str, new_source: str, source_id: str | None = None) -> None:
    path = manifest_path(workspace)
    rows = _read_manifest_rows(path)
    changed = False
    now = now_iso()
    updated = []
    for row in rows:
        if not isinstance(row, dict):
            updated.append(row)
            continue
        if row.get("source") == old_source or (source_id and row.get("id") == source_id):
            row = dict(row)
            aliases = _source_aliases(row, old_source)
            if new_source not in aliases:
                aliases.append(new_source)
            row["source"] = new_source
            row["status"] = "processed"
            row["renamed_from"] = old_source
            row["aliases"] = aliases
            row["lineage"] = _source_lineage(row, old_source, new_source, now)
            row["renamed_at"] = now
            changed = True
        updated.append(row)
    if changed:
        _write_manifest_rows(path, updated)


def update_ingest_queue_source_rename(workspace: str, old_source: str, new_source: str, source_id: str | None = None) -> None:
    path = ingest_queue_path(workspace)
    payload = load_json(path, {"items": [], "updated_at": now_iso()})
    changed = False
    items = []
    for row in payload.get("items", []):
        if not isinstance(row, dict):
            items.append(row)
            continue
        if row.get("raw") == old_source or (source_id and row.get("id") == source_id):
            row = dict(row)
            aliases = _source_aliases(row, old_source)
            if new_source not in aliases:
                aliases.append(new_source)
            row["raw"] = new_source
            row["renamed_from"] = old_source
            row["aliases"] = aliases
            row["lineage"] = _source_lineage(row, old_source, new_source)
            changed = True
        items.append(row)
    if changed:
        payload["items"] = items
        payload["updated_at"] = now_iso()
        save_json(path, payload)


def mark_ingest_queue_sources_stale(workspace: str, deleted_sources: list[dict]) -> None:
    if not deleted_sources:
        return
    path = ingest_queue_path(workspace)
    payload = load_json(path, {"items": [], "updated_at": now_iso()})
    deleted_by_source = {str(row.get("path") or ""): row for row in deleted_sources}
    deleted_by_id = {str(row.get("source_id") or ""): row for row in deleted_sources if row.get("source_id")}
    changed = False
    items = []
    for row in payload.get("items", []):
        if not isinstance(row, dict):
            items.append(row)
            continue
        deleted = deleted_by_source.get(str(row.get("raw") or "")) or deleted_by_id.get(str(row.get("id") or ""))
        if deleted:
            row = dict(row)
            row["status"] = "stale_source_removed"
            row["review_reason"] = "source_removed"
            changed = True
        items.append(row)
    if changed:
        payload["items"] = items
        payload["updated_at"] = now_iso()
        save_json(path, payload)


def save_ingest_state(
    workspace: str,
    state: dict,
    result: dict,
    successful: list[tuple[dict, dict]],
    renamed_sources: list[dict] | None = None,
    deleted_sources: list[dict] | None = None,
    unchanged_fingerprints: list[dict] | None = None,
) -> None:
    sources = dict(state.get("sources") or {})
    now = now_iso()
    for fingerprint in unchanged_fingerprints or []:
        existing = dict(sources.get(fingerprint["source_key"]) or {})
        existing.update(fingerprint)
        existing["status"] = "active"
        existing["updated_at"] = existing.get("updated_at") or now
        sources[fingerprint["source_key"]] = existing
    for row in renamed_sources or []:
        old_key = row.get("old_source_key")
        new_key = row.get("new_source_key")
        if old_key:
            sources.pop(old_key, None)
        cached = dict(row.get("cached") or {})
        old_path = str(row.get("old_path") or "")
        new_path = str(row.get("new_path") or "")
        aliases = _source_aliases(cached, old_path)
        if new_path and new_path not in aliases:
            aliases.append(new_path)
        cached.update(row.get("fingerprint") or {})
        cached["status"] = "active"
        cached["renamed_from"] = old_path
        cached["aliases"] = aliases
        cached["lineage"] = _source_lineage(cached, old_path, new_path, now)
        cached["renamed_at"] = now
        if new_key:
            sources[new_key] = cached
    for row in deleted_sources or []:
        key = row.get("source_key")
        cached = dict(row.get("cached") or sources.get(key) or {})
        cached["status"] = "stale"
        cached["stale_reason"] = "source_removed"
        cached["deleted_at"] = now
        if key:
            sources[key] = cached
    for fingerprint, item in successful:
        cached = dict(item.get("source_identity") or {})
        cached.update(fingerprint)
        cached.update(
            {
                "status": "active",
                "draft_file": item.get("draft_file"),
                "source_id": item.get("source_id"),
                "format": item.get("format"),
                "queue_status": item.get("queue_status"),
                "updated_at": now,
            }
        )
        sources[fingerprint["source_key"]] = cached
    payload = {
        "version": 1,
        "sources": sources,
        "last_run": {
            "timestamp": now,
            "duration_seconds": result.get("duration_seconds"),
            "scanned_count": result.get("scanned_count", 0),
            "changed_count": result.get("changed_count", 0),
            "renamed_count": result.get("renamed_count", 0),
            "deleted_count": result.get("deleted_count", 0),
            "reprocessed_count": result.get("reprocessed_count", 0),
            "skipped_unchanged_count": result.get("skipped_unchanged_count", 0),
            "skipped_count": result.get("skipped_count", 0),
            "supported_source_counts": result.get("supported_source_counts", {}),
        },
    }
    save_json(ingest_state_path(workspace), payload)


def discover_ingest_files(raw_target_path, workspace: str) -> tuple[list[Path], list[dict]]:
    target = Path(raw_target_path)
    if not target.is_dir():
        return list_supported_raw_files(target), []

    files = []
    skipped = []
    for candidate in sorted(target.rglob("*")):
        if not candidate.is_file():
            continue
        suffix = candidate.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            skipped.append(_skip_record(candidate, workspace, "skipped_unsupported_extension"))
            continue
        if _is_empty_skip_candidate(candidate):
            skipped.append(_skip_record(candidate, workspace, "skipped_empty"))
            continue
        files.append(candidate)
    if not files and not skipped:
        return [], []
    return _merge_source_siblings(files), skipped


def _source_group_key(path: Path) -> tuple[str, str]:
    relative = str(path).replace("\\", "/").lower()
    parent = str(path.parent).replace("\\", "/").lower()
    name = path.name.lower()
    if name.endswith(".pdf") or name.endswith(".pdf.txt") or name.endswith(".pdf.md"):
        return parent, normalized_source_stem(relative)
    return parent, name


def _source_group_rank(path: Path) -> tuple[int, str]:
    name = path.name.lower()
    if name.endswith(".pdf"):
        return 0, name
    if name.endswith(".pdf.txt") or name.endswith(".pdf.md"):
        return 1, name
    return 2, name


def _merge_source_siblings(files: list[Path]) -> list[Path]:
    grouped: dict[tuple[str, str], list[Path]] = {}
    for path in files:
        grouped.setdefault(_source_group_key(path), []).append(path)

    merged = []
    for siblings in grouped.values():
        merged.append(sorted(siblings, key=_source_group_rank)[0])
    return sorted(merged)


def ingest_single_file(raw_path, relative_raw_path, workspace, source_identity: dict | None = None):
    ingest_mode = _resolve_ingest_mode(workspace)
    extracted = _extract_multimodal_content(raw_path, workspace=workspace, ingest_mode=ingest_mode)
    enriched = _provider_semantic_enrichment(workspace, relative_raw_path, extracted, ingest_mode)
    extracted["content"] = _clean_content_for_draft(extracted.get("content", ""))
    content = _clean_content_for_draft(str(enriched["content"]))
    enriched["content"] = content

    source_identity = source_identity or {}
    source_id = source_identity.get("source_id") or deterministic_id(relative_raw_path, content)
    semantic = build_semantic_extraction(content, relative_raw_path, extracted["format"])
    summary = semantic["business_summary"]
    concepts = semantic["key_topics"][:MAX_KEY_CONCEPTS]
    possible_queries = build_possible_queries(concepts, relative_raw_path)
    confidence = _clamp(float(enriched["confidence"]))
    provider = enriched["provider"]

    conflicts = detect_conflicts(relative_raw_path, content, workspace)
    conflict_reports = write_conflict_reports(conflicts, workspace) if conflicts else []

    perception = _build_perception_report(extracted, enriched, confidence)
    promotion_status, review_reason = _review_decision(extracted["format"], confidence, conflict_reports)
    queue_status = promotion_status

    append_manifest_entry(
        workspace,
        source_id,
        relative_raw_path,
        format_name=extracted["format"],
        confidence=confidence,
        ingest_mode=ingest_mode,
        perception=perception,
        queue_status=queue_status,
        review_reason=review_reason,
        source_identity=source_identity,
    )
    draft_file = write_draft(
        workspace,
        relative_raw_path,
        summary,
        concepts,
        possible_queries,
        source_id,
        ingest_mode=ingest_mode,
        confidence=confidence,
        provenance=extracted.get("provenance", []),
        provider=provider,
        promotion_status=promotion_status,
        perception=perception,
        review_reason=review_reason,
        semantic=semantic,
        source_excerpt=content,
        draft_file=source_identity.get("draft_file"),
    )
    update_ingest_queue(
        workspace,
        source_id,
        relative_raw_path,
        draft_file,
        queue_status=queue_status,
        confidence=confidence,
        perception=perception,
        review_reason=review_reason,
    )
    return {
        "status": "draft_created",
        "raw_file": relative_raw_path,
        "draft_file": draft_file,
        "queue_status": queue_status,
        "confidence": round(confidence, 4),
        "ingest_mode": ingest_mode,
        "format": extracted["format"],
        "provenance_count": len(extracted.get("provenance", [])),
        "provider": provider,
        "promotion_status": promotion_status,
        "review_reason": review_reason,
        "perception": perception,
        "conflict_count": len(conflict_reports),
        "conflict_reports": conflict_reports,
        "source_id": source_id,
        "source_identity": source_identity,
    }


def run(task: str, workspace: str) -> dict:
    started = datetime.now(timezone.utc)
    workspace = str(workspace or ".")
    relative_target, target_path = extract_ingest_target(task, workspace=workspace)
    raw_files, skipped_files = discover_ingest_files(target_path, workspace)
    discovered_skipped_count = len(skipped_files)
    state = load_ingest_state(workspace)
    changed_files = []
    unchanged_files = []
    renamed_sources = []
    deleted_sources = []
    unchanged_fingerprints = []
    source_identity_by_path: dict[str, dict] = {}
    fingerprints: dict[str, dict] = {}
    supported_source_counts: dict[str, int] = {}
    active_sources = _active_state_sources(state)
    for raw_file in raw_files:
        relative_raw_path = str(raw_file.resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
        fingerprint = _source_fingerprint(raw_file, workspace, relative_raw_path)
        fingerprints[relative_raw_path] = fingerprint
        supported_source_counts[fingerprint["type"]] = supported_source_counts.get(fingerprint["type"], 0) + 1

    present_source_keys = {fingerprint["source_key"] for fingerprint in fingerprints.values()}
    scoped_active_sources = {
        key: cached
        for key, cached in active_sources.items()
        if _path_in_ingest_scope(str(cached.get("path") or ""), relative_target, target_path.is_dir())
    }

    for raw_file in raw_files:
        relative_raw_path = str(raw_file.resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
        fingerprint = fingerprints[relative_raw_path]
        if _is_unchanged_source(state, fingerprint):
            unchanged_files.append(raw_file)
            unchanged_fingerprints.append(fingerprint)
            skipped_files.append(_skip_record(raw_file, workspace, "skipped_unchanged", action="skipped_unchanged"))
        elif fingerprint["source_key"] not in scoped_active_sources:
            renamed = _detect_renamed_source(scoped_active_sources, fingerprint, present_source_keys)
            if renamed:
                old_key, cached = renamed
                old_path = str(cached.get("path") or "")
                source_id = cached.get("source_id")
                renamed_sources.append(
                    {
                        "old_source_key": old_key,
                        "new_source_key": fingerprint["source_key"],
                        "old_path": old_path,
                        "new_path": relative_raw_path,
                        "source_id": source_id,
                        "draft_file": cached.get("draft_file"),
                        "cached": cached,
                        "fingerprint": fingerprint,
                    }
                )
                unchanged_files.append(raw_file)
                skipped_files.append(
                    {
                        **_skip_record(raw_file, workspace, "skipped_renamed_unchanged", action="renamed"),
                        "from": old_path,
                        "source_id": source_id,
                    }
                )
                update_manifest_source_rename(workspace, old_path, relative_raw_path, source_id)
                update_ingest_queue_source_rename(workspace, old_path, relative_raw_path, source_id)
            else:
                changed_files.append(raw_file)
        else:
            cached = scoped_active_sources.get(fingerprint["source_key"])
            if isinstance(cached, dict):
                source_identity_by_path[relative_raw_path] = cached
            changed_files.append(raw_file)

    for source_key, cached in scoped_active_sources.items():
        if not target_path.is_dir():
            continue
        if source_key in present_source_keys:
            continue
        if any(row.get("old_source_key") == source_key for row in renamed_sources):
            continue
        deleted_sources.append(
            {
                "source_key": source_key,
                "path": cached.get("path"),
                "source_id": cached.get("source_id"),
                "draft_file": cached.get("draft_file"),
                "cached": cached,
            }
        )
    mark_manifest_sources_stale(workspace, deleted_sources)
    mark_ingest_queue_sources_stale(workspace, deleted_sources)

    items = []
    successful = []
    for raw_file in changed_files:
        relative_raw_path = str(raw_file.resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
        try:
            item = ingest_single_file(
                raw_file,
                relative_raw_path,
                workspace,
                source_identity=source_identity_by_path.get(relative_raw_path),
            )
            items.append(item)
            successful.append((fingerprints[relative_raw_path], item))
        except Exception as exc:  # noqa: BLE001 - directory ingest should report bad files and continue.
            if target_path.is_dir():
                skipped_files.append(_skip_record(raw_file, workspace, "skipped_parse_error", message=str(exc)))
                continue
            raise

    if not items:
        result = {
            "status": "no_drafts_created",
            "target": relative_target,
            "target_type": "directory" if target_path.is_dir() else "file",
            "ingested_count": 0,
            "ingested_files": [],
            "draft_files": [],
            "conflict_count": 0,
            "conflict_reports": [],
            "skipped_count": len(skipped_files),
            "scanned_count": len(raw_files) + discovered_skipped_count,
            "changed_count": len(changed_files),
            "renamed_count": len(renamed_sources),
            "deleted_count": len(deleted_sources),
            "reprocessed_count": len(items),
            "skipped_unchanged_count": len(unchanged_files),
            "supported_source_counts": supported_source_counts,
            "skipped_files": skipped_files,
            "renamed_sources": [
                {"from": row.get("old_path"), "to": row.get("new_path"), "source_id": row.get("source_id"), "draft_file": row.get("draft_file")}
                for row in renamed_sources
            ],
            "deleted_sources": [
                {"source": row.get("path"), "source_id": row.get("source_id"), "draft_file": row.get("draft_file")}
                for row in deleted_sources
            ],
            "items": [],
        }
        result["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 4)
        save_ingest_state(workspace, state, result, successful, renamed_sources, deleted_sources, unchanged_fingerprints)
        append_jsonl(
            ingest_runs_path(workspace),
            {
                "timestamp": now_iso(),
                "task": str(task or ""),
                "result": result,
                "source_id": None,
            },
        )
        return result

    first = items[0]
    result = {
        "status": "draft_created" if len(items) == 1 else "drafts_created",
        "raw_file": first["raw_file"],
        "draft_file": first["draft_file"],
        "queue_status": first["queue_status"],
        "confidence": first["confidence"],
        "ingest_mode": first["ingest_mode"],
        "format": first["format"],
        "provenance_count": first["provenance_count"],
        "provider": first["provider"],
        "promotion_status": first["promotion_status"],
        "review_reason": first["review_reason"],
        "perception": first["perception"],
        "conflict_count": sum(item["conflict_count"] for item in items),
        "conflict_reports": [report for item in items for report in item.get("conflict_reports", [])],
        "ingested_count": len(items),
        "ingested_files": [item["raw_file"] for item in items],
        "draft_files": [item["draft_file"] for item in items],
        "skipped_count": len(skipped_files),
        "scanned_count": len(raw_files) + discovered_skipped_count,
        "changed_count": len(changed_files),
        "renamed_count": len(renamed_sources),
        "deleted_count": len(deleted_sources),
        "reprocessed_count": len(items),
        "skipped_unchanged_count": len(unchanged_files),
        "supported_source_counts": supported_source_counts,
        "skipped_files": skipped_files,
        "renamed_sources": [
            {"from": row.get("old_path"), "to": row.get("new_path"), "source_id": row.get("source_id"), "draft_file": row.get("draft_file")}
            for row in renamed_sources
        ],
        "deleted_sources": [
            {"source": row.get("path"), "source_id": row.get("source_id"), "draft_file": row.get("draft_file")}
            for row in deleted_sources
        ],
        "target": relative_target,
        "target_type": "directory" if target_path.is_dir() else "file",
        "items": items,
    }
    result["duration_seconds"] = round((datetime.now(timezone.utc) - started).total_seconds(), 4)
    save_ingest_state(workspace, state, result, successful, renamed_sources, deleted_sources, unchanged_fingerprints)
    append_jsonl(
        ingest_runs_path(workspace),
        {
            "timestamp": now_iso(),
            "task": str(task or ""),
            "result": result,
            "source_id": first["source_id"],
        },
    )
    return result
