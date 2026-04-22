from pathlib import Path

import abw_review


MAX_REVIEW_ITEMS = 5

DOMAIN_RULES = {
    "database": {
        "keywords": ("table", "column", "schema", "select ", "join ", "sql", "field"),
        "required_missing": {
            "missing_sql": "missing SQL example",
            "missing_columns": "missing column description",
            "missing_example": "missing example",
        },
    },
    "troubleshooting": {
        "keywords": ("error", "timeout", "failed", "exception", "issue", "root cause"),
        "required_missing": {
            "missing_error_example": "missing error example",
            "missing_resolution": "missing resolution step",
            "missing_example": "missing example",
        },
    },
    "process": {
        "keywords": ("step", "workflow", "process", "procedure", "checklist"),
        "required_missing": {
            "missing_steps": "missing step-by-step flow",
            "missing_example": "missing example",
        },
    },
}

KEYWORD_GROUPS = {
    "table": ("table", "schema", "bang"),
    "column": ("column", "field", "cot"),
    "query": ("select ", "from ", "where ", "join ", "query", "sql"),
    "error": ("error", "failed", "exception", "timeout", "loi"),
}


def normalize_text(text):
    return " ".join(str(text or "").lower().split())


def split_lines(text):
    return [line.rstrip() for line in str(text or "").splitlines()]


def extract_headings(lines):
    return [line.strip().lstrip("#").strip() for line in lines if line.strip().startswith("#")]


def extract_bullets(lines):
    bullets = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
    return bullets


def extract_first_paragraph(lines):
    paragraph = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#") or stripped.startswith(("- ", "* ")):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    return " ".join(paragraph).strip()


def detect_key_elements(text):
    lowered = normalize_text(text)
    detected = []
    for label, tokens in KEYWORD_GROUPS.items():
        if any(token in lowered for token in tokens):
            detected.append(label)
    return detected


def detect_domain(text, key_elements):
    lowered = normalize_text(text)
    for domain, config in DOMAIN_RULES.items():
        if any(keyword in lowered for keyword in config["keywords"]):
            return domain
    if "query" in key_elements or "table" in key_elements or "column" in key_elements:
        return "database"
    if "error" in key_elements:
        return "troubleshooting"
    return "general"


def has_example(text):
    lowered = normalize_text(text)
    return any(token in lowered for token in ("example", "vi du", "for example", "e.g.", "sample"))


def has_sql(text):
    lowered = normalize_text(text)
    return any(token in lowered for token in ("select ", "insert ", "update ", "delete ", "sql", "join ", "where "))


def build_key_points(headings, bullets, first_paragraph, key_elements, domain):
    points = [f"Detected domain: {domain}"]
    if headings:
        points.append(f"Headings: {', '.join(headings[:3])}")
    if first_paragraph:
        points.append(f"Opening paragraph: {first_paragraph[:180]}")
    if bullets:
        points.append(f"Bullet highlights: {', '.join(bullets[:3])}")
    if key_elements:
        points.append(f"Detected elements: {', '.join(key_elements)}")
    if len(points) == 1:
        points.append("Draft has very little structured content.")
    return points[:5]


def base_missing_parts(text, headings, bullets):
    lowered = normalize_text(text)
    missing = []
    if len(str(text or "").strip()) < 120 or "no summary could be extracted" in lowered or "none detected" in lowered:
        missing.append("insufficient detail")
    if not has_example(text):
        missing.append("missing example")
    if not headings and not bullets:
        missing.append("missing structure")
    return missing


def apply_domain_missing(domain, text, key_elements, bullets):
    lowered = normalize_text(text)
    missing = []
    if domain == "database":
        if not has_sql(text):
            missing.append("missing SQL example")
        if "table" in key_elements and "column" not in key_elements:
            missing.append("missing column description")
    elif domain == "troubleshooting":
        if "error" not in key_elements:
            missing.append("missing error example")
        if not any(token in lowered for token in ("fix", "workaround", "resolve", "resolution", "khac phuc")):
            missing.append("missing resolution step")
    elif domain == "process":
        if len(bullets) < 2 and "step" not in lowered:
            missing.append("missing step-by-step flow")
    return missing


def detect_missing_parts(text, headings, bullets, domain, key_elements):
    combined = []
    for item in base_missing_parts(text, headings, bullets) + apply_domain_missing(domain, text, key_elements, bullets):
        if item not in combined:
            combined.append(item)
    return combined


