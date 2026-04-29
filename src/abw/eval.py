"""
ABW retrieval evaluation harness.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_QUESTIONS = [
    {
        "id": "MOM-TARGET-001",
        "question": "What documents describe AGV communication?",
        "expected_source_coverage": {
            "required_context": ["MOM", "WMS", "InterStock", "AGV"],
            "required_any": ["agv", "communication"]
        },
    },
    {
        "id": "MOM-TARGET-002",
        "question": "Which sources mention MOM WMS workflow constraints?",
        "expected_source_coverage": {
            "required_context": ["MOM", "WMS", "InterStock", "AGV"],
            "required_any": ["wms", "workflow"]
        },
    },
    {
        "id": "MOM-SUMMARY-001",
        "mode": "broad_summary",
        "question": "Summarize MOM WMS workflow constraints.",
        "expected_source_coverage": {
            "required_context": ["MOM", "WMS", "InterStock", "AGV"],
            "required_any": ["wms", "workflow"]
        },
    },
    {
        "id": "MOM-NEGATIVE-001",
        "expected_behavior": "missing_evidence_report",
        "question": "What is the approved production cutover date for the MOM WMS system?",
        "expected_source_coverage": {
            "required_context": ["MOM", "WMS", "InterStock", "AGV"]
        }
    },
    {
        "id": "MP2027-TARGET-001",
        "question": "What spreadsheet or CSV sources are available for MP2027 budgeting or simulation?",
        "expected_source_coverage": {
            "required_context": ["MP2027"],
            "required_any": [".csv", ".xlsx", "xls"]
        },
    },
    {
        "id": "WEB-UNSUPPORTED-001",
        "expected_behavior": "missing_evidence_report",
        "question": "What do the DOCX source files say about website content?",
        "expected_source_coverage": {
            "required_context": ["mat-the-website", "matthesinhhoanguyco", "website"]
        }
    },
]

EXPLICIT_GAP_WORDS = (
    "insufficient evidence",
    "missing evidence",
    "no evidence",
    "no evidence found",
    "cannot find",
    "could not find",
    "not found",
    "not found in local wiki",
    "not enough evidence",
    "not enough information",
    "no local evidence",
    "i don't know",
    "not mentioned",
    "khong du bang chung",
    "khong tim thay",
)

GENERIC_DASHBOARD_WORDS = (
    "dashboard",
    "health",
    "workspace state",
    "doctor",
    "version",
)

REPORTABLE_CORPUS_DIRS = ("wiki", "raw", "processed", "drafts")


class EvalQuestion:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.question = data.get("question")
        self.mode = data.get("mode", "targeted")
        self.expected_behavior = data.get("expected_behavior", "grounded_answer")
        self.expected_source_coverage = data.get("expected_source_coverage", {})
        self.required_context = self.expected_source_coverage.get("required_context", [])
        self.required_any = self.expected_source_coverage.get("required_any", [])
        self.minimum_grounding_score = data.get("minimum_grounding_score", 3)
        self.maximum_missing_evidence_score = data.get("maximum_missing_evidence_score", 1)
        self.allow_bounded_partial = data.get("allow_bounded_partial", False)
        self.must_log_gap_if_insufficient = data.get("must_log_gap_if_insufficient", True)
        self.overclaim_checks = data.get("overclaim_checks", [])


class EvalResult:
    def __init__(
        self,
        question: EvalQuestion,
        answer: str,
        citations: List[Dict[str, Any]],
        logs: List[str],
        *,
        source_coverage_available: Optional[str] = None,
    ):
        self.question = question
        self.answer = answer or ""
        self.citations = citations or []
        self.logs = logs or []
        self.source_coverage_available = source_coverage_available
        self.grounding_score = 0
        self.missing_evidence_score = 0
        self.bounded_summary_score = 0
        self.harness_runtime_status = "not_run"
        self.retrieval_quality_status = "not_scored"
        self.reason = ""
        self.failures = []
        self.warnings = []
        self.passed = False

    def score(self):
        self.grounding_score = self._calculate_grounding()
        self.missing_evidence_score = self._calculate_missing_evidence()

        if self.question.mode == "broad_summary":
            self.bounded_summary_score = self._calculate_bounded_summary()

        self._run_overclaim_checks()
        self._determine_outcome()

    def _calculate_grounding(self) -> int:
        if not self.citations:
            return 0

        if not self._matched_expected_source():
            return 1

        if len(self.citations) > 2:
            return 4
        return 3

    def _matched_expected_source(self) -> bool:
        coverage = self.question.expected_source_coverage
        required_any = coverage.get("required_any", [])
        required_context = coverage.get("required_context", [])

        haystacks = []
        for citation in self.citations:
            haystacks.extend(
                [
                    str(citation.get("source", "")),
                    str(citation.get("path", "")),
                    str(citation.get("title", "")),
                    str(citation.get("text", "")),
                    " ".join(str(term) for term in citation.get("matched_terms", []) or []),
                ]
            )
        joined = "\n".join(haystacks).lower()

        # Check required any if present
        any_match = True
        if required_any:
            any_match = any(str(term).lower() in joined for term in required_any)

        # Check required context if present
        context_match = True
        if required_context:
            context_match = any(str(term).lower() in joined for term in required_context)

        return any_match and context_match

    def _has_explicit_gap_language(self) -> bool:
        answer_lower = self.answer.lower()
        log_lower = "\n".join(str(log) for log in self.logs).lower()
        return any(term in answer_lower or term in log_lower for term in EXPLICIT_GAP_WORDS)

    def _is_generic_dashboard_answer(self) -> bool:
        answer_lower = self.answer.lower()
        if not answer_lower.strip() or self.citations:
            return False
        dashboard_hits = sum(1 for word in GENERIC_DASHBOARD_WORDS if word in answer_lower)
        evidence_terms = ("source", "citation", "wiki", "raw", "evidence", "gap", "missing")
        has_evidence_language = any(term in answer_lower for term in evidence_terms)
        return dashboard_hits >= 2 and not has_evidence_language

    def _calculate_missing_evidence(self) -> int:
        answer_lower = self.answer.lower().strip()
        matched_expected = self._matched_expected_source()

        if not answer_lower:
            return 3

        if self._has_explicit_gap_language():
            if "gap" in answer_lower or "missing" in answer_lower:
                return 3
            return 2

        if self._is_generic_dashboard_answer():
            return 2

        if not self.citations:
            return 2

        if not matched_expected:
            return 2

        if self.grounding_score <= 1 and not matched_expected:
            return 2

        return 0

    def _calculate_bounded_summary(self) -> int:
        answer_lower = self.answer.lower()
        boundary_indicators = ["bounded", "limit", "retrieved", "chunk", "trusted wiki", "partial", "scope"]

        if any(indicator in answer_lower for indicator in boundary_indicators):
            if self.grounding_score >= 3:
                return 4
            return 3

        if self.grounding_score >= 2:
            return 2

        return 1

    def _run_overclaim_checks(self):
        answer_lower = self.answer.lower()

        if "full corpus" in answer_lower or "all documents" in answer_lower:
            if self.grounding_score < 3:
                self.failures.append("hallucination_overclaim: claimed full corpus without sufficient evidence")

        if "docx" in answer_lower and "parsed" in answer_lower:
            self.failures.append("hallucination_docx: claimed docx was parsed when it is unsupported")

        if self.question.must_log_gap_if_insufficient:
            if self.missing_evidence_score > 0 and "gap" not in answer_lower:
                self.warnings.append("missing_gap_logging: reported missing evidence but did not explicitly log a gap")

    def _determine_outcome(self):
        self.harness_runtime_status = "completed"

        if self.source_coverage_available in {"corpus_gap", "not_applicable"}:
            self.retrieval_quality_status = self.source_coverage_available
            self.reason = f"expected sources or context not present in this workspace ({self.source_coverage_available})"
            self.passed = True
            return

        if self.failures:
            self.retrieval_quality_status = "fail"
            self.reason = "; ".join(self.failures)
            self.passed = False
            return

        if self.question.expected_behavior == "grounded_answer":
            if self.grounding_score >= self.question.minimum_grounding_score:
                self.retrieval_quality_status = "pass"
                self.reason = "grounding score met threshold"
                self.passed = True
            elif self.question.allow_bounded_partial and self.bounded_summary_score >= 3:
                self.retrieval_quality_status = "pass"
                self.reason = "bounded partial answer met threshold"
                self.passed = True
            else:
                self.retrieval_quality_status = "fail"
                self.reason = "grounding score below threshold"
                self.passed = False
        elif self.question.expected_behavior == "missing_evidence_report":
            if self.missing_evidence_score >= 2:
                self.retrieval_quality_status = "pass"
                self.reason = "missing evidence was reported"
                self.passed = True
            else:
                self.retrieval_quality_status = "fail"
                self.reason = "missing evidence was not reported"
                self.passed = False
        else:
            self.retrieval_quality_status = "pass"
            self.reason = "no stricter behavior threshold configured"
            self.passed = True


class EvalHarness:
    def __init__(self, workspace_path: str, abw_version: str = "0.7.0"):
        self.workspace_path = str(workspace_path)
        self.abw_version = abw_version
        self.results: List[EvalResult] = []
        self.harness_runtime_status = "not_run"

    def load_questions(self, questions_path: Optional[str] = None) -> List[Dict[str, Any]]:
        path = Path(questions_path) if questions_path else Path(self.workspace_path) / ".brain" / "eval" / "questions.json"
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("questions", [])
            if not isinstance(data, list):
                raise ValueError("eval questions must be a list or an object with a questions list")
            return data
        return list(DEFAULT_QUESTIONS)

    def _workspace_text_index(self) -> str:
        workspace = Path(self.workspace_path)
        parts = []
        for dirname in REPORTABLE_CORPUS_DIRS:
            root = workspace / dirname
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file():
                    try:
                        parts.append(str(path.relative_to(workspace)).lower())
                    except ValueError:
                        parts.append(str(path).lower())
                    if path.suffix.lower() in {".md", ".txt", ".json", ".csv", ".html", ".htm"}:
                        try:
                            parts.append(path.read_text(encoding="utf-8", errors="ignore")[:20000].lower())
                        except OSError:
                            continue
        return "\n".join(parts)

    def expected_sources_exist(self, question: EvalQuestion) -> Optional[str]:
        required_context = question.required_context
        required_any = question.required_any

        if not required_context and not required_any:
            return None

        index = self._workspace_text_index()
        # Combine index with workspace path for identity check
        identity_haystack = (index + "\n" + self.workspace_path).lower()

        if not index and not required_context:
             return "corpus_gap"

        # 1. Context check (Identity)
        if required_context:
            context_found = any(str(term).lower() in identity_haystack for term in required_context)
            if not context_found:
                return "not_applicable"

        # 2. Evidence check (Content/Type)
        if required_any:
            any_found = any(str(term).lower() in index for term in required_any)
            if not any_found:
                return "corpus_gap"

        return "pass"

    def run_eval(self, questions: List[Dict[str, Any]], runner_fn):
        self.harness_runtime_status = "completed"
        for q_data in questions:
            question = EvalQuestion(q_data)
            coverage_status = self.expected_sources_exist(question)
            if coverage_status in {"corpus_gap", "not_applicable"}:
                answer, citations, logs = "", [], [f"expected sources not present: {coverage_status}"]
            else:
                answer, citations, logs = runner_fn(question.question)
            result = EvalResult(
                question,
                answer,
                citations,
                logs,
                source_coverage_available=coverage_status,
            )
            result.score()
            self.results.append(result)

    def generate_report(self) -> Dict[str, Any]:
        passed_count = sum(1 for result in self.results if result.passed)
        failed_count = len(self.results) - passed_count
        warning_count = sum(len(result.warnings) for result in self.results)

        avg_grounding = sum(result.grounding_score for result in self.results) / len(self.results) if self.results else 0
        avg_missing = (
            sum(result.missing_evidence_score for result in self.results) / len(self.results) if self.results else 0
        )
        avg_summary = (
            sum(result.bounded_summary_score for result in self.results) / len(self.results) if self.results else 0
        )

        quality_statuses = {result.retrieval_quality_status for result in self.results}
        if not self.results:
            retrieval_quality_status = "not_run"
            reason = "no eval questions were run"
        elif any(status == "fail" for status in quality_statuses):
            retrieval_quality_status = "fail"
            reason = "one or more applicable retrieval checks failed"
        elif quality_statuses <= {"not_applicable", "corpus_gap"}:
            retrieval_quality_status = "corpus_gap"
            reason = "no applicable expected source coverage exists in this workspace"
        elif "corpus_gap" in quality_statuses or "not_applicable" in quality_statuses:
            retrieval_quality_status = "partial"
            reason = "applicable checks passed with some corpus gaps or not-applicable questions"
        else:
            retrieval_quality_status = "pass"
            reason = "all applicable retrieval checks passed"

        report = {
            "workspace_path": self.workspace_path,
            "abw_version": self.abw_version,
            "timestamp": datetime.now().isoformat(),
            "harness_runtime_status": self.harness_runtime_status,
            "retrieval_quality_status": retrieval_quality_status,
            "reason": reason,
            "summary": {
                "total": len(self.results),
                "passed": passed_count,
                "failed": failed_count,
                "warnings": warning_count,
            },
            "scores": {
                "average_grounding": round(avg_grounding, 2),
                "average_missing_evidence": round(avg_missing, 2),
                "average_bounded_summary": round(avg_summary, 2),
            },
            "details": [],
        }

        for result in self.results:
            report["details"].append(
                {
                    "id": result.question.id,
                    "question": result.question.question,
                    "passed": result.passed,
                    "grounding_score": result.grounding_score,
                    "missing_evidence_score": result.missing_evidence_score,
                    "bounded_summary_score": result.bounded_summary_score,
                    "harness_runtime_status": result.harness_runtime_status,
                    "retrieval_quality_status": result.retrieval_quality_status,
                    "reason": result.reason,
                    "failures": result.failures,
                    "warnings": result.warnings,
                    "citations_count": len(result.citations),
                }
            )

        return report

    def save_report(self, report_dir: str):
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_report_{timestamp}.json"
        filepath = os.path.join(report_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.generate_report(), f, indent=2, ensure_ascii=False)

        return filepath
