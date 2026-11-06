#!/usr/bin/env python3
"""Check the retrieval query set against OpenTitan checkouts.

For every target passage of every query, confirm that the file is part of the corpus
(see corpus.py) and that the recorded quote appears within the recorded line range.
Outdated passages (questions whose answer changed) are checked the same way against a
checkout of the earlier revision, given with --earlier.
Also report for how many queries the target passages have been checked
(see "review" in the query files).

Exit status: 0 if every passage is confirmed, 2 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus  # noqa: E402
from rank import load_queries  # noqa: E402


def check_passages(qid: str, passages: list[dict], root: Path, corpus_files: set[str],
                   label: str) -> list[str]:
    problems = []
    for t in passages:
        where = f"{qid}: {label} {t['path']}:{t['lines'][0]}-{t['lines'][1]}"
        if t["path"] not in corpus_files:
            problems.append(f"{where}: file is not in the corpus")
            continue
        lines = (root / t["path"]).read_text(encoding="utf-8").splitlines()
        start, end = t["lines"]
        if not 1 <= start <= end <= len(lines):
            problems.append(f"{where}: line range outside the file ({len(lines)} lines)")
            continue
        if t["quote"] not in "\n".join(lines[start - 1:end]):
            problems.append(f"{where}: quote not found: {t['quote']!r}")
    return problems


def check(queries: dict, root: Path, earlier: Path | None = None) -> list[str]:
    problems = []
    corpus_files = set(corpus.select_files(root))
    earlier_files = set(corpus.select_files(earlier)) if earlier else set()
    seen = set()
    for q in queries["queries"]:
        if q["id"] in seen:
            problems.append(f"{q['id']}: duplicate id")
        seen.add(q["id"])
        if q["group"] not in queries["groups"]:
            problems.append(f"{q['id']}: unknown group {q['group']!r}")
        if not q["targets"]:
            problems.append(f"{q['id']}: no targets")
        problems += check_passages(q["id"], q["targets"], root, corpus_files, "target")
        if q.get("outdated"):
            if earlier is None:
                problems.append(f"{q['id']}: has outdated passages; give the earlier checkout with --earlier")
            else:
                problems += check_passages(q["id"], q["outdated"], earlier, earlier_files, "outdated")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", type=Path, action="append",
                        help="query file (repeat for several; default: queries.json)")
    parser.add_argument("--opentitan", required=True, type=Path)
    parser.add_argument("--earlier", type=Path, help="checkout of the earlier revision")
    args = parser.parse_args(argv)
    queries = load_queries(args.queries or [Path(__file__).parent / "queries.json"])
    problems = check(queries, args.opentitan, args.earlier)
    for p in problems:
        print("PROBLEM", p)
    n = len(queries["queries"])
    targets = sum(len(q["targets"]) for q in queries["queries"])
    outdated = sum(len(q.get("outdated", [])) for q in queries["queries"])
    checked = sum(1 for q in queries["queries"] if q.get("checked"))
    print(f"{n} queries, {targets} target passages"
          + (f", {outdated} outdated passages" if outdated else "")
          + f"; targets checked for {checked} of {n} queries")
    if problems:
        print(f"{len(problems)} problem(s)")
        return 2
    print("all passages confirmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
