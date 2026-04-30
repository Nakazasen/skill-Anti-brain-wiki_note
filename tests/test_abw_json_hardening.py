import json
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Standard ABW imports
from abw import cli as abw_cli

class TestAbwJsonHardening(unittest.TestCase):
    def setUp(self):
        self.workspace = Path("D:/tmp/test_workspace")
        
    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_inspect_report")
    def test_inspect_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"data": "test_inspect"}
        
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "inspect"])
            
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "inspect")
        self.assertEqual(report["workspace"], str(self.workspace))
        self.assertIn("generated_at", report)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["data"], "test_inspect")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_gap_report")
    def test_gaps_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"data": "test_gaps"}
        
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "gaps"])
            
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "gaps")
        self.assertEqual(report["data"], "test_gaps")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_recovery_report")
    def test_recover_plan_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"data": "test_recovery"}
        
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "recover-plan"])
            
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "recover-plan")
        self.assertEqual(report["data"], "test_recovery")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_verify_report")
    def test_recover_verify_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"data": "test_verify"}
        
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "recover-verify"])
            
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "recover-verify")
        self.assertEqual(report["data"], "test_verify")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_trend_report")
    def test_trend_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"data": "test_trend"}
        
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "trend"])
            
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "trend")
        self.assertEqual(report["data"], "test_trend")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.build_improvement_plan")
    def test_improve_json_hardening(self, mock_build, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_build.return_value = {"data": "test_improve"}
        
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "improve"])
            
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "improve")
        self.assertEqual(report["data"], "test_improve")

    @patch("abw.cli.resolve_workspace")
    @patch("abw.cli.run_apply")
    def test_apply_json_hardening(self, mock_apply, mock_resolve):
        mock_resolve.return_value = self.workspace
        mock_apply.return_value = {
            "action": "cleanup-drafts",
            "files_affected_count": 0,
            "changes_planned_count": 0,
            "risk_level": "low",
            "rollback_possible": False,
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            abw_cli.main(["--json", "apply", "--dry-run", "cleanup-drafts"])

        report = json.loads(stdout.getvalue())
        self.assertEqual(report["schema_version"], "1.1.0")
        self.assertEqual(report["command_name"], "apply")
        self.assertEqual(report["action"], "cleanup-drafts")
        mock_apply.assert_called_once_with(self.workspace, "cleanup-drafts", yes=False)

if __name__ == "__main__":
    unittest.main()
