#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Find statements in hand-written documentation that give a register's reset or default value.

A statement is one of:

- prose: a sentence with a reset or default cue ("reset value", "resets to", "default is",
  "after reset", "by default", ...) and a value: a number, or "enabled"/"disabled";
- table: a row of a value table marked "(default)", whose header names the register.

The register a statement is about is a name written in code style (`NAME`) in the same
sentence; if the sentence names none, the nearest name in the lines just above it in the
same section (for example the header of the table it follows). How the register was found
is recorded with each statement.

Each statement is then compared with the design's reset value (design_index.py):

- agrees / disagrees: the stated value equals / differs from the design value;
- name not in design: the written name matches no register (names that end with it are
  listed, which often shows a renamed register);
- value in words: the statement says "enabled" for a field wider than one bit, which has
  no single value;
- design values differ: the name matches several registers whose reset values differ.

Uses only the Python standard library.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "retrieval"))

import corpus  # noqa: E402
from design_index import DesignIndex, normalize  # noqa: E402

CUE_RE = re.compile(
    r"\b(reset values?|resets? to|reset to|defaults? (?:to|is|of)|default values?|is the default"
    r"|by default|at reset|after (?:a |the )?reset|upon (?:a |the )?reset|out of reset"
    r"|on reset|upon POR|power-on[- ]reset)\b|\(default\)", re.I)
NUM = r"(0x[0-9a-fA-F_]+|\d+'[hbd][0-9a-fA-F_]+|\d+)"
TICK_VALUE_RE = re.compile(rf"`{NUM}`")
AFTER_CUE_VALUE_RE = re.compile(rf"^[^.;`]{{0,12}}?\b(?:is|to|of|=|are)\s+`?{NUM}\b`?")
TICK_RE = re.compile(r"`([^`]+)`")
SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
SENTENCE_RE = re.compile(r"(?<=[.;])\s+(?=[A-Z`\[])")
WORD_RE = re.compile(r"\b(disabled|enabled|cleared)\b", re.I)
ALL_SET_RE = re.compile(r"\ball (?:fields|bits)\b[^.;]{0,40}?\bare set\b", re.I)
BEFORE_DEFAULT_RE = re.compile(rf"`?{NUM}`?\s*\(default\)", re.I)
WORD_DISTANCE = 40
LOOKBACK = 8


def parse_number(text: str) -> int | None:
    text = text.strip().strip("`").replace("_", "")
    m = re.fullmatch(r"\d+'([hbd])([0-9a-fA-F]+)", text)
    if m:
        return int(m.group(2), {"h": 16, "b": 2, "d": 10}[m.group(1)])
    if re.fullmatch(r"0x[0-9a-fA-F]+", text):
        return int(text, 16)
    if re.fullmatch(r"\d+", text):
        return int(text)
    return None


def written_names(text: str) -> list[tuple[int, str]]:
    """Names in code style, with their position; "a/b_rest" is expanded to a_rest, b_rest."""
    out = []
    for m in TICK_RE.finditer(text):
        token = m.group(1).strip()
        if "/" in token:
            parts = token.split("/")
            last = parts[-1]
            suffix = last[last.index("_"):] if "_" in last else ""
            for p in parts:
                out.append((m.start(), p if "_" in p or not suffix else p + suffix))
        else:
            out.append((m.start(), token))
    return [(pos, n) for pos, n in out if normalize(n) and not re.fullmatch(r"\d+", n)]


REGISTER_LIKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*_[A-Z0-9_]*(\.[A-Z][A-Z0-9_*]*)?$|^[A-Z][A-Z0-9]*\.[A-Z][A-Z0-9_*]*$")


class Resolver:
    def __init__(self, index: DesignIndex):
        self.index = index

    def resolve(self, names: list[tuple[int, str]]) -> list[tuple[int, str, list]]:
        """Names that are registers in the design. If none are, the names that look like
        register names or end like one (with no design entries), so that a statement about
        a register that does not exist is reported rather than attributed elsewhere."""
        found = [(pos, n, self.index.lookup(n)) for pos, n in names]
        hits = [x for x in found if x[2]]
        if hits:
            return hits
        return [(pos, n, []) for pos, n, _ in found
                if REGISTER_LIKE_RE.match(n) or self.index.near(n)]


def compare(stated: int | None, words: str | None, entries: list, near: list[str],
            index: DesignIndex | None = None) -> dict:
    if not entries:
        return {"outcome": "name not in design", "near": near}
    if words == "all set" and index is not None:
        fields = [f for e in entries for f in index.fields_of(e.key)] or entries
        ok = all(f.value == (1 << f.width) - 1 for f in fields if f.width)
        design = {"value": "every field all ones" if ok else
                  {f.key: f.value for f in fields}, "instances": len(entries),
                  "file": entries[0].file, "line": entries[0].line}
        return {"outcome": "agrees" if ok else "disagrees", "design": design}
    values = sorted({e.value for e in entries if e.value is not None})
    widths = sorted({e.width for e in entries if e.width is not None})
    design = {"value": values[0] if len(values) == 1 else values,
              "instances": len(entries), "file": entries[0].file, "line": entries[0].line}
    if len(values) != 1:
        return {"outcome": "design values differ", "design": design}
    if stated is None:
        if words in ("disabled", "cleared"):
            stated = 0
        elif words == "enabled" and widths == [1]:
            stated = 1
        else:
            return {"outcome": "value in words", "design": design}
    return {"outcome": "agrees" if stated == values[0] else "disagrees", "design": design,
            "stated": stated}


