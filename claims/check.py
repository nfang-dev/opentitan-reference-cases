#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Check the register facts the model read from the documentation against the register
description, and against what the register tests observed in simulation.

For each claim:

1. The quote must occur in the sentence (otherwise the model did not read it there).
2. The register and field must exist in the IP's register description (read with reggen).
3. The stated value is compared with the description:
   reset_value      the field's reset value (a register: every field's, combined)
   software_access  the field's access type (a register: all fields must have one type)
   width_bits       the field's width (a register: only if it has a single field)
   locked_by        the register's lock register (regwen)
4. Where the register tests (csr/) checked the same property in simulation and it passed,
   the hardware is known to match the description, so the claim is also compared with the
   hardware.

Outcomes: agrees, disagrees, not in description (register or field), not checkable (the
description has no single value to compare with), quote not in sentence, register not named
in sentence (the model attributed the fact to a register the sentence does not name), unknown
value (a value the program cannot read, for example an access type outside the fixed list).

A review file can record, for each claim, whether the model read the sentence correctly
and, for a disagreement, whether the documentation is wrong. The report then states how
many claims were read correctly.

Uses reggen (through csr/regmodel.py) and the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "csr"))

import regmodel  # noqa: E402

ACCESS = {"read-write": "rw", "read-only": "ro", "write-only": "wo",
          "write-1-to-clear": "rw1c", "write-1-to-set": "rw1s", "write-0-to-clear": "rw0c",
          "read-to-clear": "rc"}
ACCESS_NAME = {v: k for k, v in ACCESS.items()}
ACCESS_NAME["r0w1c"] = "read-zero, write-1-to-clear"
BASE_RE = re.compile(r"_?\d+$")
BLOB = "https://github.com/lowRISC/opentitan/blob"


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("`", "").replace("*", "")).strip().lower()


def parse_number(text: str) -> int | None:
    t = text.strip().strip("`").replace("_", "").lower()
    m = re.fullmatch(r"\d+'([hbd])([0-9a-f]+)", t)
    if m:
        return int(m.group(2), {"h": 16, "b": 2, "d": 10}[m.group(1)])
    if re.fullmatch(r"0x[0-9a-f]+", t):
        return int(t, 16)
    if re.fullmatch(r"0b[01]+", t):
        return int(t, 2)
    if re.fullmatch(r"\d+", t):
        return int(t)
    return {"enabled": 1, "set": 1, "true": 1, "disabled": 0, "cleared": 0, "false": 0}.get(t)


def find_registers(model: dict, name: str) -> list[dict]:
    """Registers a written name means: exact (any case), or a multi-register's base name."""
    key = name.strip().strip("`").upper()
    exact = [r for r in model["registers"] if r["name"].upper() == key]
    if exact:
        return exact
    return [r for r in model["registers"] if BASE_RE.sub("", r["name"]).upper() == key]


def find_field(reg: dict, name: str) -> dict | None:
    key = name.strip().strip("`").lower()
    return next((f for f in reg["fields"] if f["name"].lower() == key), None)


def described(reg: dict, field: dict | None, prop: str):
    """The description's value for a property, or (None, reason) if it has no single one."""
    fields = [field] if field else reg["fields"]
    if prop == "reset_value":
        if any(f["resval"] is None for f in fields):
            return None, "no reset value in the description"
        if field:
            return field["resval"], None
        return sum(f["resval"] << f["lsb"] for f in fields), None
    if prop == "software_access":
        kinds = {f["swaccess"] for f in fields}
        if len(kinds) != 1:
            return None, "fields have different access types: " + ", ".join(sorted(kinds))
        return kinds.pop(), None
    if prop == "width_bits":
        if len(fields) != 1:
            return None, "register has several fields"
        return fields[0]["width"], None
    if prop == "locked_by":
        return (reg["regwen"].upper() if reg["regwen"] else None), None
    raise ValueError(prop)


def stated_value(prop: str, value: str):
    if prop in ("reset_value", "width_bits"):
        return parse_number(value)
    if prop == "software_access":
        return ACCESS.get(value.strip().lower())
    if prop == "locked_by":
        v = value.strip().strip("`").upper()
        return v or None
    raise ValueError(prop)


