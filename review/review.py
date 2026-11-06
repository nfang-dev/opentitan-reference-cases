#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Answer a question about a register's reset value from the documentation, check the answer
against the design, and write a report a reviewer can follow.

  review.py ask "<question>" --opentitan DIR [--earlier DIR] --out report.md [--json report.json]
  review.py scan --opentitan DIR --out scan.md [--json scan.json]
  review.py cases --opentitan DIR --scan scan.json --out cases.md

ask:   1. find passages (BM25 over the hand-written documentation; with --earlier, passages of
          the earlier revision are kept but ranked below every current passage, and are not
          used for the check);
       2. in the passages found, find statements that give a reset or default value
          (statements.py);
       3. look up the register's reset value in the register RTL (design_index.py);
       4. compare, and write the report: passages and their revision, statements, design
          evidence with file and line, outcome, and what was not checked.
scan:  the same check on every statement in the documentation, without a question.
cases: compare the outcomes of a scan with the labeled claims of the reference cases.

Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "retrieval"))

import corpus  # noqa: E402
import rank  # noqa: E402
import statements as st_mod  # noqa: E402
from design_index import DesignIndex  # noqa: E402

TOP = 5
OUTCOME_ORDER = ["disagrees", "name not in design", "design values differ", "value in words",
                 "agrees"]


