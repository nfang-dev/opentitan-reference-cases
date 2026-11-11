# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Tests for claims/: sentence selection, reading model answers, and checking claims."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "claims"))

import check  # noqa: E402
import compare  # noqa: E402
import extract  # noqa: E402
import sentences  # noqa: E402


def field(name, lsb, width, sw="rw", resval=0):
    return {"name": name, "lsb": lsb, "width": width, "swaccess": sw, "hwaccess": "hro",
            "resval": resval, "tags": []}


MODEL = {"registers": [
    {"name": "CTRL", "regwen": "REGWEN", "fields": [field("en", 0, 1), field("prescaler", 1, 12)]},
    {"name": "REGWEN", "regwen": None, "fields": [field("regwen", 0, 1, "rw0c", 1)]},
    {"name": "CAUSE", "regwen": None, "fields": [field("cause", 0, 1, "rw0c", 0)]},
    {"name": "STATE", "regwen": None, "fields": [field("a", 0, 1, "rw1c"), field("b", 1, 1, "ro")]},
    {"name": "TEST", "regwen": None, "fields": [field("t", 0, 1, "wo", None)]},
    {"name": "EN0", "regwen": None, "fields": [field("en", 0, 4)]},
    {"name": "EN1", "regwen": None, "fields": [field("en", 0, 4)]},
]}


def claim(register, prop, value, quote, field_name=""):
    return {"register": register, "field": field_name, "property": prop, "value": value,
            "quote": quote}


def sentence(text, registers):
    return {"text": text, "registers": {r: [] for r in registers}}


class SentenceTest(unittest.TestCase):
    def test_mentions(self):
        table = sentences.name_table(MODEL)
        found = sentences.mentions("Set `CTRL.en` and then EN0; `en` alone is not a register, "
                                   "nor is CONTROL. See `en1`.", table)
        self.assertEqual([m["written"] for m in found], ["CTRL.en", "EN0", "EN1"])
        self.assertEqual(sentences.mentions("Write `EN` first.", table)[0]["registers"],
                         ["EN0", "EN1"])

    def test_sentences_and_lines(self):
        text = "# Title\n\nFirst sentence names CTRL. Second one\ncontinues here.\n\n" \
               "```\nCTRL code\n```\n- Item about `CAUSE`.\n"
        got = list(sentences.sentences_of("x.md", text))
        self.assertEqual([(a, b, s) for a, b, _, s in got], [
            (3, 3, "First sentence names CTRL."), (3, 4, "Second one continues here."),
            (9, 9, "- Item about `CAUSE`.")])


class ParseTest(unittest.TestCase):
    def test_parse(self):
        claims, err = extract.parse('{"claims": [{"register": "CTRL", "field": "en", '
                                    '"property": "reset_value", "value": "0", "quote": "q"}]}')
        self.assertIsNone(err)
        self.assertEqual(claims[0]["register"], "CTRL")
        self.assertEqual(extract.parse("{}")[1], "no claims list")
        self.assertTrue(extract.parse("not json")[1].startswith("not JSON"))
        self.assertTrue(extract.parse('{"claims": [{"property": "colour"}]}')[1])

    def test_prompt_mentions_every_property(self):
        for p in extract.PROPERTIES:
            self.assertIn(p, extract.SYSTEM)


