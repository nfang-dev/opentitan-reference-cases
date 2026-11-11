#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Select the documentation sentences an AI model is asked to read.

For each IP in csr/ips.json, the hand-written documents next to its register description
are read: README.md, doc/theory_of_operation.md and doc/programmers_guide.md (registers.md
and interfaces.md are generated from the description, so they cannot disagree with it).

A sentence is selected if it names one of the IP's registers: a register name in capitals,
or in code style in any case (`name`), optionally followed by a field (`REG.field`).
Multi-registers can be named without their index in capitals (`INTR_ENABLE` for
INTR_ENABLE0).

Each sentence records its file, line, heading, and the registers it names together with
their field names. The field names are given to the model so that it can tell which
register a field belongs to; reset values and access types are not given.

The selection is deterministic: same OpenTitan revision, same sentences.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "csr"))
sys.path.insert(0, str(HERE.parent / "retrieval"))

import corpus  # noqa: E402
import regmodel  # noqa: E402

DOCS = ("README.md", "doc/theory_of_operation.md", "doc/programmers_guide.md")
SENTENCE_RE = re.compile(r"(?<=[.;:!?])\s+(?=[A-Z`\[(])")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
TICK_RE = re.compile(r"`([^`]+)`")
WORD_RE = re.compile(r"(?<![\w.])([A-Z][A-Z0-9_]*[A-Z0-9])(?:\.(\w+))?(?![\w])")
BASE_RE = re.compile(r"_?\d+$")


def doc_files(hjson: str) -> list[str]:
    ip_dir = Path(hjson).parent.parent
    return [(ip_dir / d).as_posix() for d in DOCS]


def name_table(model: dict) -> dict[str, list[str]]:
    """Written name (upper case) -> registers it can mean."""
    table: dict[str, list[str]] = {}
    for r in model["registers"]:
        table.setdefault(r["name"].upper(), []).append(r["name"])
    for r in model["registers"]:
        base = BASE_RE.sub("", r["name"]).upper()
        if base != r["name"].upper() and base not in table:
            table[base] = [x["name"] for x in model["registers"]
                           if BASE_RE.sub("", x["name"]).upper() == base]
    return table


def mentions(sentence: str, table: dict[str, list[str]]) -> list[dict]:
    """Registers named in a sentence, in order of first mention, with the field if given."""
    found: list[tuple[int, str, str | None]] = []
    for m in TICK_RE.finditer(sentence):
        token = m.group(1).strip()
        name, _, field = token.partition(".")
        # In lower case, only a complete register name counts: `en` is a field, not EN0/EN1.
        if name.upper() in table and (name.isupper() or table[name.upper()] == [name.upper()]):
            found.append((m.start(), name.upper(), field or None))
    for m in WORD_RE.finditer(sentence):
        if m.group(1) in table:
            found.append((m.start(), m.group(1), m.group(2)))
    out, seen = [], set()
    for _, name, field in sorted(found):
        key = (name, (field or "").lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"written": name + (f".{field}" if field else ""), "registers": table[name],
                    "field": field})
    return out


def sentences_of(rel: str, text: str):
    """Yield (first line, last line, heading, sentence) for every sentence outside code
    blocks."""
    lines = corpus.strip_generated(text.splitlines())
    for chain, body in corpus.sections(lines):
        in_fence = False
        prose: list[tuple[int, str]] = []
        for no, line in body:
            if corpus.FENCE_RE.match(line):
                in_fence = not in_fence
                prose.append((no, ""))
                continue
            prose.append((no, "" if in_fence else line))
        for block in corpus.blocks(prose):
            # A list item or a table row starts a new unit; continuation lines are joined.
            units: list[list[tuple[int, str]]] = []
            for no, line in block:
                if not units or LIST_ITEM_RE.match(line) or line.lstrip().startswith("|"):
                    units.append([])
                units[-1].append((no, line.strip()))
            for unit in units:
                offsets, joined = [], ""
                for no, line in unit:
                    offsets.append((len(joined), no))
                    joined += corpus.LINK_RE.sub(r"\1", line) + " "
                pos = 0
                for s in SENTENCE_RE.split(joined.strip()):
                    pos = max(joined.find(s, pos), 0)
                    first = max(no for off, no in offsets if off <= pos)
                    pos += len(s)
                    last = max(no for off, no in offsets if off <= max(pos - 1, 0))
                    if s.strip():
                        yield first, last, " > ".join(chain), s.strip()


def select(root: Path, ips: list[dict]) -> list[dict]:
    out = []
    for ip in ips:
        model = regmodel.load(root, ip["hjson"])
        regs = {r["name"]: r for r in model["registers"]}
        table = name_table(model)
        for rel in doc_files(ip["hjson"]):
            path = root / rel
            if not path.is_file():
                continue
            count: dict[int, int] = {}
            for line, last, heading, sentence in sentences_of(rel,
                                                              path.read_text(encoding="utf-8")):
                named = mentions(sentence, table)
                if not named:
                    continue
                count[line] = count.get(line, 0) + 1
                names = []
                for n in named:
                    for r in n["registers"]:
                        if r not in names:
                            names.append(r)
                out.append({
                    "id": f"{rel}:{line}" + (f"#{count[line]}" if count[line] > 1 else ""),
                    "ip": ip["ip"],
                    "path": rel,
                    "line": line,
                    "end_line": last,
                    "heading": heading,
                    "text": sentence,
                    "written": [n["written"] for n in named],
                    "registers": {r: [f["name"] for f in regs[r]["fields"]] for r in names[:12]},
                })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--opentitan", type=Path, required=True)
    ap.add_argument("--ips", type=Path, default=HERE.parent / "csr" / "ips.json")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    spec = json.loads(args.ips.read_text(encoding="utf-8"))
    found = select(args.opentitan, spec["ips"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"opentitan_revision": spec["opentitan_revision"],
                                    "sentences": found}, indent=1) + "\n", encoding="utf-8")
    per_ip: dict[str, int] = {}
    for s in found:
        per_ip[s["ip"]] = per_ip.get(s["ip"], 0) + 1
    print(f"{len(found)} sentences: " + ", ".join(f"{k} {v}" for k, v in per_ip.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
