#!/usr/bin/env python3
"""Score retrieval results against the query set and write a comparison report.

A returned passage is correct for a query if it is in the same file as one of the
query's target passages and their line ranges overlap.

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

from rank import questions_hash  # noqa: E402


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
    if len({r["corpus"]["sha256"] for r in results}) > 1:
        problems.append("the results were produced from different corpora")
    return problems


def is_hit(passage: dict, targets: list[dict]) -> bool:
    return any(
        passage["path"] == t["path"]
        and passage["start_line"] <= t["lines"][1]
        and t["lines"][0] <= passage["end_line"]
        for t in targets
    )


def first_hit_rank(ranking: list[dict], targets: list[dict]) -> int | None:
    for rank, passage in enumerate(ranking, start=1):
        if is_hit(passage, targets):
            return rank
    return None


def metrics(ranks: list[int | None]) -> dict:
    n = len(ranks)
    r1 = sum(1 for r in ranks if r == 1)
    r5 = sum(1 for r in ranks if r is not None and r <= 5)
    mrr = sum(1 / r for r in ranks if r is not None) / n if n else 0.0
    return {"n": n, "recall_at_1": r1, "recall_at_5": r5, "mrr_at_10": round(mrr, 3)}


def score(queries: dict, result: dict) -> dict:
    ranks = {}
    for q in queries["queries"]:
        ranking = result["rankings"].get(q["id"])
        if ranking is None:
            raise ValueError(f"{result['method']}: no ranking for {q['id']}")
        ranks[q["id"]] = first_hit_rank(ranking, q["targets"])
    by_group = {}
    for g in queries["groups"]:
        ids = [q["id"] for q in queries["queries"] if q["group"] == g]
        by_group[g] = metrics([ranks[i] for i in ids])
    return {"overall": metrics(list(ranks.values())), "by_group": by_group, "ranks": ranks}


def _fmt(m: dict) -> str:
    n = m["n"]
    return f"{m['recall_at_1']}/{n} | {m['recall_at_5']}/{n} | {m['mrr_at_10']:.3f}"


def report(queries: dict, results: list[dict], scores: list[dict]) -> str:
    n = len(queries["queries"])
    verified = sum(1 for q in queries["queries"] if q.get("verified"))
    revisions = {r["opentitan_revision"] for r in results}
    hashes = {r["corpus"]["sha256"] for r in results}
    lines = ["# Retrieval comparison", ""]
    lines.append(f"OpenTitan revision: `{', '.join(sorted(str(x) for x in revisions))}`. "
                 f"Corpus: {results[0]['corpus']['passages']} passages from "
                 f"{results[0]['corpus']['files']} files.")
    lines.append("All methods used the same corpus." if len(hashes) == 1
                 else "WARNING: the methods did not use the same corpus.")
    lines.append(f"Queries: {n}. Target passages verified by a person: {verified} of {n}.")
    if verified < n:
        lines.append("These results are provisional until every target passage has been verified.")
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
    lines += ["", "## Per query", "",
              "Rank of the first correct passage in the top 10 (\"-\" if none).", "",
              "| Query | Group | " + " | ".join(r["method"] for r in results) + " |",
              "|---|---|" + "---|" * len(results)]
    for q in queries["queries"]:
        cells = []
        for s in scores:
            rank = s["ranks"][q["id"]]
            cells.append("-" if rank is None else str(rank))
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
    parser.add_argument("--queries", type=Path, default=Path(__file__).parent / "queries.json")
    parser.add_argument("--report", type=Path, help="write a Markdown report")
    parser.add_argument("--strict", action="store_true",
                        help="exit with 2 if the results do not match the query set and each other")
    args = parser.parse_args(argv)
    queries = json.loads(args.queries.read_text(encoding="utf-8"))
    results = [json.loads(p.read_text(encoding="utf-8")) for p in args.results]
    problems = consistency_problems(queries, results)
    for p in problems:
        print("PROBLEM", p)
    if problems and args.strict:
        return 2
    scores = [score(queries, r) for r in results]
    for r, s in zip(results, scores):
        o = s["overall"]
        print(f"{r['method']}: Recall@1 {o['recall_at_1']}/{o['n']}, Recall@5 {o['recall_at_5']}/{o['n']}, "
              f"MRR@10 {o['mrr_at_10']:.3f}")
    if args.report:
        args.report.write_text(report(queries, results, scores), encoding="utf-8")
        print(f"report written to {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
