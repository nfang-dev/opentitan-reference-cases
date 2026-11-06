"""Tests for the reset-value review tool (review/), on small made-up inputs."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "review"))

import design_index as di  # noqa: E402
import review  # noqa: E402
import statements  # noqa: E402

REG_TOP = """
  // R[ctrl]: V(False)
  //   F[en]: 0:0
  prim_subreg #(
    .DW      (1),
    .RESVAL  (1'h1)
  ) u_ctrl_en (
  //   F[mode]: 3:1
  prim_subreg #(
    .DW      (3),
    .RESVAL  (3'h2)
  ) u_ctrl_mode (
  // R[outsel_0]: V(False)
  prim_subreg #(
    .DW      (7),
    .RESVAL  (7'h2)
  ) u_outsel_0 (
  // R[outsel_1]: V(False)
  prim_subreg #(
    .DW      (7),
    .RESVAL  (7'h2)
  ) u_outsel_1 (
  // R[class_ctrl]: V(False)
  //   F[en_e0]: 0:0
  prim_subreg #(
    .DW      (1),
    .RESVAL  (1'h1)
  ) u_class_ctrl_en_e0 (
  // R[status]: V(True)
  //   F[busy]: 0:0
  prim_subreg_ext #(
    .DW    (1)
  ) u_status_busy (
"""

REG_PKG = """
  parameter logic [BlockAw-1:0] FOO_CTRL_OFFSET = 6'h 0;
  parameter logic [BlockAw-1:0] FOO_STATUS_OFFSET = 6'h 4;
  parameter logic [0:0] FOO_STATUS_BUSY_RESVAL = 1'h 1;
"""


def index() -> di.DesignIndex:
    regs = di.parse_reg_top(REG_TOP, "rtl/foo_reg_top.sv")
    di.fill_external(regs, REG_PKG, "rtl/foo_reg_pkg.sv")
    return di.DesignIndex(di.entries_of(regs))


class DesignIndexTest(unittest.TestCase):
    def test_fields_and_registers(self):
        idx = index()
        self.assertEqual(idx.lookup("CTRL.EN")[0].value, 1)
        self.assertEqual(idx.lookup("ctrl.mode")[0].value, 2)
        # The register value combines its fields at their bit positions: 1 | (2 << 1).
        self.assertEqual(idx.lookup("CTRL")[0].value, 5)
        self.assertEqual(idx.lookup("STATUS.BUSY")[0].value, 1)   # from the package

    def test_multireg_and_one_field_register(self):
        idx = index()
        self.assertEqual([e.value for e in idx.lookup("outsel")], [2, 2])
        self.assertEqual([e.value for e in idx.lookup("OUTSEL.OUT")], [2, 2])
        self.assertEqual(idx.lookup("outsel[*]")[0].key, "outsel_0")

    def test_near_names(self):
        idx = index()
        self.assertEqual(idx.lookup("CLASS_CTRL.E0_EN"), [])
        self.assertEqual(idx.near("CLASS_CTRL.E0_EN"), ["class_ctrl.en_e0"])
        self.assertEqual(idx.lookup("ctrl.nonexistent"), [])


def found(doc: str, idx=None):
    return statements.statements_in("hw/ip/foo/doc/guide.md", doc, idx or index())


class StatementsTest(unittest.TestCase):
    def test_table_default_and_sentence_after_it(self):
        doc = ("## Config\n\n`outsel` Value | Meaning\n------|------\n0 | Low (default)\n2 | High-Z\n\n"
               "The global default at reset is `2`.\n")
        out = found(doc)
        self.assertEqual([(s["line"], s["outcome"], s["stated"]) for s in out],
                         [(5, "disagrees", 0), (8, "agrees", 2)])
        self.assertEqual(out[0]["attribution"], "table header, line 3")
        self.assertIn("line 3", out[1]["attribution"])

    def test_words_and_values(self):
        out = found("The `CTRL.MODE` field resets to `0x2`.\n"
                    "Interrupts are disabled by default, see `CTRL.EN`.\n"
                    "The `OUTSEL` timeout is off if set to 0 (default).\n"
                    "At reset all fields in `STATUS` are set.\n")
        self.assertEqual([(s["name"], s["outcome"]) for s in out],
                         [("CTRL.MODE", "agrees"), ("CTRL.EN", "disagrees"),
                          ("OUTSEL", "disagrees"), ("STATUS", "agrees")])

    def test_unknown_name_is_reported_not_guessed(self):
        out = found("The `OUTSEL` register selects the output.\n"
                    "Set the `CLASS_CTRL.E0_EN` bit (default is enabled).\n")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["outcome"], "name not in design")
        self.assertEqual(out[0]["near"], ["class_ctrl.en_e0"])
        self.assertEqual(out[0]["near_outcome"], "agrees")

    def test_no_statement_without_value_or_single_register(self):
        out = found("Use `CTRL.EN` and `OUTSEL` together.\n"
                    "After reset, everything is enabled for all instances.\n"
                    "Upon reset the pads are high-Z.\n")
        self.assertEqual(out, [])

    def test_code_blocks_are_ignored(self):
        self.assertEqual(found("```\n`CTRL.MODE` resets to `0`.\n```\n"), [])

    def test_cue_sentences(self):
        text = "First line.\nAfter reset, all is quiet. Nothing else.\n"
        self.assertEqual(statements.cue_sentences(text, {1, 2}), [(2, "After reset, all is quiet.")])


class CasesComparisonTest(unittest.TestCase):
    def test_against_reference_cases(self):
        found = [{"file": "hw/ip_templates/pinmux/doc/programmers_guide.md", "line": 48,
                  "outcome": "disagrees"},
                 {"file": "hw/ip/foo/doc/guide.md", "line": 1, "outcome": "agrees"}]
        rows, extra = review.cases_comparison(found, ROOT / "cases")
        result = {r["claim"]: r["result"] for r in rows}
        self.assertEqual(result["001-C2"], "same")
        self.assertEqual(result["001-C1"], "not found")
        self.assertEqual(result["004-C1"], "outside scope")
        self.assertEqual(len(extra), 1)


if __name__ == "__main__":
    unittest.main()
