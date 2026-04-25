"""
Comprehensive multilingual contradiction-context tests.

Covers all 6 factory concepts × every required surface form:
  qty    — 数量 / số lượng / so luong / quantity / qty
  stock  — 在庫 / tồn kho / ton kho / inventory / stock
  capacity — 能力 / công suất / cong suat / capacity
  station  — 工位 / trạm / tram / cell / station
  step     — 工程 / công đoạn / cong doan / process / step
  leadtime — 納期 / lead time / lt / leadtime

Also verifies metadata numbers (page/year/line/timestamp/manifest/section/ref)
are NOT escalated.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.conflicts import _normalize_text, _numbers
from abw.profiles.manufacturing import PROFILE as MANUFACTURING_PROFILE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_workspace(tmp: str, wiki_content: str, raw_content: str):
    ws = Path(tmp)
    (ws / "abw_config.json").write_text(
        json.dumps({"domain_profile": "manufacturing"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    wiki = ws / "wiki" / "base.md"
    wiki.parent.mkdir(parents=True, exist_ok=True)
    wiki.write_text(wiki_content, encoding="utf-8")
    raw = ws / "raw" / "incoming.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(raw_content, encoding="utf-8")
    return ws


# ---------------------------------------------------------------------------
# 1 — Synonym normalisation unit tests
# ---------------------------------------------------------------------------

class TestSynonymNormalisation(unittest.TestCase):

    def _has(self, text: str, canon: str) -> bool:
        return canon in _normalize_text(text, MANUFACTURING_PROFILE)

    # qty
    def test_qty_ja(self):           self.assertTrue(self._has("数量 50", "qty"))
    def test_qty_vi_accent(self):    self.assertTrue(self._has("số lượng 50", "qty"))
    def test_qty_vi_no_accent(self): self.assertTrue(self._has("so luong 50", "qty"))
    def test_qty_en_quantity(self):  self.assertTrue(self._has("quantity 50", "qty"))
    def test_qty_en_raw(self):       self.assertTrue(self._has("qty 50", "qty"))

    # stock
    def test_stock_ja(self):           self.assertTrue(self._has("在庫 100", "stock"))
    def test_stock_vi_accent(self):    self.assertTrue(self._has("tồn kho 100", "stock"))
    def test_stock_vi_no_accent(self): self.assertTrue(self._has("ton kho 100", "stock"))
    def test_stock_en_inventory(self): self.assertTrue(self._has("inventory 100", "stock"))
    def test_stock_en_raw(self):       self.assertTrue(self._has("stock 100", "stock"))

    # capacity
    def test_capacity_ja(self):           self.assertTrue(self._has("能力 200", "capacity"))
    def test_capacity_vi_accent(self):    self.assertTrue(self._has("công suất 200", "capacity"))
    def test_capacity_vi_no_accent(self): self.assertTrue(self._has("cong suat 200", "capacity"))
    def test_capacity_en_raw(self):       self.assertTrue(self._has("capacity 200", "capacity"))

    # station
    def test_station_ja(self):           self.assertTrue(self._has("工位 3", "station"))
    def test_station_vi_accent(self):    self.assertTrue(self._has("trạm 3", "station"))
    def test_station_vi_no_accent(self): self.assertTrue(self._has("tram 3", "station"))
    def test_station_en_cell(self):      self.assertTrue(self._has("cell 3", "station"))
    def test_station_en_raw(self):       self.assertTrue(self._has("station 3", "station"))

    # step / process
    def test_step_ja(self):           self.assertTrue(self._has("工程 7", "step"))
    def test_step_vi_accent(self):    self.assertTrue(self._has("công đoạn 7", "step"))
    def test_step_vi_no_accent(self): self.assertTrue(self._has("cong doan 7", "step"))
    def test_step_en_process(self):   self.assertTrue(self._has("process 7", "step"))
    def test_step_en_raw(self):       self.assertTrue(self._has("step 7", "step"))

    # leadtime
    def test_leadtime_ja(self):           self.assertTrue(self._has("納期 14", "leadtime"))
    def test_leadtime_en_lead_time(self): self.assertTrue(self._has("lead time 14", "leadtime"))
    def test_leadtime_en_lt(self):        self.assertTrue(self._has("lt 14", "leadtime"))
    def test_leadtime_en_raw(self):       self.assertTrue(self._has("leadtime 14", "leadtime"))


# ---------------------------------------------------------------------------
# 2 — Numeric escalation / suppression unit tests
# ---------------------------------------------------------------------------

class TestNumericEscalation(unittest.TestCase):

    def _nums(self, text): return _numbers(text, MANUFACTURING_PROFILE)

    def _assert_escalates(self, text, expected):
        self.assertIn(expected, self._nums(text),
                      f"Expected {expected!r} escalated in: {text!r}")

    def _assert_ignored(self, text):
        self.assertEqual([], self._nums(text),
                         f"Expected no escalation in: {text!r}")

    # qty variants
    def test_esc_qty_en(self):           self._assert_escalates("qty 50", "50")
    def test_esc_qty_vi_accent(self):    self._assert_escalates("số lượng 60", "60")
    def test_esc_qty_vi_no_accent(self): self._assert_escalates("so luong 70", "70")
    def test_esc_qty_ja(self):           self._assert_escalates("数量 80", "80")

    # stock variants
    def test_esc_stock_en(self):           self._assert_escalates("stock 100", "100")
    def test_esc_stock_vi_accent(self):    self._assert_escalates("tồn kho 110", "110")
    def test_esc_stock_vi_no_accent(self): self._assert_escalates("ton kho 120", "120")
    def test_esc_stock_ja(self):           self._assert_escalates("在庫 130", "130")

    # capacity variants
    def test_esc_capacity_en(self):           self._assert_escalates("capacity 200", "200")
    def test_esc_capacity_vi_accent(self):    self._assert_escalates("công suất 210", "210")
    def test_esc_capacity_vi_no_accent(self): self._assert_escalates("cong suat 220", "220")
    def test_esc_capacity_ja(self):           self._assert_escalates("能力 230", "230")

    # station variants
    def test_esc_station_en(self):   self._assert_escalates("station 4", "4")
    def test_esc_station_vi_a(self): self._assert_escalates("trạm 5", "5")
    def test_esc_station_vi_n(self): self._assert_escalates("tram 6", "6")
    def test_esc_station_ja(self):   self._assert_escalates("工位 7", "7")
    def test_esc_station_cell(self): self._assert_escalates("cell 8", "8")

    # step / process variants
    def test_esc_step_en(self):      self._assert_escalates("step 3", "3")
    def test_esc_process_en(self):   self._assert_escalates("process 4", "4")
    def test_esc_step_vi_a(self):    self._assert_escalates("công đoạn 5", "5")
    def test_esc_step_vi_n(self):    self._assert_escalates("cong doan 6", "6")
    def test_esc_step_ja(self):      self._assert_escalates("工程 7", "7")

    # leadtime variants
    def test_esc_leadtime_en(self):      self._assert_escalates("leadtime 14", "14")
    def test_esc_leadtime_lead_time(self): self._assert_escalates("lead time 14", "14")
    def test_esc_leadtime_lt(self):      self._assert_escalates("lt 14", "14")
    def test_esc_leadtime_ja(self):      self._assert_escalates("納期 21", "21")

    # metadata → ignored
    def test_ign_page(self):      self._assert_ignored("see page 12 for details")
    def test_ign_year(self):      self._assert_ignored("revised in year 2024")
    def test_ign_line(self):      self._assert_ignored("error on line 50")
    def test_ign_timestamp(self): self._assert_ignored("timestamp 123456")
    def test_ign_manifest(self):  self._assert_ignored("manifest 99 loaded")
    def test_ign_section(self):   self._assert_ignored("see section 4")
    def test_ign_ref(self):       self._assert_ignored("source ref 7 cited")


# ---------------------------------------------------------------------------
# 3 — Full-stack ingest conflict tests (one per concept × surface form)
# ---------------------------------------------------------------------------

class TestIngestConflictAllConcepts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import abw_ingest as _ai
        cls.ingest = _ai

    def _run(self, wiki: str, raw: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            ws = _make_workspace(tmp, wiki, raw)
            return self.ingest.run("ingest raw/incoming.md", str(ws))

    def _conflict(self, wiki, raw):
        self.assertEqual(self._run(wiki, raw)["conflict_count"], 1)

    def _no_conflict(self, wiki, raw):
        self.assertEqual(self._run(wiki, raw)["conflict_count"], 0)

    # qty
    def test_qty_vi_a(self):  self._conflict("Factory. qty 50", "Factory. số lượng 60")
    def test_qty_vi_n(self):  self._conflict("Factory. qty 50", "Factory. so luong 70")
    def test_qty_ja(self):    self._conflict("Factory. qty 50", "Factory. 数量 80")

    # stock
    def test_stock_vi_a(self): self._conflict("Warehouse. stock 100", "Warehouse. tồn kho 110")
    def test_stock_vi_n(self): self._conflict("Warehouse. stock 100", "Warehouse. ton kho 120")
    def test_stock_ja(self):   self._conflict("Warehouse. stock 100", "Warehouse. 在庫 130")

    # capacity
    def test_cap_vi_a(self): self._conflict("Line capacity 200", "Line công suất 210")
    def test_cap_vi_n(self): self._conflict("Line capacity 200", "Line cong suat 220")
    def test_cap_ja(self):   self._conflict("Line capacity 200", "Line 能力 230")

    # station
    def test_stn_vi_a(self): self._conflict("Assembly station 4", "Assembly trạm 5")
    def test_stn_vi_n(self): self._conflict("Assembly station 4", "Assembly tram 6")
    def test_stn_ja(self):   self._conflict("Assembly station 4", "Assembly 工位 7")
    def test_stn_cell(self): self._conflict("Assembly station 4", "Assembly cell 8")

    # step / process
    def test_step_vi_a(self):  self._conflict("Assembly process step 3", "Assembly process công đoạn 5")
    def test_step_vi_n(self):  self._conflict("Assembly process step 3", "Assembly process cong doan 6")
    def test_step_ja(self):    self._conflict("Assembly process step 3", "Assembly process 工程 7")
    def test_step_proc(self):  self._conflict("Assembly process step 3", "Assembly process process 4")

    # leadtime
    def test_lt_lead_time(self): self._conflict("Order leadtime 14 days", "Order lead time 21 days")
    def test_lt_lt(self):        self._conflict("Order leadtime 14 days", "Order lt 28 days")
    def test_lt_ja(self):        self._conflict("Order leadtime 14 days", "Order 納期 30 days")

    # metadata must NOT trigger conflicts
    def test_no_conflict_page(self):
        self._no_conflict(
            "System notes. page 12 capacity 200",
            "System notes. page 99 capacity 200",
        )

    def test_no_conflict_year(self):
        self._no_conflict(
            "Report year 2023 stock 100",
            "Report year 2025 stock 100",
        )

    def test_no_conflict_line(self):
        self._no_conflict(
            "Error on line 5 station 3",
            "Error on line 9 station 3",
        )


if __name__ == "__main__":
    unittest.main()