def show(prop: str, v) -> str:
    if v is None:
        return "none"
    if prop == "software_access":
        return ACCESS_NAME.get(v, v)
    if prop == "reset_value":
        return str(v) if v < 10 else hex(v)
    return str(v)


def hardware(results: dict | None, reg: str, field: dict | None, prop: str) -> str:
    """What the register tests observed for this register and property."""
    if not results:
        return "IP not simulated"
    seeds = results["seeds"].values()
    fmask = ((1 << field["width"]) - 1) << field["lsb"] if field else None

    def rows(test):
        out = []
        for s in seeds:
            obs = s["observed"].get(test, {})
            out += [r for r in obs.get("registers", []) if r.get("register") == reg]
        return out

    def covered(r):
        m = int(r["mask"], 16)
        return (m & fmask) == fmask if fmask else m != 0

    test = {"reset_value": "hw_reset", "software_access": "rw", "locked_by": "regwen_lock"}.get(prop)
    if test is None:
        return "not applicable"
    rs = [r for r in rows(test) if test != "rw" or "round" in r]
    if rs and all(r["result"] == "pass" for r in rs) and all("mask" not in r or covered(r) for r in rs):
        return "matches description"
    return "not checked"


def check_claim(claim: dict, sentence: dict, model: dict, results: dict | None) -> dict:
    prop = claim["property"]
    row = {"register": claim["register"], "field": claim["field"], "property": prop,
           "stated": claim["value"], "quote": claim["quote"]}
    if norm_text(claim["quote"]) not in norm_text(sentence["text"]):
        return {**row, "outcome": "quote not in sentence"}
    reg_name, field_name = claim["register"], claim["field"]
    if "." in reg_name and not field_name:
        reg_name, field_name = reg_name.split(".", 1)
    regs = find_registers(model, reg_name)
    if not regs:
        return {**row, "outcome": "not in description", "detail": f"no register {reg_name}"}
    if not any(r["name"] in sentence["registers"] for r in regs):
        return {**row, "outcome": "register not named in sentence"}
    stated = stated_value(prop, claim["value"])
    if stated is None:
        return {**row, "outcome": "unknown value"}
    described_values, hw = set(), set()
    for reg in regs:
        field = None
        if field_name:
            field = find_field(reg, field_name)
            if field is None:
                return {**row, "outcome": "not in description",
                        "detail": f"no field {field_name} in {reg['name']}"}
        elif len(reg["fields"]) == 1:
            field = reg["fields"][0]
        value, why = described(reg, field, prop)
        if why:
            return {**row, "outcome": "not checkable", "detail": why}
        described_values.add(value)
        hw.add(hardware(results, reg["name"], field, prop))
    if len(described_values) != 1:
        return {**row, "outcome": "not checkable",
                "detail": "registers named differ in the description"}
    value = described_values.pop()
    out = {**row, "described": show(prop, value),
           "outcome": "agrees" if value == stated else "disagrees",
           "hardware": hw.pop() if len(hw) == 1 else "not checked"}
    if len(regs) > 1:
        out["registers"] = [r["name"] for r in regs]
    return out


def check_all(sentences: dict, answers: dict, root: Path, ips: list[dict],
              csr_results: Path | None) -> list[dict]:
    by_id = {s["id"]: s for s in sentences["sentences"]}
    models, results = {}, {}
    for ip in ips:
        models[ip["ip"]] = regmodel.load(root, ip["hjson"])
        p = csr_results / f"{ip['ip']}.json" if csr_results else None
        results[ip["ip"]] = json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None
    out = []
    for a in answers["answers"]:
        s = by_id[a["id"]]
        for i, claim in enumerate(a["claims"], 1):
            row = check_claim(claim, s, models[a["ip"]], results[a["ip"]])
            out.append({"claim": f"{a['id']}/{i}", "ip": a["ip"], "path": s["path"],
                        "line": s["line"], "sentence": s["text"], **row})
    return out


OUTCOMES = ["agrees", "disagrees", "not in description", "not checkable", "unknown value",
            "quote not in sentence", "register not named in sentence"]