def confidence_for(text, headings, bullets, missing):
    lowered = normalize_text(text)
    if any(signal in lowered for signal in ("no summary could be extracted", "none detected")):
        return "low"
    detail_score = len(str(text or "").strip())
    if detail_score >= 300 and headings and bullets and len(missing) <= 1:
        return "high"
    if detail_score >= 120 and (headings or bullets) and len(missing) <= 3:
        return "medium"
    return "low"


def build_suggestions(domain, missing, key_elements):
    suggestions = []
    if "insufficient detail" in missing:
        suggestions.append("Expand the draft with clearer operational details and expected outputs.")
    if "missing example" in missing:
        suggestions.append("Add one concrete example so the reviewer can validate intent quickly.")
    if "missing structure" in missing:
        suggestions.append("Add headings and bullet points so the draft is easier to scan.")
    if "missing SQL example" in missing:
        suggestions.append("Add one SQL example that demonstrates the intended query or data check.")
    if "missing column description" in missing:
        suggestions.append("List the important columns explicitly if this draft describes a table.")
    if "missing error example" in missing:
        suggestions.append("Add one representative error case or failure symptom.")
    if "missing resolution step" in missing:
        suggestions.append("Describe the fix, workaround, or next diagnostic step.")
    if "missing step-by-step flow" in missing:
        suggestions.append("Convert the procedure into a step-by-step checklist.")
    if domain == "database" and "table" in key_elements and "column" in key_elements and not missing:
        suggestions.append("This draft looks reviewable; verify SQL correctness before approval.")
    return suggestions[:5]


def explain_draft(path: str, workspace: str) -> dict:
    workspace = str(workspace or ".")
    draft_relpath = abw_review.extract_draft_reference(path, workspace=workspace)
    if not draft_relpath:
        return {"status": "blocked", "reason": "No valid draft path found."}
    if not draft_relpath.startswith("drafts/"):
        return {"status": "blocked", "reason": "Draft path must be inside drafts/."}

    draft_path = Path(workspace).resolve() / draft_relpath
    if not draft_path.exists() or not draft_path.is_file():
        return {"status": "blocked", "reason": f"Draft file does not exist: {draft_relpath}"}

    _, queue_item = abw_review.validate_queue_entry(workspace, draft_relpath)
    if queue_item is None:
        return {"status": "blocked", "reason": "Draft file is not present in ingest_queue."}

    content = draft_path.read_text(encoding="utf-8-sig")
    lines = split_lines(content)
    headings = extract_headings(lines)
    bullets = extract_bullets(lines)
    first_paragraph = extract_first_paragraph(lines)
    key_elements = detect_key_elements(content)
    domain = detect_domain(content, key_elements)
    key_points = build_key_points(headings, bullets, first_paragraph, key_elements, domain)
    missing = detect_missing_parts(content, headings, bullets, domain, key_elements)
    confidence = confidence_for(content, headings, bullets, missing)
    suggestions = build_suggestions(domain, missing, key_elements)
    summary = "Draft overview:\n" + "\n".join(f"- {point}" for point in key_points)

    return {
        "status": "ok",
        "draft": draft_relpath,
        "summary": summary,
        "key_points": key_points,
        "missing": missing,
        "confidence": confidence,
        "suggestions": suggestions,
        "key_elements": key_elements,
        "domain": domain,
    }


def batch_suggestion_for(explain_result):
    if explain_result.get("status") != "ok":
        return "review"
    if explain_result.get("confidence") == "high" and not explain_result.get("missing"):
        return "approve"
    if explain_result.get("confidence") == "low" or "insufficient detail" in explain_result.get("missing", []):
        return "improve"
    return "review"


def review_drafts(workspace):
    listing = abw_review.list_drafts(workspace)
    pending = listing.get("pending_drafts", [])[:MAX_REVIEW_ITEMS]
    items = []
    for item in pending:
        draft = item.get("draft")
        if not draft:
            continue
        explained = explain_draft(draft, workspace)
        if explained.get("status") != "ok":
            items.append(
                {
                    "draft": draft,
                    "summary": explained.get("reason", "Draft explanation failed."),
                    "missing": [],
                    "confidence": "low",
                    "suggestion": "review",
                }
            )
            continue
        items.append(
            {
                "draft": explained["draft"],
                "summary": explained["summary"],
                "missing": explained["missing"],
                "confidence": explained["confidence"],
                "suggestion": batch_suggestion_for(explained),
            }
        )
    return {"items": items}