class CheckTest(unittest.TestCase):
    def run_claim(self, c, text, named):
        return check.check_claim(c, sentence(text, named), MODEL, None)

    def test_outcomes(self):
        s = "The 12-bit `CTRL.prescaler` resets to 0 and `CTRL` is locked by `REGWEN`."
        named = ["CTRL", "REGWEN"]
        cases = [
            (claim("CTRL", "width_bits", "12", "12-bit", "prescaler"), "agrees"),
            (claim("CTRL", "width_bits", "8", "12-bit", "prescaler"), "disagrees"),
            (claim("CTRL.prescaler", "reset_value", "0", "resets to 0"), "agrees"),
            (claim("CTRL", "locked_by", "`REGWEN`", "locked by `REGWEN`"), "agrees"),
            (claim("CTRL", "reset_value", "0", "resets to 0"), "agrees"),
            (claim("CTRL", "width_bits", "13", "12-bit"), "not checkable"),
            (claim("CTRL", "software_access", "read-write", "is locked"), "agrees"),
            (claim("CTRL", "software_access", "sometimes", "is locked"), "unknown value"),
            (claim("CTRL", "reset_value", "0", "not in the text"), "quote not in sentence"),
            (claim("CTRL", "reset_value", "0", "resets to 0", "missing"), "not in description"),
            (claim("NOPE", "reset_value", "0", "resets to 0"), "not in description"),
            (claim("CAUSE", "reset_value", "0", "resets to 0"), "register not named in sentence"),
        ]
        for c, want in cases:
            with self.subTest(c=c):
                self.assertEqual(self.run_claim(c, s, named)["outcome"], want)

    def test_access_and_reset(self):
        r = self.run_claim(claim("CAUSE", "software_access", "write-0-to-clear", "writing 0"),
                           "Clear it by writing 0 to `CAUSE`.", ["CAUSE"])
        self.assertEqual((r["outcome"], r["described"]), ("agrees", "write-0-to-clear"))
        r = self.run_claim(claim("STATE", "software_access", "write-1-to-clear", "w1c"),
                           "`STATE` is w1c.", ["STATE"])
        self.assertEqual(r["outcome"], "not checkable")
        r = self.run_claim(claim("TEST", "reset_value", "0", "is 0"), "`TEST` is 0.", ["TEST"])
        self.assertEqual(r["outcome"], "not checkable")
        r = self.run_claim(claim("CTRL", "reset_value", "enabled", "enabled", "en"),
                           "`CTRL.en` is enabled after reset.", ["CTRL"])
        self.assertEqual((r["outcome"], r["described"]), ("disagrees", "0"))

    def test_multi_register_base_name(self):
        r = self.run_claim(claim("EN", "width_bits", "4", "4-bit"), "The 4-bit `EN` registers.",
                           ["EN0", "EN1"])
        self.assertEqual((r["outcome"], r["registers"]), ("agrees", ["EN0", "EN1"]))

    def test_hardware(self):
        results = {"seeds": {"1": {"observed": {
            "hw_reset": {"registers": [{"register": "CTRL", "mask": "0x1fff", "result": "pass"},
                                       {"register": "TEST", "mask": "0x0",
                                        "result": "no reset value specified"}]},
            "regwen_lock": {"registers": [{"register": "CTRL", "mask": "0x1fff",
                                           "result": "pass"}]},
            "rw": {"registers": [{"register": "CTRL", "round": 1, "mask": "0x1",
                                  "result": "pass"}]}}}}}
        f = MODEL["registers"][0]["fields"]
        self.assertEqual(check.hardware(results, "CTRL", f[1], "reset_value"),
                         "matches description")
        self.assertEqual(check.hardware(results, "TEST", None, "reset_value"), "not checked")
        self.assertEqual(check.hardware(results, "CTRL", None, "locked_by"),
                         "matches description")
        self.assertEqual(check.hardware(results, "CTRL", f[0], "software_access"),
                         "matches description")
        self.assertEqual(check.hardware(results, "CTRL", f[1], "software_access"), "not checked")
        self.assertEqual(check.hardware(results, "CTRL", f[1], "width_bits"), "not applicable")
        self.assertEqual(check.hardware(None, "CTRL", None, "reset_value"), "IP not simulated")


class CompareTest(unittest.TestCase):
    def test_compare(self):
        c = claim("CTRL", "reset_value", "0", "q")
        a = {"answers": [{"id": "x", "claims": [c]}, {"id": "y", "claims": []}]}
        b = {"answers": [{"id": "x", "claims": [dict(c, quote="other")]},
                         {"id": "y", "claims": [c]}]}
        self.assertEqual(compare.compare(a, b), (2, 1, ["y"]))


if __name__ == "__main__":
    unittest.main()
