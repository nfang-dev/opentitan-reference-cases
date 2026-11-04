#!/usr/bin/env python3
"""Re-check a reference case against an OpenTitan checkout.

A case file (case.json) records, for one setting:

- the written requirements that state its value after reset (with file and line),
- the design evidence for its actual reset value (with file and line, or a pattern
  that must match every register instance),
- the expected value, conditions, ambiguities and the finding.

This script confirms that every piece of evidence is still where the case says it
is, that the design evidence agrees on one value, and which written requirements
agree or disagree with that value. It uses only the Python standard library.

Exit status:
  0  all evidence located and the design evidence is consistent
  1  --fail-on-inconsistency was given and a requirement disagrees with the design
  2  evidence could not be located or the design evidence is inconsistent
     (the case needs updating for this revision)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_KEYS = {"id", "title", "opentitan_revision", "expected_after_reset",
                 "requirements", "design", "finding"}


@dataclass
class Located:
    item_id: str
    ok: bool
    detail: str
    value: int | None = None


@dataclass
class Report:
    revision_matches: bool
    revision: str
    evidence: list[Located] = field(default_factory=list)
    comparisons: list[tuple[str, int, int, bool]] = field(default_factory=list)
    design_value: int | None = None
    design_consistent: bool = True

    @property
    def evidence_ok(self) -> bool:
        return all(e.ok for e in self.evidence) and self.design_consistent

    @property
    def inconsistencies(self) -> list[str]:
        return [rid for rid, _, _, agrees in self.comparisons if not agrees]


def load_case(path: Path) -> dict:
    case = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_KEYS - case.keys()
    if missing:
        raise ValueError(f"{path}: missing keys {sorted(missing)}")
    return case


def current_revision(checkout: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def locate_line(checkout: Path, item: dict) -> Located:
    path = checkout / item["file"]
    if not path.is_file():
        return Located(item["id"], False, f"file not found: {item['file']}")
    lines = path.read_text(encoding="utf-8").splitlines()
    want, line = item["text"], item["line"]
    if 1 <= line <= len(lines) and want in lines[line - 1]:
        return Located(item["id"], True, f"{item['file']}:{line}", item.get("value"))
    hits = [i + 1 for i, text in enumerate(lines) if want in text]
    if len(hits) == 1:
        return Located(item["id"], True, f"{item['file']}:{hits[0]} (moved from line {line})",
                       item.get("value"))
    if hits:
        return Located(item["id"], False,
                       f"text found on several lines {hits} of {item['file']}, expected line {line}")
    return Located(item["id"], False, f"text not found in {item['file']}")


def locate_all_instances(checkout: Path, item: dict) -> Located:
    path = checkout / item["file"]
    if not path.is_file():
        return Located(item["id"], False, f"file not found: {item['file']}")
    values = [int(v, 16) for v in re.findall(item["pattern"], path.read_text(encoding="utf-8"))]
    expected_count = item.get("expected_count")
    if not values:
        return Located(item["id"], False, f"pattern matched nothing in {item['file']}")
    if expected_count is not None and len(values) != expected_count:
        return Located(item["id"], False,
                       f"{len(values)} instances in {item['file']}, case expects {expected_count}")
    distinct = sorted(set(values))
    if len(distinct) != 1:
        return Located(item["id"], False, f"instances disagree in {item['file']}: values {distinct}")
    return Located(item["id"], True, f"{len(values)} instances in {item['file']}, all {distinct[0]}",
                   distinct[0])


def check(case: dict, checkout: Path) -> Report:
    revision = current_revision(checkout)
    report = Report(revision_matches=(revision == case["opentitan_revision"]), revision=revision)

    for item in case["requirements"]:
        report.evidence.append(locate_line(checkout, item))

    design_values = set()
    for item in case["design"]:
        if item.get("kind") == "all_instances":
            located = locate_all_instances(checkout, item)
            if located.ok and located.value != item["value"]:
                located = Located(item["id"], False,
                                  f"{located.detail}, but the case records {item['value']}",
                                  located.value)
        else:
            located = locate_line(checkout, item)
        report.evidence.append(located)
        if located.ok and located.value is not None:
            design_values.add(located.value)

    expected = case["expected_after_reset"]["value"]
    if design_values and design_values != {expected}:
        report.design_consistent = False
    report.design_value = expected if report.design_consistent else None

    for item in case["requirements"]:
        stated = item["states_value"]
        report.comparisons.append((item["id"], stated, expected, stated == expected))
    return report


def format_report(case: dict, report: Report) -> str:
    out = [f"Case {case['id']}: {case['title']}"]
    if report.revision_matches:
        out.append(f"OpenTitan revision: {report.revision} (matches the case)")
    else:
        out.append(f"OpenTitan revision: {report.revision} "
                   f"(case recorded {case['opentitan_revision']}; lines were searched)")
    out.append("")
    out.append("Evidence:")
    for e in report.evidence:
        out.append(f"  [{'ok' if e.ok else 'MISSING'}] {e.item_id}: {e.detail}")
    out.append("")
    meaning = case["expected_after_reset"].get("meaning", "")
    if report.design_consistent:
        out.append(f"Design value after reset: {report.design_value} ({meaning})")
    else:
        out.append("Design evidence does not agree on a single value; the case needs review.")
    out.append("")
    out.append("Written requirements vs design:")
    for rid, stated, expected, agrees in report.comparisons:
        verdict = "agrees" if agrees else "DISAGREES"
        out.append(f"  {rid}: states {stated}, design {expected} -> {verdict}")
    out.append("")
    if not report.evidence_ok:
        out.append("RESULT: evidence could not be confirmed at this revision")
    elif report.inconsistencies:
        out.append(f"RESULT: documentation and design disagree ({', '.join(report.inconsistencies)})")
    else:
        out.append("RESULT: documentation and design agree")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("case", type=Path, help="path to a case.json")
    parser.add_argument("--opentitan", type=Path, required=True,
                        help="path to an OpenTitan checkout")
    parser.add_argument("--fail-on-inconsistency", action="store_true",
                        help="exit 1 if a written requirement disagrees with the design")
    args = parser.parse_args(argv)

    case = load_case(args.case)
    report = check(case, args.opentitan)
    print(format_report(case, report))
    if not report.evidence_ok:
        return 2
    if args.fail_on_inconsistency and report.inconsistencies:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
