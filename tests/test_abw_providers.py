import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.providers import (  # noqa: E402
    PROVIDER_REGISTRY,
    execute_provider_chain,
    explain_route,
    list_providers,
    prepare_ask_task,
    run_provider_health_checks,
    set_ask_mode,
    set_default_provider,
)
from abw.version import build_version_report  # noqa: E402
from abw.doctor import build_doctor_report  # noqa: E402


class AbwProvidersTests(unittest.TestCase):
    def test_registry_contains_required_providers(self):
        names = {item.name for item in PROVIDER_REGISTRY}
        self.assertEqual(names, {"claude", "openai", "gemini", "ollama", "vllm", "mock"})

    def test_set_default_persists_to_workspace_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = set_default_provider(tmp, "openai")
            self.assertEqual(result["default"], "openai")
            config = json.loads((Path(tmp) / "abw_config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["providers"]["default"], "openai")

    def test_list_providers_marks_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_default_provider(tmp, "gemini")
            report = list_providers(tmp)
            marked = [row["name"] for row in report["providers"] if row["is_default"]]
            self.assertEqual(marked, ["gemini"])

    def test_health_check_reports_mock_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_provider_health_checks(tmp)
            row = next(item for item in report["results"] if item["name"] == "mock")
            self.assertEqual(row["status"], "healthy")

    def test_route_prefers_local_for_high_sensitivity(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = explain_route(tmp, task="analysis", sensitivity="high", cost_mode="balanced")
            self.assertIn(report["selected"], {"vllm", "ollama", "mock"})

    def test_route_can_be_cost_aware(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = explain_route(tmp, task="analysis", sensitivity="normal", cost_mode="low")
            self.assertIn(report["selected"], {"mock", "ollama", "vllm", "gemini", "openai", "claude"})

    def test_route_respects_fallback_chain_and_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_default_provider(tmp, "claude")
            workspace = Path(tmp)
            payload = json.loads((workspace / "abw_config.json").read_text(encoding="utf-8"))
            payload.setdefault("providers", {})["fallback_chain"] = ["openai", "claude", "mock"]
            (workspace / "abw_config.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with patch.dict("os.environ", {"OPENAI_API_KEY": "x", "ANTHROPIC_API_KEY": ""}, clear=False):
                report = explain_route(tmp, task="coding", sensitivity="normal", cost_mode="balanced")
            self.assertEqual(report["selected"], "openai")

    def test_prepare_ask_task_local_mode_keeps_original_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_ask_mode(tmp, "local")
            plan = prepare_ask_task(tmp, "hello world")
            self.assertEqual(plan["task"], "hello world")
            self.assertEqual(plan["provider"]["mode"], "local")
            self.assertFalse(plan["provider"]["used"])

    def test_prepare_ask_task_ai_mode_uses_provider_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_ask_mode(tmp, "ai")
            plan = prepare_ask_task(tmp, "explain architecture")
            self.assertIn("[provider_draft]", plan["task"])
            self.assertEqual(plan["provider"]["mode"], "ai")
            self.assertTrue(isinstance(plan["provider"]["fail_count"], int))

    def test_provider_fallback_on_failure_writes_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            payload = {
                "project_name": workspace.name,
                "workspace_schema": 1,
                "abw_version": "0.2.6",
                "domain_profile": "generic",
                "raw_dir": "raw",
                "wiki_dir": "wiki",
                "drafts_dir": "drafts",
                "providers": {
                    "ask_mode": "ai",
                    "default": "mock",
                    "fallback_chain": ["mock", "vllm"],
                    "task_routes": {"general": ["mock", "vllm"]},
                    "sensitivity_routes": {"normal": ["mock", "vllm"]},
                },
            }
            (workspace / "abw_config.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            with patch.dict("os.environ", {"ABW_PROVIDER_FORCE_FAIL": "mock"}, clear=False):
                result = execute_provider_chain(tmp, prompt="hello", task="general", sensitivity="normal", cost_mode="balanced")
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["provider"], "vllm")
            self.assertGreaterEqual(result["fail_count"], 1)
            telemetry = workspace / ".brain" / "provider_telemetry.jsonl"
            self.assertTrue(telemetry.exists())
            rows = [json.loads(line) for line in telemetry.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(any(row["status"] == "failed" for row in rows))
            self.assertTrue(any(row["status"] == "success" for row in rows))

    def test_version_and_doctor_include_provider_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            set_default_provider(tmp, "openai")
            set_ask_mode(tmp, "hybrid")
            version = build_version_report(tmp)
            self.assertIn("provider_default", version)
            self.assertIn("provider_ask_mode", version)
            self.assertIn("provider_healthy_count", version)
            doctor = build_doctor_report(tmp)
            messages = [row["message"] for row in doctor["engine_checks"]]
            self.assertTrue(any("provider state mode=" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
