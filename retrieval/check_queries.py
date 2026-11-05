#!/usr/bin/env python3
"""Check the retrieval query set against an OpenTitan checkout.

For every target passage of every query, confirm that the file is part of the corpus
(see corpus.py) and that the recorded quote appears within the recorded line range.
Also report how many queries have been verified by a person.

Exit status: 0 if every target is confirmed, 2 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus  # noqa: E402


def check(queries: dict, root: Path) -> list[str]:
    problems = []
    corpus_files = set(corpus.select_files(root))
    seen = set()
    for q in queries["queries"]:
        if q["id"] in seen:
            problems.append(f"{q['id']}: duplicate id")
        seen.add(q["id"])
        if q["group"] not in queries["groups"]:
            problems.append(f"{q['id']}: unknown group {q['group']!r}")
        if not q["targets"]:
            problems.append(f"{q['id']}: no targets")
        for t in q["targets"]:
            where = f"{q['id']}: {t['path']}:{t['lines'][0]}-{t['lines'][1]}"
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queries", type=Path, default=Path(__file__).parent / "queries.json")
    parser.add_argument("--opentitan", required=True, type=Path)
    args = parser.parse_args(argv)
    queries = json.loads(args.queries.read_text(encoding="utf-8"))
    problems = check(queries, args.opentitan)
    for p in problems:
        print("PROBLEM", p)
    n = len(queries["queries"])
    targets = sum(len(q["targets"]) for q in queries["queries"])
    verified = sum(1 for q in queries["queries"] if q.get("verified"))
    print(f"{n} queries, {targets} target passages; {verified} of {n} queries verified by a person")
    if problems:
        print(f"{len(problems)} problem(s)")
        return 2
    print("all target passages confirmed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
