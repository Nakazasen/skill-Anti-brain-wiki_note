import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

SECURITY_DIR_RE = re.compile(r"(^|/)(auth|security|secrets?|oauth|permissions?)(/|$)", re.I)
MIGRATION_RE = re.compile(r"(^|/)(migrations?|schema|db/migrate)(/|$)", re.I)
PROD_CONFIG_RE = re.compile(r"(^|/)(prod|production|deploy|infra|k8s|terraform)(/|$)|(^|/)(Dockerfile|docker-compose|\\.env)(\\.|$)", re.I)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(path, root):
    return path.relative_to(root).as_posix()


def count_lines(path):
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def zone_id_for(kind, path_pattern):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path_pattern).strip("-").lower()
    return f"heuristic-{kind}-{slug[:60]}"


def make_zone(kind, path_pattern, reason, confidence="medium", restrictions=None):
    return {
        "zone_id": zone_id_for(kind, path_pattern),
        "path_pattern": path_pattern,
        "reason": reason,
        "source": "heuristic_suspected",
        "confidence": confidence,
        "restrictions": restrictions or ["requires_audit_before_change"],
        "created_at": now_iso(),
        "created_by": "continuation_detect_unsafe.py",
    }


def detect(workspace, max_lines=500):
    workspace = Path(workspace).resolve()
    zones = {}
    for path in workspace.rglob("*"):
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        if not path.is_file():
            continue
        rp = rel(path, workspace)
        parent_pattern = str(Path(rp).parent / "**").replace("\\", "/")
        if parent_pattern == ".//**":
            parent_pattern = rp

        if SECURITY_DIR_RE.search(rp):
            zone = make_zone("security", parent_pattern, "Security/auth-related path detected.", "medium", ["requires_audit_before_change", "no_mass_edit"])
            zones[zone["zone_id"]] = zone
        if MIGRATION_RE.search(rp):
            zone = make_zone("migration", parent_pattern, "Migration/schema path detected.", "medium", ["requires_audit_before_change", "no_rename"])
            zones[zone["zone_id"]] = zone
        if PROD_CONFIG_RE.search(rp):
            zone = make_zone("prod-config", rp, "Production/deployment configuration detected.", "medium", ["requires_audit_before_change"])
            zones[zone["zone_id"]] = zone
        if count_lines(path) > max_lines:
            zone = make_zone("large-file", rp, f"Large file detected (> {max_lines} lines).", "low", ["no_mass_edit"])
            zones[zone["zone_id"]] = zone
    return sorted(zones.values(), key=lambda z: z["zone_id"])


def merge_zones(workspace, detected):
    path = Path(workspace) / ".brain" / "unsafe_zones.json"
    data = load_json(path, {"zones": []})
    existing = {zone.get("zone_id"): zone for zone in data.get("zones", [])}
    for zone in detected:
        existing.setdefault(zone["zone_id"], zone)
    merged = {"zones": list(existing.values())}
    save_json(path, merged)
    return merged


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Detect heuristic-suspected unsafe zones.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--max-lines", type=int, default=500)
    parser.add_argument("--write", action="store_true", help="Merge detected heuristic zones into .brain/unsafe_zones.json.")
    args = parser.parse_args(argv)

    detected = detect(args.workspace, max_lines=args.max_lines)
    result = {"status": "ok", "detected_count": len(detected), "zones": detected}
    if args.write:
        merged = merge_zones(args.workspace, detected)
        result["written"] = True
        result["total_zones"] = len(merged.get("zones", []))
    write_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
