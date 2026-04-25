import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw import version as version_module  # noqa: E402


class _FakeDistribution:
    def __init__(self, version: str):
        self.version = version


class AbwVersionRuntimeTruthTests(unittest.TestCase):
    def test_package_version_prefers_importlib_metadata(self):
        with patch.object(version_module, "_safe_distribution", return_value=_FakeDistribution("0.3.0")):
            details = version_module.package_version_details()
        self.assertEqual(details["resolved_version"], "0.3.0")
        self.assertEqual(details["source"], "importlib.metadata")

    def test_package_version_falls_back_to_init_version(self):
        with patch.object(version_module, "_safe_distribution", return_value=None):
            details = version_module.package_version_details()
        self.assertEqual(details["resolved_version"], version_module.__version__)
        self.assertEqual(details["source"], "abw.__version__")

    def test_render_version_report_includes_runtime_path_and_mismatch_warning(self):
        report = {
            "package_version": "0.3.0",
            "git_tag": "v0.3.0",
            "git_commit": "abc1234",
            "release_match_state": "matched",
            "workspace": "D:/w",
            "workspace_schema": 1,
            "install_mode": "pip package",
            "python": "3.13",
            "runtime_source": "packaged_legacy",
            "runtime_source_path": "site-packages/abw/_legacy",
            "version_source": "importlib.metadata",
            "version_runtime_path": "site-packages/abw/version.py",
            "version_metadata": "0.3.0",
            "version_fallback": "0.2.9",
            "version_mismatch": True,
            "version_warning": "Version mismatch detected",
            "mirror_status": "matched",
            "mirror_mismatches": [],
            "provider_default": "openai",
            "provider_ask_mode": "default",
            "provider_healthy_count": 1,
            "provider_cost_mode": "balanced",
            "note": "ok",
            "stale_install_suspected": False,
            "self_check_hint": "Run `abw self-check`",
        }
        rendered = version_module.render_version_report(report)
        self.assertIn("version_runtime_path:", rendered)
        self.assertIn("WARN: Version mismatch detected", rendered)


if __name__ == "__main__":
    unittest.main()
