# Case 007: kmac: where software selects the mode, and the squeeze status bit

| | |
|---|---|
| Module | `kmac` (KMAC and SHA-3 accelerator) |
| Setting | Which register holds the hashing mode software sets for KMAC, and the status bit software polls once absorbing is complete |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | One instruction points to a register that does not hold the mode; the status bit is described correctly under a wrong name |
| Machine-readable record | [`case.json`](case.json) |

## Question

The theory of operation and the programmer's guide give the same instruction for KMAC, "configure ... `mode` to cSHAKE", but name different registers for it. Which register holds the mode? And does the status bit the programmer's guide tells software to poll exist?

Each setting is recorded as `1` if the register has the field (or bit) described and `0` if it does not.

## Written requirement

| ID | File and line | What it says |
|---|---|---|
| R1 | `hw/ip/kmac/doc/theory_of_operation.md:172` | "If KMAC is enabled, the software should configure `CMD.mode` to cSHAKE and the first six bytes of `PREFIX` to `0x01204B4D4143`." |
| R2 | `hw/ip/kmac/doc/programmers_guide.md:14` | "If KMAC is enabled, the software should configure `CFG_SHADOWED.mode` to cSHAKE ..." |
| R3 | `hw/ip/kmac/doc/theory_of_operation.md:124` | The padding logic "appends proper ending bits with respect to the `CFG_SHADOWED.mode` value." |
| R4 | `hw/ip/kmac/doc/programmers_guide.md:36` | "Or the software can poll the `STATUS.squeeze` bit until it becomes 1." |
| R5 | `hw/ip/kmac/doc/programmers_guide.md:41` | "The software should check `STATUS.squeeze` register field for the readiness of `STATE` value." |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/kmac/data/kmac.hjson`, lines 622 to 771 | The `CMD` register has no field named `mode`; its fields are `cmd`, `entropy_req`, `hash_cnt_clr` and `err_processed`. |
| D2 | `hw/ip/kmac/data/kmac.hjson:445` | `CFG_SHADOWED.mode` selects SHA3, SHAKE or cSHAKE. |
| D3 | `hw/ip/kmac/rtl/kmac.sv:678` | The hand-written top level takes the mode from `reg2hw.cfg_shadowed.mode.q`. |
| D4 | `hw/ip/kmac/data/kmac.hjson`, lines 772 to 875 | The `STATUS` register has no field named `squeeze`. |
| D5 | `hw/ip/kmac/data/kmac.hjson:788` | `STATUS.sha3_squeeze`: "If 1, SHA3 completes sponge absorbing stage. In this stage, SW can manually run the hashing engine." |
| D6 | `hw/ip/kmac/rtl/kmac.sv:502` | `sha3_squeeze` is 1 while the SHA-3 state machine is in its squeeze state. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | `CMD` has a field named `mode` (R1) | 1 | 0 (D1) | disagrees |
| C2 | `CFG_SHADOWED` has a `mode` field that sets the hashing mode (R2, R3) | 1 | 1 (D2, D3) | agrees |
| C3 | `STATUS` has a field named `squeeze` (R4, R5) | 1 | 0 (D4) | disagrees |
| C4 | `STATUS` has a bit that is 1 once absorbing is complete (R4) | 1 | 1 (D5, D6) | agrees |

## Which evidence is independent

D1, D2, D4 and D5 are in `kmac.hjson`, from which `reggen` generates the register RTL and `registers.md`; those generated files are not counted as more evidence.
D3 and D6 are in the hand-written `kmac.sv`.
R1 to R5 are hand-written.

## Finding

The programmer's guide (R2) and another passage of the theory of operation (R3) put the mode in `CFG_SHADOWED.mode`, which is where the design reads it.
R1, in the theory of operation's section on KMAC padding, gives the same instruction with `CMD.mode`. `CMD` has no mode field, only the command and error-handling fields, so a reader following R1 would look for the mode in the wrong register.
Separately, R4 and R5 call the squeeze status bit `STATUS.squeeze`. The bit exists and behaves as described, but its name is `sha3_squeeze`.

This case was found by the name checks in [`claims/`](../../claims/README.md).

## Ambiguities

- `STATUS.squeeze` is close enough to `STATUS.sha3_squeeze` that a reader is likely to find the right bit. `CMD.mode` points to a different register.

## Missing information

This case reads the register description and the top-level assignments; it does not simulate an operation.

## Out of scope

- The `PREFIX` value in R1, which is not compared here.
- `CFG_SHADOWED` is a shadowed register and must be written twice; the documents say so elsewhere.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/007-kmac-mode-and-squeeze/case.json
python3 tools/check_case.py cases/007-kmac-mode-and-squeeze/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 CMD has a field named mode (1 yes, 0 no): stated 1, design 0 (D1) -> disagrees
  C2 CFG_SHADOWED has a field named mode that sets the hashing mode (1 yes, 0 no): stated 1, design 1 (D2, D3) -> agrees
  C3 STATUS has a field named squeeze (1 yes, 0 no): stated 1, design 0 (D4) -> disagrees
  C4 STATUS has a bit that is 1 once absorbing is complete (1 yes, 0 no): stated 1, design 1 (D5, D6) -> agrees

RESULT: 2 agree, 2 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R1, R4 and R5 are still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
