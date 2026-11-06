#!/usr/bin/env python3
"""Score retrieval results against the query set and write a comparison report.

A returned passage is correct for a query if it is from the current revision, in the
same file as one of the query's target passages, and their line ranges overlap.
When the corpus also holds passages of an earlier revision, the report also counts, for
the questions whose answer changed, how often a passage giving the earlier answer was
ranked above the first correct one, and for all questions, how often the first result
came from the earlier revision.

For each method the report gives, overall and per query group, with the number of
queries as the denominator:

- Recall@1: queries whose first returned passage is correct;
- Recall@5: queries with a correct passage among the first five;
- MRR@10: mean of 1/rank of the first correct passage within the first ten (0 if none);

and lists, per query, the rank of the first correct passage, and for every query
without a correct passage in the first five, what was returned first.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rank import load_queries, questions_hash  # noqa: E402


def consistency_problems(queries: dict, results: list[dict]) -> list[str]:
    """Reasons why results cannot be compared with each other or with the query set."""
    problems = []
    current = questions_hash({q["id"]: q["question"] for q in queries["queries"]})
    for r in results:
        if r["opentitan_revision"] != queries["opentitan_revision"]:
            problems.append(f"{r['method']}: OpenTitan revision {r['opentitan_revision']} differs "
                            f"from the queries' {queries['opentitan_revision']}")
        if r.get("questions_sha256") != current:
            problems.append(f"{r['method']}: produced from different questions; re-run rank.py")
        if r.get("earlier_revision") != queries.get("earlier_revision"):
            problems.append(f"{r['method']}: earlier revision {r.get('earlier_revision')} differs "
                            f"from the queries' {queries.get('earlier_revision')}")
    if len({r["corpus"]["sha256"] for r in results}) > 1:
        problems.append("the results were produced from different corpora")
    return problems


def _overlaps(passage: dict, targets: list[dict]) -> bool:
    return any(
        passage["path"] == t["path"]
        and passage["start_line"] <= t["lines"][1]
        and t["lines"][0] <= passage["end_line"]
        for t in targets
    )


def is_hit(passage: dict, targets: list[dict]) -> bool:
    """A correct passage: current revision, same file, overlapping lines."""
    return "revision" not in passage and _overlaps(passage, targets)


def is_outdated_hit(passage: dict, outdated: list[dict]) -> bool:
    """A passage of the earlier revision that gives the earlier answer."""
    return "revision" in passage and _overlaps(passage, outdated)


def first_rank(ranking: list[dict], match) -> int | None:
    for rank, passage in enumerate(ranking, start=1):
        if match(passage):
            return rank
    return None


def first_hit_rank(ranking: list[dict], targets: list[dict]) -> int | None:
    return first_rank(ranking, lambda p: is_hit(p, targets))


def metrics(ranks: list[int | None]) -> dict:
    n = len(ranks)
    r1 = sum(1 for r in ranks if r == 1)
    r5 = sum(1 for r in ranks if r is not None and r <= 5)
    mrr = sum(1 / r for r in ranks if r is not None) / n if n else 0.0
    return {"n": n, "recall_at_1": r1, "recall_at_5": r5, "mrr_at_10": round(mrr, 3)}


def score(queries: dict, result: dict) -> dict:
    ranks, outdated_ranks, earlier_first = {}, {}, []
    for q in queries["queries"]:
        ranking = result["rankings"].get(q["id"])
        if ranking is None:
            raise ValueError(f"{result['method']}: no ranking for {q['id']}")
        ranks[q["id"]] = first_hit_rank(ranking, q["targets"])
        if q.get("outdated"):
            outdated_ranks[q["id"]] = first_rank(ranking, lambda p: is_outdated_hit(p, q["outdated"]))
        if ranking and "revision" in ranking[0]:
            earlier_first.append(q["id"])
    by_group = {}
    for g in queries["groups"]:
        ids = [q["id"] for q in queries["queries"] if q["group"] == g]
        by_group[g] = metrics([ranks[i] for i in ids])
    outdated_above = [i for i, o in outdated_ranks.items()
                      if o is not None and (ranks[i] is None or o < ranks[i])]
    return {"overall": metrics(list(ranks.values())), "by_group": by_group, "ranks": ranks,
            "outdated_ranks": outdated_ranks, "outdated_above": outdated_above,
            "earlier_first": earlier_first}


def _fmt(m: dict) -> str:
    n = m["n"]
    return f"{m['recall_at_1']}/{n} | {m['recall_at_5']}/{n} | {m['mrr_at_10']:.3f}"


def report(queries: dict, results: list[dict], scores: list[dict]) -> str:
    n = len(queries["queries"])
    checked = sum(1 for q in queries["queries"] if q.get("checked"))
    revisions = {r["opentitan_revision"] for r in results}
    hashes = {r["corpus"]["sha256"] for r in results}
    earlier = queries.get("earlier_revision")
    lines = ["# Retrieval comparison" + (" across two revisions" if earlier else ""), ""]
    lines.append(f"OpenTitan revision: `{', '.join(sorted(str(x) for x in revisions))}`. "
                 f"Corpus: {results[0]['corpus']['passages']} passages from "
                 f"{results[0]['corpus']['files']} files.")
    if earlier:
        lines.append(f"The corpus also holds {results[0].get('earlier_passages')} passages of the earlier "
                     f"revision `{earlier}` whose text differs from the current revision. "
                     "Only passages of the current revision count as correct.")
    lines.append("All methods used the same corpus." if len(hashes) == 1
                 else "WARNING: the methods did not use the same corpus.")
    n_targets = sum(len(q["targets"]) for q in queries["queries"])
    lines.append(f"Queries: {n}, with {n_targets} target passages. "
                 f"Target passages checked: {checked} of {n} queries.")
    if checked < n:
        lines.append("These results are provisional until the target passages of every query "
                     "have been checked.")
    for review in queries.get("reviews", []):
        lines.append(f"How the targets in `{review['file']}` were checked ({review['date']}): "
                     f"{review['method']}")
    lines += ["", "## Methods", ""]
    for r in results:
        p = r["parameters"]
        if r["method"] == "embedding":
            desc = (f"`{p['model']}` at revision `{p['model_revision']}`, cosine similarity, "
                    f"query prefix \"{p['query_prefix'].strip()}\"")
        else:
            desc = f"k1 = {p['k1']}, b = {p['b']}; tokens: {p['tokenizer']}"
        lines.append(f"- **{r['method']}**: {desc}.")
    lines += ["", "## Results", "",
              "| Method | Queries | Recall@1 | Recall@5 | MRR@10 |", "|---|---|---|---|---|"]
    for r, s in zip(results, scores):
        lines.append(f"| {r['method']} | all | {_fmt(s['overall'])} |")
        for g, m in s["by_group"].items():
            lines.append(f"| {r['method']} | {g} | {_fmt(m)} |")
    lines += ["", "Group meanings:", ""]
    for g, desc in queries["groups"].items():
        lines.append(f"- **{g}**: {desc}")
    if earlier:
        n_changed = sum(1 for q in queries["queries"] if q.get("outdated"))
        lines += ["", "## Outdated passages", "",
                  "| Method | Earlier answer ranked above the current one "
                  "| First result from the earlier revision |",
                  "|---|---|---|"]
        for r, s in zip(results, scores):
            above = ", ".join(s["outdated_above"]) or "none"
            first = ", ".join(s["earlier_first"]) or "none"
            lines.append(f"| {r['method']} | {len(s['outdated_above'])}/{n_changed} ({above}) | "
                         f"{len(s['earlier_first'])}/{n} ({first}) |")
    lines += ["", "## Per query", "",
              "Rank of the first correct passage in the top 10 (\"-\" if none)"
              + ("; for questions whose answer changed, the rank of the first passage giving the "
                 "earlier answer follows in brackets." if earlier else "."), "",
              "| Query | Group | " + " | ".join(r["method"] for r in results) + " |",
              "|---|---|" + "---|" * len(results)]
    for q in queries["queries"]:
        cells = []
        for s in scores:
            rank = s["ranks"][q["id"]]
            cell = "-" if rank is None else str(rank)
            if q["id"] in s["outdated_ranks"]:
                o = s["outdated_ranks"][q["id"]]
                cell += f" ({'-' if o is None else o})"
            cells.append(cell)
        lines.append(f"| {q['id']} | {q['group']} | " + " | ".join(cells) + " |")
    lines += ["", "## Queries without a correct passage in the top 5", ""]
    any_miss = False
    for q in queries["queries"]:
        misses = [(r, s) for r, s in zip(results, scores)
                  if s["ranks"][q["id"]] is None or s["ranks"][q["id"]] > 5]
        if not misses:
            continue
        any_miss = True
        lines.append(f"**{q['id']}** ({q['group']}): {q['question']}")
        lines.append("")
        targets = "; ".join(f"`{t['path']}:{t['lines'][0]}-{t['lines'][1]}`" for t in q["targets"])
        lines.append(f"- expected: {targets}")
        for r, s in misses:
            first = r["rankings"][q["id"]][0]
            rank = s["ranks"][q["id"]]
            lines.append(f"- {r['method']}: first correct at {rank if rank else 'none in top 10'}; "
                         f"returned first `{first['id']}`")
        lines.append("")
    if not any_miss:
        lines.append("None.")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="+", type=Path, help="output files of rank.py")
    parser.add_argument("--queries", type=Path, action="append",
                        help="query file (repeat for several; default: queries.json)")
    parser.add_argument("--report", type=Path, help="write a Markdown report")
    parser.add_argument("--strict", action="store_true",
                        help="exit with 2 if the results do not match the query set and each other")
    args = parser.parse_args(argv)
    queries = load_queries(args.queries or [Path(__file__).parent / "queries.json"])
    results = [json.loads(p.read_text(encoding="utf-8")) for p in args.results]
    problems = consistency_problems(queries, results)
    for p in problems:
        print("PROBLEM", p)
    if problems and args.strict:
        return 2
    scores = [score(queries, r) for r in results]
    for r, s in zip(results, scores):
        o = s["overall"]
        extra = ""
        if queries.get("earlier_revision"):
            extra = (f"; earlier answer above the current one {len(s['outdated_above'])}, "
                     f"first result from the earlier revision {len(s['earlier_first'])}")
        print(f"{r['method']}: Recall@1 {o['recall_at_1']}/{o['n']}, Recall@5 {o['recall_at_5']}/{o['n']}, "
              f"MRR@10 {o['mrr_at_10']:.3f}{extra}")
    if args.report:
        args.report.write_text(report(queries, results, scores), encoding="utf-8")
        print(f"report written to {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
