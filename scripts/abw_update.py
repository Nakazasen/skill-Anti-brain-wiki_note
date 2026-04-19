import compileall
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import abw_proof


CRITICAL_FILES = (
    "scripts/abw_runner.py",
    "scripts/abw_proof.py",
    "scripts/abw_output.py",
)
MODULES_TO_RELOAD = (
    "abw_accept",
    "abw_health",
    "abw_knowledge",
    "abw_output",
    "abw_proof",
    "abw_runner",
    "abw_update",
)
FORBIDDEN_PATH_NAMES = {
    ".env",
    ".env.local",
    ".pytest_cache",
    "__pycache__",
    ".cache",
    "secrets",
}
LOCK_FILENAME = ".abw_update.lock"
VERSION_FILENAME = ".abw_version.json"
STAGING_DIRNAME = ".abw_update_staging"
BACKUP_DIRNAME = ".abw_backup"
PRESERVED_ENTRY_NAMES = {
    ".git",
    ".brain",
    LOCK_FILENAME,
    VERSION_FILENAME,
    STAGING_DIRNAME,
    BACKUP_DIRNAME,
}
_RUNTIME_BASELINE = {}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_runtime_id():
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def render_finalization_block(current_state, evidence, gaps_or_limitations, next_steps):
    return (
        "## Finalization\n"
        f"- current_state: {current_state}\n"
        f"- evidence: {evidence}\n"
        f"- gaps_or_limitations: {gaps_or_limitations}\n"
        f"- next_steps: {next_steps}\n"
    )


def compose_answer(body, finalization_block):
    body = str(body or "").strip()
    if body:
        return f"{body}\n\n{finalization_block}".strip()
    return str(finalization_block or "").strip()


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def version_file_path(workspace):
    return Path(workspace) / VERSION_FILENAME


def lock_file_path(workspace):
    return Path(workspace) / LOCK_FILENAME


def update_log_path(workspace):
    return Path(workspace) / ".brain" / "update_log.jsonl"


def staging_path(workspace):
    return Path(workspace) / STAGING_DIRNAME


def backup_root_path(workspace):
    return Path(workspace) / BACKUP_DIRNAME


def latest_backup_dir(workspace):
    root = backup_root_path(workspace)
    if not root.exists():
        return None
    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def backup_live_path(backup_dir):
    return Path(backup_dir) / "live"


def backup_manifest_path(backup_dir):
    return Path(backup_dir) / "manifest.json"


