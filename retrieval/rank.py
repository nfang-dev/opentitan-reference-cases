#!/usr/bin/env python3
"""Rank corpus passages for every query with one retrieval method.

Methods:

- bm25: Okapi BM25 over word tokens (standard library only).
- embedding: cosine similarity between sentence embeddings from a locally run model
  (needs the packages in requirements-embed.txt; the model is downloaded once).

Both methods index the same passage text (see corpus.py) and return the top K passages
for each query. With --earlier, passages of an earlier revision whose text differs from
the current revision are added to the corpus (see corpus.build_earlier); with
--earlier-last as well, every current passage is ranked above every earlier passage.
The output records the method, its parameters, the OpenTitan revision of the checkout
and a hash of the corpus, so that results from different methods can be checked to use
the same input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus  # noqa: E402

TOP_K = 10

# A short list of English function words. Domain words such as "reset", "after",
# "before" and "not" are kept.
STOPWORDS = frozenset("""
a an and are as at be been by can do does for from has have how if in into is it its
of on or should so such that the their then there these this those to was were what
when where which while who will with would
""".split())

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, split on anything that is not a letter or digit, drop function words.

    Identifiers are split at underscores, so IO_MEAS_CTRL_EN becomes io, meas, ctrl, en.
    """
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg_len = sum(self.len) / len(docs)
        df = Counter(t for d in self.tf for t in d)
        n = len(docs)
        self.idf = {t: math.log((n - f + 0.5) / (f + 0.5) + 1.0) for t, f in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for tf, length in zip(self.tf, self.len):
            norm = self.k1 * (1 - self.b + self.b * length / self.avg_len)
            s = 0.0
            for t in query:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out


def top_k(passages: list[dict], scores: list[float], k: int = TOP_K,
          earlier_last: bool = False) -> list[dict]:
    """The k best passages. With earlier_last, every passage of the current revision ranks
    above every passage of an earlier revision; within each, by score."""
    def key(i):
        return (earlier_last and "revision" in passages[i], -scores[i], passages[i]["id"])
    order = sorted(range(len(passages)), key=key)
    out = []
    for i in order[:k]:
        item = {"id": passages[i]["id"], "path": passages[i]["path"],
                "start_line": passages[i]["start_line"], "end_line": passages[i]["end_line"],
                "score": round(float(scores[i]), 6)}
        if "revision" in passages[i]:
            item["revision"] = passages[i]["revision"]
        out.append(item)
    return out


def load_queries(paths: list[Path]) -> dict:
    """Merge query files that share one OpenTitan revision into a single query set."""
    merged = {"opentitan_revision": None, "earlier_revision": None, "groups": {}, "queries": [],
              "reviews": []}
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if merged["opentitan_revision"] not in (None, data["opentitan_revision"]):
            raise ValueError(f"{path}: OpenTitan revision differs from the other query files")
        merged["opentitan_revision"] = data["opentitan_revision"]
        if "earlier_revision" in data:
            if merged["earlier_revision"] not in (None, data["earlier_revision"]):
                raise ValueError(f"{path}: earlier revision differs from the other query files")
            merged["earlier_revision"] = data["earlier_revision"]
        merged["groups"].update(data["groups"])
        merged["queries"].extend(data["queries"])
        if data.get("review"):
            merged["reviews"].append(dict(data["review"], file=Path(path).name))
    ids = [q["id"] for q in merged["queries"]]
    if len(ids) != len(set(ids)):
        raise ValueError("query ids repeat across the query files")
    return merged


def rank_bm25(passages: list[dict], questions: dict[str, str],
              earlier_last: bool = False) -> tuple[dict, dict]:
    index = BM25([tokenize(p["text"]) for p in passages])
    rankings = {qid: top_k(passages, index.scores(tokenize(q)), earlier_last=earlier_last)
                for qid, q in questions.items()}
    return {"k1": index.k1, "b": index.b, "tokenizer": "lowercase, split on non-alphanumeric, "
            "drop function words"}, rankings


def rank_embedding(passages: list[dict], questions: dict[str, str], model_name: str,
                   revision: str, query_prefix: str,
                   earlier_last: bool = False) -> tuple[dict, dict]:
    import numpy as np
    import sentence_transformers
    import torch
    import transformers
    from huggingface_hub import HfApi
    from sentence_transformers import SentenceTransformer

    resolved = HfApi().model_info(model_name, revision=revision).sha
    torch.manual_seed(0)
    model = SentenceTransformer(model_name, revision=resolved, device="cpu")
    doc_vecs = model.encode([p["text"] for p in passages], batch_size=32,
                            normalize_embeddings=True, show_progress_bar=False)
    ids = list(questions)
    q_vecs = model.encode([query_prefix + questions[i] for i in ids],
                          normalize_embeddings=True, show_progress_bar=False)
    sims = np.asarray(q_vecs) @ np.asarray(doc_vecs).T
    rankings = {qid: top_k(passages, sims[n].tolist(), earlier_last=earlier_last)
                for n, qid in enumerate(ids)}
    params = {
        "model": model_name,
        "model_revision": resolved,
        "query_prefix": query_prefix,
        "max_seq_length": model.max_seq_length,
        "similarity": "cosine",
        "versions": {
            "sentence_transformers": sentence_transformers.__version__,
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
    }
    return params, rankings


def corpus_hash(passages: list[dict]) -> str:
    h = hashlib.sha256()
    for p in passages:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def questions_hash(questions: dict[str, str]) -> str:
    """Hash of the query ids and question texts, to detect results from older questions."""
    return hashlib.sha256(json.dumps(questions, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def checkout_revision(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--method", required=True, choices=["bm25", "embedding"])
    parser.add_argument("--opentitan", required=True, type=Path)
    parser.add_argument("--queries", type=Path, action="append",
                        help="query file (repeat for several; default: queries.json)")
    parser.add_argument("--earlier", type=Path,
                        help="checkout of the earlier revision named in the query files")
    parser.add_argument("--earlier-last", action="store_true",
                        help="with --earlier, rank every passage of the current revision above "
                        "every passage of the earlier revision (uses the passages' revision)")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--model-revision", default="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
                        help="model revision (a commit of the model repository); the resolved commit "
                        "is recorded in the output")
    parser.add_argument("--query-prefix",
                        default="Represent this sentence for searching relevant passages: ",
                        help="instruction prepended to each question (as recommended for BGE)")
    args = parser.parse_args(argv)

    queries = load_queries(args.queries or [Path(__file__).parent / "queries.json"])
    revision = checkout_revision(args.opentitan)
    if revision and revision != queries["opentitan_revision"]:
        print(f"warning: checkout is at {revision}, queries record {queries['opentitan_revision']}",
              file=sys.stderr)
    passages = corpus.build(args.opentitan)
    earlier_revision = None
    if args.earlier:
        if not queries["earlier_revision"]:
            parser.error("--earlier needs a query file that records an earlier_revision")
        earlier_revision = checkout_revision(args.earlier) or queries["earlier_revision"]
        if earlier_revision != queries["earlier_revision"]:
            parser.error(f"earlier checkout is at {earlier_revision}, "
                         f"queries record {queries['earlier_revision']}")
        passages = passages + corpus.build_earlier(args.earlier, earlier_revision, passages)
    if args.earlier_last and not args.earlier:
        parser.error("--earlier-last needs --earlier")
    questions = {q["id"]: q["question"] for q in queries["queries"]}

    if args.method == "bm25":
        params, rankings = rank_bm25(passages, questions, args.earlier_last)
    else:
        params, rankings = rank_embedding(passages, questions, args.model, args.model_revision,
                                          args.query_prefix, args.earlier_last)
    if args.earlier_last:
        params["earlier_revision_ranked_last"] = True

    result = {
        "method": args.method + ("+revision" if args.earlier_last else ""),
        "parameters": params,
        "opentitan_revision": revision,
        **({"earlier_revision": earlier_revision,
            "earlier_passages": sum(1 for p in passages if "revision" in p)} if earlier_revision else {}),
        "corpus": {"passages": len(passages), "files": len({p["path"] for p in passages}),
                   "sha256": corpus_hash(passages), "max_chars": corpus.MAX_CHARS},
        "questions_sha256": questions_hash(questions),
        "top_k": TOP_K,
        "rankings": rankings,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.method}: ranked {len(passages)} passages for {len(questions)} queries -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
