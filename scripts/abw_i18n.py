import json
from pathlib import Path


SUPPORTED_LANGUAGES = {"en", "vi"}
DEFAULT_LANGUAGE = "en"

TRANSLATIONS = {
    "en": {
        "action.audit_system": "Audit system",
        "action.coverage": "Check knowledge coverage",
        "action.help": "Show help",
        "action.improve_knowledge_base": "Improve knowledge base",
        "action.ingest_more_knowledge": "Ingest more knowledge",
        "action.ingest_raw_file": "Ingest raw file",
        "action.review_drafts": "Review drafts",
        "dashboard.title": "ABW Dashboard",
        "dashboard.version": "Version",
        "dashboard.health": "Health",
        "dashboard.knowledge": "Knowledge",
        "dashboard.bottlenecks": "Bottlenecks",
        "dashboard.none_detected": "none detected",
        "dashboard.top_gaps": "Top gaps",
        "dashboard.none": "none",
        "dashboard.next_actions": "Next actions",
        "help.message": "You can continue from the current state:",
        "help.overview": "Overview",
        "help.next_actions": "Next actions",
        "help.situational_guidance": "Situational guidance",
        "help.minimal_commands": "Minimal commands",
        "help.guidance.no_data": "No knowledge data yet. Add documents to raw/ and run ingest raw/<file>.",
        "help.guidance.pending_drafts": "There are drafts to review before they become trusted wiki notes.",
        "help.guidance.low_coverage": "Coverage is low. Add or normalize more knowledge.",
        "help.guidance.raw_without_wiki": "Raw files exist but trusted wiki notes do not. Create drafts with ingest first.",
        "help.guidance.ready": "The system has basic data. Choose the next useful step.",
        "help.command.add_raw_and_ingest": "add documents to raw/ then run ingest raw/<file>",
        "help.command.ask_direct": "ask directly",
        "language.set.en": "Language set to English.",
        "language.set.vi": "Language set to Vietnamese.",
        "language.unsupported": "Unsupported language. Use: set language en or set language vi.",
        "trust.informational": "informational",
        "trust.checked": "checked",
        "trust.enforced": "enforced",
        "trust.blocked": "blocked",
        "trust.field": "trust",
        "trust.reason_non_structured": "non-structured output",
    },
    "vi": {
        "action.audit_system": "Kiem tra he thong",
        "action.coverage": "Kiem tra do phu tri thuc",
        "action.help": "Xem huong dan",
        "action.improve_knowledge_base": "Cai thien kho tri thuc",
        "action.ingest_more_knowledge": "Nap them tri thuc",
        "action.ingest_raw_file": "Nap tai lieu raw",
        "action.review_drafts": "Duyet ban nhap",
        "dashboard.title": "Bang dieu khien ABW",
        "dashboard.version": "Phien ban",
        "dashboard.health": "Suc khoe he thong",
        "dashboard.knowledge": "Tri thuc",
        "dashboard.bottlenecks": "Diem nghen",
        "dashboard.none_detected": "chua phat hien",
        "dashboard.top_gaps": "Khoang trong lon",
        "dashboard.none": "khong co",
        "dashboard.next_actions": "Buoc tiep theo",
        "help.message": "Ban co the tiep tuc dua tren trang thai hien tai:",
        "help.overview": "Tong quan",
        "help.next_actions": "Buoc tiep theo",
        "help.situational_guidance": "Goi y theo trang thai",
        "help.minimal_commands": "Lenh toi thieu",
        "help.guidance.no_data": "Chua co du lieu tri thuc. Dua tai lieu vao raw/ roi chay ingest raw/<file>.",
        "help.guidance.pending_drafts": "Dang co ban nhap can duyet truoc khi tro thanh wiki dang tin.",
        "help.guidance.low_coverage": "Do phu dang thap. Nen bo sung hoac chuan hoa them tri thuc.",
        "help.guidance.raw_without_wiki": "Da co raw nhung chua co wiki dang tin. Hay tao draft bang ingest truoc.",
        "help.guidance.ready": "He thong da co du lieu co ban. Chon buoc tiep theo phu hop.",
        "help.command.add_raw_and_ingest": "dua tai lieu vao raw/ roi chay ingest raw/<file>",
        "help.command.ask_direct": "hoi truc tiep",
        "language.set.en": "Da chuyen ngon ngu sang tieng Anh.",
        "language.set.vi": "Da chuyen ngon ngu sang tieng Viet.",
        "language.unsupported": "Ngon ngu chua ho tro. Dung: set language en hoac set language vi.",
        "trust.informational": "thong tin",
        "trust.checked": "da kiem tra",
        "trust.enforced": "da rang buoc",
        "trust.blocked": "bi chan",
        "trust.field": "muc_tin_cay",
        "trust.reason_non_structured": "dau ra khong co cau truc",
    },
}

ACTION_KEYS = {
    "audit system": "action.audit_system",
    "coverage": "action.coverage",
    "help": "action.help",
    "improve knowledge base": "action.improve_knowledge_base",
    "ingest more knowledge": "action.ingest_more_knowledge",
    "ingest raw/<file>": "action.ingest_raw_file",
    "review drafts": "action.review_drafts",
}


def ui_config_path(workspace="."):
    return Path(workspace or ".") / ".brain" / "ui_config.json"


def normalize_language(language):
    normalized = str(language or "").strip().lower()
    return normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def get_language(workspace="."):
    path = ui_config_path(workspace)
    if not path.exists():
        return DEFAULT_LANGUAGE
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_LANGUAGE
    return normalize_language(payload.get("language"))


def set_language(workspace=".", language="en"):
    normalized = str(language or "").strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        return None
    path = ui_config_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"language": normalized}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return normalized


def t(key, workspace=".", **kwargs):
    language = get_language(workspace)
    text = TRANSLATIONS.get(language, TRANSLATIONS[DEFAULT_LANGUAGE]).get(
        key,
        TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key),
    )
    return text.format(**kwargs) if kwargs else text


def action_label(command, workspace="."):
    key = ACTION_KEYS.get(str(command or "").strip())
    return t(key, workspace) if key else str(command or "").strip()


def trust_label(label, workspace="."):
    return t(f"trust.{label}", workspace)
