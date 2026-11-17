#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Check the register and field names written in OpenTitan's hand-written documentation
against each IP's register description. No language model is involved.

Three checks, on the README, theory of operation and programmer's guide of every IP
listed (claims/all_ips.json by default):

  field     a field written as `REGISTER.FIELD` that the register does not have
  link      a link whose text names one register and whose target is another
  target    a link into the IP's registers.md (or its description) whose anchor is not a
            register entry there, nor REGISTER--FIELD for one of its fields

The same name written several times in one IP is one finding with several places.
A review file (names_review.json) records, for each finding, what it is (a name the
description does not have, a wrong register, a link written in the wrong form, a shorthand
the documentation uses on purpose, or a match that is not a register reference at all) and
whether the same check still finds it on OpenTitan's master branch. The report counts the
findings by kind.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check  # noqa: E402
import sentences as sel  # noqa: E402

KINDS = {
    "not in description": "the documentation names a register or field that the "
                          "description does not have",
    "wrong register": "the documentation names a register that exists, but not the one it "
                      "means",
    "link format": "the register exists, but the link's target is written in a form "
                   "registers.md does not use",
    "shorthand": "a deliberate shorthand for several fields (one per channel or instance)",
    "not a register reference": "the match is not a reference to a register",
}


def findings(root: Path, ips: list[dict]) -> list[dict]:
    models = check.load_models(root, ips)
    selected = {"sentences": sel.select(root, ips)}
    raw = []
    for u in check.unknown_fields(selected, models):
        raw.append({"check": "field", "ip": u["ip"], "name": u["written"], "path": u["path"],
                    "line": u["line"], "detail": "fields: " + ", ".join(u["fields"])})
    for u in check.link_mismatches(root, ips, models):
        raw.append({"check": "link", "ip": u["ip"], "name": u["text"], "path": u["path"],
                    "line": u["line"], "detail": f"link goes to #{u['target']}"})
    for u in check.missing_targets(root, ips, models):
        raw.append({"check": "target", "ip": u["ip"], "name": u["text"], "path": u["path"],
                    "line": u["line"], "detail": f"no entry #{u['target']}"})
    grouped: dict[str, dict] = {}
    for r in raw:
        key = f"{r['ip']}:{r['check']}:{r['name']}"
        g = grouped.setdefault(key, {"key": key, "check": r["check"], "ip": r["ip"],
                                     "name": r["name"], "detail": r["detail"], "places": []})
        place = f"{r['path']}:{r['line']}"
        if place not in g["places"]:
            g["places"].append(place)
    return sorted(grouped.values(), key=lambda g: (g["ip"], g["check"], g["name"]))


def markdown(found: list[dict], review: dict, rev: str, n_ips: int) -> str:
    blob = f"{check.BLOB}/{rev}/"
    by_kind: dict[str, list[dict]] = {}
    for f in found:
        by_kind.setdefault(review.get(f["key"], {}).get("kind", "not reviewed"), []).append(f)
    lines = ["# Register and field names in the documentation, checked against the description",
             "", f"OpenTitan revision `{rev}`; {n_ips} IPs; no language model involved.", "",
             f"{len(found)} findings: " + ", ".join(
                 f"{k} {len(v)}" for k, v in sorted(by_kind.items(),
                                                    key=lambda kv: -len(kv[1]))) + ".", ""]
    for kind in list(KINDS) + ["not reviewed"]:
        items = by_kind.get(kind)
        if not items:
            continue
        lines += [f"## {kind[0].upper() + kind[1:]} ({len(items)})", ""]
        if kind in KINDS:
            lines += [KINDS[kind][0].upper() + KINDS[kind][1:] + ".", ""]
        lines += ["| IP | Written | Check | Where | Detail | Note | On master |",
                  "|---|---|---|---|---|---|---|"]
        for f in items:
            where = ", ".join(f"[{Path(p.rsplit(':', 1)[0]).name}:{p.rsplit(':', 1)[1]}]"
                              f"({blob}{p.rsplit(':', 1)[0]}#L{p.rsplit(':', 1)[1]})"
                              for p in f["places"])
            rv = review.get(f["key"], {})
            lines.append(f"| {f['ip']} | `{f['name']}` | {f['check']} | {where} | "
                         f"{f['detail']} | {rv.get('note', '')} | {rv.get('on_master', '')} |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--opentitan", type=Path, required=True)
    ap.add_argument("--ips", type=Path, default=HERE / "all_ips.json")
    ap.add_argument("--review", type=Path, default=HERE / "names_review.json")
    ap.add_argument("--out", type=Path, required=True, help="report (.md); .json written beside")
    args = ap.parse_args(argv)
    spec = json.loads(args.ips.read_text(encoding="utf-8"))
    review = (json.loads(args.review.read_text(encoding="utf-8"))["findings"]
              if args.review.exists() else {})
    found = findings(args.opentitan, spec["ips"])
    unknown = sorted(set(review) - {f["key"] for f in found})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown(found, review, spec["opentitan_revision"], len(spec["ips"])),
                        encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(
        {"opentitan_revision": spec["opentitan_revision"], "ips": len(spec["ips"]),
         "findings": [dict(f, **review.get(f["key"], {})) for f in found]}, indent=1) + "\n",
        encoding="utf-8")
    kinds: dict[str, int] = {}
    for f in found:
        k = review.get(f["key"], {}).get("kind", "not reviewed")
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{len(found)} findings: {kinds}")
    if unknown:
        print("reviewed findings no longer found: " + ", ".join(unknown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
