import json
import subprocess
from pathlib import Path


VERSION_FILENAME = ".abw_version.json"
STABLE_STATUSES = {"ok", "stable", "deployed"}
FAILED_STATUSES = {"failed", "error", "rollback_failed"}
IN_PROGRESS_STATUSES = {"updating", "rollback", "pending"}


def load_version(workspace="."):
    path = Path(workspace or ".") / VERSION_FILENAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def get_git_commit(workspace="."):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(workspace or "."),
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    commit = str(result.stdout or "").strip()
    return commit or None


def normalize_status(status):
    normalized = str(status or "").strip().lower()
    if normalized in STABLE_STATUSES:
        return "ok"
    if normalized in FAILED_STATUSES:
        return "failed"
    if normalized in IN_PROGRESS_STATUSES:
        return "out_of_sync"
    return "unknown"


def detect_deploy_status(version_payload, git_commit):
    if not version_payload:
        return "unknown"

    version_status = normalize_status(version_payload.get("status"))
    if version_status == "failed":
        return "failed"

    version_commit = str(version_payload.get("commit") or "").strip()
    if version_commit and git_commit and version_commit != git_commit:
        return "out_of_sync"

    if version_status == "ok":
        return "ok"
    if version_status == "out_of_sync":
        return "out_of_sync"
    return "unknown"


def resolve_version(workspace="."):
    workspace = str(workspace or ".")
    version_payload = load_version(workspace)
    git_commit = get_git_commit(workspace)
    version_commit = str((version_payload or {}).get("commit") or "").strip() or None
    commit = version_commit or git_commit or "unknown"
    deploy_status = detect_deploy_status(version_payload, git_commit)
    source = "version_file" if version_commit else ("git" if git_commit else "unknown")
    return {
        "commit": commit,
        "git_commit": git_commit or "unknown",
        "version_file_commit": version_commit or "unknown",
        "status": normalize_status((version_payload or {}).get("status")),
        "deploy_status": deploy_status,
        "deploy_state": deploy_status,
        "updated_at": str((version_payload or {}).get("updated_at") or "unknown"),
        "source": source,
        "version_file_present": version_payload is not None,
    }
