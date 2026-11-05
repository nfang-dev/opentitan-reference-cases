# Retrieval comparison

Given a question a reviewer might ask about a setting in the design, can a search method find the passage in OpenTitan's hand-written documentation that answers it?
This directory compares two methods on the same questions, the same documents and the same scoring:

- **BM25**, a standard keyword ranking (implemented in `rank.py` with the Python standard library);
- a **text-embedding model** run locally on CPU (`BAAI/bge-small-en-v1.5` through `sentence-transformers`), ranking passages by cosine similarity.

The results are in [`results/report.md`](results/report.md).

## Status

The target passages for each question have not yet been verified by a person (`"verified": false` in `queries.json`).
Until they are, the results are provisional.

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
| renamed | 5 | The question uses the register or field name the design defines; the passage that answers it uses an older or different name (for example `IO_MEAS_CTRL_EN` in the design, `IO_MEASURE_CTRL` in the documentation). |
| general | 18 | Reset values, defaults and configuration in other modules. |

Each question lists one or more target passages (file, line range and a short quote that must appear in that range).
`check_queries.py` confirms every target against a checkout.

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
```

Each result file records the method and its parameters (for the embedding model, the resolved model revision and library versions), the OpenTitan revision, a hash of the corpus and a hash of the questions.
With `--strict`, `evaluate.py` refuses to compare results produced from different revisions, corpora or questions.

CI re-checks every target passage, re-runs BM25 and compares it with the committed results on every push.
The embedding method runs in a separate workflow when files in this directory change.

## Limitations

- The set is small (27 questions), so differences of one or two questions between methods are not meaningful.
- The questions were written after reading the documentation, which may make their wording closer to the target passages than a real reviewer's would be.
- All passages come from one revision, so the comparison does not yet test whether a method returns an outdated version of a passage.
- One embedding model and one keyword method are compared; no reranking or language model is used.
- A passage that answers a question but is not listed as a target counts as wrong. The target lists are being checked against the top results of both methods.
