#!/usr/bin/env python3
"""Re-check reference cases against an OpenTitan checkout.

A case file (case.json) records:

- requirements: quoted lines from hand-written documents, located by file and line;
- design: evidence from the design, located by file and line, by a pattern that must
  match every instance of a register, or by a pattern that must NOT match (to show
  that something a document names does not exist);
- claims: what a requirement states about a setting, which design evidence decides
  it, and the recorded label (agrees, disagrees or unresolved).

This script confirms that every piece of evidence is still where the case says it is,
recomputes the outcome of every claim, and compares it with the recorded label.
It uses only the Python standard library.

Exit status:
  0  all evidence confirmed and every outcome matches its recorded label
  1  as 0, but --fail-on-inconsistency was given and some outcome is not "agrees"
  2  the case needs review: evidence could not be confirmed at this checkout, the
     design evidence for a claim is inconsistent, or an outcome no longer matches
     its recorded label
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = 2
REQUIRED_KEYS = {"schema", "id", "title", "opentitan_revision", "requirements", "design",
                 "claims"}
LABELS = {"agrees", "disagrees", "unresolved"}


@dataclass
class Located:
    item_id: str
    ok: bool
    detail: str
    value: int | None = None
    absent: bool = False


@dataclass
class ClaimResult:
    claim_id: str
    setting: str
    stated: str
    design: str
    outcome: str
    label: str
    evidence_ok: bool

    @property
    def matches_label(self) -> bool:
        return self.outcome == self.label


@dataclass
class Report:
    case_id: str
    title: str
    revision: str
    revision_matches: bool
    recorded_revision: str
    evidence: list[Located] = field(default_factory=list)
    claims: list[ClaimResult] = field(default_factory=list)

    @property
    def evidence_ok(self) -> bool:
        return all(e.ok for e in self.evidence) and all(c.evidence_ok for c in self.claims)

    @property
    def labels_ok(self) -> bool:
        return all(c.matches_label for c in self.claims)

    @property
    def needs_review(self) -> bool:
        return not (self.evidence_ok and self.labels_ok)

    @property
    def not_agreeing(self) -> list[str]:
        return [c.claim_id for c in self.claims if c.outcome != "agrees"]


def load_case(path: Path) -> dict:
    case = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_KEYS - case.keys()
    if missing:
        raise ValueError(f"{path}: missing keys {sorted(missing)}")
    if case["schema"] != SCHEMA_VERSION:
        raise ValueError(f"{path}: schema {case['schema']} is not supported "
                         f"(expected {SCHEMA_VERSION})")
    ids = [i["id"] for i in case["requirements"] + case["design"] + case["claims"]]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"{path}: duplicate ids {duplicates}")
    known = {i["id"] for i in case["requirements"] + case["design"]}
    for claim in case["claims"]:
        if claim["label"] not in LABELS:
            raise ValueError(f"{path}: claim {claim['id']} has unknown label {claim['label']!r}")
        for ref in claim["requirements"] + claim["design"]:
            if ref not in known:
                raise ValueError(f"{path}: claim {claim['id']} refers to unknown id {ref}")
    return case


def current_revision(checkout: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _read_lines(checkout: Path, item: dict) -> list[str] | None:
    path = checkout / item["file"]
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").splitlines()


def locate_line(checkout: Path, item: dict) -> Located:
    """Find a quoted line, at its recorded line number or by searching.

    With "after", the first occurrence of the text within "within" lines (default 20)
    after the single line containing the anchor text is used. This disambiguates text
    that occurs more than once in a file, such as a reset value.
    """
    lines = _read_lines(checkout, item)
    if lines is None:
        return Located(item["id"], False, f"file not found: {item['file']}")
    want, line = item["text"], item["line"]
    value = item.get("value")

    if "after" in item:
        anchors = [i for i, text in enumerate(lines) if item["after"] in text]
        if len(anchors) != 1:
            return Located(item["id"], False,
                           f"anchor {item['after']!r} found {len(anchors)} times in {item['file']}")
        start = anchors[0] + 1
        window = range(start, min(start + item.get("within", 20), len(lines)))
        hits = [i + 1 for i in window if want in lines[i]][:1]
    else:
        hits = [i + 1 for i, text in enumerate(lines) if want in text]

    if line in hits:
        return Located(item["id"], True, f"{item['file']}:{line}", value)
    if len(hits) == 1:
        return Located(item["id"], True, f"{item['file']}:{hits[0]} (moved from line {line})",
                       value)
    if hits:
        return Located(item["id"], False,
                       f"text found on several lines {hits} of {item['file']}, expected line {line}")
    return Located(item["id"], False, f"text not found in {item['file']}")


def locate_all_instances(checkout: Path, item: dict) -> Located:
    lines = _read_lines(checkout, item)
    if lines is None:
        return Located(item["id"], False, f"file not found: {item['file']}")
    values = [int(v, 16) for v in re.findall(item["pattern"], "\n".join(lines))]
    expected_count = item.get("expected_count")
    if not values:
        return Located(item["id"], False, f"pattern matched nothing in {item['file']}")
    if expected_count is not None and len(values) != expected_count:
        return Located(item["id"], False,
                       f"{len(values)} instances in {item['file']}, case expects {expected_count}")
    distinct = sorted(set(values))
    if len(distinct) != 1:
        return Located(item["id"], False,
                       f"instances disagree in {item['file']}: values {distinct}")
    if "value" in item and distinct[0] != item["value"]:
        return Located(item["id"], False,
                       f"{len(values)} instances in {item['file']} are all {distinct[0]}, "
                       f"but the case records {item['value']}", distinct[0])
    return Located(item["id"], True,
                   f"{len(values)} instances in {item['file']}, all {distinct[0]}", distinct[0])


def locate_absent(checkout: Path, item: dict) -> Located:
    lines = _read_lines(checkout, item)
    if lines is None:
        return Located(item["id"], False, f"file not found: {item['file']}")
    hits = [i + 1 for i, text in enumerate(lines) if re.search(item["pattern"], text)]
    if hits:
        return Located(item["id"], False,
                       f"expected no match, but found one on lines {hits} of {item['file']}")
    return Located(item["id"], True, f"absent from {item['file']}: {item['description']}",
                   absent=True)


LOCATORS = {
    "line": locate_line,
    "all_instances": locate_all_instances,
    "absent": locate_absent,
}


def _fmt(value: int | None, radix: int) -> str:
    if value is None:
        return "-"
    return hex(value) if radix == 16 else str(value)


def evaluate_claim(claim: dict, located: dict[str, Located]) -> ClaimResult:
    radix = claim.get("radix", 10)
    evidence = [located[ref] for ref in claim["design"]]
    evidence_ok = all(e.ok for e in evidence) and all(located[r].ok for r in claim["requirements"])
    stated = claim.get("stated")
    stated_text = _fmt(stated, radix) if stated is not None else claim.get("stated_text", "-")
    refs = ", ".join(claim["design"])

    if any(e.absent for e in evidence):
        design_text = f"not present ({refs})"
        outcome = "unresolved"
    else:
        values = {e.value for e in evidence if e.value is not None}
        if len(values) != 1:
            design_text = f"inconsistent or missing values {sorted(values)} ({refs})"
            return ClaimResult(claim["id"], claim["setting"], stated_text, design_text,
                               "unresolved", claim["label"], False)
        design_value = values.pop()
        design_text = f"{_fmt(design_value, radix)} ({refs})"
        if stated is None:
            outcome = "unresolved"
        else:
            outcome = "agrees" if stated == design_value else "disagrees"

    return ClaimResult(claim["id"], claim["setting"], stated_text, design_text, outcome,
                       claim["label"], evidence_ok)


def check(case: dict, checkout: Path) -> Report:
    revision = current_revision(checkout)
    report = Report(case["id"], case["title"], revision,
                    revision == case["opentitan_revision"], case["opentitan_revision"])
    located: dict[str, Located] = {}
    for item in case["requirements"]:
        located[item["id"]] = locate_line(checkout, item)
    for item in case["design"]:
        located[item["id"]] = LOCATORS[item.get("kind", "line")](checkout, item)
    report.evidence = list(located.values())
    report.claims = [evaluate_claim(c, located) for c in case["claims"]]
    return report


def format_report(report: Report) -> str:
    out = [f"Case {report.case_id}: {report.title}"]
    if report.revision_matches:
        out.append(f"OpenTitan revision: {report.revision} (matches the case)")
    else:
        out.append(f"OpenTitan revision: {report.revision} "
                   f"(case recorded {report.recorded_revision}; lines were searched)")
    out += ["", "Evidence:"]
    for e in report.evidence:
        out.append(f"  [{'ok' if e.ok else 'MISSING'}] {e.item_id}: {e.detail}")
    out += ["", "Claims:"]
    for c in report.claims:
        line = f"  {c.claim_id} {c.setting}: stated {c.stated}, design {c.design} -> {c.outcome}"
        if not c.matches_label:
            line += f" (RECORDED LABEL: {c.label})"
        out.append(line)
    counts = {label: sum(c.outcome == label for c in report.claims) for label in
              ("agrees", "disagrees", "unresolved")}
    out.append("")
    summary = (f"{counts['agrees']} agree, {counts['disagrees']} disagree, "
               f"{counts['unresolved']} unresolved")
    if not report.evidence_ok:
        out.append(f"RESULT: {summary}; evidence could not be confirmed, case needs review")
    elif not report.labels_ok:
        out.append(f"RESULT: {summary}; outcomes differ from the recorded labels, "
                   f"case needs review")
    else:
        out.append(f"RESULT: {summary}; all outcomes match the recorded labels")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", type=Path, nargs="+", help="paths to case.json files")
    parser.add_argument("--opentitan", type=Path, required=True,
                        help="path to an OpenTitan checkout")
    parser.add_argument("--fail-on-inconsistency", action="store_true",
                        help="exit 1 if any claim does not agree with the design")
    args = parser.parse_args(argv)

    status = 0
    for i, path in enumerate(args.cases):
        if i:
            print("\n" + "=" * 72 + "\n")
        report = check(load_case(path), args.opentitan)
        print(format_report(report))
        if report.needs_review:
            status = 2
        elif args.fail_on_inconsistency and report.not_agreeing and status == 0:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
