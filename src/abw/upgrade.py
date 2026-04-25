from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from importlib import metadata
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .version import DISTRIBUTION_NAME, REPO_URL, build_version_report, install_mode_details, package_root, package_version

try:
    from packaging.version import InvalidVersion, Version
except Exception:  # pragma: no cover - packaging should exist in normal env
    InvalidVersion = Exception
    Version = None  # type: ignore[assignment]


PROTECTED_WORKSPACE_DIRS = ("raw", "wiki", "drafts", "processed", ".brain")
UPGRADE_BACKUP_ROOT = ".brain/upgrade_backups"
LATEST_BACKUP_FILENAME = "latest.json"
WHEEL_FILE_PATTERN = re.compile(r"^abw_skill-(?P<version>[^-]+)-.+\.whl$", re.IGNORECASE)


def _now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_version(value: str | None):
    if not value or Version is None:
        return None
    try:
        return Version(str(value).strip())
    except (InvalidVersion, TypeError, ValueError):
        return None


def _is_channel_allowed(version_value, channel: str) -> bool:
    if version_value is None:
        return False
    if channel == "beta":
        return True
    return not bool(getattr(version_value, "is_prerelease", False))


def _run_subprocess(args: list[str], *, cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _installed_distribution_version() -> str:
    try:
        return metadata.version(DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return package_version()


def _discover_local_wheels(workspace: str | Path = ".") -> list[dict]:
    roots = []
    workspace_dist = Path(workspace).resolve() / "dist"
    package_dist = package_root() / "dist"
    for root in (workspace_dist, package_dist):
        if root.exists() and root.is_dir():
            roots.append(root)

    seen = set()
    candidates = []
    for root in roots:
        for wheel in root.glob("*.whl"):
            key = str(wheel.resolve())
            if key in seen:
                continue
            seen.add(key)
            match = WHEEL_FILE_PATTERN.match(wheel.name)
            if not match:
                continue
            raw_version = match.group("version")
            parsed = _parse_version(raw_version)
            if parsed is None:
                continue
            candidates.append(
                {
                    "version": str(parsed),
                    "parsed_version": parsed,
                    "path": str(wheel.resolve()),
                }
            )
    return candidates


def _pick_local_wheel(
    wheels: list[dict],
    *,
    channel: str,
    exact_version: str | None = None,
) -> dict | None:
    exact = _parse_version(exact_version) if exact_version else None
    filtered = []
    for item in wheels:
        parsed = item.get("parsed_version")
        if parsed is None or not _is_channel_allowed(parsed, channel):
            continue
        if exact and parsed != exact:
            continue
        filtered.append(item)
    if not filtered:
        return None
    return sorted(filtered, key=lambda item: item["parsed_version"])[-1]


def _detect_latest_release_version(channel: str) -> str | None:
    cmd = [sys.executable, "-m", "pip", "index", "versions", DISTRIBUTION_NAME]
    completed = _run_subprocess(cmd)
    if completed.returncode != 0:
        return None
    available_line = ""
    for line in completed.stdout.splitlines():
        if "Available versions:" in line:
            available_line = line
            break
    if not available_line:
        return None
    _, _, version_blob = available_line.partition(":")
    versions = []
    for token in version_blob.split(","):
        parsed = _parse_version(token.strip())
        if parsed is None or not _is_channel_allowed(parsed, channel):
            continue
        versions.append(parsed)
    if not versions:
        return None
    return str(sorted(versions)[-1])


def _resolve_target(workspace: str | Path, channel: str, to_version: str | None) -> dict:
    wheels = _discover_local_wheels(workspace)
    if to_version:
        local_exact = _pick_local_wheel(wheels, channel=channel, exact_version=to_version)
        parsed_requested = _parse_version(to_version)
        if parsed_requested is None:
            return {
                "status": "error",
                "reason": f"invalid version: {to_version}",
                "target_version": "",
                "install_spec": "",
                "source": "unknown",
                "local_wheel_path": None,
                "local_wheels": wheels,
                "release_version": None,
            }
        if local_exact:
            return {
                "status": "ok",
                "target_version": str(local_exact["parsed_version"]),
                "install_spec": local_exact["path"],
                "source": "local_wheel",
                "local_wheel_path": local_exact["path"],
                "local_wheels": wheels,
                "release_version": None,
            }
        return {
            "status": "ok",
            "target_version": str(parsed_requested),
            "install_spec": f"{DISTRIBUTION_NAME}=={parsed_requested}",
            "source": "release_pin",
            "local_wheel_path": None,
            "local_wheels": wheels,
            "release_version": None,
        }

    local_latest = _pick_local_wheel(wheels, channel=channel)
    release_latest_raw = _detect_latest_release_version(channel)
    release_latest = _parse_version(release_latest_raw)

    if local_latest and release_latest:
        if local_latest["parsed_version"] >= release_latest:
            return {
                "status": "ok",
                "target_version": str(local_latest["parsed_version"]),
                "install_spec": local_latest["path"],
                "source": "local_wheel",
                "local_wheel_path": local_latest["path"],
                "local_wheels": wheels,
                "release_version": str(release_latest),
            }
        return {
            "status": "ok",
            "target_version": str(release_latest),
            "install_spec": f"{DISTRIBUTION_NAME}=={release_latest}",
            "source": "release",
            "local_wheel_path": None,
            "local_wheels": wheels,
            "release_version": str(release_latest),
        }

    if local_latest:
        return {
            "status": "ok",
            "target_version": str(local_latest["parsed_version"]),
            "install_spec": local_latest["path"],
            "source": "local_wheel",
            "local_wheel_path": local_latest["path"],
            "local_wheels": wheels,
            "release_version": None,
        }
    if release_latest:
        return {
            "status": "ok",
            "target_version": str(release_latest),
            "install_spec": f"{DISTRIBUTION_NAME}=={release_latest}",
            "source": "release",
            "local_wheel_path": None,
            "local_wheels": wheels,
            "release_version": str(release_latest),
        }
    return {
        "status": "error",
        "reason": "no target version found from local wheel or release index",
        "target_version": "",
        "install_spec": "",
        "source": "none",
        "local_wheel_path": None,
        "local_wheels": wheels,
        "release_version": None,
    }


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_workspace_dirs(workspace: str | Path) -> dict:
    root = Path(workspace).resolve()
    snapshot: dict[str, dict] = {}
    for dirname in PROTECTED_WORKSPACE_DIRS:
        directory = root / dirname
        files = {}
        if directory.exists() and directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if not path.is_file():
                    continue
                relpath = path.relative_to(root).as_posix()
                files[relpath] = _file_hash(path)
        snapshot[dirname] = {
            "exists": directory.exists() and directory.is_dir(),
            "files": files,
        }
    return snapshot


def _compare_snapshots(before: dict, after: dict) -> dict:
    changed = []
    missing = []
    for dirname in PROTECTED_WORKSPACE_DIRS:
        before_files = dict((before.get(dirname) or {}).get("files") or {})
        after_files = dict((after.get(dirname) or {}).get("files") or {})
        for path, before_hash in before_files.items():
            after_hash = after_files.get(path)
            if after_hash is None:
                missing.append(path)
                continue
            if after_hash != before_hash:
                changed.append(path)
    return {
        "ok": not changed and not missing,
        "changed": changed,
        "missing": missing,
    }


def _ensure_backup_root(workspace: str | Path) -> Path:
    backup_root = Path(workspace).resolve() / UPGRADE_BACKUP_ROOT
    backup_root.mkdir(parents=True, exist_ok=True)
    return backup_root


def _write_backup(
    workspace: str | Path,
    *,
    previous_version: str,
    target_version: str,
    install_spec: str,
    channel: str,
    operation: str,
    snapshot_before: dict,
) -> Path:
    root = Path(workspace).resolve()
    backup_root = _ensure_backup_root(root)
    backup_dir = backup_root / _now_utc_compact()
    backup_dir.mkdir(parents=True, exist_ok=True)

    rollback_target = _resolve_target(root, channel=channel, to_version=previous_version)
    rollback_spec = rollback_target.get("install_spec") or f"{DISTRIBUTION_NAME}=={previous_version}"

    manifest = {
        "operation": operation,
        "previous_version": previous_version,
        "target_version": target_version,
        "install_spec": install_spec,
        "rollback_spec": rollback_spec,
        "channel": channel,
        "created_at": _now_utc_compact(),
    }
    (backup_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (backup_dir / "snapshot_before.json").write_text(
        json.dumps(snapshot_before, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for filename in ("abw_config.json", ".abw_version.json"):
        source = root / filename
        if source.exists() and source.is_file():
            shutil.copy2(source, backup_dir / filename)

    latest = _ensure_backup_root(root) / LATEST_BACKUP_FILENAME
    latest.write_text(
        json.dumps({"backup_dir": str(backup_dir), "updated_at": _now_utc_compact()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return backup_dir


def _latest_backup_manifest(workspace: str | Path) -> tuple[Path, dict] | tuple[None, None]:
    root = Path(workspace).resolve()
    backup_root = root / UPGRADE_BACKUP_ROOT
    if not backup_root.exists():
        return None, None

    latest_file = backup_root / LATEST_BACKUP_FILENAME
    if latest_file.exists():
        try:
            payload = json.loads(latest_file.read_text(encoding="utf-8-sig"))
            backup_dir = Path(str(payload.get("backup_dir") or "")).resolve()
            manifest_path = backup_dir / "manifest.json"
            if manifest_path.exists():
                return backup_dir, json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except Exception:  # noqa: BLE001
            pass

    backup_dirs = sorted([path for path in backup_root.iterdir() if path.is_dir()])
    for backup_dir in reversed(backup_dirs):
        manifest_path = backup_dir / "manifest.json"
        if manifest_path.exists():
            return backup_dir, json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    return None, None


def _install_package(spec: str, *, channel: str) -> dict:
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", spec]
    if channel == "beta":
        cmd.insert(5, "--pre")
    completed = _run_subprocess(cmd)
    return {
        "args": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _run_health_checks(workspace: str | Path) -> list[dict]:
    abw_binary = shutil.which("abw")
    prefix = [abw_binary] if abw_binary else [sys.executable, "-m", "abw.cli"]
    check_plan = [
        ("abw version", [*prefix, "--workspace", str(Path(workspace).resolve()), "version"]),
        ("abw doctor", [*prefix, "--workspace", str(Path(workspace).resolve()), "doctor"]),
        ('abw ask "dashboard"', [*prefix, "--workspace", str(Path(workspace).resolve()), "ask", "dashboard"]),
    ]
    checks = []
    for label, command in check_plan:
        completed = _run_subprocess(command, cwd=Path(workspace).resolve())
        checks.append(
            {
                "command": label,
                "returncode": completed.returncode,
                "ok": completed.returncode == 0,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
    return checks


def _summarize_checks(checks: list[dict]) -> str:
    failing = [item["command"] for item in checks if not item.get("ok")]
    if not failing:
        return "All health checks passed."
    return "Health check failures: " + ", ".join(failing)


def build_upgrade_report(
    workspace: str | Path = ".",
    *,
    channel: str = "stable",
    to_version: str | None = None,
    rollback: bool = False,
) -> dict:
    version = build_version_report(workspace)
    install = install_mode_details()
    mode = install["install_mode"]
    channel = str(channel or "stable").strip().lower()
    if channel not in {"stable", "beta"}:
        channel = "stable"

    target = _resolve_target(workspace, channel=channel, to_version=to_version)
    rollback_dir, rollback_manifest = _latest_backup_manifest(workspace)

    if mode == "pip package":
        commands = ["abw upgrade --check", "abw upgrade", "abw doctor"]
        summary = "Package install detected. `abw upgrade` can update in place."
    elif mode == "git+pip":
        commands = ["abw upgrade --check", f"py -m pip install -U git+{REPO_URL}", "abw doctor"]
        summary = "Git+pip install detected. Upgrade runs pip package update only."
    elif mode == "editable/dev":
        source_path = install.get("source_path") or "."
        commands = [f'py -m pip install -e "{source_path}"', "abw upgrade --check", "abw doctor"]
        summary = "Editable install detected. Upgrade still targets package installation only."
    else:
        commands = ["abw upgrade --check", "py -m pip install -U abw-skill", "abw doctor"]
        summary = "Install mode is unknown, so only generic upgrade guidance is safe."

    return {
        "workspace": version["workspace"],
        "package_version": package_version(),
        "install_mode": mode,
        "channel": channel,
        "requested_version": to_version or "",
        "rollback_requested": bool(rollback),
        "target_status": target.get("status"),
        "target_version": target.get("target_version") or "",
        "target_source": target.get("source") or "",
        "target_install_spec": target.get("install_spec") or "",
        "target_reason": target.get("reason") or "",
        "local_wheels": [item["version"] for item in target.get("local_wheels", [])],
        "rollback_available": bool(rollback_manifest),
        "rollback_from_version": str((rollback_manifest or {}).get("target_version") or ""),
        "rollback_to_version": str((rollback_manifest or {}).get("previous_version") or ""),
        "rollback_backup_dir": str(rollback_dir) if rollback_dir else "",
        "commands": commands,
        "summary": summary,
        "note": "Use `abw upgrade` to execute. `--check` performs dry-run detection only.",
    }


def perform_upgrade(
    workspace: str | Path = ".",
    *,
    check: bool = False,
    to_version: str | None = None,
    rollback: bool = False,
    channel: str = "stable",
) -> dict:
    root = Path(workspace).resolve()
    channel = str(channel or "stable").strip().lower()
    if channel not in {"stable", "beta"}:
        channel = "stable"

    current = _installed_distribution_version()
    before_snapshot = _snapshot_workspace_dirs(root)

    if rollback:
        backup_dir, manifest = _latest_backup_manifest(root)
        if not manifest:
            return {
                "workspace": str(root),
                "status": "error",
                "operation": "rollback",
                "package_version_before": current,
                "package_version_after": current,
                "summary": "Rollback requested but no backup manifest exists.",
                "backup_dir": "",
                "data_preserved": True,
                "health_checks": [],
                "health_ok": False,
            }
        target_version = str(manifest.get("previous_version") or "").strip()
        install_spec = str(manifest.get("rollback_spec") or f"{DISTRIBUTION_NAME}=={target_version}").strip()
        detected = {
            "status": "ok" if target_version and install_spec else "error",
            "target_version": target_version,
            "install_spec": install_spec,
            "source": "rollback_backup",
            "backup_dir": str(backup_dir),
        }
    else:
        detected = _resolve_target(root, channel=channel, to_version=to_version)

    base_report = build_upgrade_report(root, channel=channel, to_version=to_version, rollback=rollback)
    base_report["operation"] = "rollback" if rollback else "upgrade"
    base_report["package_version_before"] = current
    base_report["status"] = "check" if check else "pending"
    base_report["data_preserved"] = True
    base_report["health_checks"] = []
    base_report["health_ok"] = False
    base_report["backup_dir"] = ""
    base_report["package_version_after"] = current
    base_report["installed_change"] = False

    if detected.get("status") != "ok":
        base_report["status"] = "error"
        base_report["summary"] = str(detected.get("reason") or "target resolution failed")
        return base_report

    base_report["target_version"] = detected.get("target_version") or ""
    base_report["target_install_spec"] = detected.get("install_spec") or ""
    base_report["target_source"] = detected.get("source") or ""

    if check:
        current_parsed = _parse_version(current)
        target_parsed = _parse_version(base_report["target_version"])
        base_report["status"] = "check"
        base_report["upgrade_needed"] = bool(target_parsed and current_parsed and target_parsed != current_parsed)
        base_report["summary"] = "Check completed. No package changes were applied."
        return base_report

    if rollback:
        base_report["backup_dir"] = str(detected.get("backup_dir") or "")
    else:
        backup_dir = _write_backup(
            root,
            previous_version=current,
            target_version=str(base_report["target_version"]),
            install_spec=str(base_report["target_install_spec"]),
            channel=channel,
            operation=str(base_report["operation"]),
            snapshot_before=before_snapshot,
        )
        base_report["backup_dir"] = str(backup_dir)

    install_result = _install_package(str(base_report["target_install_spec"]), channel=channel)
    base_report["install_returncode"] = install_result["returncode"]
    base_report["install_stdout"] = install_result["stdout"].strip()
    base_report["install_stderr"] = install_result["stderr"].strip()

    after_version = _installed_distribution_version()
    base_report["package_version_after"] = after_version
    base_report["installed_change"] = after_version != current

    after_snapshot = _snapshot_workspace_dirs(root)
    preservation = _compare_snapshots(before_snapshot, after_snapshot)
    base_report["data_preserved"] = bool(preservation.get("ok"))
    base_report["data_changed_files"] = preservation.get("changed", [])
    base_report["data_missing_files"] = preservation.get("missing", [])

    checks = _run_health_checks(root)
    base_report["health_checks"] = checks
    base_report["health_ok"] = all(item.get("ok") for item in checks)

    if install_result["returncode"] == 0 and base_report["data_preserved"] and base_report["health_ok"]:
        base_report["status"] = "success"
        base_report["summary"] = _summarize_checks(checks)
    else:
        base_report["status"] = "failed"
        failure_bits = []
        if install_result["returncode"] != 0:
            failure_bits.append("package install failed")
        if not base_report["data_preserved"]:
            failure_bits.append("workspace preservation check failed")
        if not base_report["health_ok"]:
            failure_bits.append("health checks failed")
        base_report["summary"] = "; ".join(failure_bits) if failure_bits else "upgrade failed"
    return base_report


def render_upgrade_report(report: dict) -> str:
    lines = [
        "ABW Upgrade",
        f"- workspace: {report['workspace']}",
        f"- package_version: {report.get('package_version') or report.get('package_version_before', 'unknown')}",
        f"- install_mode: {report['install_mode']}",
        f"- operation: {report.get('operation', 'upgrade')}",
        f"- channel: {report.get('channel', 'stable')}",
        f"- target_version: {report.get('target_version', '') or 'unknown'}",
        f"- target_source: {report.get('target_source', 'unknown')}",
        f"- status: {report.get('status', 'check')}",
        f"- summary: {report['summary']}",
    ]
    if report.get("package_version_before"):
        lines.append(f"- package_version_before: {report['package_version_before']}")
    if report.get("package_version_after"):
        lines.append(f"- package_version_after: {report['package_version_after']}")
    if report.get("backup_dir"):
        lines.append(f"- backup_dir: {report['backup_dir']}")
    if "data_preserved" in report:
        lines.append(f"- data_preserved: {'yes' if report.get('data_preserved') else 'no'}")
    if "health_ok" in report:
        lines.append(f"- health_ok: {'yes' if report.get('health_ok') else 'no'}")
    for command in report["commands"]:
        lines.append(f"- RUN: {command}")
    for check in report.get("health_checks", []):
        status = "OK" if check.get("ok") else "FAIL"
        lines.append(f"- CHECK [{status}]: {check.get('command')} (rc={check.get('returncode')})")
    if report.get("data_changed_files"):
        lines.append("- changed_files: " + ", ".join(report["data_changed_files"]))
    if report.get("data_missing_files"):
        lines.append("- missing_files: " + ", ".join(report["data_missing_files"]))
    lines.append(f"- note: {report['note']}")
    return "\n".join(lines)
