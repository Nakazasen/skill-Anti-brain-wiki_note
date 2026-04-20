import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_version  # noqa: E402


class AbwVersionTests(unittest.TestCase):
    def test_resolve_version_uses_version_file_as_primary_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".abw_version.json").write_text(
                json.dumps(
                    {
                        "commit": "file123",
                        "status": "stable",
                        "updated_at": "2026-04-21T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(abw_version, "get_git_commit", return_value="file123"):
                result = abw_version.resolve_version(tmp)

            self.assertEqual(result["commit"], "file123")
            self.assertEqual(result["source"], "version_file")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["deploy_status"], "ok")

    def test_resolve_version_detects_out_of_sync_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".abw_version.json").write_text(
                json.dumps({"commit": "file123", "status": "stable"}),
                encoding="utf-8",
            )

            with patch.object(abw_version, "get_git_commit", return_value="git456"):
                result = abw_version.resolve_version(tmp)

            self.assertEqual(result["commit"], "file123")
            self.assertEqual(result["git_commit"], "git456")
            self.assertEqual(result["deploy_status"], "out_of_sync")

    def test_resolve_version_detects_failed_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".abw_version.json").write_text(
                json.dumps({"commit": "file123", "status": "failed"}),
                encoding="utf-8",
            )

            with patch.object(abw_version, "get_git_commit", return_value="file123"):
                result = abw_version.resolve_version(tmp)

            self.assertEqual(result["deploy_status"], "failed")

    def test_resolve_version_falls_back_to_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(abw_version, "get_git_commit", return_value="git123"):
                result = abw_version.resolve_version(tmp)

            self.assertEqual(result["commit"], "git123")
            self.assertEqual(result["source"], "git")
            self.assertEqual(result["deploy_status"], "unknown")

    def test_resolve_version_returns_unknown_without_version_or_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(abw_version, "get_git_commit", return_value=None):
                result = abw_version.resolve_version(tmp)

            self.assertEqual(result["commit"], "unknown")
            self.assertEqual(result["source"], "unknown")
            self.assertEqual(result["deploy_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
