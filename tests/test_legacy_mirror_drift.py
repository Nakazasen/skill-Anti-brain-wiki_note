import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.runtime_manifest import (  # noqa: E402
    CRITICAL_RUNTIME_MODULES,
    MIRRORED_RUNTIME_MODULES,
    PACKAGE_ONLY_MODULES,
    SCRIPT_ONLY_MODULES,
)


class LegacyMirrorDriftTests(unittest.TestCase):
    def test_every_scripts_python_file_is_classified(self):
        script_files = {path.name for path in (REPO_ROOT / "scripts").glob("*.py")}
        classified = set(MIRRORED_RUNTIME_MODULES) | set(SCRIPT_ONLY_MODULES)
        unclassified = sorted(script_files - classified)
        self.assertEqual(
            unclassified,
            [],
            "Unclassified scripts runtime files: " + ", ".join(unclassified),
        )

    def test_every_legacy_python_file_is_classified(self):
        legacy_files = {path.name for path in (REPO_ROOT / "src" / "abw" / "_legacy").glob("*.py")}
        classified = set(MIRRORED_RUNTIME_MODULES) | set(PACKAGE_ONLY_MODULES)
        unclassified = sorted(legacy_files - classified)
        self.assertEqual(
            unclassified,
            [],
            "Unclassified packaged legacy files: " + ", ".join(unclassified),
        )

    def test_critical_mirrors_match_byte_for_byte(self):
        mismatches = []
        for filename in CRITICAL_RUNTIME_MODULES:
            script_path = REPO_ROOT / "scripts" / filename
            mirror_path = REPO_ROOT / "src" / "abw" / "_legacy" / filename
            if script_path.read_bytes() != mirror_path.read_bytes():
                mismatches.append(filename)
        self.assertEqual(
            mismatches,
            [],
            "Critical runtime mirror drift detected for: " + ", ".join(mismatches),
        )


if __name__ == "__main__":
    unittest.main()