def run_git(workspace, args):
    result = subprocess.run(
        ["git", *args],
        cwd=str(Path(workspace).resolve()),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "args": ["git", *args],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def require_git_success(workspace, args):
    result = run_git(workspace, args)
    if result["returncode"] != 0:
        stderr = (result.get("stderr") or "").strip()
        stdout = (result.get("stdout") or "").strip()
        details = stderr or stdout or "git command failed"
        raise RuntimeError(f"{' '.join(result['args'])}: {details}")
    return result


def git_rev_parse(workspace, ref):
    result = require_git_success(workspace, ["rev-parse", ref])
    return str(result.get("stdout") or "").strip()


def read_version_file(workspace):
    path = version_file_path(workspace)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def write_version_file(workspace, commit_hash, timestamp, source="origin/main", status="stable"):
    payload = {
        "commit": str(commit_hash or "").strip(),
        "updated_at": timestamp,
        "source": source,
        "status": status,
    }
    version_file_path(workspace).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def ensure_version_file(workspace, source="origin/main"):
    existing = read_version_file(workspace)
    if existing:
        return existing
    commit = ""
    try:
        commit = git_rev_parse(workspace, "HEAD")
    except Exception:  # noqa: BLE001
        commit = ""
    return write_version_file(workspace, commit, now_iso(), source=source, status="stable")


def file_hash(path):
    hasher = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def current_integrity_snapshot(workspace):
    root = Path(workspace).resolve()
    snapshot = {}
    for relpath in CRITICAL_FILES:
        path = root / relpath
        if path.exists():
            snapshot[relpath] = file_hash(path)
    return snapshot


def verify_runtime_integrity(workspace="."):
    workspace = Path(workspace).resolve()
    missing = []
    compromised = []
    for relpath in (*CRITICAL_FILES, "scripts/abw_accept.py"):
        if not (workspace / relpath).exists():
            missing.append(relpath)

    current_snapshot = current_integrity_snapshot(workspace)
    baseline = _RUNTIME_BASELINE.get(str(workspace))
    if baseline:
        for relpath, old_hash in baseline.items():
            new_hash = current_snapshot.get(relpath)
            if new_hash is None or new_hash != old_hash:
                compromised.append(relpath)

    state = "verified"
    if missing or compromised:
        state = "integrity_compromised"

    return {
        "state": state,
        "missing": missing,
        "changed": compromised,
        "snapshot": current_snapshot,
    }


def initialize_runtime(workspace="."):
    workspace = Path(workspace).resolve()
    version = ensure_version_file(workspace)
    key = str(workspace)
    if key not in _RUNTIME_BASELINE:
        _RUNTIME_BASELINE[key] = current_integrity_snapshot(workspace)
    integrity = verify_runtime_integrity(workspace)
    return {"version": version, "integrity": integrity}


def acquire_update_lock(workspace):
    payload = {
        "pid": os.getpid(),
        "timestamp": now_iso(),
    }
    path = lock_file_path(workspace)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise RuntimeError("update lock already present") from exc
    return path


def release_update_lock(workspace):
    path = lock_file_path(workspace)
    if path.exists():
        path.unlink()


def cleanup_staging(workspace):
    stage = staging_path(workspace)
    if stage.exists():
        try:
            require_git_success(workspace, ["worktree", "remove", "--force", str(stage)])
        except Exception:  # noqa: BLE001
            shutil.rmtree(stage, ignore_errors=True)


def resolve_target(workspace, target_ref=None):
    target = str(target_ref or "origin/main").strip()
    object_type = str(
        require_git_success(workspace, ["cat-file", "-t", target]).get("stdout") or ""
    ).strip()
    if object_type != "commit":
        raise RuntimeError(f"invalid target object: {target}")
    commit = git_rev_parse(workspace, target)
    return target, commit


def prepare_staging_worktree(workspace, target):
    cleanup_staging(workspace)
    stage = staging_path(workspace)
    require_git_success(workspace, ["worktree", "add", "--force", str(stage), target])
    return stage


def verify_required_files(root):
    missing = [relpath for relpath in CRITICAL_FILES if not (Path(root) / relpath).exists()]
    if missing:
        raise RuntimeError("critical files missing after staging: " + ", ".join(missing))


def verify_forbidden_files(root):
    root = Path(root)
    forbidden = []
    for path in root.rglob("*"):
        parts = set(path.parts)
        if ".git" in parts:
            continue
        if path.name in FORBIDDEN_PATH_NAMES:
            forbidden.append(str(path.relative_to(root)))
    if forbidden:
        raise RuntimeError("forbidden files present in staging: " + ", ".join(sorted(forbidden)[:20]))


def compile_staging_python(root):
    scripts_dir = Path(root) / "scripts"
    if not scripts_dir.exists():
        raise RuntimeError("scripts directory missing in staging")
    if not compileall.compile_dir(str(scripts_dir), quiet=1, force=True):
        raise RuntimeError("python syntax check failed in staging scripts")


def run_staging_tests(root):
    tests_dir = Path(root) / "tests"
    if not tests_dir.exists():
        return {"ran": False, "stdout": "", "stderr": "", "returncode": 0}
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=str(Path(root).resolve()),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise RuntimeError("staging tests failed: " + details)
    return {
        "ran": True,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def verify_staging_integrity(root):
    verify_required_files(root)
    verify_forbidden_files(root)
    compile_staging_python(root)
    return run_staging_tests(root)


def create_backup_dir(workspace, timestamp, from_commit, to_commit, target_ref):
    backup_dir = backup_root_path(workspace) / timestamp.replace(":", "-")
    live_dir = backup_live_path(backup_dir)
    live_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "timestamp": timestamp,
        "from_commit": from_commit,
        "to_commit": to_commit,
        "target_ref": target_ref,
    }
    backup_manifest_path(backup_dir).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup_dir


def move_live_to_backup(workspace, backup_dir):
    workspace = Path(workspace).resolve()
    live_dir = backup_live_path(backup_dir)
    moved = []
    for entry in workspace.iterdir():
        if entry.name in PRESERVED_ENTRY_NAMES:
            continue
        destination = live_dir / entry.name
        shutil.move(str(entry), str(destination))
        moved.append(entry.name)
    return moved


def move_staging_to_live(workspace, stage):
    workspace = Path(workspace).resolve()
    stage = Path(stage).resolve()
    moved = []
    for entry in stage.iterdir():
        if entry.name == ".git":
            continue
        destination = workspace / entry.name
        if destination.exists():
            raise RuntimeError(f"destination already exists during switch: {entry.name}")
        shutil.move(str(entry), str(destination))
        moved.append(entry.name)
    return moved


def restore_backup(workspace, backup_dir):
    workspace = Path(workspace).resolve()
    backup_dir = Path(backup_dir)
    rollback_stage = backup_dir / "failed_attempt"
    rollback_stage.mkdir(parents=True, exist_ok=True)
    for entry in workspace.iterdir():
        if entry.name in PRESERVED_ENTRY_NAMES:
            continue
        shutil.move(str(entry), str(rollback_stage / entry.name))
    for entry in backup_live_path(backup_dir).iterdir():
        shutil.move(str(entry), str(workspace / entry.name))


def finalize_git_state(workspace, target_commit):
    require_git_success(workspace, ["reset", "--hard", target_commit])
    require_git_success(workspace, ["clean", "-fd"])


def reload_system_modules():
    importlib.invalidate_caches()
    reloaded = []
    for module_name in MODULES_TO_RELOAD:
        module = sys.modules.get(module_name)
        if module is None:
            continue
        importlib.reload(module)
        reloaded.append(module_name)
    return reloaded


def build_result(
    *,
    task,
    binding_source,
    binding_status,
    current_state,
    runner_status,
    body,
    evidence,
    gaps_or_limitations,
    next_steps,
    details,
):
    runtime_id = new_runtime_id()
    nonce = abw_proof.new_nonce()
    finalization_block = render_finalization_block(
        current_state=current_state,
        evidence=evidence,
        gaps_or_limitations=gaps_or_limitations,
        next_steps=next_steps,
    )
    answer = compose_answer(body, finalization_block)
    result = {
        "task": task,
        "answer": answer,
        "binding_status": binding_status,
        "binding_source": binding_source,
        "current_state": current_state,
        "runner_status": runner_status,
        "runtime_id": runtime_id,
        "nonce": nonce,
        "finalization_block": finalization_block,
        "update": details,
    }
    result["validation_proof"] = abw_proof.generate_proof(
        answer,
        finalization_block,
        runtime_id,
        nonce,
        binding_source,
    )
    return result


def log_update_event(workspace, from_commit, to_commit, status, reason, duration_ms):
    append_jsonl(
        update_log_path(workspace),
        {
            "timestamp": now_iso(),
            "from_commit": from_commit,
            "to_commit": to_commit,
            "status": status,
            "reason": reason,
            "duration_ms": duration_ms,
        },
    )


def perform_update(workspace=".", target_ref=None):
    started_at = time.perf_counter()
    workspace = Path(workspace).resolve()
    initialize_runtime(workspace)
    acquire_update_lock(workspace)
    previous_commit = ""
    target_commit = ""
    backup_dir = None
    rollback_performed = False
    reloaded = []
    changed = False
    tests_result = {"ran": False}
    target_label = str(target_ref or "origin/main").strip() or "origin/main"

    try:
        previous_commit = git_rev_parse(workspace, "HEAD")
        write_version_file(workspace, previous_commit, now_iso(), source=target_label, status="updating")

        require_git_success(workspace, ["fetch", "origin"])
        target_label, target_commit = resolve_target(workspace, target_ref=target_ref)
        changed = previous_commit != target_commit

        stage = prepare_staging_worktree(workspace, target_label)
        tests_result = verify_staging_integrity(stage)

        backup_dir = create_backup_dir(workspace, now_iso(), previous_commit, target_commit, target_label)
        move_live_to_backup(workspace, backup_dir)
        move_staging_to_live(workspace, stage)
        cleanup_staging(workspace)
        finalize_git_state(workspace, target_commit)
        verify_required_files(workspace)
        write_version_file(workspace, target_commit, now_iso(), source=target_label, status="stable")
        reloaded = reload_system_modules()
        _RUNTIME_BASELINE[str(workspace)] = current_integrity_snapshot(workspace)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log_update_event(workspace, previous_commit, target_commit, "success", "update applied", duration_ms)
        return build_result(
            task="/abw-update",
            binding_source="cli",
            binding_status="runner_enforced",
            current_state="verified",
            runner_status="completed",
            body="ABW update completed successfully.",
            evidence=(
                f"current_version={previous_commit}; target_version={target_commit}; "
                f"changed={changed}; tests_ran={tests_result.get('ran', False)}"
            ),
            gaps_or_limitations="update replaces tracked live content using staged worktree and backup",
            next_steps="restart the outer caller only if it keeps stale process state",
            details={
                "current_version": previous_commit,
                "target_version": target_commit,
                "target_ref": target_label,
                "update_result": "success",
                "changed": changed,
                "rollback_performed": rollback_performed,
                "backup_dir": str(backup_dir) if backup_dir else "",
                "version_file": str(version_file_path(workspace)),
                "tests_ran": tests_result.get("ran", False),
                "reloaded_modules": reloaded,
            },
        )
    except Exception as exc:  # noqa: BLE001
        reason = str(exc)
        if backup_dir and backup_live_path(backup_dir).exists():
            try:
                restore_backup(workspace, backup_dir)
                finalize_git_state(workspace, previous_commit)
                write_version_file(workspace, previous_commit, now_iso(), source="origin/main", status="failed")
                rollback_performed = True
                _RUNTIME_BASELINE[str(workspace)] = current_integrity_snapshot(workspace)
            except Exception as rollback_exc:  # noqa: BLE001
                reason = f"{reason}; rollback_failed={rollback_exc}"
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log_update_event(
            workspace,
            previous_commit,
            target_commit or target_label,
            "rollback" if rollback_performed else "failed",
            reason,
            duration_ms,
        )
        return build_result(
            task="/abw-update",
            binding_source="cli",
            binding_status="runner_enforced",
            current_state="blocked",
            runner_status="blocked",
            body="ABW update failed.",
            evidence=(
                f"current_version={previous_commit}; target_version={target_commit or target_label}; "
                f"update_result={'rollback' if rollback_performed else 'failed'}; reason={reason}"
            ),
            gaps_or_limitations="live system could not complete a stable staged switch",
            next_steps="inspect .brain/update_log.jsonl and use /abw-rollback if manual recovery is still needed",
            details={
                "current_version": previous_commit,
                "target_version": target_commit or target_label,
                "target_ref": target_label,
                "update_result": "rollback" if rollback_performed else "failed",
                "changed": changed,
                "rollback_performed": rollback_performed,
                "backup_dir": str(backup_dir) if backup_dir else "",
                "version_file": str(version_file_path(workspace)),
                "tests_ran": tests_result.get("ran", False),
                "reason": reason,
            },
        )
    finally:
        cleanup_staging(workspace)
        release_update_lock(workspace)


def perform_rollback(workspace="."):
    started_at = time.perf_counter()
    workspace = Path(workspace).resolve()
    initialize_runtime(workspace)
    acquire_update_lock(workspace)
    current_commit = ""
    restored_commit = ""
    try:
        current_commit = git_rev_parse(workspace, "HEAD")
        backup_dir = latest_backup_dir(workspace)
        if backup_dir is None:
            raise RuntimeError("no backup available for rollback")

        manifest = json.loads(backup_manifest_path(backup_dir).read_text(encoding="utf-8-sig"))
        restored_commit = str(manifest.get("from_commit") or "").strip()
        if not restored_commit:
            raise RuntimeError("backup manifest missing from_commit")

        restore_backup(workspace, backup_dir)
        finalize_git_state(workspace, restored_commit)
        verify_required_files(workspace)
        write_version_file(workspace, restored_commit, now_iso(), source="rollback", status="stable")
        _RUNTIME_BASELINE[str(workspace)] = current_integrity_snapshot(workspace)
        reloaded = reload_system_modules()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log_update_event(workspace, current_commit, restored_commit, "rollback", "manual rollback", duration_ms)
        return build_result(
            task="/abw-rollback",
            binding_source="cli",
            binding_status="runner_enforced",
            current_state="verified",
            runner_status="completed",
            body="ABW rollback completed successfully.",
            evidence=f"current_version={current_commit}; target_version={restored_commit}; update_result=rollback",
            gaps_or_limitations="rollback restores the most recent backup snapshot only",
            next_steps="inspect the restored system if the previous update failed for repository-specific reasons",
            details={
                "current_version": current_commit,
                "target_version": restored_commit,
                "update_result": "rollback",
                "backup_dir": str(backup_dir),
                "version_file": str(version_file_path(workspace)),
                "reloaded_modules": reloaded,
            },
        )
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        log_update_event(workspace, current_commit, restored_commit or "unknown", "failed", str(exc), duration_ms)
        return build_result(
            task="/abw-rollback",
            binding_source="cli",
            binding_status="runner_enforced",
            current_state="blocked",
            runner_status="blocked",
            body="ABW rollback failed.",
            evidence=f"current_version={current_commit}; target_version={restored_commit or 'unknown'}; update_result=failed; reason={exc}",
            gaps_or_limitations="rollback could not restore a stable backup",
            next_steps="inspect .brain/update_log.jsonl and .abw_backup before retrying rollback",
            details={
                "current_version": current_commit,
                "target_version": restored_commit or "unknown",
                "update_result": "failed",
                "reason": str(exc),
            },
        )
    finally:
        release_update_lock(workspace)
