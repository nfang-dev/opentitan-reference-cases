# Retrieval comparison

OpenTitan revision: `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Corpus: 2979 passages from 198 files.
All methods used the same corpus.
Queries: 70, with 127 target passages. Target passages checked: 70 of 70 queries.
How the targets in `queries.json` were checked (2026-11-05): Every target passage was read against the source text at the recorded revision and confirmed to answer its question. Every passage that either method ranked in its first three for a question, but that was not a target, was read; the ones that state at least part of the answer were added as targets.
How the targets in `queries_heldout.json` were checked (2026-11-05): Every target passage was read against the source text at the recorded revision and confirmed to answer its question. Every passage that either method ranked in its first three for a question, but that was not a target, was read; the ones that state at least part of the answer were added as targets.

## Methods

- **bm25**: k1 = 1.2, b = 0.75; tokens: lowercase, split on non-alphanumeric, drop function words.
- **embedding**: `BAAI/bge-small-en-v1.5` at revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, cosine similarity, query prefix "Represent this sentence for searching relevant passages:".

## Results

| Method | Queries | Recall@1 | Recall@5 | MRR@10 |
|---|---|---|---|---|
| bm25 | all | 53/70 | 65/70 | 0.832 |
| bm25 | case | 3/4 | 4/4 | 0.875 |
| bm25 | renamed | 3/4 | 4/4 | 0.812 |
| bm25 | general | 14/19 | 17/19 | 0.822 |
| bm25 | heldout | 33/43 | 40/43 | 0.834 |
| embedding | all | 54/70 | 67/70 | 0.853 |
| embedding | case | 3/4 | 4/4 | 0.812 |
| embedding | renamed | 4/4 | 4/4 | 1.000 |
| embedding | general | 14/19 | 18/19 | 0.833 |
| embedding | heldout | 33/43 | 41/43 | 0.852 |

Group meanings:

- **case**: Taken from the statements in reference cases 001 to 003.
- **renamed**: The question uses the register or field name defined in the design; the passage that answers it uses an older or different name.
- **general**: Questions about reset values, defaults and configuration in other modules.
- **heldout**: Written after the methods were fixed, about modules not used in the earlier questions.

## Per query

Rank of the first correct passage in the top 10 ("-" if none).

| Query | Group | bm25 | embedding |
|---|---|---|---|
| Q01 | case | 2 | 1 |
| Q02 | case | 1 | 1 |
| Q03 | case | 1 | 4 |
| Q04 | case | 1 | 1 |
| Q05 | general | 1 | - |
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
| Q27 | general | 2 | 1 |
| H01 | heldout | - | 10 |
| H02 | heldout | 1 | 1 |
| H03 | heldout | 1 | 1 |
| H04 | heldout | 1 | 1 |
| H05 | heldout | 1 | 1 |
| H06 | heldout | 1 | 1 |
| H07 | heldout | 1 | 1 |
| H08 | heldout | 1 | 1 |
| H09 | heldout | 2 | 2 |
| H10 | heldout | 2 | 5 |
| H11 | heldout | 1 | 1 |
| H12 | heldout | 1 | 1 |
| H13 | heldout | 1 | 1 |
| H14 | heldout | 3 | 2 |
| H15 | heldout | 1 | 1 |
| H16 | heldout | 3 | 1 |
| H17 | heldout | 1 | 1 |
| H18 | heldout | 1 | 1 |
| H19 | heldout | 1 | 1 |
| H20 | heldout | 1 | 1 |
| H21 | heldout | 1 | 1 |
| H22 | heldout | 1 | 1 |
| H23 | heldout | 1 | 1 |
| H24 | heldout | 4 | 1 |
| H25 | heldout | 1 | 3 |
| H26 | heldout | 1 | 1 |
| H27 | heldout | 1 | 1 |
| H28 | heldout | 1 | 1 |
| H29 | heldout | 1 | 1 |
| H30 | heldout | 1 | 1 |
| H31 | heldout | - | 2 |
| H32 | heldout | 3 | - |
| H33 | heldout | 2 | 2 |
| H34 | heldout | 1 | 1 |
| H35 | heldout | 1 | 1 |
| H36 | heldout | 1 | 2 |
| H37 | heldout | 1 | 1 |
| H38 | heldout | 1 | 1 |
| H39 | heldout | 1 | 1 |
| H40 | heldout | 1 | 1 |
| H41 | heldout | 1 | 1 |
| H42 | heldout | 1 | 1 |
| H43 | heldout | 8 | 2 |

## Queries without a correct passage in the top 5

**Q05** (general): What does setting IO_MEAS_CTRL_EN in clkmgr turn on?

- expected: `hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.md:265-271`; `hw/top_earlgrey/ip_autogen/clkmgr/doc/theory_of_operation.md:300-300`
- embedding: first correct at none in top 10; returned first `hw/ip_templates/clkmgr/doc/programmers_guide.md:13-13`

**Q15** (general): Which EDN request mode is active after reset before software configures the block?

- expected: `hw/ip/edn/doc/theory_of_operation.md:28-30`; `hw/ip/edn/doc/theory_of_operation.md:137-138`
- bm25: first correct at 6; returned first `hw/ip/edn/doc/theory_of_operation.md:75-77`

**Q21** (general): Does the PLIC forward a pending interrupt to the CPU right after reset if software has not configured it?

- expected: `hw/ip_templates/rv_plic/doc/programmers_guide.md:3-7`
- bm25: first correct at 8; returned first `hw/ip_templates/rv_plic/doc/programmers_guide.md:36-53`

**H01** (heldout): How deep is the UART receive FIFO?

- expected: `hw/ip/uart/doc/theory_of_operation.md:63-63`
- bm25: first correct at none in top 10; returned first `hw/ip/uart/README.md:33-38`
- embedding: first correct at 10; returned first `hw/ip/uart/doc/theory_of_operation.md:48-54`

**H31** (heldout): In which life cycle states can the RISC-V debug module be used?

- expected: `hw/ip/rv_dm/doc/theory_of_operation.md:58-58`; `hw/ip/rv_dm/doc/interfaces.md:69-69`
- bm25: first correct at none in top 10; returned first `hw/ip/lc_ctrl/doc/theory_of_operation.md:499-506`

**H32** (heldout): In the DEV life cycle state, what decides whether the RISC-V debug module is fully ungated?

- expected: `hw/ip/rv_dm/doc/theory_of_operation.md:59-59`; `hw/ip/rv_dm/doc/theory_of_operation.md:63-69`
- embedding: first correct at none in top 10; returned first `hw/ip/lc_ctrl/doc/theory_of_operation.md:499-506`

**H43** (heldout): Which fields of the TL-UL a_user bus carry integrity information?

- expected: `hw/ip/tlul/README.md:102-105`
- bm25: first correct at 8; returned first `hw/ip/tlul/README.md:69-77`
