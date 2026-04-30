import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any

from .apply import run_apply
from .inspect import SUPPORTED_EXTENSIONS

# Domain-specific keywords for purpose detection and ambiguity guardrails
NOVEL_KEYWORDS = [r"truyện", r"novel", r"chapter", r"chương", r"nhân vật", r"tác giả", r"tieu thuyet", r"tiểu thuyết", r"đọc truyện", r"nam chính", r"nữ chính"]
INDUSTRIAL_KEYWORDS = [r"agv", r"mom", r"wms", r"manufacturing", r"industry", r"industrial", r"warehouse", r"logistics", r"automation", r"specification", r"technical"]

# Specific tokens that strongly identify a domain (must match at least one for confident routing)
DOMAIN_SPECIFIC_INDUSTRIAL = {"agv", "wms", "mom", "warehouse", "manufacturing", "production", "logistics", "plc", "sensor", "actuator", "automation"}
DOMAIN_SPECIFIC_NOVEL = {"chương", "chuong", "truyện", "truyen", "nhân vật", "nhan vat", "tiểu thuyết", "tieu thuyet", "sinh tồn", "novel", "chapter"}

# Generic terms that should not trigger confident routing alone
GENERIC_ROUTING_TERMS = {
    "hệ thống", "he thong", "system", "platform", "project", 
    "tài liệu", "information", "dữ liệu", "data", "quy trình", "process",
    "là gì", "là ai", "ở đâu", "khi nào", "làm sao", "tại sao"
}

