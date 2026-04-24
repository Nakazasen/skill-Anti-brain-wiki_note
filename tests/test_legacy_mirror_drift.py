import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

MIRRORED_FILES = (
    "abw_runner.py",
    "abw_output.py",
    "abw_entry.py",
    "abw_help.py",
    "abw_update.py",
    "abw_proof.py",
)


class LegacyMirrorDriftTests(unittest.TestCase):
    def test_critical_legacy_runtime_mirror_matches_scripts(self):
        mismatches = []
        for filename in MIRRORED_FILES:
            script_path = REPO_ROOT / "scripts" / filename
            mirror_path = REPO_ROOT / "src" / "abw" / "_legacy" / filename
            if script_path.read_bytes() != mirror_path.read_bytes():
                mismatches.append(filename)

        self.assertEqual(
            mismatches,
            [],
            "Legacy mirror drift detected for: " + ", ".join(mismatches),
        )


if __name__ == "__main__":
    unittest.main()
