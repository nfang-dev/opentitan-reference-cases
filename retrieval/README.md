# Retrieval comparison

Given a question a reviewer might ask about a setting in the design, can a search method find the passage in OpenTitan's hand-written documentation that answers it?
This directory compares two methods on the same questions, the same documents and the same scoring:

- **BM25**, a standard keyword ranking (implemented in `rank.py` with the Python standard library);
- a **text-embedding model** run locally on CPU (`BAAI/bge-small-en-v1.5` at model revision `5c38ec7c`, through `sentence-transformers`), ranking passages by cosine similarity.

The results are in [`results/report.md`](results/report.md).

## Results

At OpenTitan revision `0ea5236fe749`, on 27 questions:

| Method | Recall@1 | Recall@5 | MRR@10 |
|---|---|---|---|
| BM25 | 20/27 | 25/27 | 0.829 |
| Embedding model | 21/27 | 26/27 | 0.855 |

With 27 questions, a difference of one question is not evidence that either method is better.
Per-group and per-question results, and the questions each method missed, are in the report.

## Two revisions: outdated passages

A reviewer may have older documentation at hand, and a search index may hold several versions.
The second experiment asks whether a method returns the earlier answer when an earlier revision's documentation is also searchable.

- Earlier revision: `63c8a5025a0b` (2026-05-01). Its passages whose text differs from the current revision are added to the corpus: 371 passages, for 3,350 in total. Passages with identical text are not added, since they give the same answer.
- [`queries_changed.json`](queries_changed.json) holds 8 questions whose documented answer changed between the two revisions (keymgr_dpe, otbn, spi_device, sram_ctrl, spi_host). Each lists target passages at the current revision and the outdated passages at the earlier revision that give the earlier answer. They were chosen from a line-by-line comparison of the two revisions' documentation, limited to statements about settings whose meaning changed. Every passage either method ranked in its first three was read; three target passages and two outdated passages were added this way.
- All 35 questions (the 27 above and these 8) are run on this corpus. Only passages of the current revision count as correct.

| Method | Recall@1 | Recall@5 | MRR@10 | Earlier answer ranked above the current one (of 8) | First result from the earlier revision (of 35) |
|---|---|---|---|---|---|
| BM25 | 24/35 | 33/35 | 0.796 | 3 (V01, V05, V08) | 3 |
| Embedding model | 25/35 | 34/35 | 0.821 | 2 (V05, V08) | 3 |

Both methods ranked the earlier answer first for V05 (spi_device dummy cycles) and V08 (whether spi_host keeps a separate `CONFIGOPTS` per chip select).
Neither method uses the revision a passage comes from, so when outdated documentation is indexed, ranking by text alone can return it first.
The full results are in [`results/two_revisions/report.md`](results/two_revisions/report.md).

While checking V01, a conflict inside the current revision turned up: `hw/ip/keymgr_dpe/doc/theory_of_operation.md` line 85 says "The latching of the root key can only happen once until the keymgr_DPE is reset.", while line 145 says the latching can be repeated with the load root key operation unless locked, and the design defines that operation and `LOAD_ROOT_KEY_LOCK` (`keymgr_dpe.hjson`).
Line 85 counts neither as a target nor as an outdated passage; it has not been reported upstream.

## Corpus

`corpus.py` builds the passages from an OpenTitan checkout at the revision recorded in `queries.json` (`0ea5236fe749`, 2026-11-03):

- every Markdown file under `hw/ip/` and `hw/ip_templates/`;
- for documents that exist only as templates (`*.md.tpl`), the rendered copy for Earl Grey, or for Darjeeling or English Breakfast when Earl Grey has none;
- excluding `registers.md` (generated from the register description), `checklist.md`, `dv/` directories and symbolic links, and leaving out every block between `BEGIN CMDGEN` and `END CMDGEN` markers (also generated).

Files are split at headings, and sections into passages of at most 1200 characters at paragraph boundaries.
Each passage keeps its file and line range.
The indexed text is the module name, file name, heading chain and passage, with Markdown links reduced to their text; both methods index the same text.
At the recorded revision the corpus has 2979 passages from 198 files.

## Queries

`queries.json` holds 27 questions in three groups:

