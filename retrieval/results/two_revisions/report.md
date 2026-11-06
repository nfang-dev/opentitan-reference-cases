# Retrieval comparison across two revisions

OpenTitan revision: `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Corpus: 3350 passages from 204 files.
Of these, 371 are passages of the earlier revision `63c8a5025a0b02f50c3502e8ae0653cfd4a36ff9` whose text differs from the current revision. Only passages of the current revision count as correct.
All methods used the same corpus.
Queries: 35, with 57 target passages. Target passages checked: 35 of 35 queries.
How the targets in `queries.json` were checked (2026-11-05): Every target passage was read against the source text at the recorded revision and confirmed to answer its question. Every passage that either method ranked in its first three for a question, but that was not a target, was read; the ones that state at least part of the answer were added as targets.
How the targets in `queries_changed.json` were checked (2026-11-05): Each question was chosen from a line-by-line comparison of the two revisions' documentation, limited to statements about settings whose meaning changed. Every target and outdated passage was read against the source text of its revision.

## Methods

- **bm25**: k1 = 1.2, b = 0.75; tokens: lowercase, split on non-alphanumeric, drop function words.
- **embedding**: `BAAI/bge-small-en-v1.5` at revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, cosine similarity, query prefix "Represent this sentence for searching relevant passages:".

## Results

| Method | Queries | Recall@1 | Recall@5 | MRR@10 |
|---|---|---|---|---|
| bm25 | all | 24/35 | 33/35 | 0.796 |
| bm25 | case | 3/4 | 4/4 | 0.875 |
| bm25 | renamed | 3/4 | 4/4 | 0.800 |
| bm25 | general | 14/19 | 17/19 | 0.823 |
| bm25 | changed | 4/8 | 8/8 | 0.692 |
| embedding | all | 25/35 | 34/35 | 0.821 |
| embedding | case | 3/4 | 4/4 | 0.812 |
| embedding | renamed | 4/4 | 4/4 | 1.000 |
| embedding | general | 13/19 | 18/19 | 0.807 |
| embedding | changed | 5/8 | 8/8 | 0.771 |

Group meanings:

- **case**: Taken from the statements in reference cases 001 to 003.
- **renamed**: The question uses the register or field name defined in the design; the passage that answers it uses an older or different name.
- **general**: Questions about reset values, defaults and configuration in other modules.
- **changed**: The documentation's answer changed between the earlier and the current revision.

## Outdated passages

| Method | Earlier answer ranked above the current one | First result from the earlier revision |
|---|---|---|
| bm25 | 3/8 (V01, V05, V08) | 3/35 (V01, V05, V08) |
| embedding | 2/8 (V05, V08) | 3/35 (Q08, V05, V08) |

## Per query

Rank of the first correct passage in the top 10 ("-" if none); for questions whose answer changed, the rank of the first passage giving the earlier answer follows in brackets.

| Query | Group | bm25 | embedding |
|---|---|---|---|
| Q01 | case | 2 | 1 |
| Q02 | case | 1 | 1 |
| Q03 | case | 1 | 4 |
| Q04 | case | 1 | 1 |
| Q05 | general | 1 | - |
| Q06 | renamed | 5 | 1 |
| Q07 | renamed | 1 | 1 |
| Q08 | general | 1 | 2 |
| Q09 | renamed | 1 | 1 |
| Q10 | renamed | 1 | 1 |
| Q11 | general | 1 | 1 |
| Q12 | general | 1 | 1 |
| Q13 | general | 1 | 2 |
| Q14 | general | 1 | 1 |
| Q15 | general | 6 | 1 |
| Q16 | general | 1 | 1 |
| Q17 | general | 1 | 1 |
| Q18 | general | 1 | 2 |
| Q19 | general | 1 | 1 |
| Q20 | general | 1 | 2 |
| Q21 | general | 7 | 3 |
| Q22 | general | 1 | 1 |
| Q23 | general | 3 | 1 |
| Q24 | general | 1 | 1 |
| Q25 | general | 1 | 1 |
| Q26 | general | 2 | 1 |
| Q27 | general | 2 | 1 |
| V01 | changed | 3 (1) | 1 (4) |
| V02 | changed | 1 (3) | 1 (2) |
| V03 | changed | 1 (2) | 1 (2) |
| V04 | changed | 2 (-) | 3 (-) |
| V05 | changed | 2 (1) | 2 (1) |
| V06 | changed | 1 (2) | 1 (2) |
| V07 | changed | 1 (2) | 1 (4) |
| V08 | changed | 5 (1) | 3 (1) |

## Queries without a correct passage in the top 5

**Q05** (general): What does setting IO_MEAS_CTRL_EN in clkmgr turn on?

- expected: `hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.md:265-271`; `hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.md:300-300`
- embedding: first correct at none in top 10; returned first `hw/ip_templates/clkmgr/doc/programmers_guide.md:13-13`

**Q15** (general): Which EDN request mode is active after reset before software configures the block?

- expected: `hw/ip/edn/doc/theory_of_operation.md:28-30`; `hw/ip/edn/doc/theory_of_operation.md:137-138`
- bm25: first correct at 6; returned first `hw/ip/edn/doc/theory_of_operation.md:75-77`

**Q21** (general): Does the PLIC forward a pending interrupt to the CPU right after reset if software has not configured it?

- expected: `hw/ip_templates/rv_plic/doc/programmers_guide.md:3-7`
- bm25: first correct at 7; returned first `hw/ip_templates/rv_plic/doc/programmers_guide.md:36-53`
