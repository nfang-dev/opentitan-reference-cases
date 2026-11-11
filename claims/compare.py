#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Compare the model's answers from two runs, sentence by sentence.

Usage: compare.py <answers.json> <answers.json>

Prints how many sentences got the same claims in both runs and lists the others. Exits
with 0 either way: a language model can answer differently on different hardware even at
temperature 0, so a difference is reported, not treated as a failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def key(claims: list[dict]) -> list[tuple]:
    return sorted((c["register"].upper(), c["field"].lower(), c["property"], c["value"].lower())
                  for c in claims)


def compare(a: dict, b: dict) -> tuple[int, int, list[str]]:
    first = {x["id"]: x for x in a["answers"]}
    second = {x["id"]: x for x in b["answers"]}
    common = [i for i in first if i in second]
    differ = [i for i in common if key(first[i]["claims"]) != key(second[i]["claims"])]
    return len(common), len(common) - len(differ), differ


def main(argv: list[str]) -> int:
    a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in argv[:2])
    common, same, differ = compare(a, b)
    print(f"{same} of {common} sentences have the same claims in both runs")
    for i in differ:
        print(f"  differs: {i}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
