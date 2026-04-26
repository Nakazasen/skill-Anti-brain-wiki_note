import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from abw.conflicts import detect_conflicts, write_conflict_reports
from abw.providers import execute_provider_chain
from abw.workspace import read_workspace_config


MAX_SUMMARY_CHARS = 500
MAX_KEY_CONCEPTS = 5
MAX_QUERY_SUGGESTIONS = 5
TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".adoc"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | {".xlsx", ".pdf", ".pptx"}
ENTERPRISE_PERCEPTION_EXTENSIONS = IMAGE_EXTENSIONS | {".xlsx", ".pdf", ".pptx"}
LOW_CONFIDENCE_REVIEW_THRESHOLD = 0.45
AUTO_PROMOTE_THRESHOLD = 0.8
LOCAL_OCR_PROVIDERS = ("paddleocr", "tesseract", "binary_text_probe")
VISION_PROVIDERS = ("openai_vision", "claude_vision", "gemini_vision")
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


def supported_perception_providers() -> dict:
    return {
        "local_ocr": list(LOCAL_OCR_PROVIDERS),
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
        marker_words = [word for word in words if word.lower().strip("_-") in OCR_METADATA_MARKERS]
        if words and len(marker_words) / max(1, len(words)) >= 0.8:
            continue
        if len(text) > 180 and len(set(text)) < 12:
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
    decoded = data.decode("latin-1", errors="ignore")
    pattern = rf"[A-Za-z0-9][A-Za-z0-9 _.,:;#%()/\\+\-=]{{{min_len - 1},}}"
    candidates = re.findall(pattern, decoded)
    cleaned = [item.strip(" \t\r\n\x00") for item in candidates]
    return _clean_extracted_lines(cleaned, limit=80)


def _text_quality(text_lines: list[str]) -> dict:
    text = " ".join(text_lines)
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    lowered = [word.lower().strip("_-") for word in words]
    non_metadata = [word for word in lowered if word not in OCR_METADATA_MARKERS]
    if not text or not words:
        return {
            "alpha_ratio": 0.0,
            "readable_token_score": 0.0,
            "language_token_score": 0.0,
            "metadata_only": True,
            "usable": False,
        }

    alpha_chars = len(re.findall(r"[A-Za-z]", text))
    alpha_ratio = alpha_chars / max(1, len(text))
    good_tokens = [
        word
        for word in non_metadata
        if len(word) >= 3
        and not re.search(r"([A-Za-z0-9])\1{3,}", word)
        and (re.search(r"[aeiou]", word) or word in LANGUAGE_HINT_TOKENS)
    ]
    language_hits = [word for word in good_tokens if word in LANGUAGE_HINT_TOKENS or re.search(r"[aeiou].*[aeiou]", word)]
    readable_token_score = len(good_tokens) / max(1, len(words))
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
    if not shutil.which("tesseract"):
        return [], {"provider": "tesseract", "status": "unavailable", "reason": "tesseract executable not found"}
    try:
        completed = subprocess.run(
            ["tesseract", str(path), "stdout", "--psm", "6"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return [], {"provider": "tesseract", "status": "failed", "reason": str(exc)}
    if completed.returncode != 0:
        return [], {"provider": "tesseract", "status": "failed", "reason": completed.stderr.strip()[:200]}
    lines = _dedupe_text([line for line in completed.stdout.splitlines() if line.strip()])
    return lines, {"provider": "tesseract", "status": "success" if lines else "empty", "tokens": len(lines)}


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


def _ocr_noise_score(text_lines: list[str]) -> float:
    text = " ".join(text_lines)
    if not text:
        return 1.0
    chars = len(text)
    alpha_num = len(re.findall(r"[A-Za-z0-9]", text))
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
    text_lines = []
    paddle_lines, paddle_status = _run_paddleocr(path)
    attempts.append(paddle_status)
    text_lines.extend(paddle_lines)
    if not text_lines:
        tess_lines, tess_status = _run_tesseract(path)
        attempts.append(tess_status)
        text_lines.extend(tess_lines)
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

    real_ocr_success = any(row.get("status") == "success" and row.get("provider") != "binary_text_probe" for row in attempts)
    text_lines = _dedupe_text(text_lines if real_ocr_success else [])
    quality = _text_quality(text_lines)
    noisy = _ocr_noise_score(text_lines)
    if not real_ocr_success or not quality["usable"]:
        confidence = 0.08
    else:
        confidence = _calibrate_confidence(
            base=0.28,
            text_lines=text_lines,
            structured=False,
            noisy=noisy,
            provider_success=True,
            method="real_ocr",
        )
    return {
        "text_lines": text_lines,
        "metadata_lines": _filter_metadata_markers(probe_lines),
        "attempts": attempts,
        "confidence": confidence,
        "noise": noisy,
        "real_ocr_success": real_ocr_success and quality["usable"],
        "quality": quality,
        "probe_quality": probe_quality,
    }


def _classify_visual_artifact(text_lines: list[str], *, width: int | None = None, height: int | None = None, image_count: int = 0) -> dict:
    text = "\n".join(text_lines)
    lowered = text.lower()
    table_markers = len(re.findall(r"\b(total|qty|quantity|amount|price|date|id|row|column)\b", lowered))
    ui_markers = len(re.findall(r"\b(ok|cancel|save|submit|login|sign in|menu|settings|search|button|filter|tab)\b", lowered))
    diagram_markers = len(re.findall(r"\b(flow|arrow|step|node|input|output|process|system|module|architecture)\b", lowered))
    label_markers = len(re.findall(r"\b(label|status|error|warning|required|enabled|disabled)\b", lowered))
    button_labels = re.findall(r"\b(OK|Cancel|Save|Submit|Login|Search|Filter|Apply|Next|Back|Close)\b", text)
    pipe_rows = len([line for line in text_lines if "|" in line or "\t" in line])
    numeric_grid_rows = len([line for line in text_lines if len(re.findall(r"\b\d+(?:\.\d+)?\b", line)) >= 2])
    aspect = (width / height) if width and height else None

    return {
        "tables": pipe_rows >= 2 or numeric_grid_rows >= 2 or table_markers >= 3,
        "ui_screenshot": ui_markers >= 2 or (aspect is not None and aspect > 1.2 and ui_markers >= 1),
        "diagrams": diagram_markers >= 2 or (image_count > 0 and diagram_markers >= 1),
        "labels_buttons": label_markers >= 1 or bool(button_labels),
        "button_labels": _dedupe_text(button_labels, limit=20),
        "signals": {
            "table_markers": table_markers,
            "ui_markers": ui_markers,
            "diagram_markers": diagram_markers,
            "label_markers": label_markers,
            "pipe_rows": pipe_rows,
            "numeric_grid_rows": numeric_grid_rows,
        },
    }


def _semantic_summary_for_visual(kind: str, text_lines: list[str], detections: dict) -> str:
    found = [name for name in ("tables", "ui_screenshot", "diagrams", "labels_buttons") if detections.get(name)]
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
            _best_component_confidence(provenance, {"layout", "tables", "ui_screenshot", "diagrams", "labels_buttons", "page_images"}),
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
    match = re.search(r"\b(?:ingest|process|review)\s+([^\s]+)", text, flags=re.IGNORECASE)
    if match:
        tokens.append(match.group(1))
    pattern = r"(?:raw(?:[\\/][A-Za-z0-9_./\\-]+)?)|(?:[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)"
    tokens.extend(re.findall(pattern, text))
    deduped = []
    seen = set()
    for token in tokens:
        cleaned = str(token).strip("`'\"()[]{}<>.,;:")
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

    if not resolved.exists():
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


def deterministic_id(relative_raw_path, content):
    payload = f"{relative_raw_path}\n{content}".encode("utf-8", errors="ignore")
    return "ingest-" + hashlib.sha256(payload).hexdigest()[:16]


def manifest_path(workspace="."):
    return Path(workspace) / "processed" / "manifest.jsonl"


def ingest_queue_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_queue.json"


def ingest_runs_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_runs.jsonl"


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


def summarize_text(content):
    lines = []
    for raw in str(content or "").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        lines.append(stripped)
    summary = " ".join(lines).strip()
    if len(summary) <= MAX_SUMMARY_CHARS:
        return summary
    return summary[: MAX_SUMMARY_CHARS - 3].rstrip() + "..."


def extract_key_concepts(content):
    counts = {}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", str(content or "")):
        lowered = token.lower()
        if lowered in {
            "this",
            "that",
            "with",
            "from",
            "have",
            "there",
            "their",
            "about",
            "into",
            "while",
            "where",
            "which",
        }:
            continue
        counts[lowered] = counts.get(lowered, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    return [item[0] for item in ranked[:MAX_KEY_CONCEPTS]]


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
    stem = Path(relative_raw_path).stem
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


def _extract_xlsx(path: Path) -> dict:
    cells = []
    comments = []
    textboxes = []
    charts = []
    embedded_images = []
    with zipfile.ZipFile(path, "r") as archive:
        for name in archive.namelist():
            lowered = name.lower()
            if lowered.startswith("xl/media/"):
                image_bytes = archive.read(name)
                image_text = _binary_text_probe(image_bytes)
                quality = _text_quality(image_text)
                embedded_images.append({"name": name, "bytes": len(image_bytes), "text": image_text if quality["usable"] else [], "quality": quality, "probe_count": len(image_text)})
                continue
            if not lowered.endswith(".xml"):
                continue
            try:
                xml_text = archive.read(name).decode("utf-8", errors="ignore")
            except KeyError:
                continue
            tokens = _extract_xml_text(xml_text)
            if lowered.startswith("xl/comments"):
                comments.extend(tokens)
            elif lowered.startswith("xl/drawings"):
                textboxes.extend(tokens)
            elif lowered.startswith("xl/charts"):
                charts.extend(tokens)
            elif lowered.startswith("xl/sharedstrings") or lowered.startswith("xl/worksheets"):
                cells.extend(tokens)

    sections = []
    if cells:
        sections.append("Cells:\n" + "\n".join(f"- {item}" for item in cells[:40]))
    if comments:
        sections.append("Comments:\n" + "\n".join(f"- {item}" for item in comments[:20]))
    if textboxes:
        sections.append("Textboxes:\n" + "\n".join(f"- {item}" for item in textboxes[:20]))
    if charts:
        sections.append("Chart Text:\n" + "\n".join(f"- {item}" for item in charts[:20]))
    if embedded_images:
        image_lines = []
        for image in embedded_images[:20]:
            detail = f"- {image['name']} ({image['bytes']} bytes)"
            if image["text"]:
                detail += ": " + "; ".join(image["text"][:6])
            image_lines.append(detail)
        sections.append("Embedded image metadata/text probe:\n" + "\n".join(image_lines))

    content = "\n\n".join(sections) or "No textual worksheet payload extracted from XLSX container."
    image_text_lines = [line for image in embedded_images for line in image["text"]]
    noisy = _ocr_noise_score(image_text_lines)
    structured = bool(cells or textboxes or charts)
    confidence = _calibrate_confidence(
        base=0.52,
        text_lines=cells + comments + textboxes + charts + image_text_lines,
        structured=structured,
        noisy=noisy if image_text_lines else 0.1,
        provider_success=bool(cells or textboxes or charts),
        method="structured_native",
    )
    confidence = _clamp(confidence, 0.0, 0.82)

    return {
        "format": "xlsx",
        "content": content,
        "confidence": confidence,
        "provenance": [
            _provenance("cells", "xlsx_xml_parse", 0.74 if cells else 0.2, f"{len(cells)} cell tokens", ref="xl/sharedStrings.xml|xl/worksheets/*"),
            _provenance("comments", "xlsx_xml_parse", 0.68 if comments else 0.2, f"{len(comments)} comment tokens", ref="xl/comments*.xml"),
            _provenance("textboxes", "xlsx_drawing_parse", 0.66 if textboxes else 0.2, f"{len(textboxes)} drawing tokens", ref="xl/drawings/*.xml"),
            _provenance("charts", "xlsx_chart_parse", 0.64 if charts else 0.2, f"{len(charts)} chart tokens", ref="xl/charts/*.xml"),
            _provenance(
                "embedded_images",
                "xlsx_embedded_image_probe",
                0.32 if image_text_lines else (0.25 if embedded_images else 0.2),
                f"{len(embedded_images)} image assets; {len(image_text_lines)} readable metadata/text tokens; {sum(image.get('probe_count', 0) for image in embedded_images)} binary tokens",
                ref="xl/media/*",
            ),
        ],
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


def _extract_pdf(path: Path) -> dict:
    raw = path.read_bytes()
    decoded = raw.decode("latin-1", errors="ignore")
    page_count = max(1, len(re.findall(r"/Type\s*/Page\b", decoded)) or len(re.findall(r"\bendobj\b", decoded)) // 8)
    image_refs = re.findall(r"/Subtype\s*/Image\b", decoded)
    text_pages, text_status = _extract_pdf_text_layer(path)
    if text_pages:
        text_lines = [line for page in text_pages for line in page["lines"]]
        noisy = _ocr_noise_score(text_lines)
        confidence = _calibrate_confidence(
            base=0.44,
            text_lines=text_lines,
            structured=False,
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
        return {
            "format": "pdf",
            "content": "\n".join(content_parts),
            "confidence": confidence,
            "provenance": [
                _provenance("text", "pdf_text_layer", confidence, f"{len(text_lines)} readable text lines via {text_status.get('backend')}; noise={noisy:.2f}", ref="pdf:/pages/*/text"),
                _provenance("page_images", "pdf_xobject_scan", 0.35 if image_refs else 0.2, f"{len(image_refs)} image XObject candidates", ref="pdf:/pages/*/images"),
                _provenance("layout", "pdf_text_page_blocks", confidence, f"{len(text_pages)} pages with readable text", ref="pdf:/pages/*/blocks"),
            ],
        }

    probe_snippets = _binary_text_probe(raw, min_len=8)
    quality = _text_quality(probe_snippets)
    snippets = probe_snippets if quality["usable"] else []
    layout_blocks = []
    for idx, line in enumerate(snippets[:80], start=1):
        page_ref = min(page_count, ((idx - 1) % page_count) + 1)
        layout_blocks.append({"page": page_ref, "text": line})
    detections = _classify_visual_artifact(snippets, image_count=len(image_refs))
    summary = _semantic_summary_for_visual("PDF scan", snippets, detections)
    content_parts = [
        f"PDF pages detected: {page_count}",
        f"Page image candidates: {len(image_refs)}",
        summary,
    ]
    if layout_blocks:
        content_parts.append("Layout blocks:\n" + "\n".join(f"- page {row['page']}: {row['text']}" for row in layout_blocks[:80]))
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
            _provenance("semantic_summary", "local_visual_classifier", confidence, ", ".join(name for name in ("tables", "ui_screenshot", "diagrams", "labels_buttons") if detections.get(name)) or "visual_artifact", ref="pdf:/summary"),
        ],
    }


def _extract_image(path: Path) -> dict:
    size = path.stat().st_size if path.exists() else 0
    width, height = _image_dimensions(path)
    ocr = _local_ocr_image(path)
    text_lines = ocr["text_lines"]
    detections = _classify_visual_artifact(text_lines, width=width, height=height)
    structured = bool(detections.get("tables"))
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
    dimensions = f"{width}x{height}" if width and height else "unknown dimensions"
    content = "\n".join(
        [
            f"Image artifact detected ({path.name}, {size} bytes, {dimensions}).",
            _semantic_summary_for_visual("Image", text_lines, detections),
            "Detected buttons/labels: " + (", ".join(detections["button_labels"]) if detections["button_labels"] else "none"),
            "OCR text:",
            *([f"- {line}" for line in text_lines[:80]] or ["- none recovered"]),
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
            _provenance("layout", "image_metadata_scan", 0.48 if width and height else 0.28, f"{size} bytes; dimensions={dimensions}", ref=f"image:{path.name}"),
            _provenance("tables", "visual_table_detector", 0.7 if detections["tables"] else 0.25, str(detections["signals"]), ref=f"image:{path.name}#tables"),
            _provenance("ui_screenshot", "visual_ui_detector", 0.7 if detections["ui_screenshot"] else 0.25, str(detections["signals"]), ref=f"image:{path.name}#ui"),
            _provenance("diagrams", "visual_diagram_detector", 0.68 if detections["diagrams"] else 0.25, str(detections["signals"]), ref=f"image:{path.name}#diagram"),
            _provenance("labels_buttons", "visual_label_button_detector", 0.72 if detections["labels_buttons"] else 0.25, str(detections["button_labels"] or detections["signals"]), ref=f"image:{path.name}#labels"),
        ],
    }


def _extract_multimodal_content(raw_path: Path) -> dict:
    suffix = raw_path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return _extract_text_file(raw_path)
    if suffix == ".xlsx":
        return _extract_xlsx(raw_path)
    if suffix == ".pptx":
        return _extract_pptx(raw_path)
    if suffix == ".pdf":
        return _extract_pdf(raw_path)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image(raw_path)
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
):
    relpath = draft_relpath(relative_raw_path)
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
    stage_lines = []
    for row in perception.get("stages") or []:
        stage_lines.append(f"- {row.get('stage')}: confidence={float(row.get('confidence') or 0.0):.2f}")

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
            "",
            "## Summary",
            summary or "No summary could be extracted from the raw file.",
            "",
            "## Key Concepts",
            *([f"- {concept}" for concept in concepts] or ["- none detected"]),
            "",
            "## Provenance",
            *(prov_lines or ["- none"]),
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
            "## Trust Notice",
            "This draft is not trusted wiki knowledge until explicitly approved or promoted by governed workflow.",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return relpath


def append_manifest_entry(workspace, source_id, relative_raw_path, *, format_name, confidence, ingest_mode, perception, queue_status, review_reason):
    path = manifest_path(workspace)
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
    append_jsonl(path, entry)
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
    payload.setdefault("items", []).append(item)
    payload["updated_at"] = now_iso()
    save_json(path, payload)
    return item


def list_supported_raw_files(raw_target_path):
    target = Path(raw_target_path)
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: {target.suffix or '<none>'}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        return [target]
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
    return files


def ingest_single_file(raw_path, relative_raw_path, workspace):
    ingest_mode = _resolve_ingest_mode(workspace)
    extracted = _extract_multimodal_content(raw_path)
    enriched = _provider_semantic_enrichment(workspace, relative_raw_path, extracted, ingest_mode)
    extracted["content"] = _clean_content_for_draft(extracted.get("content", ""))
    content = _clean_content_for_draft(str(enriched["content"]))
    enriched["content"] = content

    source_id = deterministic_id(relative_raw_path, content)
    summary = summarize_text(content)
    concepts = extract_key_concepts(content)
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
    }


def run(task: str, workspace: str) -> dict:
    workspace = str(workspace or ".")
    relative_target, target_path = extract_ingest_target(task, workspace=workspace)
    raw_files = list_supported_raw_files(target_path)
    items = []
    for raw_file in raw_files:
        relative_raw_path = str(raw_file.resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
        items.append(ingest_single_file(raw_file, relative_raw_path, workspace))

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
        "target": relative_target,
        "target_type": "directory" if target_path.is_dir() else "file",
        "items": items,
    }
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