STALE_DRAFT_DAYS = 14
DUPLICATE_FILENAME_THRESHOLD = 2
LOW_WIKI_COVERAGE_RATIO = 0.25
OVERSIZED_FOLDER_FILE_COUNT = 500
OVERSIZED_FOLDER_BYTES = 100 * 1024 * 1024
AUTO_FIXES = {
    "stale_drafts": {
        "apply_action": "cleanup-drafts",
        "recommended_action": "Preview then archive drafts through the existing cleanup-drafts apply action.",
        "can_auto_fix": True,
        "risk_level": "low",
        "estimated_impact": "Archives draft files into .brain/actions so they stop cluttering retrieval while remaining rollbackable.",
    },
    "low_wiki_coverage": {
        "apply_action": "rebuild-wiki",
        "recommended_action": "Preview then generate a safe wiki source index from raw filenames.",
        "can_auto_fix": True,
        "risk_level": "medium",
        "estimated_impact": "Adds or updates wiki/_abw_source_index.md with a backed-up previous copy when one exists.",
    },
    "oversized_folder": {
        "apply_action": "archive-stale",
        "recommended_action": "Preview stale processed-file archival if the oversized folder is processed; otherwise split manually.",
        "can_auto_fix": True,
        "risk_level": "medium",
        "estimated_impact": "Archives stale processed files through .brain/actions; does not delete source material.",
    },
}
MANUAL_REMEDIATION = {
    "duplicate_docs": {
        "recommended_action": "Review duplicate groups and rename or document canonical sources manually.",
        "can_auto_fix": False,
        "risk_level": "medium",
        "estimated_impact": "Manual disambiguation improves source trust without risking accidental merges.",
    },
    "unsupported_raw_formats": {
        "recommended_action": "Convert unsupported raw files into supported text, PDF, CSV, XLSX, HTML, JSON, or Markdown.",
        "can_auto_fix": False,
        "risk_level": "low",
        "estimated_impact": "Conversion makes sources searchable without changing original unsupported files.",
    },
}


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _files_under(root: Path, names: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for name in names:
        base = root / name
        if not base.exists():
            continue
        files.extend(path for path in base.rglob("*") if path.is_file())
    return files


def _issue(issue_type: str, severity: str, count: int, recommendation: str, **extra: Any) -> dict[str, Any]:
    remediation = AUTO_FIXES.get(issue_type) or MANUAL_REMEDIATION.get(
        issue_type,
        {
            "recommended_action": recommendation,
            "can_auto_fix": False,
            "risk_level": severity,
            "estimated_impact": "Manual review required.",
        },
    )
    issue = {
        "type": issue_type,
        "severity": severity,
        "count": count,
        "recommendation": recommendation,
        "recommended_action": remediation["recommended_action"],
        "can_auto_fix": remediation["can_auto_fix"],
        "risk_level": remediation["risk_level"],
        "estimated_impact": remediation["estimated_impact"],
    }
    issue.update(extra)
    return issue


def _stale_draft_issue(root: Path, now: float) -> dict[str, Any] | None:
    drafts = root / "drafts"
    if not drafts.exists():
        return None
    stale_paths = []
    cutoff_seconds = STALE_DRAFT_DAYS * 24 * 60 * 60
    for path in drafts.rglob("*.md"):
        if path.is_file() and now - path.stat().st_mtime > cutoff_seconds:
            stale_paths.append(_relative(path, root))
    if not stale_paths:
        return None
    return _issue(
        "stale_drafts",
        "medium" if len(stale_paths) < 25 else "high",
        len(stale_paths),
        "Review, archive, or approve old drafts so retrieval does not rank outdated intermediate notes.",
        sample_paths=stale_paths[:10],
        threshold_days=STALE_DRAFT_DAYS,
    )


def _duplicate_filename_issue(root: Path, files: list[Path]) -> dict[str, Any] | None:
    by_name: dict[str, list[str]] = defaultdict(list)
    for path in files:
        by_name[path.name.lower()].append(_relative(path, root))
    duplicates = {name: paths for name, paths in by_name.items() if len(paths) >= DUPLICATE_FILENAME_THRESHOLD}
    if not duplicates:
        return None
    duplicate_count = sum(len(paths) for paths in duplicates.values())
    return _issue(
        "duplicate_docs",
        "medium",
        duplicate_count,
        "Disambiguate duplicate filenames with clearer folder names or canonical wiki index notes.",
        duplicate_groups={name: paths[:5] for name, paths in sorted(duplicates.items())[:10]},
    )


def _unsupported_raw_issue(root: Path) -> dict[str, Any] | None:
    raw = root / "raw"
    if not raw.exists():
        return None
    by_ext: dict[str, int] = defaultdict(int)
    sample_paths = []
    for path in raw.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower() or "<no-ext>"
        if ext not in SUPPORTED_EXTENSIONS:
            by_ext[ext] += 1
            if len(sample_paths) < 10:
                sample_paths.append(_relative(path, root))
    total = sum(by_ext.values())
    if not total:
        return None
    return _issue(
        "unsupported_raw_formats",
        "medium" if total < 20 else "high",
        total,
        "Convert unsupported raw sources to markdown, text, PDF, CSV, XLSX, HTML, JSON, or another supported format.",
        by_ext=dict(sorted(by_ext.items())),
        sample_paths=sample_paths,
    )


def _low_wiki_coverage_issue(root: Path, raw_files: list[Path], wiki_files: list[Path]) -> dict[str, Any] | None:
    supported_raw = [path for path in raw_files if path.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not supported_raw:
        return None
    ratio = len(wiki_files) / max(1, len(supported_raw))
    if len(wiki_files) > 0 and ratio >= LOW_WIKI_COVERAGE_RATIO:
        return None
    return _issue(
        "low_wiki_coverage",
        "high" if len(wiki_files) == 0 else "medium",
        len(supported_raw),
        "Create concise wiki notes for the most important raw source topics before relying on search answers.",
        wiki_notes=len(wiki_files),
        supported_raw=len(supported_raw),
        coverage_ratio=round(ratio, 3),
    )


def _oversized_folder_issues(root: Path) -> list[dict[str, Any]]:
    issues = []
    for name in ("raw", "wiki", "drafts", "processed"):
        folder = root / name
        if not folder.exists():
            continue
        file_count = 0
        total_bytes = 0
        for path in folder.rglob("*"):
            if path.is_file():
                file_count += 1
                try:
                    total_bytes += path.stat().st_size
                except OSError:
                    pass
        if file_count >= OVERSIZED_FOLDER_FILE_COUNT or total_bytes >= OVERSIZED_FOLDER_BYTES:
            issues.append(
                _issue(
                    "oversized_folder",
                    "medium",
                    file_count,
                    "Split or archive oversized workspace folders to keep indexing and search responsive.",
                    folder=name,
                    bytes=total_bytes,
                    thresholds={"files": OVERSIZED_FOLDER_FILE_COUNT, "bytes": OVERSIZED_FOLDER_BYTES},
                )
            )
    return issues


def _top_actions(issues: list[dict[str, Any]]) -> list[str]:
    actions = []
    for issue in issues:
        recommendation = str(issue.get("recommendation") or "").strip()
        if recommendation and recommendation not in actions:
            actions.append(recommendation)
        if len(actions) >= 5:
            break
    return actions


def normalize_text(text: str) -> list[str]:
    text = text.lower()
    # Basic Vietnamese/English cleaning - preserving Unicode word characters
    # \w in Python 3 regex is Unicode-aware by default.
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    stopwords = {
        "và", "với", "cho", "của", "là", "có", "được", "trong", "đã", "đang", "sẽ", "cũng", "này",
        "gì", "nào", "đâu", "đấy", "thế", "vậy", # Added common Vietnamese question words
        "the", "and", "for", "with", "is", "of", "to", "in", "it", "on", "this", "that"
    }
    # Preserve words like 'truyện', 'chương', 'nhân vật' etc. by ensuring \w doesn't strip them
    # and they are not in stopwords.
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def extract_tokens_from_file(path: Path) -> list[str]:
    ext = path.suffix.lower()
    content = ""
    try:
        if ext in {".md", ".txt"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
        elif ext == ".docx":
            with zipfile.ZipFile(path) as z:
                xml_content = z.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                texts = [t.text for t in tree.findall('.//w:t', namespace) if t.text]
                content = ' '.join(texts)
    except Exception:
        pass
    return normalize_text(content + " " + path.name) # Also include filename


def get_workspace_semantic_profile(root: Path, limit_files: int = 100) -> dict[str, int]:
    tokens = []
    
    # 1. Include root markers (README, Path)
    path_str = str(root).replace("\\", "/")
    tokens.extend(normalize_text(path_str))
    
    for name in ["README.md", "README.txt", "SPECS.md", "SPECS ý tưởng.md", "implementation_plan.md"]:
        p = root / name
        if p.exists():
            tokens.extend(extract_tokens_from_file(p))

    # 2. Sample files to keep it fast
    for folder_name in ("wiki", "drafts", "raw"):
        folder = root / folder_name
        if not folder.exists():
            continue
        # Also include filenames in the profile
        all_files = list(folder.rglob("*"))
        for f in all_files:
            if f.is_file():
                tokens.extend(normalize_text(f.name))
                
        files = [p for p in all_files if p.is_file() and p.suffix.lower() in {".md", ".txt", ".docx"}]
        # Take a sample if too many
        if len(files) > limit_files:
            import random
            files = random.sample(files, limit_files)
        for f in files:
            tokens.extend(extract_tokens_from_file(f))
    
    counts = Counter(tokens)
    return dict(counts.most_common(200))


def compute_semantic_similarity(query: str, workspace_profile: dict[str, int]) -> float:
    query_tokens = set(normalize_text(query))
    if not query_tokens:
        return 0.0
    
    workspace_tokens = set(workspace_profile.keys())
    intersection = query_tokens.intersection(workspace_tokens)
    
    # Overlap ratio relative to query
    return len(intersection) / len(query_tokens)


def _apply_action_for_issue(issue_type: str) -> str:
    remediation = AUTO_FIXES.get(issue_type)
    if not remediation:
        raise ValueError(f"Issue type is not auto-fixable: {issue_type}")
    return str(remediation["apply_action"])



def detect_workspace_purpose(workspace: str | Path = ".", query: str | None = None) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    evidence = []
    novel_markers = []
    industrial_markers = []
    
    # Semantic similarity check
    profile = get_workspace_semantic_profile(root)
    profile_keys = set(profile.keys())
    similarity_score = 0.0
    if query:
        similarity_score = compute_semantic_similarity(query, profile)
        evidence.append(f"Semantic similarity score: {similarity_score:.2f}")

    # 1. Path analysis
    path_str = str(root).lower()
    if any(k in path_str for k in ["mat-the", "web-novel", "novel", "truyen"]):
        novel_markers.append("path")
        evidence.append(f"Workspace path contains novel-related keyword: {path_str}")
    if any(k in path_str for k in ["mom", "wms", "agv", "manufacturing", "industry"]):
        industrial_markers.append("path")
        evidence.append(f"Workspace path contains industrial keyword: {path_str}")

    # 2. File search (README, SPECS, etc)
    for name in ["README.md", "README.txt", "SPECS ý tưởng.md", "implementation_plan tối 26.3.md", "SPECS.md"]:
        path = root / name
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").lower()
                if any(k in content for k in NOVEL_KEYWORDS):
                    novel_markers.append(f"file_content:{name}")
                    evidence.append(f"Found novel-related terms in {name}")
                if any(k in content for k in INDUSTRIAL_KEYWORDS):
                    # Caution: SPECS might mention "AI Oracle" or "Command Center" which sounds industrial but is novel gamification
                    if "gamification" in content or "hud" in content or "reader" in content:
                        novel_markers.append(f"file_content_gamification:{name}")
                        evidence.append(f"Found industrial terms in {name} but with gamification context")
                    else:
                        industrial_markers.append(f"file_content:{name}")
                        evidence.append(f"Found industrial terms in {name}")
            except Exception:
                pass

    # 3. raw/draft keyword profile
    raw_dir = root / "raw"
    if raw_dir.exists():
        chapter_files = [p for p in raw_dir.glob("*.docx") if re.search(r"Chương|Chapter|Ch\s*|Chương\s*\d+", p.name, re.I)]
        if len(chapter_files) > 10:
            novel_markers.append("raw_chapters")
            evidence.append(f"Detected {len(chapter_files)} novel-style chapter files in raw/")
        
        # Check for technical docs
        tech_docs = [p for p in raw_dir.glob("*") if any(k in p.name.lower() for k in ["manual", "spec", "datasheet", "guide"])]
        if tech_docs:
            industrial_markers.append("raw_tech_docs")
            evidence.append(f"Found potential technical documents: {[p.name for p in tech_docs[:3]]}")

    # 4. Profile markers
    if any(k in profile_keys for k in NOVEL_KEYWORDS):
        novel_markers.append("profile_keywords")
    if any(k in profile_keys for k in INDUSTRIAL_KEYWORDS):
        industrial_markers.append("profile_keywords")

    # Decision logic
    purpose = "unknown"
    confidence = "low"
    
    if len(novel_markers) > len(industrial_markers):
        purpose = "web_novel_platform"
        confidence = "high" if len(novel_markers) > 2 else "medium"
    elif len(industrial_markers) > len(novel_markers):
        purpose = "industrial_documentation"
        confidence = "high" if len(industrial_markers) > 2 else "medium"
    elif len(novel_markers) > 0 and len(industrial_markers) > 0:
        # Balanced markers
        purpose = "balanced"
        confidence = "medium"
        
    return {
        "workspace_purpose": purpose,
        "confidence": confidence,
        "evidence": evidence,
        "novel_markers": novel_markers,
        "industrial_markers": industrial_markers,
        "similarity_score": similarity_score,
        "top_terms": list(profile.keys())[:10]
    }


def run_workspace_fix(workspace: str | Path = ".", issue_type: str = "", *, dry_run: bool = True) -> dict[str, Any]:
    issue_type = str(issue_type or "").strip()
    if not issue_type:
        raise ValueError("issue_type is required")
    action = _apply_action_for_issue(issue_type)
    report = run_apply(workspace, action, yes=not dry_run)
    remediation = AUTO_FIXES[issue_type]
    return {
        "workspace": report["workspace"],
        "issue_type": issue_type,
        "apply_action": action,
        "mode": "dry-run" if dry_run else "apply",
        "dry_run": dry_run,
        "recommended_action": remediation["recommended_action"],
        "risk_level": remediation["risk_level"],
        "estimated_impact": remediation["estimated_impact"],
        "backup_or_archive_first": True,
        "apply_report": report,
    }


def build_workspace_intel_report(workspace: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    raw_files = _files_under(root, ("raw",))
    wiki_files = [path for path in _files_under(root, ("wiki",)) if path.suffix.lower() == ".md"]
    draft_files = [path for path in _files_under(root, ("drafts",)) if path.suffix.lower() == ".md"]
    processed_files = _files_under(root, ("processed",))
    corpus_files = raw_files + wiki_files + draft_files + processed_files
    now = __import__("time").time()

    issues: list[dict[str, Any]] = []
    for issue in (
        _stale_draft_issue(root, now),
        _duplicate_filename_issue(root, corpus_files),
        _unsupported_raw_issue(root),
        _low_wiki_coverage_issue(root, raw_files, wiki_files),
    ):
        if issue:
            issues.append(issue)
    issues.extend(_oversized_folder_issues(root))

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda item: (severity_order.get(str(item.get("severity")), 9), str(item.get("type"))))

    summary = {
        "workspace": str(root),
        "raw_files": len(raw_files),
        "wiki_topics": len(wiki_files),
        "drafts": len(draft_files),
        "processed_files": len(processed_files),
        "issue_count": len(issues),
        "highest_severity": issues[0]["severity"] if issues else "none",
    }
    intel = detect_workspace_purpose(root)
    return {
        "summary": summary, 
        "issues": issues, 
        "top_actions": _top_actions(issues),
        "workspace_purpose": intel["workspace_purpose"],
        "confidence": intel["confidence"],
        "evidence": intel["evidence"],
        "similarity_score": intel.get("similarity_score", 0.0),
        "top_terms": intel.get("top_terms", [])
    }


def render_workspace_intel_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines = [
        "Workspace Intel",
        "-" * 15,
        f"Workspace: {summary.get('workspace', 'unknown')}",
        (
            "Corpus: "
            f"raw={summary.get('raw_files', 0)} "
            f"wiki={summary.get('wiki_topics', 0)} "
            f"drafts={summary.get('drafts', 0)} "
            f"processed={summary.get('processed_files', 0)}"
        ),
        f"Issues: {summary.get('issue_count', 0)} highest={summary.get('highest_severity', 'none')}",
        "",
    ]
    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    if not issues:
        lines.append("No workspace intelligence issues detected.")
    else:
        lines.append("Issues:")
        for issue in issues:
            lines.append(
                f"- {issue.get('type')} [{issue.get('severity')}] "
                f"count={issue.get('count')}: {issue.get('recommendation')}"
            )
    actions = report.get("top_actions") if isinstance(report.get("top_actions"), list) else []
    lines.append("")
    lines.append("Top actions:")
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- None")
    return "\n".join(lines)
