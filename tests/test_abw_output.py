import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_output  # noqa: E402
import abw_proof  # noqa: E402


ASCII_HEADER_RULE = "=========="


def dev_output_env():
    env = os.environ.copy()
    env["ABW_DEV_OUTPUT"] = "1"
    return env


def raw_json_env():
    env = dev_output_env()
    env["ABW_RAW_JSON"] = "1"
    return env


def make_proof(answer, finalization_block, runtime_id="123", nonce=None, binding_source="mcp"):
    nonce = nonce or ("a" * 32)
    return abw_proof.generate_proof(answer, finalization_block, runtime_id, nonce, binding_source)


def run_output(args=None, **kwargs):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "abw_output.py")] + (args or []),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        cwd=str(REPO_ROOT),
        **kwargs,
    )


class AbwOutputTests(unittest.TestCase):
    def test_enforce_runner_output_rejects_non_dict(self):
        result = abw_output.enforce_runner_output("plain text")
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["reason"], "output not produced by runner")

    def test_enforce_runner_output_rejects_missing_binding_fields(self):
        result = abw_output.enforce_runner_output({"binding_status": "runner_checked"})
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["current_state"], "blocked")

    def test_enforce_runner_output_rejects_missing_runtime_id(self):
        result = abw_output.enforce_runner_output(
            {
                "binding_status": "runner_checked",
                "binding_source": "mcp",
                "nonce": "a" * 32,
                "validation_proof": "a" * 64,
            }
        )
        self.assertEqual(result["binding_status"], "rejected")

    def test_enforce_runner_output_passes_runner_payload(self):
        runtime_id = "123"
        finalization_block = "## Finalization\n- current_state: verified"
        nonce = "a" * 32
        payload = {
            "binding_status": "runner_checked",
            "binding_source": "mcp",
            "nonce": nonce,
            "validation_proof": make_proof("ok", finalization_block, runtime_id, nonce=nonce),
            "answer": "ok",
            "finalization_block": finalization_block,
            "runtime_id": runtime_id,
        }
        self.assertEqual(abw_output.enforce_runner_output(payload), payload)

    def test_enforce_runner_output_rejects_invalid_nonce(self):
        result = abw_output.enforce_runner_output(
            {
                "binding_status": "runner_checked",
                "binding_source": "mcp",
                "nonce": "bad",
                "validation_proof": "a" * 64,
                "answer": "ok",
                "finalization_block": "## Finalization\n- current_state: verified",
                "runtime_id": "123",
            }
        )
        self.assertEqual(result["binding_status"], "rejected")
        self.assertEqual(result["reason"], "invalid nonce")

    def test_render_user_view_hides_internal_fields(self):
        result = abw_output.render_user_view(
            {
                "binding_status": "runner_checked",
                "runtime_id": "123",
                "validation_proof": "a" * 64,
                "route": "help",
                "nonce": "a" * 32,
                "finalization_block": "## Finalization",
                "evaluation": {"status": "accepted"},
                "message": "Help is ready.",
                "next_actions": [{"label": "Help", "command": "help"}],
                "sections": [{"title": "Overview", "items": []}],
            }
        )
        self.assertEqual(set(result), {"message", "next_actions", "sections"})
        self.assertIn("trust: checked", result["message"])
        self.assertIn("Help is ready.", result["message"])

    def test_render_cli_routes_help_to_clean_text_view(self):
        rendered = abw_output.render_cli(
            {
                "binding_status": "runner_checked",
                "runtime_id": "123",
                "validation_proof": "a" * 64,
                "evaluation": {"status": "accepted"},
                "route": {"lane": "help"},
                "state_snapshot": {
                    "raw_files": 1,
                    "draft_files": 2,
                    "wiki_files": 3,
                    "pending_drafts": 4,
                },
                "next_actions": [{"label": "Help", "command": "help"}],
                "sections": [
                    {"title": "Quick start", "items": ['Use `abw ask "..."` for most tasks.']},
                    {"title": "Commands", "items": ["abw ask \"...\" - Ask ABW to route a normal task.", "abw doctor - Check system health."]},
                    {"title": "Workspace", "items": ["Raw files: 1", "Draft files: 2", "Wiki files: 3", "Pending drafts: 4"]},
                    {"title": "Suggested next steps", "items": ["help"]},
                ],
            }
        )
        self.assertIn("ABW Help", rendered)
        self.assertIn(ASCII_HEADER_RULE, rendered)
        self.assertIn("Quick start", rendered)
        self.assertIn("Commands", rendered)
        self.assertIn('abw ask "..."', rendered)
        self.assertIn("abw doctor", rendered)
        self.assertIn("Workspace", rendered)
        self.assertIn("Raw files: 1", rendered)
        self.assertIn("Pending drafts: 4", rendered)
        self.assertIn("- help", rendered)
        self.assertNotIn("binding_status", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("runtime_id", rendered)
        self.assertNotIn("evaluation", rendered)
        self.assertLessEqual(len(rendered.splitlines()), 20)

    def test_render_cli_routes_query_and_strips_finalization(self):
        rendered = abw_output.render_cli(
            {
                "route": {"lane": "query"},
                "summary": "local wiki",
                "answer": "The answer.\n\n## Finalization\n- current_state: verified",
                "finalization_block": "## Finalization\n- current_state: verified",
                "next_actions": ["audit system"],
            }
        )
        self.assertIn("ABW Query", rendered)
        self.assertIn("local wiki", rendered)
        self.assertIn("The answer.", rendered)
        self.assertIn("- audit system", rendered)
        self.assertNotIn("Finalization", rendered)
        self.assertLessEqual(len(rendered.splitlines()), 15)

    def test_agent_mode_renders_markdown_and_hides_internal_fields(self):
        with unittest.mock.patch.dict(os.environ, {"ABW_AGENT_MODE": "1"}):
            rendered = abw_output.render(
                {
                    "route": {"lane": "query"},
                    "summary": "local wiki",
                    "answer": "The answer.\n\n## Finalization\n- current_state: verified",
                    "finalization_block": "## Finalization\n- current_state: verified",
                    "validation_proof": "a" * 64,
                    "runtime_id": "123",
                    "nonce": "a" * 32,
                    "evaluation": {"status": "accepted"},
                    "next_actions": [{"label": "Audit", "command": "audit system"}],
                }
            )
        self.assertIn("### ABW Query", rendered)
        self.assertIn("### Summary", rendered)
        self.assertIn("- local wiki", rendered)
        self.assertIn("### Answer", rendered)
        self.assertIn("- The answer.", rendered)
        self.assertIn("### Next Actions", rendered)
        self.assertIn("- audit system", rendered)
        self.assertNotIn("┌", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("runtime_id", rendered)
        self.assertNotIn("nonce", rendered)
        self.assertNotIn("evaluation", rendered)
        self.assertNotIn("route", rendered)
        self.assertNotIn("finalization_block", rendered)
        self.assertNotIn("Finalization", rendered)

    def test_render_auto_detects_cli_mode_from_entry_caller(self):
        with unittest.mock.patch.dict(os.environ, {"ABW_ENTRY_CALLER": "abw_cli"}, clear=False):
            rendered = abw_output.render(
                {
                    "route": {"lane": "query"},
                    "summary": "local wiki",
                    "answer": "The answer.",
                    "next_actions": ["audit system"],
                }
            )
        self.assertIn("ABW Query", rendered)
        self.assertNotIn("### ABW Query", rendered)
        self.assertIn("=========", rendered)

    def test_render_debug_always_returns_json(self):
        rendered = abw_output.render(
            {
                "route": {"lane": "query"},
                "answer": "ok",
                "runtime_id": "123",
            },
            debug=True,
        )
        payload = json.loads(rendered)
        self.assertEqual(payload["answer"], "ok")
        self.assertEqual(payload["runtime_id"], "123")

    def test_detect_user_level_uses_actions_heuristic(self):
        self.assertEqual(abw_output.detect_user_level({"next_actions": ["one"]}), "beginner")
        self.assertEqual(abw_output.detect_user_level({"next_actions": ["one", "two"]}), "intermediate")
        self.assertEqual(
            abw_output.detect_user_level({"next_actions": ["one", "two", "three", "four"]}),
            "expert",
        )

    def test_render_agent_uses_level_variants(self):
        result = {
            "route": {"lane": "query"},
            "summary": "local wiki",
            "answer": "Detailed answer.",
            "binding_status": "runner_checked",
            "runner_status": "completed",
            "next_actions": [
                "ingest raw/<file>",
                'ask "..."',
                "coverage",
                "audit system",
                "deep query",
            ],
        }
        beginner = abw_output.render_agent(result, level="beginner")
        intermediate = abw_output.render_agent(result, level="intermediate")
        expert = abw_output.render_agent(result, level="expert")

        self.assertIn("### Next Actions", beginner)
        self.assertIn("- ingest raw/<file>", beginner)
        self.assertNotIn("- coverage", beginner)
        self.assertIn("### Answer", intermediate)
        self.assertIn("- coverage", intermediate)
        self.assertNotIn("- deep query", intermediate)
        self.assertIn("### Details", expert)
        self.assertIn("- deep query", expert)
        self.assertNotIn("runtime_id", expert)
        self.assertNotIn("validation_proof", expert)
        self.assertNotIn("binding_status", expert)
        self.assertNotIn("runner_checked", expert)

    def test_dashboard_agent_uses_user_facing_fields_only(self):
        rendered = abw_output.render_agent(
            {
                "route": {"lane": "dashboard"},
                "summary": "14 lanes, 27 modules, 9 wiki files",
                "answer": "commit: abc\n\n## Finalization\n- evidence: internal",
                "current_state": "checked_only",
                "binding_status": "runner_checked",
                "validation_proof": "a" * 64,
                "health": {"modules": 27, "lanes": 14},
                "knowledge": {
                    "raw_files": 1,
                    "draft_files": 0,
                    "wiki_files": 9,
                    "pending_drafts": 0,
                    "coverage_ratio": 1.0,
                },
                "next_actions": [{"label": "Ingest raw file", "command": "ingest raw/<file>"}],
            }
        )
        self.assertIn("- Raw files: 1", rendered)
        self.assertIn("- Draft files: 0", rendered)
        self.assertIn("- Wiki files: 9", rendered)
        self.assertIn("- Coverage: 1.0", rendered)
        self.assertIn("- ingest raw/<file>", rendered)
        self.assertNotIn("commit", rendered)
        self.assertNotIn("Finalization", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("runner_checked", rendered)
        self.assertNotIn("Modules:", rendered)
        self.assertNotIn("Lanes:", rendered)

    def test_agent_help_view_stays_on_v2_public_surface(self):
        rendered = abw_output.render_agent(
            {
                "route": {"lane": "help"},
                "sections": [
                    {"title": "Quick start", "items": ['Use `abw ask "..."` for most tasks.']},
                    {"title": "Commands", "items": ["abw ask \"...\" - Ask ABW to route a normal task.", "abw review - Review pending drafts."]},
                    {"title": "Advanced commands", "items": ["abw upgrade - Upgrade the local ABW runtime."]},
                ],
                "next_actions": [{"label": "Help", "command": "help"}],
            }
        )
        self.assertIn('abw ask "..."', rendered)
        self.assertIn("abw review", rendered)
        self.assertIn("abw upgrade", rendered)
        self.assertNotIn("validation_proof", rendered)
        self.assertNotIn("runtime_id", rendered)

    def test_user_level_env_override(self):
        with unittest.mock.patch.dict(os.environ, {"ABW_USER_LEVEL": "expert"}):
            rendered = abw_output.render_agent(
                {
                    "route": {"lane": "query"},
                    "answer": "ok",
                    "binding_status": "runner_checked",
                    "next_actions": ["one"],
                }
            )
        self.assertIn("### Details", rendered)

    def test_render_cli_routes_review(self):
        rendered = abw_output.render_cli(
            {
                "route": {"lane": "review_drafts"},
                "summary": "2 drafts checked",
                "answer": "Draft batch review:\n- drafts/a.md",
            }
        )
        self.assertIn("ABW Review", rendered)
        self.assertIn("2 drafts checked", rendered)
        self.assertIn("Draft batch review", rendered)
        self.assertLessEqual(len(rendered.splitlines()), 15)

    def test_render_cli_routes_coverage(self):
        rendered = abw_output.render_cli(
            {
                "route": {"lane": "coverage"},
                "coverage_report": {
                    "coverage_ratio": 0.5,
                    "total_questions": 4,
                    "success": 2,
                    "weak": 1,
                    "fail": 1,
                    "wiki_topic_count": 9,
                    "top_gaps": ["missing MOM", "weak RCA"],
                },
                "next_actions": ["ingest raw/<file>"],
            }
        )
        self.assertIn("ABW Coverage", rendered)
        self.assertIn("Coverage ratio: 0.5", rendered)
        self.assertIn("Pass/Weak/Fail: 2/1/1", rendered)
        self.assertIn("missing MOM", rendered)
        self.assertLessEqual(len(rendered.splitlines()), 15)

    def test_render_cli_routes_dashboard(self):
        rendered = abw_output.render_cli(
            {
                "route": {"lane": "dashboard"},
                "health": {"modules": 12, "lanes": 8, "bottleneck_count": 1},
                "knowledge": {
                    "raw_files": 1,
                    "draft_files": 2,
                    "wiki_files": 3,
                    "pending_drafts": 4,
                    "coverage_ratio": 0.75,
                },
                "next_actions": [{"label": "Review", "command": "review drafts"}],
            }
        )
        self.assertIn("ABW Dashboard", rendered)
        self.assertIn("Workspace", rendered)
        self.assertIn("Raw files: 1", rendered)
        self.assertIn("Draft files: 2", rendered)
        self.assertIn("Wiki files: 3", rendered)
        self.assertNotIn("Modules: 12", rendered)
        self.assertNotIn("Lanes:", rendered)
        self.assertIn("Review: review drafts", rendered)
        self.assertLessEqual(len(rendered.splitlines()), 15)

    def test_cli_returns_rejected_shape_for_invalid_input(self):
        completed = run_output(input=json.dumps({"binding_status": "runner_checked"}), env=dev_output_env())
        self.assertEqual(completed.returncode, 3)
        self.assertIn("ABW", completed.stdout)
        self.assertIn("invalid runtime_id", completed.stdout)
        self.assertNotIn("binding_status", completed.stdout)

    def test_dev_output_debug_returns_full_json(self):
        finalization_block = "## Finalization\n- current_state: verified"
        nonce = "a" * 32
        payload = {
            "binding_status": "runner_checked",
            "binding_source": "mcp",
            "nonce": nonce,
            "validation_proof": make_proof("ok", finalization_block, nonce=nonce),
            "answer": "ok",
            "finalization_block": finalization_block,
            "runtime_id": "123",
        }
        completed = run_output(["--debug"], input=json.dumps(payload), env=dev_output_env())
        self.assertEqual(completed.returncode, 0)
        rendered = json.loads(completed.stdout)
        self.assertEqual(rendered["binding_status"], "runner_checked")
        self.assertEqual(rendered["validation_proof"], payload["validation_proof"])

    def test_dev_output_debug_with_raw_json_env_returns_full_payload(self):
        finalization_block = "## Finalization\n- current_state: verified"
        nonce = "a" * 32
        payload = {
            "binding_status": "runner_checked",
            "binding_source": "mcp",
            "nonce": nonce,
            "validation_proof": make_proof("ok", finalization_block, nonce=nonce),
            "answer": "ok",
            "finalization_block": finalization_block,
            "runtime_id": "123",
        }
        completed = run_output(["--debug"], input=json.dumps(payload), env=raw_json_env())
        self.assertEqual(completed.returncode, 0)
        rendered = json.loads(completed.stdout)
        self.assertEqual(rendered["binding_status"], "runner_checked")
        self.assertEqual(rendered["validation_proof"], payload["validation_proof"])

    def test_output_level_flag_overrides_agent_level(self):
        finalization_block = "## Finalization\n- current_state: verified"
        nonce = "a" * 32
        payload = {
            "binding_status": "runner_checked",
            "binding_source": "mcp",
            "nonce": nonce,
            "validation_proof": make_proof("ok", finalization_block, nonce=nonce),
            "answer": "ok",
            "finalization_block": finalization_block,
            "runtime_id": "123",
            "next_actions": [{"label": "One", "command": "one"}],
        }
        completed = run_output(["--level", "expert"], input=json.dumps(payload), env=dev_output_env())
        self.assertEqual(completed.returncode, 0)
        self.assertIn("### Details", completed.stdout)

    def test_cli_file_with_rendered_text_passes_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "output_raw.json"
            output_file.write_text("ABW Help\n========\n", encoding="utf-8")
            completed = run_output(["--file", str(output_file), "--debug"], env=dev_output_env())
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), "ABW Help\n========")

    def test_cli_file_with_powershell_redirect_encoding_passes_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "output_raw.json"
            output_file.write_text("ABW Help\n========\n", encoding="utf-16")
            completed = run_output(["--file", str(output_file), "--debug"], env=dev_output_env())
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout.strip(), "ABW Help\n========")

    def test_cli_task_debug_is_rendered_as_normal_text(self):
        finalization_block = "## Finalization\n- current_state: verified"
        nonce = "a" * 32
        payload = {
            "binding_status": "runner_checked",
            "binding_source": "mcp",
            "nonce": nonce,
            "validation_proof": make_proof("ok", finalization_block, nonce=nonce),
            "answer": "ok",
            "finalization_block": finalization_block,
            "runtime_id": "123",
            "task": "help --debug",
        }
        completed = run_output(input=json.dumps(payload), env=dev_output_env())
        self.assertEqual(completed.returncode, 0)
        self.assertIn("### ABW", completed.stdout)
        self.assertNotIn("binding_status", completed.stdout)
        self.assertNotIn("validation_proof", completed.stdout)

    def test_direct_output_without_dev_is_blocked(self):
        completed = run_output(input="{}")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Do not run abw_output directly. Use 'abw' CLI.", completed.stderr)


if __name__ == "__main__":
    unittest.main()
