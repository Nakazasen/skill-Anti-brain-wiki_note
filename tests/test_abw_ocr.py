import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.ocr import available_tesseract_languages, preferred_tesseract_language, resolve_tesseract_executable, tesseract_status


def subprocess_result(stdout="", stderr="", returncode=0):
    return type("Completed", (), {"stdout": stdout, "stderr": stderr, "returncode": returncode})()


class AbwOcrTests(unittest.TestCase):
    def test_resolve_tesseract_uses_explicit_env_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "tesseract.exe"
            exe.write_text("", encoding="utf-8")

            with patch.dict(os.environ, {"ABW_TESSERACT_CMD": str(exe)}, clear=False), patch("abw.ocr.shutil.which", return_value=None):
                self.assertEqual(resolve_tesseract_executable(), str(exe))

    def test_tesseract_status_reports_unavailable_without_binary(self):
        with patch("abw.ocr.resolve_tesseract_executable", return_value=None):
            status = tesseract_status()

        self.assertEqual(status["provider"], "tesseract")
        self.assertEqual(status["status"], "unavailable")

    def test_preferred_tesseract_language_uses_japanese_when_available(self):
        available_tesseract_languages.cache_clear()
        completed = subprocess_result(stdout="List of available languages in x:\neng\njpn\n")
        with patch("abw.ocr.resolve_tesseract_executable", return_value="tesseract"), patch("abw.ocr.subprocess.run", return_value=completed):
            self.assertEqual(preferred_tesseract_language(), "eng+jpn")

    def test_preferred_tesseract_language_falls_back_to_english(self):
        available_tesseract_languages.cache_clear()
        completed = subprocess_result(stdout="List of available languages in x:\neng\n")
        with patch("abw.ocr.resolve_tesseract_executable", return_value="tesseract"), patch("abw.ocr.subprocess.run", return_value=completed):
            self.assertEqual(preferred_tesseract_language(), "eng")


if __name__ == "__main__":
    unittest.main()
