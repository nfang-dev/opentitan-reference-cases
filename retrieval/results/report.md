# Retrieval comparison

OpenTitan revision: `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Corpus: 2979 passages from 198 files.
All methods used the same corpus.
Queries: 27. Target passages verified by a person: 0 of 27.
These results are provisional until every target passage has been verified.

## Methods

- **bm25**: k1 = 1.2, b = 0.75; tokens: lowercase, split on non-alphanumeric, drop function words.
- **embedding**: `BAAI/bge-small-en-v1.5` at revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, cosine similarity, query prefix "Represent this sentence for searching relevant passages:".

## Results

| Method | Queries | Recall@1 | Recall@5 | MRR@10 |
|---|---|---|---|---|
| bm25 | all | 19/27 | 24/27 | 0.792 |
| bm25 | case | 3/4 | 4/4 | 0.875 |
| bm25 | renamed | 3/5 | 4/5 | 0.650 |
| bm25 | general | 13/18 | 16/18 | 0.812 |
| embedding | all | 20/27 | 26/27 | 0.836 |
| embedding | case | 3/4 | 4/4 | 0.812 |
| embedding | renamed | 4/5 | 4/5 | 0.800 |
| embedding | general | 13/18 | 18/18 | 0.852 |

Group meanings:

- **case**: Taken from the statements in reference cases 001 to 003.
- **renamed**: The question uses the register or field name defined in the design; the passage that answers it uses an older or different name.
- **general**: Questions about reset values, defaults and configuration in other modules.

## Per query

Rank of the first correct passage in the top 10 ("-" if none).

| Query | Group | bm25 | embedding |
|---|---|---|---|
| Q01 | case | 2 | 1 |
| Q02 | case | 1 | 1 |
| Q03 | case | 1 | 4 |
| Q04 | case | 1 | 1 |
| Q05 | renamed | - | - |
| Q06 | renamed | 4 | 1 |
| Q07 | renamed | 1 | 1 |
| Q08 | general | 1 | 1 |
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
| Q21 | general | 8 | 3 |
| Q22 | general | 1 | 1 |
| Q23 | general | 3 | 1 |
| Q24 | general | 1 | 1 |
| Q25 | general | 1 | 1 |
| Q26 | general | 2 | 1 |
| Q27 | general | 2 | 2 |

## Queries without a correct passage in the top 5

**Q05** (renamed): What does setting IO_MEAS_CTRL_EN in clkmgr turn on?

- expected: `hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.md:265-271`
- bm25: first correct at none in top 10; returned first `hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.md:293-301`
- embedding: first correct at none in top 10; returned first `hw/ip_templates/clkmgr/doc/programmers_guide.md:13-13`

**Q15** (general): Which EDN request mode is active after reset before software configures the block?

- expected: `hw/ip/edn/doc/theory_of_operation.md:28-30`; `hw/ip/edn/doc/theory_of_operation.md:137-138`
- bm25: first correct at 6; returned first `hw/ip/edn/doc/theory_of_operation.md:75-77`

**Q21** (general): Does the PLIC forward a pending interrupt to the CPU right after reset if software has not configured it?

- expected: `hw/ip_templates/rv_plic/doc/programmers_guide.md:3-7`
- bm25: first correct at 8; returned first `hw/ip_templates/rv_plic/doc/programmers_guide.md:36-53`