def checkout_revision(root: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _value(v) -> str:
    if isinstance(v, int):
        return f"{v} (0x{v:x})" if v > 9 else str(v)
    return str(v)


def _module(rel: str) -> str:
    return corpus.module_of(rel)


# ---------------------------------------------------------------------------- ask

def ask(question: str, root: Path, earlier: Path | None, top: int = TOP) -> dict:
    passages = corpus.build(root)
    earlier_rev = None
    if earlier:
        earlier_rev = checkout_revision(earlier)
        passages += corpus.build_earlier(earlier, earlier_rev, passages)
    _, rankings = rank.rank_bm25(passages, {"q": question}, earlier_last=True)
    ranked = rankings["q"]
    current = [p for p in ranked if "revision" not in p][:top]
    outdated = [p for p in ranked if "revision" in p]

    by_id = {p["id"]: p for p in passages}
    found, unchecked = [], []
    indexes: dict[str, DesignIndex] = {}
    for p in current:
        rel = p["path"]
        if rel not in indexes:
            indexes[rel] = DesignIndex.for_document(root, rel)
        wanted = set(range(p["start_line"], p["end_line"] + 1))
        text = (root / rel).read_text(encoding="utf-8")
        got = st_mod.statements_in(rel, text, indexes[rel], wanted)
        for s in got:
            s["passage"] = p["id"]
            found.append(s)
        lines_with = {s["line"] for s in got}
        for no, sentence in st_mod.cue_sentences(text, wanted):
            if no not in lines_with:
                unchecked.append({"file": rel, "line": no, "text": sentence})
    # Registers the question names: check every statement about them in the same modules'
    # documentation too, since the passages found may not include all of them.
    asked = question_registers(question, indexes)
    elsewhere = []
    if asked:
        seen = {(s["file"], s["line"], s["name"]) for s in found}
        modules = {_module(p["path"]) for p in current}
        for rel in corpus.select_files(root):
            if _module(rel) not in modules:
                continue
            idx = indexes.get(rel) or DesignIndex.for_document(root, rel)
            for s in st_mod.statements_in(rel, (root / rel).read_text(encoding="utf-8"), idx):
                if _base_name(s["name"]) in asked and (s["file"], s["line"], s["name"]) not in seen:
                    elsewhere.append(s)
    return {
        "question": question,
        "registers_in_question": sorted(asked),
        "opentitan_revision": checkout_revision(root),
        "earlier_revision": earlier_rev,
        "retrieval": {"method": "bm25", "corpus_passages": len(passages), "top": top},
        "passages": [dict(p, heading=by_id[p["id"]]["heading"]) for p in current],
        "outdated_passages": outdated,
        "statements": found,
        "statements_elsewhere": elsewhere,
        "unchecked_sentences": unchecked,
        "conclusion": conclude(found + elsewhere),
    }


def _base_name(name: str) -> str:
    """Register part of a written name, lower case, without index or field."""
    import re
    n = re.sub(r"\[[^\]]*\]", "", name).lower().split(".")[0]
    return re.sub(r"_\d+$", "", n)


def question_registers(question: str, indexes: dict) -> set[str]:
    """Register names in the question (code style or upper case with an underscore) that some
    module of the passages found defines."""
    import re
    tokens = set(re.findall(r"`([^`]+)`", question)) | set(re.findall(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+(?:\.[A-Z0-9_]+)?\b", question))
    out = set()
    for t in tokens:
        if any(idx.lookup(t) for idx in indexes.values()):
            out.add(_base_name(t))
    return out


def conclude(found: list[dict]) -> dict:
    if not found:
        return {"outcome": "not checked",
                "text": "No passage found gives a reset or default value in a form the tool can "
                        "compare (a number, or enabled/disabled/cleared for a named register). "
                        "Read the passages listed; the question needs a person to decide."}
    worst = min(found, key=lambda s: OUTCOME_ORDER.index(s["outcome"]))["outcome"]
    texts = {
        "disagrees": "At least one statement gives a value that differs from the design's reset value.",
        "name not in design": "A statement names a register or field that the design does not define "
                              "under that name; see the closest design names.",
        "design values differ": "The name matches registers with different reset values; the "
                                "statement cannot be checked as one value.",
        "value in words": "A statement gives its value in words that do not map to one number.",
        "agrees": "Every statement found agrees with the design's reset value.",
    }
    return {"outcome": worst, "text": texts[worst]}


def ask_markdown(r: dict) -> str:
    rev = r["opentitan_revision"]
    L = [f"# Review: {r['question']}", ""]
    L.append(f"OpenTitan revision `{rev}`." + (
        f" Passages of the earlier revision `{r['earlier_revision']}` were searched too, ranked "
        "below every current passage, and not used for the check." if r["earlier_revision"] else ""))
    L += ["", f"**Outcome: {r['conclusion']['outcome']}.** {r['conclusion']['text']}", ""]

    L += ["## 1. Passages found", "",
          f"BM25 over {r['retrieval']['corpus_passages']} passages of hand-written documentation; "
          f"the first {len(r['passages'])} current passages:", "",
          "| # | Passage | Section | Score |", "|---|---|---|---|"]
    for i, p in enumerate(r["passages"], 1):
        L.append(f"| {i} | `{p['path']}` lines {p['start_line']}–{p['end_line']} | "
                 f"{p['heading'] or '-'} | {p['score']:.2f} |")
    if r["outdated_passages"]:
        L += ["", "Earlier-revision passages also among the first ten (not used): " +
              ", ".join(f"`{p['path']}` {p['start_line']}–{p['end_line']}"
                        for p in r["outdated_passages"]) + "."]

    L += ["", "## 2. Statements that give a value, and the design", ""]
    if not r["statements"]:
        L.append("None in these passages.")
    for s in r["statements"]:
        L += statement_markdown(s)
    if r["registers_in_question"]:
        names = ", ".join(f"`{n}`" for n in r["registers_in_question"])
        L += ["", f"### Other statements about {names} in the same modules' documentation", ""]
        if not r["statements_elsewhere"]:
            L.append("None.")
        for s in r["statements_elsewhere"]:
            L += statement_markdown(s)

    if r["unchecked_sentences"]:
        L += ["", "### Sentences about reset or defaults that the tool could not check", "",
              "No value, or no single register, could be identified in these; a reviewer should "
              "read them.", ""]
        for u in r["unchecked_sentences"]:
            L.append(f"- `{u['file']}` line {u['line']}: \"{u['text']}\"")

    L += ["", "## 3. What this check does not cover", "",
          "- Statements that describe a value only in words such as \"high-Z\" or \"enabled for all "
          "instances\" are not compared; nor are statements whose register cannot be identified "
          "from a code-style name in the sentence or just above it.",
          "- The design value is the register's reset value in the generated register RTL. It comes "
          "from the same register description as registers.md, so it is not independent of it, and "
          "it does not show what the rest of the logic does with the value. A behavior check "
          "(simulation) is needed for that; see `behavior/` for one.",
          "- Passages ranked below the first few are not read; a statement elsewhere in the "
          "documentation may say something different. `review.py scan` checks every statement.", ""]
    return "\n".join(L)


def statement_markdown(s: dict) -> list[str]:
    L = [f"- **{s['outcome']}** — `{s['file']}` line {s['line']} ({s['kind']}):",
         f"  > {s['text']}",
         f"  - Register: `{s['name']}` ({s['attribution']})."]
    stated = s["stated"] if s["stated"] is not None else s.get("stated_words")
    L.append(f"  - Stated value: {_value(stated)}.")
    d = s.get("design")
    if d:
        inst = f", {d['instances']} instances" if d["instances"] > 1 else ""
        L.append(f"  - Design reset value: {_value(d['value'])} (`{d['file']}` line {d['line']}{inst}).")
    if s.get("near"):
        L.append(f"  - Not a design name. Closest design names: {', '.join('`'+n+'`' for n in s['near'])}.")
    if s.get("near_design"):
        nd = s["near_design"]
        L.append(f"  - If `{s['near'][0]}` is meant: design reset value {_value(nd['value'])} "
                 f"(`{nd['file']}` line {nd['line']}), so the value {s['near_outcome']}.")
    return L


# ---------------------------------------------------------------------------- scan

def scan_markdown(found: list[dict], rev: str) -> str:
    counts = {o: sum(1 for s in found if s["outcome"] == o) for o in OUTCOME_ORDER}
    L = ["# Scan: reset and default values stated in the documentation", "",
         f"OpenTitan revision `{rev}`. Every hand-written document in the retrieval corpus was "
         f"read; {len(found)} statements give a value the tool can compare.", "",
         "| Outcome | Statements |", "|---|---|"]
    L += [f"| {o} | {n} |" for o, n in counts.items() if n]
    L.append("")
    for o in OUTCOME_ORDER:
        group = [s for s in found if s["outcome"] == o]
        if not group:
            continue
        L += [f"## {o}", ""]
        for s in group:
            L += statement_markdown(s)
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------- cases

def cases_comparison(found: list[dict], cases_dir: Path) -> tuple[list[dict], list[dict]]:
    """For each labeled claim, what the scan found for its requirement lines."""
    by_line = {}
    for s in found:
        by_line.setdefault((s["file"], s["line"]), []).append(s)
    rows, matched = [], set()
    for path in sorted(cases_dir.glob("*/case.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        reqs = {r["id"]: r for r in case["requirements"]}
        for claim in case["claims"]:
            hits = []
            for rid in claim["requirements"]:
                key = (reqs[rid]["file"], reqs[rid]["line"])
                hits += by_line.get(key, [])
                if key in by_line:
                    matched.add(key)
            reset_claim = "after reset" in claim["setting"]
            if not reset_claim:
                result = "outside scope"
            elif not hits:
                result = "not found"
            else:
                outcomes = {h["outcome"] for h in hits}
                result = "same" if outcomes == {claim["label"]} else "different: " + ", ".join(sorted(outcomes))
            rows.append({"claim": f"{case['id']}-{claim['id']}", "setting": claim["setting"],
                         "label": claim["label"], "tool": sorted({h['outcome'] for h in hits}),
                         "result": result})
    extra = [s for s in found if (s["file"], s["line"]) not in matched]
    return rows, extra


def cases_markdown(rows: list[dict], extra: list[dict]) -> str:
    n = {k: sum(1 for r in rows if r["result"] == k or r["result"].startswith(k))
         for k in ("same", "different", "not found", "outside scope")}
    L = ["# The review tool against the labeled reference cases", "",
         "Each labeled claim of cases 001 to 004 is compared with what `review.py scan` reports for "
         "the requirement lines the claim comes from.", "",
         f"- Same outcome as the label: {n['same']}",
         f"- Different outcome: {n['different']}",
         f"- Requirement not found by the tool: {n['not found']}",
         f"- Outside the tool's scope (not a reset value): {n['outside scope']}", "",
         "| Claim | Setting | Label | Tool | Result |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['claim']} | {r['setting']} | {r['label']} | "
                 f"{', '.join(r['tool']) or '-'} | {r['result']} |")
    L += ["", f"## Statements the tool found outside the reference cases ({len(extra)})", ""]
    for s in extra:
        L += statement_markdown(s)
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--opentitan", required=True, type=Path)
    a.add_argument("--earlier", type=Path)
    a.add_argument("--top", type=int, default=TOP)
    a.add_argument("--out", required=True, type=Path)
    a.add_argument("--json", type=Path)
    s = sub.add_parser("scan")
    s.add_argument("--opentitan", required=True, type=Path)
    s.add_argument("--out", required=True, type=Path)
    s.add_argument("--json", type=Path)
    c = sub.add_parser("cases")
    c.add_argument("--scan", required=True, type=Path, help="JSON written by review.py scan")
    c.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    if args.cmd == "ask":
        r = ask(args.question, args.opentitan, args.earlier, args.top)
        args.out.write_text(ask_markdown(r), encoding="utf-8")
        if args.json:
            args.json.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
        print(f"{r['conclusion']['outcome']}: {len(r['statements'])} statements -> {args.out}")
    elif args.cmd == "scan":
        found = st_mod.scan(args.opentitan)
        rev = checkout_revision(args.opentitan)
        args.out.write_text(scan_markdown(found, rev), encoding="utf-8")
        if args.json:
            args.json.write_text(json.dumps({"opentitan_revision": rev, "statements": found},
                                            indent=1) + "\n", encoding="utf-8")
        print(f"{len(found)} statements -> {args.out}")
    else:
        found = json.loads(args.scan.read_text(encoding="utf-8"))["statements"]
        rows, extra = cases_comparison(found, REPO / "cases")
        args.out.write_text(cases_markdown(rows, extra), encoding="utf-8")
        print(f"{len(rows)} claims compared -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