def statements_in(doc_rel: str, text: str, index: DesignIndex,
                  lines_wanted: set[int] | None = None) -> list[dict]:
    lines = corpus.strip_generated(text.splitlines())
    resolver = Resolver(index)
    out: list[dict] = []
    in_fence = False
    header: dict | None = None        # current table: header columns and their names
    recent: list[tuple[int, list]] = []  # (line, resolved names) of recent lines in this section
    for no, line in enumerate(lines, start=1):
        if corpus.FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if corpus.HEADING_RE.match(line):
            recent, header = [], None
            continue
        if not line.strip():
            header = None if header and header.get("rows_started") else header
            continue
        if SEP_RE.match(line) and no > 1:
            cols = [c.strip() for c in lines[no - 2].strip().strip("|").split("|")]
            header = {"cols": [resolver.resolve(written_names(c)) for c in cols], "line": no - 1}
            continue
        plain = corpus.LINK_RE.sub(r"\1", line)
        wanted = lines_wanted is None or no in lines_wanted
        if header and "|" in line:
            header["rows_started"] = True
            if wanted and "(default)" in line.lower():
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                for col, names in enumerate(header["cols"]):
                    value = parse_number(cells[col]) if col < len(cells) else None
                    for _, name, entries in names:
                        if value is None:
                            continue
                        out.append(_statement(doc_rel, no, line, "table row", name,
                                              f"table header, line {header['line']}",
                                              value, None, entries, index))
            continue
        names_here = resolver.resolve(written_names(plain))
        if wanted:
            for sentence in SENTENCE_RE.split(plain):
                out.extend(_prose(doc_rel, no, sentence, resolver, recent, index))
        if names_here:
            recent.append((no, names_here))
        recent = [(n, r) for n, r in recent if no - n <= LOOKBACK]
        if header and "|" not in line:
            header = None
    return out


def _prose(doc_rel, no, sentence, resolver, recent, index) -> list[dict]:
    cue = CUE_RE.search(sentence)
    if not cue:
        return []
    rest = sentence[cue.end():]
    value_m = TICK_VALUE_RE.search(rest) or AFTER_CUE_VALUE_RE.search(rest)
    value_pos = cue.end() + value_m.start() if value_m else None
    stated = parse_number(value_m.group(1)) if value_m else None
    if stated is None and cue.group(0).lower() == "(default)":
        before = BEFORE_DEFAULT_RE.search(sentence)
        if before:
            stated, value_pos = parse_number(before.group(1)), before.start()
    words = None
    if stated is None and ALL_SET_RE.search(sentence):
        words = "all set"
    elif stated is None:
        # A word value counts only close to the cue, in the same clause.
        near = [w for w in WORD_RE.finditer(sentence)
                if min(abs(w.start() - cue.end()), abs(cue.start() - w.end())) <= WORD_DISTANCE]
        if not near:
            return []
        words = near[0].group(1).lower()
    names = resolver.resolve(written_names(sentence))
    names = [n for n in names if parse_number(n[1]) is None]
    if names:
        anchor = value_pos if value_pos is not None else cue.start()
        before = [n for n in names if n[0] <= anchor]
        pos, name, entries = (before or names)[-1] if before else names[0]
        how = "named in the sentence" if len(names) == 1 else "nearest name before the value"
    elif recent:
        line_no, names_then = recent[-1]
        if len({n for _, n, _ in names_then}) != 1:
            return []
        _, name, entries = names_then[0]
        how = f"named on line {line_no} above"
    else:
        return []
    return [_statement(doc_rel, no, sentence, "prose", name, how, stated, words, entries, index)]


def _statement(doc_rel, no, text, kind, name, how, stated, words, entries, index) -> dict:
    st = {"file": doc_rel, "line": no, "text": text.strip(), "kind": kind, "name": name,
          "attribution": how, "stated": stated, "stated_words": words}
    st.update(compare(stated, words, entries, index.near(name) if not entries else [], index))
    st["stated"] = stated if stated is not None else st.get("stated")
    if st["outcome"] == "name not in design" and len(st.get("near", [])) == 1:
        # What the statement would mean for the one register or field it most likely names.
        guess = compare(stated, words, index.lookup(st["near"][0]), [], index)
        if "design" in guess:
            st["near_design"] = guess["design"]
            st["near_outcome"] = guess["outcome"]
    return st


def cue_sentences(text: str, lines_wanted: set[int]) -> list[tuple[int, str]]:
    """Sentences in the wanted lines that mention reset or a default, outside code blocks."""
    out, in_fence = [], False
    for no, line in enumerate(corpus.strip_generated(text.splitlines()), start=1):
        if corpus.FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or no not in lines_wanted:
            continue
        for sentence in SENTENCE_RE.split(corpus.LINK_RE.sub(r"\1", line)):
            if CUE_RE.search(sentence):
                out.append((no, sentence.strip()))
    return out


def scan(root: Path, files: list[str] | None = None) -> list[dict]:
    out = []
    for rel in files or corpus.select_files(root):
        index = DesignIndex.for_document(root, rel)
        if not index.entries:
            continue
        out.extend(statements_in(rel, (root / rel).read_text(encoding="utf-8"), index))
    return out
