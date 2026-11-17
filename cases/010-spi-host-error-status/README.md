# Case 010: spi_host: the error status bits for programming violations

| | |
|---|---|
| Module | `spi_host` (SPI host controller) |
| Setting | The ERROR_STATUS bits that report violations of the programming model, and how they are cleared |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | The conditions and the clearing agree with the design; the first error's field is CMDBUSY, not CMDERR |
| Machine-readable record | [`case.json`](case.json) |

## Question

The theory of operation lists six error events and the `ERROR_STATUS` bit each one asserts, and says each must be acknowledged by writing 1 to that bit. Do the bits exist, and does the design set and clear them as described?

Each setting is recorded as `1` if the statement holds for the design and `0` if it does not.

## Written requirement

| ID | File and line | What it says |
|---|---|---|
| R1 | `hw/ip/spi_host/doc/theory_of_operation.md:590` | "If `COMMAND` is written when `STATUS.READY` is zero, the IP will assert `ERROR_STATUS.CMDERR`." |
| R2 | `hw/ip/spi_host/doc/theory_of_operation.md:591` | "The IP asserts `ERROR_STATUS.OVERFLOW` if it receives a write to `TXDATA` when the TX FIFO is full." |
| R3 | `hw/ip/spi_host/doc/theory_of_operation.md:592` | "The IP asserts `ERROR_STATUS.UNDERFLOW` if ... software attempts to read `RXDATA` when the RX FIFO is empty." |
| R4 | `hw/ip/spi_host/doc/theory_of_operation.md:593` | An invalid width or direction "will trigger a `ERROR_STATUS.CMDINVAL` error event." |
| R5 | `hw/ip/spi_host/doc/theory_of_operation.md:594` | An invalid CSID "will trigger a `ERROR_STATUS.CSIDINVAL` event." |
| R6 | `hw/ip/spi_host/doc/theory_of_operation.md:595` | "`ERROR_STATUS.ACCESSINVAL` is asserted if the IP receives a write event to the `TXDATA` window that does not correspond to any known processor data type" |
| R7 | `hw/ip/spi_host/doc/theory_of_operation.md:599` | "... the error must be acknowledged by clearing (write 1 to clear) the corresponding bit in `ERROR_STATUS`." |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/spi_host/rtl/spi_host_command_queue.sv:38` | The command queue reports an error when a command is written while it is busy. |
| D2 | `hw/ip/spi_host/rtl/spi_host.sv:291` | `STATUS.READY` is the inverse of the same busy signal. |
| D3 | `hw/ip/spi_host/rtl/spi_host.sv:553` | That error sets `ERROR_STATUS.CMDBUSY`. |
| D4 | `hw/ip/spi_host/data/spi_host.hjson:629` | `ERROR_STATUS.CMDBUSY`: "Indicates a write to `COMMAND` when `STATUS.READY` = 0." |
| D5 | `hw/ip/spi_host/data/spi_host.hjson` | No field named `CMDERR`; `ERROR_STATUS`'s fields are `ACCESSINVAL`, `CSIDINVAL`, `CMDINVAL`, `UNDERFLOW`, `OVERFLOW` and `CMDBUSY`. |
| D6 | `hw/ip/spi_host/data/spi_host.hjson:621` | `ERROR_STATUS.OVERFLOW` (bit 1). |
| D7 | `hw/ip/spi_host/data/spi_host.hjson:615` | `ERROR_STATUS.UNDERFLOW` (bit 2). |
| D8 | `hw/ip/spi_host/data/spi_host.hjson:608` | `ERROR_STATUS.CMDINVAL` (bit 3). |
| D9 | `hw/ip/spi_host/data/spi_host.hjson:603` | `ERROR_STATUS.CSIDINVAL` (bit 4). |
| D10 | `hw/ip/spi_host/data/spi_host.hjson:595` | `ERROR_STATUS.ACCESSINVAL` (bit 5). |
| D11 | `hw/ip/spi_host/data/spi_host.hjson:591` | `ERROR_STATUS` is write-1-to-clear. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | Writing `COMMAND` while `STATUS.READY` is 0 sets an `ERROR_STATUS` bit (R1) | 1 | 1 (D1, D2, D3, D4) | agrees |
| C2 | `ERROR_STATUS` has a field named `CMDERR` (R1) | 1 | 0 (D5) | disagrees |
| C3 | `ERROR_STATUS` has fields named `OVERFLOW`, `UNDERFLOW`, `CMDINVAL`, `CSIDINVAL` and `ACCESSINVAL` (R2, R3, R4, R5, R6) | 1 | 1 (D6, D7, D8, D9, D10) | agrees |
| C4 | An `ERROR_STATUS` bit is cleared by writing 1 to it (R7) | 1 | 1 (D11) | agrees |

## Which evidence is independent

D4 to D11 are in `spi_host.hjson`, from which `reggen` generates the register RTL and `registers.md`; those generated files are not counted as more evidence.
D1 to D3 are in the hand-written RTL.
R1 to R7 are hand-written.

## Finding

The six error events, the condition for the first one and the write-1-to-clear acknowledgement agree with the design.
One name is wrong: writing `COMMAND` while `STATUS.READY` is 0 sets `ERROR_STATUS.CMDBUSY`. There is no `CMDERR` field.

This case was found by the name checks in [`claims/`](../../claims/README.md). It is mostly a control case: five of the six error bits are named and described correctly.

## Ambiguities

- None found: R1 describes the condition precisely, and only the name differs.

## Missing information

This case reads the register description and the RTL; it does not simulate an error. The conditions in R2 to R6 are compared by name only.

## Out of scope

- That the IP halts until the error bit is cleared (line 598).
- `ERROR_ENABLE`, which selects which errors raise the error interrupt.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/010-spi-host-error-status/case.json
python3 tools/check_case.py cases/010-spi-host-error-status/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 writing COMMAND while STATUS.READY is 0 sets an ERROR_STATUS bit (1 yes, 0 no): stated 1, design 1 (D1, D2, D3, D4) -> agrees
  C2 ERROR_STATUS has a field named CMDERR (1 yes, 0 no): stated 1, design 0 (D5) -> disagrees
  C3 ERROR_STATUS has fields named OVERFLOW, UNDERFLOW, CMDINVAL, CSIDINVAL and ACCESSINVAL (1 yes, 0 no): stated 1, design 1 (D6, D7, D8, D9, D10) -> agrees
  C4 an ERROR_STATUS bit is cleared by writing 1 to it (1 yes, 0 no): stated 1, design 1 (D11) -> agrees

RESULT: 3 agree, 1 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R1 is still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
