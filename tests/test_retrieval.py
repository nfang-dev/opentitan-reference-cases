"""Tests for the retrieval comparison scripts, using a small fake checkout."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "retrieval"))

import check_queries  # noqa: E402
import corpus  # noqa: E402
import evaluate  # noqa: E402
import rank  # noqa: E402

GUIDE = """# Programmer's Guide

## Configuration

Upon reset, all outputs of the [`OUTSEL`](registers.md#outsel) register are high-Z.

```c
# not a heading
```

## Other

<!-- BEGIN CMDGEN util/regtool.py -->
Generated text that must not be indexed.
<!-- END CMDGEN -->
Hand-written text after the generated block.
"""


def write(root: Path, rel: str, text: str = "# Title\n\nBody text.\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class FakeCheckout(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        write(self.root, "hw/ip/foo/doc/programmers_guide.md", GUIDE)
        write(self.root, "hw/ip/foo/doc/registers.md")
        write(self.root, "hw/ip/foo/doc/checklist.md")
        write(self.root, "hw/ip/foo/dv/README.md")
        write(self.root, "hw/ip_templates/bar/doc/programmers_guide.md")
        write(self.root, "hw/ip_templates/bar/README.md.tpl", "# ${name}\n")
        write(self.root, "hw/top_earlgrey/ip_autogen/bar/README.md")
        write(self.root, "hw/top_darjeeling/ip_autogen/bar/README.md")
        write(self.root, "hw/ip_templates/baz/doc/theory_of_operation.md.tpl", "# ${name}\n")
        write(self.root, "hw/top_darjeeling/ip_autogen/baz/doc/theory_of_operation.md")
        os.symlink("programmers_guide.md", self.root / "hw/ip/foo/doc/link.md")

    def tearDown(self):
        self._tmp.cleanup()


class CorpusTest(FakeCheckout):
    def test_file_selection(self):
        self.assertEqual(corpus.select_files(self.root), [
            "hw/ip/foo/doc/programmers_guide.md",
            "hw/ip_templates/bar/doc/programmers_guide.md",
            "hw/top_darjeeling/ip_autogen/baz/doc/theory_of_operation.md",
            "hw/top_earlgrey/ip_autogen/bar/README.md",
        ])

    def test_passages(self):
        rel = "hw/ip/foo/doc/programmers_guide.md"
        passages = corpus.passages_of(rel, GUIDE)
        by_heading = {p["heading"]: p for p in passages}
        config = by_heading["Programmer's Guide > Configuration"]
        self.assertEqual((config["start_line"], config["end_line"]), (5, 9))
        self.assertIn("all outputs of the `OUTSEL` register", config["text"])
        self.assertNotIn("registers.md", config["text"])
        self.assertTrue(config["text"].startswith("foo programmers_guide.md: "))
        other = by_heading["Programmer's Guide > Other"]
        self.assertNotIn("Generated text", other["text"])
        self.assertEqual(other["start_line"], other["end_line"])
        self.assertIn("Hand-written text", other["text"])
        self.assertEqual(len(passages), 2)

    def test_long_section_is_split(self):
        para = "word " * 50
        text = "# Title\n\n" + "\n\n".join(f"{i} {para}" for i in range(20)) + "\n"
        passages = corpus.passages_of("hw/ip/foo/README.md", text)
        self.assertGreater(len(passages), 1)
        for p in passages:
            body = p["text"].split("\n", 1)[1]
            self.assertLessEqual(len(body), corpus.MAX_CHARS)
        starts = [p["start_line"] for p in passages]
        self.assertEqual(starts, sorted(starts))


class Bm25Test(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(rank.tokenize("What is IO_MEAS_CTRL_EN after the reset?"),
                         ["io", "meas", "ctrl", "en", "after", "reset"])

    def test_ranking(self):
        passages = [
            {"id": "a.md:1-1", "path": "a.md", "start_line": 1, "end_line": 1,
             "text": "the clock measurement is enabled by the measure control register"},
            {"id": "b.md:1-1", "path": "b.md", "start_line": 1, "end_line": 1,
             "text": "the uart baud rate is set by the nco"},
            {"id": "c.md:1-1", "path": "c.md", "start_line": 1, "end_line": 1,
             "text": "the uart baud rate is set by the nco"},
        ]
        params, rankings = rank.rank_bm25(passages, {"Q1": "clock measurement enable", "Q2": "uart nco"})
        self.assertEqual(rankings["Q1"][0]["id"], "a.md:1-1")
        # Equal scores are ordered by passage id, so results are deterministic.
        self.assertEqual([r["id"] for r in rankings["Q2"][:2]], ["b.md:1-1", "c.md:1-1"])


class EvaluateTest(unittest.TestCase):
    TARGETS = [{"path": "a.md", "lines": [10, 12]}]

    def passage(self, path, start, end):
        return {"id": f"{path}:{start}-{end}", "path": path, "start_line": start, "end_line": end}

    def test_hit_requires_same_file_and_overlap(self):
        self.assertTrue(evaluate.is_hit(self.passage("a.md", 12, 20), self.TARGETS))
        self.assertTrue(evaluate.is_hit(self.passage("a.md", 1, 10), self.TARGETS))
        self.assertFalse(evaluate.is_hit(self.passage("a.md", 13, 20), self.TARGETS))
        self.assertFalse(evaluate.is_hit(self.passage("b.md", 10, 12), self.TARGETS))

    def test_metrics(self):
        m = evaluate.metrics([1, 3, None, 6])
        self.assertEqual((m["n"], m["recall_at_1"], m["recall_at_5"]), (4, 1, 2))
        self.assertAlmostEqual(m["mrr_at_10"], round((1 + 1 / 3 + 1 / 6) / 4, 3))

    def test_consistency(self):
        queries = {"opentitan_revision": "r1", "queries": [{"id": "Q1", "question": "x?"}]}
        good = {"method": "bm25", "opentitan_revision": "r1", "corpus": {"sha256": "c"},
                "questions_sha256": rank.questions_hash({"Q1": "x?"})}
        self.assertEqual(evaluate.consistency_problems(queries, [good]), [])
        stale = dict(good, method="embedding", questions_sha256="old", corpus={"sha256": "d"})
        problems = evaluate.consistency_problems(queries, [good, stale])
        self.assertEqual(len(problems), 2)


class CheckQueriesTest(FakeCheckout):
    def queries(self, **target):
        t = {"path": "hw/ip/foo/doc/programmers_guide.md", "lines": [5, 5], "quote": "Upon reset"}
        t.update(target)
        return {"groups": {"case": ""},
                "queries": [{"id": "Q1", "group": "case", "question": "?", "targets": [t]}]}

    def test_confirmed(self):
        self.assertEqual(check_queries.check(self.queries(), self.root), [])

    def test_problems(self):
        self.assertIn("quote not found",
                      check_queries.check(self.queries(lines=[3, 3]), self.root)[0])
        self.assertIn("outside the file",
                      check_queries.check(self.queries(lines=[5, 99]), self.root)[0])
        self.assertIn("not in the corpus",
                      check_queries.check(self.queries(path="hw/ip/foo/doc/registers.md"), self.root)[0])


class TwoRevisionTest(unittest.TestCase):
    def test_earlier_passages_keep_only_changed_text(self):
        with tempfile.TemporaryDirectory() as old_dir, tempfile.TemporaryDirectory() as new_dir:
            old, new = Path(old_dir), Path(new_dir)
            write(old, "hw/ip/foo/README.md", "# Foo\n\nSame text.\n\n## Reset\n\nOld default is 0.\n")
            write(new, "hw/ip/foo/README.md", "# Foo\n\nSame text.\n\n## Reset\n\nNew default is 2.\n")
            current = corpus.build(new)
            earlier = corpus.build_earlier(old, "0123456789abcdef", current)
            self.assertEqual(len(earlier), 1)
            self.assertIn("Old default", earlier[0]["text"])
            self.assertEqual(earlier[0]["revision"], "0123456789ab")
            self.assertTrue(earlier[0]["id"].startswith("0123456789ab:hw/ip/foo/README.md:"))

    def test_only_current_passages_are_correct(self):
        targets = [{"path": "a.md", "lines": [3, 3]}]
        current = {"path": "a.md", "start_line": 1, "end_line": 5}
        old = dict(current, revision="0123456789ab")
        self.assertTrue(evaluate.is_hit(current, targets))
        self.assertFalse(evaluate.is_hit(old, targets))
        self.assertTrue(evaluate.is_outdated_hit(old, targets))
        self.assertFalse(evaluate.is_outdated_hit(current, targets))

    def test_outdated_counts(self):
        queries = {"groups": {"changed": ""}, "queries": [
            {"id": "V1", "group": "changed", "targets": [{"path": "a.md", "lines": [1, 1]}],
             "outdated": [{"path": "a.md", "lines": [1, 1]}]},
            {"id": "V2", "group": "changed", "targets": [{"path": "b.md", "lines": [1, 1]}],
             "outdated": [{"path": "b.md", "lines": [1, 1]}]},
        ]}

        def item(path, revision=None):
            d = {"id": path, "path": path, "start_line": 1, "end_line": 1}
            if revision:
                d["revision"] = revision
            return d
        result = {"method": "m", "rankings": {
            "V1": [item("a.md", "r"), item("a.md")],
            "V2": [item("b.md"), item("b.md", "r")],
        }}
        s = evaluate.score(queries, result)
        self.assertEqual(s["ranks"], {"V1": 2, "V2": 1})
        self.assertEqual(s["outdated_ranks"], {"V1": 1, "V2": 2})
        self.assertEqual(s["outdated_above"], ["V1"])
        self.assertEqual(s["earlier_first"], ["V1"])

    def test_load_queries_merges_and_checks(self):
        with tempfile.TemporaryDirectory() as d:
            a, b, c = Path(d, "a.json"), Path(d, "b.json"), Path(d, "c.json")
            a.write_text(json.dumps({"opentitan_revision": "r1", "groups": {"x": ""},
                                     "queries": [{"id": "Q1"}]}))
            b.write_text(json.dumps({"opentitan_revision": "r1", "earlier_revision": "r0",
                                     "groups": {"y": ""}, "queries": [{"id": "V1"}]}))
            c.write_text(json.dumps({"opentitan_revision": "r2", "groups": {}, "queries": [{"id": "Q1"}]}))
            merged = rank.load_queries([a, b])
            self.assertEqual([q["id"] for q in merged["queries"]], ["Q1", "V1"])
            self.assertEqual(merged["earlier_revision"], "r0")
            self.assertEqual(set(merged["groups"]), {"x", "y"})
            with self.assertRaises(ValueError):
                rank.load_queries([a, c])
            with self.assertRaises(ValueError):
                rank.load_queries([a, a])


class QuerySetTest(unittest.TestCase):
    def test_query_files_are_well_formed(self):
        files = [ROOT / "retrieval" / "queries.json", ROOT / "retrieval" / "queries_changed.json"]
        merged = rank.load_queries(files)
        for q in merged["queries"]:
            self.assertIn(q["group"], merged["groups"])
            self.assertTrue(q["targets"])
            self.assertIsInstance(q["checked"], bool)
            for t in q["targets"] + q.get("outdated", []):
                self.assertLessEqual(t["lines"][0], t["lines"][1])
                self.assertTrue(t["quote"])
        changed = json.loads(files[1].read_text(encoding="utf-8"))
        self.assertTrue(changed["earlier_revision"])
        self.assertTrue(all(q["outdated"] for q in changed["queries"]))


if __name__ == "__main__":
    unittest.main()
