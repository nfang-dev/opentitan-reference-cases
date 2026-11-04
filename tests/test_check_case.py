"""Tests for tools/check_case.py, using a small fake checkout."""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import check_case  # noqa: E402

GUIDE = """# Programmer's Guide
Upon POR, all outputs are high-Z.

Value | Meaning
0     | Constant zero (default)
2     | High-Z
The global default at reset is `2`.
Writing requires the WRITE_ENABLE register.
"""

BLOCK = """{
  name: "OUTSEL",
  fields: [
    { name: "OUT",
      resval: 2,
    }
  ]
  name: "OTHER",
  fields: [
    { name: "X",
      resval: 2,
    }
  ]
}
"""

REG_TOP = """
  prim_subreg #(
    .DW      (7),
    .RESVAL  (7'h2),
    .Mubi    (1'b0)
  ) u_outsel_0 (
  prim_subreg #(
    .DW      (7),
    .RESVAL  (7'h2),
    .Mubi    (1'b0)
  ) u_outsel_1 (
"""

PATTERN = (r"\.RESVAL\s*\(\d+'h([0-9a-fA-F]+)\),\s*\.Mubi\s*\([^)]*\)\s*\)"
           r"\s*u_outsel_\d+\s*\(")


def make_case():
    return {
        "schema": 2,
        "id": "T",
        "title": "test case",
        "opentitan_revision": "not-a-real-revision",
        "requirements": [
            {"id": "R1", "file": "doc/guide.md", "line": 2, "text": "all outputs are high-Z"},
            {"id": "R2", "file": "doc/guide.md", "line": 5, "text": "0     | Constant zero (default)"},
            {"id": "R3", "file": "doc/guide.md", "line": 8, "text": "WRITE_ENABLE register"},
        ],
        "design": [
            {"id": "D1", "kind": "line", "file": "data/block.hjson", "after": 'name: "OUTSEL"',
             "line": 5, "text": "resval: 2,", "value": 2},
            {"id": "D2", "kind": "all_instances", "file": "rtl/reg_top.sv", "pattern": PATTERN,
             "expected_count": 2, "value": 2},
            {"id": "D3", "kind": "absent", "file": "data/block.hjson",
             "pattern": r'name:\s*"WRITE_ENABLE"', "description": "no WRITE_ENABLE register"},
        ],
        "claims": [
            {"id": "C1", "setting": "OUT", "requirements": ["R1"], "stated": 2,
             "design": ["D1", "D2"], "label": "agrees"},
            {"id": "C2", "setting": "OUT", "requirements": ["R2"], "stated": 0,
             "design": ["D1", "D2"], "label": "disagrees"},
            {"id": "C3", "setting": "write enable", "requirements": ["R3"],
             "stated_text": "enabled", "design": ["D3"], "label": "unresolved"},
        ],
    }


class FakeCheckoutTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.write("doc/guide.md", GUIDE)
        self.write("data/block.hjson", BLOCK)
        self.write("rtl/reg_top.sv", REG_TOP)
        self.case = make_case()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_check(self):
        return check_case.check(self.case, self.root)

    def outcomes(self, report):
        return {c.claim_id: c.outcome for c in report.claims}

    def test_outcomes_match_labels(self):
        report = self.run_check()
        self.assertTrue(report.evidence_ok)
        self.assertTrue(report.labels_ok)
        self.assertEqual(self.outcomes(report),
                         {"C1": "agrees", "C2": "disagrees", "C3": "unresolved"})
        self.assertEqual(report.not_agreeing, ["C2", "C3"])

    def test_moved_line_is_found_by_search(self):
        self.write("doc/guide.md", "Intro line\n" + GUIDE)
        report = self.run_check()
        self.assertTrue(report.evidence_ok)
        r1 = next(e for e in report.evidence if e.item_id == "R1")
        self.assertIn("moved from line 2", r1.detail)

    def test_anchor_disambiguates_repeated_text(self):
        # "resval: 2," occurs twice; the anchor picks the one after OUTSEL.
        self.write("data/block.hjson", "\n\n" + BLOCK)
        report = self.run_check()
        d1 = next(e for e in report.evidence if e.item_id == "D1")
        self.assertTrue(d1.ok)
        self.assertIn("moved from line 5", d1.detail)

    def test_repeated_text_without_anchor_is_an_error(self):
        del self.case["design"][0]["after"]
        self.write("data/block.hjson", "\n\n" + BLOCK)
        self.assertFalse(self.run_check().evidence_ok)

    def test_duplicate_anchor_is_an_error(self):
        self.write("data/block.hjson", BLOCK + 'name: "OUTSEL"\n')
        self.assertFalse(self.run_check().evidence_ok)

    def test_missing_text_is_an_evidence_error(self):
        self.write("doc/guide.md", GUIDE.replace("all outputs are high-Z", "outputs are driven"))
        self.assertFalse(self.run_check().evidence_ok)

    def test_register_instances_that_disagree(self):
        self.write("rtl/reg_top.sv", REG_TOP.replace(
            "(7'h2),\n    .Mubi    (1'b0)\n  ) u_outsel_1", "(7'h0),\n    .Mubi    (1'b0)\n  ) u_outsel_1"))
        self.assertFalse(self.run_check().evidence_ok)

    def test_unexpected_instance_count(self):
        self.case["design"][1]["expected_count"] = 3
        self.assertFalse(self.run_check().evidence_ok)

    def test_design_value_differs_from_case(self):
        self.write("rtl/reg_top.sv", REG_TOP.replace("7'h2", "7'h0"))
        self.assertFalse(self.run_check().evidence_ok)

    def test_absent_item_that_appears_is_an_error(self):
        self.write("data/block.hjson", BLOCK + '  name: "WRITE_ENABLE",\n')
        report = self.run_check()
        self.assertFalse(report.evidence_ok)

    def test_label_change_is_detected(self):
        # The documentation is fixed: R2 now agrees, but the case still says "disagrees".
        self.write("doc/guide.md", GUIDE.replace("0     | Constant zero (default)", "0     | Constant zero"))
        self.case["requirements"][1]["text"] = "0     | Constant zero"
        self.case["claims"][1]["stated"] = 2
        report = self.run_check()
        self.assertTrue(report.evidence_ok)
        self.assertFalse(report.labels_ok)
        self.assertTrue(report.needs_review)
        self.assertIn("RECORDED LABEL: disagrees", check_case.format_report(report))

    def test_exit_codes(self):
        def run(case, *extra):
            path = self.root / "case.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                return check_case.main([str(path), "--opentitan", str(self.root), *extra])

        self.assertEqual(run(self.case), 0)
        self.assertEqual(run(self.case, "--fail-on-inconsistency"), 1)
        agreeing = copy.deepcopy(self.case)
        agreeing["claims"] = [agreeing["claims"][0]]
        self.assertEqual(run(agreeing, "--fail-on-inconsistency"), 0)
        wrong_label = copy.deepcopy(self.case)
        wrong_label["claims"][0]["label"] = "disagrees"
        self.assertEqual(run(wrong_label), 2)
        self.write("data/block.hjson", "{}\n")
        self.assertEqual(run(self.case), 2)


class LoadCaseTest(unittest.TestCase):

    def load(self, case):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            path.write_text(json.dumps(case), encoding="utf-8")
            return check_case.load_case(path)

    def test_rejects_unknown_reference(self):
        case = make_case()
        case["claims"][0]["design"].append("D9")
        with self.assertRaises(ValueError):
            self.load(case)

    def test_rejects_unknown_label(self):
        case = make_case()
        case["claims"][0]["label"] = "maybe"
        with self.assertRaises(ValueError):
            self.load(case)

    def test_rejects_duplicate_ids(self):
        case = make_case()
        case["design"][1]["id"] = "D1"
        with self.assertRaises(ValueError):
            self.load(case)

    def test_rejects_old_schema(self):
        case = make_case()
        case["schema"] = 1
        with self.assertRaises(ValueError):
            self.load(case)


class CaseFilesTest(unittest.TestCase):

    def test_every_case_file_loads(self):
        cases = sorted((ROOT / "cases").glob("*/case.json"))
        self.assertGreaterEqual(len(cases), 3)
        revisions = {check_case.load_case(p)["opentitan_revision"] for p in cases}
        self.assertEqual(len(revisions), 1, "all cases should use one OpenTitan revision")


@unittest.skipUnless(os.environ.get("OPENTITAN_DIR"), "set OPENTITAN_DIR to an OpenTitan checkout")
class RealCheckoutTest(unittest.TestCase):

    def test_all_cases_at_recorded_revision(self):
        checkout = Path(os.environ["OPENTITAN_DIR"])
        for path in sorted((ROOT / "cases").glob("*/case.json")):
            with self.subTest(case=path.parent.name):
                report = check_case.check(check_case.load_case(path), checkout)
                self.assertTrue(report.evidence_ok, check_case.format_report(report))
                self.assertTrue(report.labels_ok, check_case.format_report(report))


if __name__ == "__main__":
    unittest.main()
