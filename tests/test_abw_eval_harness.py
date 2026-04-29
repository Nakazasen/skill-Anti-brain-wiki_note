import pytest
import os
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.eval import EvalHarness, EvalQuestion, EvalResult

def test_eval_question_init():
    q = EvalQuestion({"id": "TEST-01", "question": "What?"})
    assert q.id == "TEST-01"
    assert q.mode == "targeted"

def test_eval_result_scoring_grounded():
    q = EvalQuestion({
        "id": "T-01",
        "question": "AGV?",
        "expected_source_coverage": {"required_any": ["agv"]}
    })
    # Mock result with citation
    result = EvalResult(q, "AGV is active", [{"source": "agv_manual.pdf"}], [])
    result.score()
    assert result.grounding_score >= 3
    assert result.passed is True

def test_eval_result_scoring_missing():
    q = EvalQuestion({
        "id": "T-02",
        "question": "Secret?",
        "expected_behavior": "missing_evidence_report"
    })
    result = EvalResult(q, "Insufficient evidence found in local wiki.", [], [])
    result.score()
    assert result.missing_evidence_score >= 2
    assert result.passed is True

def test_eval_result_hallucination_docx():
    q = EvalQuestion({"id": "T-03", "question": "DOCX?"})
    result = EvalResult(q, "Parsed DOCX manual: content here.", [], [])
    result.score()
    assert any("hallucination_docx" in f for f in result.failures)
    assert result.passed is False

def test_harness_generate_report():
    h = EvalHarness("/mock/path")
    q_data = {"id": "Q-01", "question": "What?"}
    
    def mock_runner(text):
        return "Nothing", [], []
    
    h.run_eval([q_data], mock_runner)
    report = h.generate_report()
    assert report["workspace_path"] == "/mock/path"
    assert len(report["details"]) == 1
    assert report["summary"]["total"] == 1
    assert "harness_runtime_status" in report
    assert "retrieval_quality_status" in report


def test_empty_answer_counts_as_missing_evidence():
    q = EvalQuestion({
        "id": "T-04",
        "question": "Missing?",
        "expected_behavior": "missing_evidence_report",
    })
    result = EvalResult(q, "", [], [])
    result.score()
    assert result.missing_evidence_score == 3
    assert result.retrieval_quality_status == "pass"
    assert result.passed is True


def test_generic_dashboard_answer_counts_as_missing_evidence():
    q = EvalQuestion({
        "id": "T-05",
        "question": "Project topic?",
        "expected_behavior": "missing_evidence_report",
    })
    result = EvalResult(q, "Dashboard health: workspace state verified. Version checked.", [], [])
    result.score()
    assert result.missing_evidence_score >= 2
    assert result.passed is True


def test_no_citation_counts_as_missing_evidence_signal():
    q = EvalQuestion({
        "id": "T-06",
        "question": "AGV?",
        "expected_source_coverage": {"required_any": ["agv"]},
    })
    result = EvalResult(q, "AGV communication is described.", [], [])
    result.score()
    assert result.grounding_score == 0
    assert result.missing_evidence_score >= 2
    assert result.retrieval_quality_status == "fail"


def test_workspace_specific_question_loading():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        questions_dir = workspace / ".brain" / "eval"
        questions_dir.mkdir(parents=True)
        questions_path = questions_dir / "questions.json"
        questions_path.write_text(
            json.dumps({"questions": [{"id": "LOCAL-01", "question": "Local question?"}]}),
            encoding="utf-8",
        )

        harness = EvalHarness(str(workspace))
        questions = harness.load_questions()
        assert [q["id"] for q in questions] == ["LOCAL-01"]


def test_topical_mismatch_classifies_as_corpus_gap():
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "wiki").mkdir()
        (workspace / "wiki" / "note.md").write_text("This note is about billing only.", encoding="utf-8")
        harness = EvalHarness(str(workspace))
        questions = [{
            "id": "NO-SOURCE-01",
            "question": "What mentions AGV communication?",
            "expected_source_coverage": {"required_any": ["agv", "communication"]},
        }]

        def runner(text):
            raise AssertionError("runner should not execute when expected source coverage is absent")

        harness.run_eval(questions, runner)
        report = harness.generate_report()
        detail = report["details"][0]
        assert detail["retrieval_quality_status"] == "corpus_gap"

def test_eval_decontamination_mp2027_in_mom():
    # Mock index with MOM data and .xlsx files but NO MP2027 keyword
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "wiki").mkdir()
        (workspace / "wiki" / "mom_wms.md").write_text("MOM WMS details here.", encoding="utf-8")
        (workspace / "raw").mkdir()
        (workspace / "raw" / "data.xlsx").write_text("XLSX content", encoding="utf-8")
        
        harness = EvalHarness(str(workspace))
        # MP2027 question
        questions = [{
            "id": "MP2027-T-01",
            "question": "MP2027 budget?",
            "expected_source_coverage": {
                "required_context": ["MP2027"],
                "required_any": [".xlsx"]
            }
        }]
        
        def runner(text):
            raise AssertionError("Should not run for not_applicable")
            
        harness.run_eval(questions, runner)
        report = h_report = harness.generate_report()
        assert h_report["details"][0]["retrieval_quality_status"] == "not_applicable"
        assert h_report["details"][0]["passed"] is True

def test_eval_decontamination_mom_in_website():
    # Mock index with Website data but NO MOM context and NO WMS evidence
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "wiki").mkdir()
        (workspace / "wiki" / "web.md").write_text("mat-the-website content.", encoding="utf-8")
        
        harness = EvalHarness(str(workspace))
        # MOM question
        questions = [{
            "id": "MOM-T-01",
            "question": "MOM workflow?",
            "expected_source_coverage": {
                "required_context": ["MOM", "WMS"],
                "required_any": ["workflow"]
            }
        }]
        
        def runner(text):
            raise AssertionError("Should not run for corpus_gap")
            
        harness.run_eval(questions, runner)
        report = harness.generate_report()
        # It's not_applicable because "MOM" and "WMS" are missing
        assert report["details"][0]["retrieval_quality_status"] == "not_applicable"

def test_eval_decontamination_mom_corpus_gap():
    # Mock index with MOM context but NO workflow evidence
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / "wiki").mkdir()
        (workspace / "wiki" / "mom.md").write_text("MOM system info.", encoding="utf-8")
        
        harness = EvalHarness(str(workspace))
        questions = [{
            "id": "MOM-T-02",
            "question": "MOM workflow?",
            "expected_source_coverage": {
                "required_context": ["MOM"],
                "required_any": ["workflow"]
            }
        }]
        
        harness.run_eval(questions, lambda x: ("", [], []))
        report = harness.generate_report()
        assert report["details"][0]["retrieval_quality_status"] == "corpus_gap"
