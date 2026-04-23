import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class V2SurfaceDocsTests(unittest.TestCase):
    def test_readme_quick_start_matches_v2_surface(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(r'.\abw.bat ask "what you want to do"', readme)
        self.assertIn(r'.\abw.bat ingest raw\<file>', readme)
        self.assertIn(r'.\abw.bat review', readme)
        self.assertIn(r'.\abw.bat overview', readme)
        self.assertIn(r'.\abw.bat save "..."', readme)
        self.assertIn(r'.\abw.bat doctor', readme)
        self.assertIn("Ingest now checks for possible contradictions", readme)
        self.assertNotIn("42 public workflow commands", readme)

    def test_workflow_readme_no_longer_claims_full_equal_public_surface(self):
        content = (REPO_ROOT / "workflows" / "README.md").read_text(encoding="utf-8")
        self.assertIn("It is not a guarantee that every file here is an equal public runtime command.", content)
        self.assertIn("abw ask", content)
        self.assertIn("abw doctor", content)

    def test_installers_register_curated_public_surface_not_42_equal_commands(self):
        for installer in ("install.ps1", "install.sh"):
            with self.subTest(installer=installer):
                content = (REPO_ROOT / installer).read_text(encoding="utf-8")
                self.assertIn("## Public Commands", content)
                self.assertIn("## Legacy Compatibility Aliases", content)
                self.assertIn("ABW_INSTALL_DEV_SURFACE", content)
                self.assertNotIn("## Registered Extended Commands", content)


if __name__ == "__main__":
    unittest.main()
