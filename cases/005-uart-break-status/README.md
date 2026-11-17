# Case 005: uart: reading the current line-break status

| | |
|---|---|
| Module | `uart` (serial port) |
| Setting | How software learns that the RX line is in a break (held low for several character times) |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | The interrupt is described correctly; the status bit the document tells software to read does not exist |
| Machine-readable record | [`case.json`](case.json) |

## Question

The theory of operation describes break detection in four steps: a break raises the `rx_break_err` interrupt, only one interrupt is raised per break, the current break status can be read from `STATUS.BREAK`, and the two can be combined to tell whether a break is still going on. Which of these does the design provide?

Each setting is recorded as `1` if the statement holds for the design and `0` if it does not.

## Written requirement

`hw/ip/uart/doc/theory_of_operation.md`

| ID | Line | What it says | Value it implies |
|---|---:|---|---:|
| R1 | 153 | "The `rx_break_err` interrupt is triggered if a break condition has been detected." | interrupt: 1 |
| R2 | 158 | "only one interrupt is generated per break -- the line must return high for at least half a bit-time before an additional break interrupt is generated." | 1 |
| R3 | 159 | "The current break status can be read from the `STATUS.BREAK` bit." | status bit: 1 |
| R4 | 160 | "If STATUS.BREAK is set but `INTR_STATE.BREAK` is clear then the line break has already caused an interrupt that has been cleared but the line break is still going on." (Line 161 describes the opposite combination.) | status bit: 1; INTR_STATE.BREAK: 1 |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/uart/data/uart.hjson` | No register field or interrupt is named `BREAK` (the break detection levels are named `break2` to `break16`). |
| D2 | `hw/ip/uart/rtl/uart_core.sv` | No `STATUS` field is driven from the break detector. |
| D3 | `hw/ip/uart/data/uart.hjson:297` | `STATUS` has six fields: TXFULL, RXFULL, TXEMPTY, TXIDLE, RXIDLE and RXEMPTY. The core drives exactly these six (`uart_core.sv` lines 148 to 153). |
| D4 | `hw/ip/uart/data/uart.hjson:73` | The interrupt, and so its `INTR_STATE` field, is named `rx_break_err`. |
| D5 | `hw/ip/uart/rtl/uart_core.sv:482` | The break event drives the `rx_break_err` interrupt. |
| D6 | `hw/ip/uart/rtl/uart_core.sv:400` | A break event is raised only in state `BRK_CHK`; the event moves the detector to `BRK_WAIT` (line 130). |
| D7 | `hw/ip/uart/rtl/uart_core.sv:134` | The detector returns to `BRK_CHK` only when the RX input is high. Its state, `break_st_q` (line 96), is internal and reaches no register. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | A detected break raises an interrupt (R1) | 1 | 1 (D4, D5) | agrees |
| C2 | No further break interrupt until the RX line has been high (R2) | 1 | 1 (D6, D7) | agrees |
| C3 | Software can read the current break status from a `STATUS` bit (R3, R4) | 1 | 0 (D1, D2, D3) | disagrees |
| C4 | `INTR_STATE` has a field named `BREAK` (R4) | 1 | 0 (D1) | disagrees |

## Which evidence is independent

D1, D3 and D4 are in `uart.hjson`, from which `reggen` generates the register RTL and `registers.md`; those generated files are not counted as more evidence.
D2 and D5 to D7 are in the hand-written `uart_core.sv`.
R1 to R4 are hand-written.

## Finding

The interrupt and its one-per-break behavior agree with the design.
R3 tells software to read the current break status from `STATUS.BREAK`, and R4 and line 161 explain how to combine it with `INTR_STATE.BREAK`.
The design has neither. `STATUS` has six FIFO and idle fields and none for break; the core keeps the break state in an internal register that reaches no register; and the interrupt field is `rx_break_err`.
Software that follows R3 reads a bit that does not exist. The only break indication the design gives software is the `rx_break_err` interrupt, so software cannot tell from the registers whether a break is still going on.

This case was found by the name checks in [`claims/`](../../claims/README.md), which look up every `REGISTER.FIELD` written in the documentation in the register description.

## Ambiguities

- R4 and line 161 could be read as using `INTR_STATE.BREAK` as a short name for `INTR_STATE.rx_break_err`. Even so, they depend on `STATUS.BREAK`, which has no counterpart.

## Missing information

This case reads the register description and the core's break detector; it does not simulate a break. The "half a bit-time" in R2 depends on how the receiver samples the RX input and is not checked.

## Out of scope

- How a top-level design connects the RX pin and its pull resistors, which the same section also discusses.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/005-uart-break-status/case.json
python3 tools/check_case.py cases/005-uart-break-status/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 a detected break raises an interrupt (1 yes, 0 no): stated 1, design 1 (D4, D5) -> agrees
  C2 after a break interrupt, no further one until the RX line has been high (1 yes, 0 no): stated 1, design 1 (D6, D7) -> agrees
  C3 software can read the current break status from a STATUS bit (1 yes, 0 no): stated 1, design 0 (D1, D2, D3) -> disagrees
  C4 INTR_STATE has a field named BREAK (1 yes, 0 no): stated 1, design 0 (D1) -> disagrees

RESULT: 2 agree, 2 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R3 and R4 are still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
