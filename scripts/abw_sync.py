import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def package_sources(package_dir, include_reports=False):
    package_dir = Path(package_dir)
    sources = []
    for subdir in ("WIKI_COMPRESSED", "CRITICAL_ORIGINALS", "HIGH_PRIORITY_ORIGINALS", "FORCE_KEPT_ORIGINALS"):
        root = package_dir / subdir
        if root.exists():
            sources.extend(p for p in root.rglob("*") if p.is_file())
    if include_reports:
        for name in ("package_manifest.json", "QA_REPORT.md"):
            p = package_dir / name
            if p.exists():
                sources.append(p)
    return sorted(set(sources), key=lambda p: p.as_posix())


def run_cmd(args):
    return subprocess.run(args, text=True, capture_output=True)


def display_cmd(args):
    return subprocess.list2cmdline(args)


def sync_package(package_dir, notebook_id, profile, execute, allow_needs_review, include_reports, wait):
    package_dir = Path(package_dir).resolve()
    manifest_path = package_dir / "package_manifest.json"
    if not manifest_path.exists():
        return 1, {"status": "error", "error": f"Missing package manifest: {manifest_path}"}

    manifest = load_json(manifest_path)
    qa_status = manifest.get("qa_status", "unknown")
    if qa_status == "fail":
        return 3, {"status": "blocked", "reason": "package qa_status is fail", "package_id": manifest.get("package_id")}
    if qa_status == "needs_review" and not allow_needs_review:
        return 2, {
            "status": "blocked",
            "reason": "package qa_status is needs_review; pass --allow-needs-review to override",
            "package_id": manifest.get("package_id"),
        }

    sources = package_sources(package_dir, include_reports=include_reports)
    if not sources:
        return 1, {"status": "error", "error": "No package source files found"}

    source_limit = manifest.get("policy_snapshot", {}).get("hard_source_limit", 50)
    if len(sources) > source_limit:
        return 3, {
            "status": "blocked",
            "reason": f"sync source count {len(sources)} exceeds hard limit {source_limit}",
            "package_id": manifest.get("package_id"),
        }

    if execute and shutil.which("nlm") is None:
        return 1, {
            "status": "error",
            "error": "Missing `nlm` CLI on PATH. Install/authenticate NotebookLM CLI before using --execute.",
            "package_id": manifest.get("package_id"),
        }

    commands = []
    for source in sources:
        cmd = ["nlm", "source", "add", notebook_id, "--file", str(source), "--title", source.name]
        if wait:
            cmd.append("--wait")
        if profile:
            cmd.extend(["--profile", profile])
        commands.append(cmd)

    report = {
        "package_id": manifest.get("package_id"),
        "package_dir": str(package_dir),
        "qa_status": qa_status,
        "notebook_id": notebook_id,
        "execute": execute,
        "source_count": len(sources),
        "sources": [str(p.relative_to(package_dir)) for p in sources],
        "commands": [display_cmd(cmd) for cmd in commands],
        "synced_at": datetime.now(timezone.utc).isoformat() if execute else None,
        "results": [],
    }

    if not execute:
        report["status"] = "dry_run"
        return 0, report

    for cmd in commands:
        result = run_cmd(cmd)
        report["results"].append({
            "command": display_cmd(cmd),
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        })
        if result.returncode != 0:
            report["status"] = "error"
            return 1, report

    report["status"] = "synced"
    return 0, report


def main():
    parser = argparse.ArgumentParser(description="Dry-run or execute NotebookLM sync for an ABW package.")
    parser.add_argument("--package-dir", required=True, help="Path to notebooks/packages/<package_id>")
    parser.add_argument("--notebook-id", required=True, help="NotebookLM notebook ID or alias")
    parser.add_argument("--profile", default=None, help="Optional nlm profile")
    parser.add_argument("--execute", action="store_true", help="Actually upload sources. Default is dry-run.")
    parser.add_argument("--allow-needs-review", action="store_true", help="Allow syncing needs_review packages.")
    parser.add_argument("--include-reports", action="store_true", help="Also upload package_manifest.json and QA_REPORT.md.")
    parser.add_argument("--wait", action="store_true", help="Wait for NotebookLM source processing.")
    args = parser.parse_args()

    code, report = sync_package(
        package_dir=args.package_dir,
        notebook_id=args.notebook_id,
        profile=args.profile,
        execute=args.execute,
        allow_needs_review=args.allow_needs_review,
        include_reports=args.include_reports,
        wait=args.wait,
    )

    package_dir = Path(args.package_dir)
    try:
        if package_dir.exists():
            with open(package_dir / "sync_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(code)


if __name__ == "__main__":
    main()