def summary(rows: list[dict], answers: dict, review: dict) -> dict:
    total = len(answers["answers"])
    with_claims = sum(1 for a in answers["answers"] if a["claims"])
    errors = sum(1 for a in answers["answers"] if a["error"])
    by_outcome = {o: sum(1 for r in rows if r["outcome"] == o) for o in OUTCOMES}
    by_prop: dict[str, int] = {}
    for r in rows:
        by_prop[r["property"]] = by_prop.get(r["property"], 0) + 1
    reviewed = [review[r["claim"]] for r in rows if r["claim"] in review]
    return {"sentences": total, "sentences_with_claims": with_claims, "answer_errors": errors,
            "claims": len(rows), "by_property": by_prop, "by_outcome": by_outcome,
            "reviewed": len(reviewed),
            "read_correctly": sum(1 for v in reviewed if v["reading"] == "correct"),
            "documentation_differs": sum(1 for v in reviewed if v.get("documentation") == "differs")}


def markdown(rows: list[dict], summ: dict, answers: dict, review: dict, rev: str) -> str:
    lines = ["# Register facts read from the documentation, checked against the description", "",
             f"OpenTitan revision `{rev}`. Model: {answers['model']} "
             f"(llama-cpp-python {answers['llama_cpp_python']}, temperature 0).", "",
             f"- Sentences read: {summ['sentences']}; with at least one claim: "
             f"{summ['sentences_with_claims']}; answers not in the fixed form: "
             f"{summ['answer_errors']}",
             f"- Claims: {summ['claims']} ("
             + ", ".join(f"{k} {v}" for k, v in sorted(summ["by_property"].items())) + ")",
             "- Outcomes: " + ", ".join(f"{k} {v}" for k, v in summ["by_outcome"].items() if v)]
    if summ["reviewed"]:
        lines.append(f"- Reviewed: {summ['reviewed']} of {summ['claims']} claims; the model read "
                     f"the sentence correctly in {summ['read_correctly']}; documentation that "
                     f"differs from the description: {summ['documentation_differs']}")
    lines += ["", "| Claim | Sentence | Stated | Description | Outcome | Hardware | Review |",
              "|---|---|---|---|---|---|---|"]
    order = {o: i for i, o in enumerate(["disagrees", "not in description", "quote not in sentence",
                                         "register not named in sentence", "unknown value",
                                         "not checkable", "agrees"])}
    for r in sorted(rows, key=lambda r: (order[r["outcome"]], r["claim"])):
        target = r["register"] + (f".{r['field']}" if r["field"] else "")
        link = f"[{r['ip']}/{Path(r['path']).name}:{r['line']}]" \
               f"({BLOB}/{rev}/{r['path']}#L{r['line']})"
        sent = r["sentence"].replace("|", "\\|")
        if len(sent) > 160:
            sent = sent[:157] + "..."
        rv = review.get(r["claim"], {})
        note = rv.get("reading", "")
        if rv.get("note"):
            note += f": {rv['note']}"
        described = r.get("described", r.get("detail", ""))
        lines.append(f"| {link} | {sent} | {target} {r['property']} = {r['stated']} | "
                     f"{described} | {r['outcome']} | {r.get('hardware', '')} | "
                     f"{note.replace('|', '/')} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--opentitan", type=Path, required=True)
    ap.add_argument("--sentences", type=Path, required=True)
    ap.add_argument("--answers", type=Path, required=True)
    ap.add_argument("--ips", type=Path, default=HERE.parent / "csr" / "ips.json")
    ap.add_argument("--csr-results", type=Path, default=HERE.parent / "csr" / "results")
    ap.add_argument("--review", type=Path, default=HERE / "review.json")
    ap.add_argument("--out", type=Path, required=True, help="report (.md); .json written beside")
    args = ap.parse_args(argv)
    sentences = json.loads(args.sentences.read_text(encoding="utf-8"))
    answers = json.loads(args.answers.read_text(encoding="utf-8"))
    review = (json.loads(args.review.read_text(encoding="utf-8"))["claims"]
              if args.review.exists() else {})
    ips = json.loads(args.ips.read_text(encoding="utf-8"))["ips"]
    rows = check_all(sentences, answers, args.opentitan, ips, args.csr_results)
    summ = summary(rows, answers, review)
    rev = sentences["opentitan_revision"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown(rows, summ, answers, review, rev), encoding="utf-8")
    args.out.with_suffix(".json").write_text(
        json.dumps({"summary": summ, "claims": rows}, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
