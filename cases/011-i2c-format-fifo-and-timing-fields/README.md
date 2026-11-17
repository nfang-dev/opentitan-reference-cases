# Case 011: i2c: format FIFO fields, the stop setup time and the format FIFO threshold

| | |
|---|---|
| Module | `i2c` (I2C controller and target) |
| Setting | The format FIFO fields, the register for the stop setup time, the format FIFO threshold, and the format FIFO reset |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | Four statements agree; the stop setup time field and the format FIFO threshold field are named wrongly |
| Machine-readable record | [`case.json`](case.json) |

## Question

The theory of operation describes the fields of a format FIFO entry, and the programmer's guide tells software which timing fields to set and which FIFO fields to use while waiting for a transfer. Do these fields exist and do what the documents say?

C2 records a width in bits; the other settings are recorded as `1` if the statement holds for the design and `0` if it does not.

## Written requirement

| ID | File and line | What it says |
|---|---|---|
| R1 | `hw/ip/i2c/doc/theory_of_operation.md:55` | A format FIFO entry consists "of one single format byte (entered into the format FIFO through `FDATA.FBYTE`), and five 1-bit flags" (`FDATA.READB`, `RCONT`, `START`, `STOP`, `NAKOK`). |
| R2 | `hw/ip/i2c/doc/programmers_guide.md:56` | Input the timing parameters "into their corresponding registers (... `TIMING4.T_BUF`, `TIMING4.T_STO`)". |
| R3 | `hw/ip/i2c/doc/programmers_guide.md:101` | Example timing table row: "`TIMING4.T_STO` | 260 | 87 | 161 | Spec. Minimum". |
| R4 | `hw/ip/i2c/doc/programmers_guide.md:139` | Wait until "`INTR_STATE.FMT_THRESHOLD` bit is 1 ( as long as `FIFO_CTRL.FMTILVL` is set to 1)." |
| R5 | `hw/ip/i2c/doc/programmers_guide.md:141` | "... set `FIFO_CTRL.FMTRST` to reset the FMT FIFO". |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/i2c/data/i2c.hjson:439` | `FDATA.START` is bit 8. |
| D2 | `hw/ip/i2c/data/i2c.hjson:443` | `FDATA.STOP` is bit 9. |
| D3 | `hw/ip/i2c/data/i2c.hjson:447` | `FDATA.READB` is bit 10. |
| D4 | `hw/ip/i2c/data/i2c.hjson:460` | `FDATA.RCONT` is bit 11. |
| D5 | `hw/ip/i2c/data/i2c.hjson:464` | `FDATA.NAKOK` is bit 12. |
| D6 | `hw/ip/i2c/data/i2c.hjson:429` | `FDATA.FBYTE` is bits 7:0. |
| D7 | `hw/ip/i2c/data/i2c.hjson` | No field named `T_STO`; `TIMING4`'s fields are `TSU_STO` and `T_BUF`. |
| D8 | `hw/ip/i2c/data/i2c.hjson:741` | `TIMING4.TSU_STO`: "Actual setup time for stop signals." |
| D9 | `hw/ip/i2c/rtl/i2c_core.sv:296` | The core takes the stop setup time from `TIMING4.TSU_STO`. |
| D10 | `hw/ip/i2c/data/i2c.hjson` | No field named `FMTILVL`; `FIFO_CTRL`'s fields are `RXRST`, `FMTRST`, `ACQRST` and `TXRST`. The format FIFO threshold is `HOST_FIFO_CONFIG.FMT_THRESH` (`i2c_core.sv` line 314). |
| D11 | `hw/ip/i2c/data/i2c.hjson:489` | `FIFO_CTRL.FMTRST`: "Write 1 to the register resets FMT_FIFO." |
| D12 | `hw/ip/i2c/rtl/i2c_core.sv:312` | A write of 1 to `FMTRST` resets the format FIFO. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | `FDATA` has 1-bit fields `READB`, `RCONT`, `START`, `STOP` and `NAKOK` (R1) | 1 | 1 (D1, D2, D3, D4, D5) | agrees |
| C2 | Width of `FDATA.FBYTE` in bits (R1) | 8 | 8 (D6) | agrees |
| C3 | `TIMING4` has a field named `T_STO` (R2, R3) | 1 | 0 (D7) | disagrees |
| C4 | The stop setup time is set in `TIMING4` (R2) | 1 | 1 (D8, D9) | agrees |
| C5 | `FIFO_CTRL` has a field named `FMTILVL` (R4) | 1 | 0 (D10) | disagrees |
| C6 | Writing 1 to `FIFO_CTRL.FMTRST` resets the format FIFO (R5) | 1 | 1 (D11, D12) | agrees |

## Which evidence is independent

D1 to D8, D10 and D11 are in `i2c.hjson`, from which `reggen` generates the register RTL and `registers.md`; those generated files are not counted as more evidence.
D9 and D12 are in the hand-written `i2c_core.sv`.
R1 to R5 are hand-written.

## Finding

The format FIFO entry, the timing register and the FIFO reset agree with the design.
Two names do not. The stop setup time field is `TIMING4.TSU_STO`, not `T_STO` (R2, R3). And `FIFO_CTRL` has no `FMTILVL` field: the format FIFO threshold is now `HOST_FIFO_CONFIG.FMT_THRESH` (R4), so software following R4 would look for the threshold in the wrong register.

This case was found by the name checks in [`claims/`](../../claims/README.md).

## Ambiguities

- `T_STO` is the name of the timing parameter (`T_STO_MIN`, line 52); R2 and R3 use it as a field name.

## Missing information

This case reads the register description and the core's assignments; it does not simulate a transfer. R4's "set to 1" is not compared with `HOST_FIFO_CONFIG.FMT_THRESH`'s encoding.

## Out of scope

- The other timing fields in R2 and the example values in R3.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/011-i2c-format-fifo-and-timing-fields/case.json
python3 tools/check_case.py cases/011-i2c-format-fifo-and-timing-fields/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 FDATA has 1-bit fields READB, RCONT, START, STOP and NAKOK (1 yes, 0 no): stated 1, design 1 (D1, D2, D3, D4, D5) -> agrees
  C2 width of FDATA.FBYTE in bits: stated 8, design 8 (D6) -> agrees
  C3 TIMING4 has a field named T_STO (1 yes, 0 no): stated 1, design 0 (D7) -> disagrees
  C4 the stop setup time is set in TIMING4 (1 yes, 0 no): stated 1, design 1 (D8, D9) -> agrees
  C5 FIFO_CTRL has a field named FMTILVL (1 yes, 0 no): stated 1, design 0 (D10) -> disagrees
  C6 writing 1 to FIFO_CTRL.FMTRST resets the format FIFO (1 yes, 0 no): stated 1, design 1 (D11, D12) -> agrees

RESULT: 4 agree, 2 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R2, R3 and R4 are still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