| Group | Questions | What they test |
|---|---|---|
| case | 4 | The statements checked in reference cases 001 to 003. |
| renamed | 4 | The question uses the register or field name the design defines; the passage that answers it uses an older or different name (for example `IO_MEAS_CTRL_EN` in the design, `IO_MEASURE_CTRL` in the documentation). |
| general | 19 | Reset values, defaults and configuration in other modules. |

Each question lists one or more target passages (file, line range and a short quote that must appear in that range), 44 in total.
`check_queries.py` confirms every target against a checkout.

The targets were first chosen by reading the documentation, and then checked (2026-11-05, recorded under `review` in `queries.json`):

- every target passage was read against the source text at the recorded revision and confirmed to answer its question;
- every passage that either method ranked in its first three for a question, but that was not a target, was read (pooling), and the ones that state at least part of the answer were added as targets: seven passages, for Q01, Q05, Q13, Q15, Q24 and Q27 (two).

A passage counts as answering if it states at least part of the answer; for example, for a question with two parts, a passage that answers one part.
Q05 and Q08 were moved from the renamed group to the general group, because a passage that uses the design's name also answers each of them.

## Scoring

A returned passage is correct if it is in the same file as a target passage and their line ranges overlap.
`evaluate.py` reports, overall and per group, with the number of questions as the denominator:

- Recall@1: questions whose first result is correct;
- Recall@5: questions with a correct result in the first five;
- MRR@10: the mean of 1/rank of the first correct result in the first ten (0 if none);

and, for each question, the rank of the first correct result and, where there is none in the top five, what was returned first.

## Re-running

```sh
# Fetch only the documentation files, at the recorded revision (about 11 MB).
./retrieval/fetch_docs.sh otdocs

python3 retrieval/check_queries.py --opentitan otdocs
python3 retrieval/rank.py --method bm25 --opentitan otdocs --out retrieval/results/bm25.json

# The embedding method needs PyTorch and sentence-transformers:
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.3.1
pip install -r retrieval/requirements-embed.txt
python3 retrieval/rank.py --method embedding --opentitan otdocs --out retrieval/results/embedding.json

python3 retrieval/evaluate.py retrieval/results/bm25.json retrieval/results/embedding.json \
  --strict --report retrieval/results/report.md

# Two revisions: also fetch the earlier documentation and pass both query files.
./retrieval/fetch_docs.sh otdocs-earlier earlier
Q="--queries retrieval/queries.json --queries retrieval/queries_changed.json"
python3 retrieval/check_queries.py $Q --opentitan otdocs --earlier otdocs-earlier
python3 retrieval/rank.py --method bm25 $Q --opentitan otdocs --earlier otdocs-earlier \
  --out retrieval/results/two_revisions/bm25.json
python3 retrieval/rank.py --method embedding $Q --opentitan otdocs --earlier otdocs-earlier \
  --out retrieval/results/two_revisions/embedding.json
python3 retrieval/evaluate.py retrieval/results/two_revisions/*.json $Q --strict \
  --report retrieval/results/two_revisions/report.md
```

Each result file records the method and its parameters (for the embedding model, the resolved model revision and library versions), the OpenTitan revision, a hash of the corpus and a hash of the questions.
With `--strict`, `evaluate.py` refuses to compare results produced from different revisions, corpora or questions.

CI re-checks every target passage, re-runs BM25 and compares it with the committed results on every push.
The embedding method runs in a separate workflow when files in this directory change.
A second run with the pinned model revision ([run 41979669877](https://github.com/nfang-dev/opentitan-reference-cases/actions/runs/41979669877)) returned the same ten passages in the same order for every question as the committed results, with scores differing by at most 0.000001.

## Limitations

- The set is small (27 questions), so differences of one or two questions between methods are not meaningful.
- The questions were written after reading the documentation, which may make their wording closer to the target passages than a real reviewer's would be.
- The two-revision experiment uses one earlier revision and 8 questions whose answer changed, so it shows that outdated passages can be ranked first, not how often this happens in general.
- One embedding model and one keyword method are compared; no reranking or language model is used.
- A passage that answers a question but is not listed as a target counts as wrong. Pooling covers the first three results of these two methods only; another method could surface further answering passages.
