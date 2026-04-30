import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.gaps import build_gap_report, render_gap_report  # noqa: E402


def _write_eval(workspace: Path, detail: dict, *, summary: dict | None = None):
    eval_dir = workspace / ".brain" / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "workspace_path": str(workspace),
        "abw_version": "0.8.3",
        "summary": summary or {"total": 1, "passed": 0, "failed": 1, "warnings": 0},
        "details": [detail],
    }
    (eval_dir / "eval_report_20260429_010101.json").write_text(json.dumps(payload), encoding="utf-8")


def _failed_detail(question_id: str, question: str):
    return {
        "id": question_id,
        "question": question,
        "passed": False,
        "grounding_score": 0,
        "missing_evidence_score": 2,
        "retrieval_quality_status": "fail",
        "reason": "grounding score below threshold",
        "citations_count": 0,
    }


def _passed_warning_detail(question_id: str, question: str):
    return {
        "id": question_id,
        "question": question,
        "passed": True,
        "grounding_score": 3,
        "missing_evidence_score": 0,
        "retrieval_quality_status": "pass",
        "reason": "passed with warning",
        "warnings": ["missing_gap_logging: reported missing evidence but did not explicitly log a gap"],
        "citations_count": 1,
    }


def _gap_types(report: dict) -> set[str]:
    return {gap["type"] for gap in report["gaps"]}


def test_eval_failure_with_raw_and_no_wiki_reports_missing_wiki_coverage(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "agv_comm.csv").write_text("topic,agv communication\n", encoding="utf-8")
    _write_eval(tmp_path, _failed_detail("MOM-TARGET-001", "What documents describe AGV communication?"))

    report = build_gap_report(tmp_path)

    assert "missing_wiki_coverage" in _gap_types(report)
    gap = next(gap for gap in report["gaps"] if gap["type"] == "missing_wiki_coverage")
    assert gap["affected_questions"] == ["MOM-TARGET-001"]
    assert gap["evidence"]["raw_total"] == 1
    assert gap["evidence"]["wiki_total"] == 0
    assert gap["severity"] == "warn"


def test_eval_pass_with_warnings_raw_and_no_wiki_reports_missing_wiki_coverage(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source.md").write_text("MP2027 raw-only evidence\n", encoding="utf-8")
    _write_eval(
        tmp_path,
        _passed_warning_detail("MP2027-TARGET-001", "What sources describe MP2027?"),
        summary={"total": 1, "passed": 1, "failed": 0, "warnings": 1},
    )

    report = build_gap_report(tmp_path)

    assert "missing_wiki_coverage" in _gap_types(report)
    gap = next(gap for gap in report["gaps"] if gap["type"] == "missing_wiki_coverage")
    assert gap["severity"] == "warn"
    assert gap["affected_questions"] == []
    assert gap["evidence"]["raw_total"] == 1


def test_eval_pass_with_warnings_and_raw_or_drafts_reports_weak_retrieval_signal(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source.md").write_text("MP2027 raw-only evidence\n", encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "source.md").write_text("Draft answer\n", encoding="utf-8")
    _write_eval(
        tmp_path,
        _passed_warning_detail("MP2027-TARGET-001", "What sources describe MP2027?"),
        summary={"total": 1, "passed": 1, "failed": 0, "warnings": 1},
    )

    report = build_gap_report(tmp_path)

    assert "weak_retrieval_signal" in _gap_types(report)
    gap = next(gap for gap in report["gaps"] if gap["type"] == "weak_retrieval_signal")
    assert gap["severity"] == "warn"
    assert gap["affected_questions"] == ["MP2027-TARGET-001"]
    assert gap["evidence"]["warnings"] == 1


def test_xls_heavy_workspace_reports_format_block(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for index in range(5):
        (raw / f"website_{index}.xls").write_bytes(b"\xd0\xcf\x11\xe0")
    _write_eval(tmp_path, _failed_detail("WEB-UNSUPPORTED-001", "What do the XLS source files say about website content?"))

    report = build_gap_report(tmp_path)

    assert "format_block" in _gap_types(report)
    gap = next(gap for gap in report["gaps"] if gap["type"] == "format_block")
    assert gap["evidence"]["xls_count"] == 5
    assert gap["affected_questions"] == ["WEB-UNSUPPORTED-001"]


def test_high_draft_count_reports_stale_draft_noise(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source.md").write_text("MOM workflow\n", encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    for index in range(11):
        (drafts / f"draft_{index}.md").write_text("draft\n", encoding="utf-8")
    _write_eval(tmp_path, _failed_detail("MOM-SUMMARY-001", "Summarize MOM WMS workflow constraints."))

    report = build_gap_report(tmp_path)

    assert "stale_draft_noise" in _gap_types(report)
    gap = next(gap for gap in report["gaps"] if gap["type"] == "stale_draft_noise")
    assert gap["evidence"]["draft_total"] == 11


def test_mp2027_style_identity_mismatch_reports_identity_gap(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source_file_order.csv").write_text(
        "filename,description\n"
        "MPFY2027.xlsx,Facility source\n"
        "Simulation_FY2027.xls,IT simulation source\n",
        encoding="utf-8",
    )
    _write_eval(
        tmp_path,
        _failed_detail("MP2027-TARGET-001", "What spreadsheet or CSV sources are available for MP2027 budgeting or simulation?"),
    )

    report = build_gap_report(tmp_path)

    assert "identity_gap" in _gap_types(report)
    gap = next(gap for gap in report["gaps"] if gap["type"] == "identity_gap")
    assert gap["affected_questions"] == ["MP2027-TARGET-001"]
    assert "mp2027" in gap["evidence"]["missing_identity_terms"]
    assert "mpfy2027" in gap["evidence"]["near_match_terms"]


def test_render_gap_report_includes_core_sections(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "source.csv").write_text("a,b\n", encoding="utf-8")
    _write_eval(tmp_path, _failed_detail("Q1", "What is missing?"))

    rendered = render_gap_report(build_gap_report(tmp_path))

    assert "ABW Retrieval Gaps" in rendered
    assert "Gap Summary:" in rendered
    assert "affected_questions:" in rendered
