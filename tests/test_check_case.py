"""Tests for tools/check_case.py, using a small fake checkout."""

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
"""

REG_TOP = """
  prim_subreg #(
    .DW      (7),
    .RESVAL  (7'h2),
    .Mubi    (1'b0)
  ) u_mio_outsel_0 (
  prim_subreg #(
    .DW      (7),
    .RESVAL  (7'h2),
    .Mubi    (1'b0)
  ) u_mio_outsel_1 (
"""

PATTERN = (r"\.RESVAL\s*\(\d+'h([0-9a-fA-F]+)\),\s*\.Mubi\s*\([^)]*\)\s*\)"
           r"\s*u_mio_outsel_\d+\s*\(")


def make_case():
    return {
        "id": "T",
        "title": "test case",
        "opentitan_revision": "not-a-real-revision",
        "expected_after_reset": {"value": 2, "meaning": "high-Z"},
        "requirements": [
            {"id": "R1", "file": "doc/guide.md", "line": 2, "text": "all outputs are high-Z",
             "states_value": 2},
            {"id": "R2", "file": "doc/guide.md", "line": 5, "text": "0     | Constant zero (default)",
             "states_value": 0},
        ],
        "design": [
            {"id": "D1", "kind": "line", "file": "data/block.hjson", "line": 3, "text": "resval: 2,",
             "value": 2},
            {"id": "D2", "kind": "all_instances", "file": "rtl/reg_top.sv", "pattern": PATTERN,
             "expected_count": 2, "value": 2},
        ],
        "finding": "R2 disagrees",
    }


class FakeCheckoutTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.write("doc/guide.md", GUIDE)
        self.write("data/block.hjson", "{\n  name: OUT,\n  resval: 2,\n}\n")
        self.write("rtl/reg_top.sv", REG_TOP)
        self.case = make_case()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_check(self):
        return check_case.check(self.case, self.root)

    def test_reports_disagreeing_requirement(self):
        report = self.run_check()
        self.assertTrue(report.evidence_ok)
        self.assertEqual(report.design_value, 2)
        self.assertEqual(report.inconsistencies, ["R2"])

    def test_moved_line_is_found_by_search(self):
        self.write("doc/guide.md", "Intro line\n" + GUIDE)
        report = self.run_check()
        self.assertTrue(report.evidence_ok)
        r1 = next(e for e in report.evidence if e.item_id == "R1")
        self.assertIn("moved from line 2", r1.detail)

    def test_missing_text_is_an_evidence_error(self):
        self.write("doc/guide.md", GUIDE.replace("all outputs are high-Z", "outputs are driven"))
        report = self.run_check()
        self.assertFalse(report.evidence_ok)

    def test_ambiguous_text_is_an_evidence_error(self):
        self.write("doc/guide.md", "all outputs are high-Z\n" + GUIDE)
        report = self.run_check()
        self.assertFalse(report.evidence_ok)

    def test_register_instances_that_disagree(self):
        self.write("rtl/reg_top.sv", REG_TOP.replace("(7'h2),\n    .Mubi    (1'b0)\n  ) u_mio_outsel_1",
                                                     "(7'h0),\n    .Mubi    (1'b0)\n  ) u_mio_outsel_1"))
        report = self.run_check()
        self.assertFalse(report.evidence_ok)

    def test_unexpected_instance_count(self):
        self.case["design"][1]["expected_count"] = 3
        self.assertFalse(self.run_check().evidence_ok)

    def test_design_value_differs_from_case(self):
        self.write("rtl/reg_top.sv", REG_TOP.replace("7'h2", "7'h0"))
        self.case["design"][1]["value"] = 0
        report = self.run_check()
        self.assertFalse(report.design_consistent)
        self.assertFalse(report.evidence_ok)

    def test_fixed_documentation_agrees(self):
        self.write("doc/guide.md", GUIDE.replace("Constant zero (default)", "Constant zero"))
        self.case["requirements"][1]["text"] = "0     | Constant zero"
        self.case["requirements"][1]["states_value"] = 2
        self.assertEqual(self.run_check().inconsistencies, [])

    def test_exit_codes(self):
        case_path = self.root / "case.json"
        case_path.write_text(json.dumps(self.case), encoding="utf-8")
        devnull = open(os.devnull, "w")
        self.addCleanup(devnull.close)
        stdout = sys.stdout
        sys.stdout = devnull
        try:
            plain = check_case.main([str(case_path), "--opentitan", str(self.root)])
            strict = check_case.main([str(case_path), "--opentitan", str(self.root),
                                      "--fail-on-inconsistency"])
            self.write("data/block.hjson", "{}\n")
            broken = check_case.main([str(case_path), "--opentitan", str(self.root)])
        finally:
            sys.stdout = stdout
        self.assertEqual((plain, strict, broken), (0, 1, 2))


class CaseFilesTest(unittest.TestCase):

    def test_every_case_file_loads(self):
        cases = sorted((ROOT / "cases").glob("*/case.json"))
        self.assertTrue(cases)
        for path in cases:
            case = check_case.load_case(path)
            ids = [i["id"] for i in case["requirements"] + case["design"]]
            self.assertEqual(len(ids), len(set(ids)), f"duplicate ids in {path}")


@unittest.skipUnless(os.environ.get("OPENTITAN_DIR"), "set OPENTITAN_DIR to an OpenTitan checkout")
class RealCheckoutTest(unittest.TestCase):

    def test_case_001_at_recorded_revision(self):
        case = check_case.load_case(ROOT / "cases/001-pinmux-mio-outsel-reset/case.json")
        report = check_case.check(case, Path(os.environ["OPENTITAN_DIR"]))
        self.assertTrue(report.evidence_ok)
        self.assertEqual(report.inconsistencies, ["R2"])


if __name__ == "__main__":
    unittest.main()
