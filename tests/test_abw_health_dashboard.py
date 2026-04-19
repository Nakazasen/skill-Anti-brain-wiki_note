import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import abw_health  # noqa: E402


class AbwHealthDashboardTests(unittest.TestCase):
    def make_layout(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        workspace = root / "workspace"
        runtime = root / "runtime"
        (workspace / "scripts").mkdir(parents=True)
        (workspace / "workflows").mkdir(parents=True)
        (runtime / "scripts").mkdir(parents=True)
        (runtime / "global_workflows").mkdir(parents=True)
        return tmp, workspace, runtime

    def make_clean_pair(self, workspace, runtime):
        (workspace / "scripts" / "abw_runner.py").write_text("print('ok')\n", encoding="utf-8")
        (workspace / "workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")
        (runtime / "scripts" / "abw_runner.py").write_text("print('ok')\n", encoding="utf-8")
        (runtime / "global_workflows" / "abw-ask.md").write_text("# ask\n", encoding="utf-8")

    def test_log_file_created(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            abw_health.run_health(workspace=workspace, runtime_root=runtime)

            log_path = workspace / ".brain" / "health_log.jsonl"
            self.assertTrue(log_path.exists())
            rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["clean_pass"], 1)
            self.assertEqual(rows[0]["used_validation"], 0)
            self.assertEqual(rows[0]["validation_source"], "none")
            self.assertEqual(rows[0]["mojibake_detected"], 0)
            self.assertEqual(rows[0]["status"], "verified")

    def test_multiple_runs_compute_trend(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            abw_health.run_health(workspace=workspace, runtime_root=runtime)
            (runtime / "scripts" / "abw_runner.py").write_text("print('drift')\n", encoding="utf-8")
            abw_health.run_health(workspace=workspace, runtime_root=runtime)

            trend = abw_health.compute_health_trend(workspace / ".brain" / "health_log.jsonl")
            self.assertEqual(trend["total_runs"], 2)
            self.assertEqual(len(trend["recent_runs"]), 2)
            self.assertGreater(trend["drift_rate"], 0.0)
            self.assertLess(trend["clean_pass_rate"], 1.0)
            self.assertGreater(trend["remediation_rate"], 0.0)
            self.assertEqual(trend["mojibake_rate"], 0.0)
            self.assertEqual(trend["validation_rate"], 0.0)
            self.assertEqual(trend["validation_rate_fallback"], 0.0)
            self.assertEqual(trend["validation_rate_policy"], 0.0)
            self.assertEqual(trend["execution_rate"], 1.0)

    def test_stability_score_decreases_when_drift_present(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            clean = abw_health.run_health(workspace=workspace, runtime_root=runtime)
            (runtime / "scripts" / "abw_runner.py").write_text("print('drift')\n", encoding="utf-8")
            drifted = abw_health.run_health(workspace=workspace, runtime_root=runtime)

            self.assertGreater(
                clean["health_dashboard"]["stability_score"],
                drifted["health_dashboard"]["stability_score"],
            )
            self.assertNotEqual(
                clean["health_dashboard"]["trend"],
                drifted["health_dashboard"]["trend"],
            )

    def test_stability_score_is_100_when_clean(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            result = abw_health.run_health(workspace=workspace, runtime_root=runtime)

            self.assertEqual(result["health_dashboard"]["stability_score"], 100)
            self.assertEqual(result["health_dashboard"]["total_runs"], 1)
            self.assertEqual(result["health_dashboard"]["clean_pass_rate"], 1.0)
            self.assertEqual(result["health_dashboard"]["remediation_rate"], 0.0)
            self.assertEqual(result["health_dashboard"]["mojibake_rate"], 0.0)
            self.assertEqual(result["health_dashboard"]["validation_rate"], 0.0)
            self.assertEqual(result["health_dashboard"]["validation_rate_fallback"], 0.0)
            self.assertEqual(result["health_dashboard"]["validation_rate_policy"], 0.0)
            self.assertEqual(result["health_dashboard"]["execution_rate"], 1.0)
            self.assertTrue(result["health_dashboard"]["trend"].startswith("trend: "))
            self.assertLessEqual(len(result["health_dashboard"]["trend"].replace("trend: ", "")), 10)
            self.assertIn("## Health Dashboard", result["answer"])

    def test_validation_and_execution_rates_track_binding_status(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            abw_health.run_health(workspace=workspace, runtime_root=runtime, binding_status="runner_enforced")
            abw_health.run_health(workspace=workspace, runtime_root=runtime, binding_status="runner_checked")

            trend = abw_health.compute_health_trend(workspace / ".brain" / "health_log.jsonl")
            self.assertEqual(trend["validation_rate"], 0.5)
            self.assertEqual(trend["execution_rate"], 0.5)

    def test_validation_source_rates_split_fallback_and_policy(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            abw_health.run_health(
                workspace=workspace,
                runtime_root=runtime,
                binding_status="runner_checked",
                validation_source="fallback",
            )
            abw_health.run_health(
                workspace=workspace,
                runtime_root=runtime,
                binding_status="runner_checked",
                validation_source="policy",
            )

            trend = abw_health.compute_health_trend(workspace / ".brain" / "health_log.jsonl")
            self.assertEqual(trend["validation_rate"], 1.0)
            self.assertEqual(trend["validation_rate_fallback"], 0.5)
            self.assertEqual(trend["validation_rate_policy"], 0.5)
            self.assertFalse(trend["invariant_violation"])
            self.assertEqual(trend["invariant_severity"], "none")
            self.assertTrue(
                math.isclose(
                    trend["validation_rate"],
                    trend["validation_rate_fallback"] + trend["validation_rate_policy"],
                    rel_tol=0,
                    abs_tol=abw_health.EPS,
                )
            )

    def test_missing_validation_source_defaults_to_none(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            log_path = workspace / ".brain" / "health_log.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-01-01T00:00:00Z",
                        "drift_detected": 0,
                        "drift_remaining": 0,
                        "encoding_detected": 0,
                        "encoding_remaining": 0,
                        "clean_pass": 1,
                        "used_validation": 0,
                        "status": "verified",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            trend = abw_health.compute_health_trend(log_path)
            self.assertEqual(trend["validation_rate"], 0.0)
            self.assertEqual(trend["validation_rate_fallback"], 0.0)
            self.assertEqual(trend["validation_rate_policy"], 0.0)
            self.assertFalse(trend["invariant_violation"])
            self.assertEqual(trend["invariant_severity"], "none")

    def test_invariant_violation_flags_dashboard_without_raising(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            log_path = workspace / ".brain" / "health_log.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            rows = [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "drift_detected": 0,
                    "drift_remaining": 0,
                    "encoding_detected": 0,
                    "encoding_remaining": 0,
                    "clean_pass": 1,
                    "used_validation": 1,
                    "validation_source": "none",
                    "status": "verified",
                }
            ]
            log_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )

            trend = abw_health.compute_health_trend(log_path)
            self.assertTrue(trend["invariant_violation"])
            self.assertEqual(trend["invariant_severity"], "major")

            self.make_clean_pair(workspace, runtime)
            result = abw_health.run_health(workspace=workspace, runtime_root=runtime)
            self.assertIn("invariant_violation", result["health_dashboard"])
            self.assertIn("anomaly_override_reason", result["health_dashboard"])

    def test_anomaly_degrading_case(self):
        recent_runs = [
            {"drift_detected": 0, "encoding_detected": 0},
            {"drift_detected": 1, "encoding_detected": 0},
            {"drift_detected": 1, "encoding_detected": 1},
        ]

        self.assertEqual(abw_health.detect_anomaly(recent_runs), "DEGRADING")

    def test_anomaly_stable_case(self):
        recent_runs = [
            {"drift_detected": 0, "encoding_detected": 0},
            {"drift_detected": 0, "encoding_detected": 0},
            {"drift_detected": 0, "encoding_detected": 0},
        ]

        self.assertEqual(abw_health.detect_anomaly(recent_runs), "STABLE")

    def test_anomaly_recovering_case(self):
        recent_runs = [
            {"drift_detected": 1, "encoding_detected": 1},
            {"drift_detected": 1, "encoding_detected": 0},
            {"drift_detected": 0, "encoding_detected": 0},
        ]

        self.assertEqual(abw_health.detect_anomaly(recent_runs), "RECOVERING")

    def test_anomaly_weak_degrading_case(self):
        recent_runs = [
            {"drift_detected": 0, "encoding_detected": 0},
            {"drift_detected": 1, "encoding_detected": 0},
            {"drift_detected": 1, "encoding_detected": 0},
        ]

        self.assertEqual(abw_health.detect_anomaly(recent_runs), "WEAK_DEGRADING")

    def test_mojibake_rate_tracks_without_affecting_stability_score(self):
        tmp, workspace, runtime = self.make_layout()
        with tmp:
            self.make_clean_pair(workspace, runtime)
            log_path = workspace / ".brain" / "health_log.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                "".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-01-01T00:00:00Z",
                                "drift_detected": 0,
                                "drift_remaining": 0,
                                "encoding_detected": 0,
                                "encoding_remaining": 0,
                                "mojibake_detected": 1,
                                "clean_pass": 1,
                                "used_validation": 0,
                                "validation_source": "none",
                                "status": "verified",
                            }
                        )
                        + "\n"
                    ]
                ),
                encoding="utf-8",
            )

            trend = abw_health.compute_health_trend(log_path)
            self.assertEqual(trend["mojibake_rate"], 1.0)
            self.assertEqual(trend["stability_score"], 100)
