import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_menu  # noqa: E402


class AbwMenuTests(unittest.TestCase):
    def test_query_flow_routes_to_cli_ask(self):
        inputs = iter(["MOM la gi?"])
        with patch("abw_menu.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            result = abw_menu.query_flow(input_func=lambda _prompt: next(inputs), output_func=lambda _text: None)

        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_args.args[0][2:], ["ask", "MOM la gi?"])

    def test_ingest_flow_routes_to_cli_ingest(self):
        with patch("abw_menu.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            result = abw_menu.ingest_flow(input_func=lambda _prompt: "raw/mom.pdf", output_func=lambda _text: None)

        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_args.args[0][2:], ["ingest", "raw/mom.pdf"])

    def test_review_flow_routes_to_cli_review(self):
        with patch("abw_menu.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            result = abw_menu.review_flow()

        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_args.args[0][2:], ["review"])

    def test_system_flow_routes_to_coverage_dashboard_health(self):
        cases = [("1", "coverage"), ("2", "dashboard"), ("3", "health")]
        for choice, command in cases:
            with self.subTest(choice=choice), patch(
                "abw_menu.subprocess.run",
                return_value=SimpleNamespace(returncode=0),
            ) as run_mock:
                result = abw_menu.system_flow(input_func=lambda _prompt, value=choice: value, output_func=lambda _text: None)

            self.assertEqual(result, 0)
            self.assertEqual(run_mock.call_args.args[0][2:], [command])

    def test_main_menu_routes_dashboard(self):
        inputs = iter(["1", "0"])
        with patch("abw_menu.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run_mock:
            result = abw_menu.menu_main(
                input_func=lambda _prompt: next(inputs),
                output_func=lambda _text: None,
                clear=False,
            )

        self.assertEqual(result, 0)
        self.assertEqual(run_mock.call_args_list[0].args[0][2:], ["ask", "dashboard"])

    def test_invalid_menu_choice_does_not_crash(self):
        inputs = iter(["x", "0"])
        output = []

        result = abw_menu.menu_main(
            input_func=lambda _prompt: next(inputs),
            output_func=output.append,
            clear=False,
        )

        self.assertEqual(result, 0)
        self.assertIn("Invalid choice.", output)


if __name__ == "__main__":
    unittest.main()
