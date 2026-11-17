# Case 012: aon_timer: wake-up timer and watchdog register facts (control case)

| | |
|---|---|
| Module | `aon_timer` (always-on wake-up and watchdog timer) |
| Setting | Facts about the wake-up timer and watchdog registers that software relies on: a field width, how requests and interrupts are cleared, which register holds which half of the threshold, and how the watchdog is locked |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | Five statements agree; one link text names the wrong register |
| Machine-readable record | [`case.json`](case.json) |

## Question

The aon_timer documents state a field width, how software acknowledges a wake-up and clears an interrupt, which registers hold the two halves of the 64-bit threshold, and how software locks the watchdog configuration. Does the design match?

C1 records a width in bits; the other settings are recorded as `1` if the statement holds for the design and `0` if it does not.

## Written requirement

| ID | File and line | What it says |
|---|---|---|
| R1 | `hw/ip/aon_timer/README.md:32` | "The number of cycles per tick is one more than the 12-bit `WKUP_CTRL.prescaler` field." |
| R2 | `hw/ip/aon_timer/README.md:41` | "The wakeup signal (`wkup_req_o`) stays high until software explicitly acknowledges it by software writing 0 to `WKUP_CAUSE`." |
| R3 | `hw/ip/aon_timer/README.md:43` | "To clear the level interrupt (`intr_wkup_timer_expired_o`), write 1 to the field `INTR_STATE.wkup_timer_expired`." |
| R4 | `hw/ip/aon_timer/doc/theory_of_operation.md:31` | "Bits[63:32] in registers `WKUP_COUNT_HI` and `WKUP_THOLD_HI`." |
| R5 | `hw/ip/aon_timer/doc/theory_of_operation.md:32` | "Bits[31:0] in registers `WKUP_COUNT_LO` and `WKUP_THOLD_HI`." (the link goes to `WKUP_THOLD_LO`) |
| R6 | `hw/ip/aon_timer/doc/programmers_guide.md:9` | "If desired, lock the watchdog configuration by writing 0 to the `regwen` bit in `WDOG_REGWEN`." |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/aon_timer/data/aon_timer.hjson:193` | `WKUP_CTRL.prescaler` is bits 12:1. |
| D2 | `hw/ip/aon_timer/data/aon_timer.hjson:357` | `WKUP_CAUSE` is cleared by writing 0. |
| D3 | `hw/ip/aon_timer/rtl/aon_timer.sv:189` | The wake-up request output is `WKUP_CAUSE` itself, so clearing it drops the request. |
| D4 | `hw/ip/aon_timer/data/aon_timer.hjson:323` | `INTR_STATE` is write-1-to-clear. |
| D5 | `hw/ip/aon_timer/data/aon_timer.hjson:201` | `WKUP_THOLD_HI`: "Wakeup Timer Threshold Register (bits 63 - 32)". |
| D6 | `hw/ip/aon_timer/rtl/aon_timer_core.sv:57` | The core forms the 64-bit threshold with `WKUP_THOLD_HI` as the upper half. |
| D7 | `hw/ip/aon_timer/data/aon_timer.hjson:213` | `WKUP_THOLD_LO`: "Wakeup Timer Threshold Register (bits 31 - 0)". |
| D8 | `hw/ip/aon_timer/rtl/aon_timer_core.sv:57` | The same line as D6: `WKUP_THOLD_LO` is the lower half. |
| D9 | `hw/ip/aon_timer/data/aon_timer.hjson:254` | `WDOG_REGWEN` is cleared by writing 0. |
| D10 | `hw/ip/aon_timer/data/aon_timer.hjson:269` | `WDOG_CTRL` is locked by `WDOG_REGWEN`, as are `WDOG_BARK_THOLD` and `WDOG_BITE_THOLD`. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | Width of `WKUP_CTRL.prescaler` in bits (R1) | 12 | 12 (D1) | agrees |
| C2 | Writing 0 to `WKUP_CAUSE` clears the wake-up request (R2) | 1 | 1 (D2, D3) | agrees |
| C3 | Writing 1 to an `INTR_STATE` field clears the interrupt (R3) | 1 | 1 (D4) | agrees |
| C4 | `WKUP_THOLD_HI` holds bits 63:32 of the threshold (R4) | 1 | 1 (D5, D6) | agrees |
| C5 | `WKUP_THOLD_HI` holds bits 31:0 of the threshold (R5) | 1 | 0 (D7, D8) | disagrees |
| C6 | Writing 0 to `WDOG_REGWEN` locks the watchdog configuration (R6) | 1 | 1 (D9, D10) | agrees |

## Which evidence is independent

D1, D2, D4, D5, D7, D9 and D10 are in `aon_timer.hjson`, from which `reggen` generates the register RTL and `registers.md`; those generated files are not counted as more evidence.
D3, D6 and D8 are in the hand-written RTL (D6 and D8 are the same line, read for two settings).
R1 to R6 are hand-written.

## Finding

Five of the six statements agree with the design. This is mostly a control case: these documents state register facts correctly.
The one exception is R5: its link text names `WKUP_THOLD_HI` for bits 31:0, which `WKUP_THOLD_LO` holds. The link itself goes to `WKUP_THOLD_LO`.

The register tests in [`csr/`](../../csr/README.md) also observe C6 in simulation: once `WDOG_REGWEN` is cleared, `WDOG_CTRL`, `WDOG_BARK_THOLD` and `WDOG_BITE_THOLD` ignore writes. R1 to R3 were also found by the AI model in [`claims/`](../../claims/README.md), and R5 by the name checks there.

## Ambiguities

- R5's link goes to the right register, so a reader who follows the link finds `WKUP_THOLD_LO`; a reader who reads only the text does not.

## Missing information

This case reads the register description and the RTL. The register tests in `csr/` simulate the lock (C6) but are not part of this case's evidence.

## Out of scope

- What the prescaler and thresholds do over time (the timer's counting).

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/012-aon-timer-register-facts/case.json
python3 tools/check_case.py cases/012-aon-timer-register-facts/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 width of WKUP_CTRL.prescaler in bits: stated 12, design 12 (D1) -> agrees
  C2 writing 0 to WKUP_CAUSE clears the wake-up request (1 yes, 0 no): stated 1, design 1 (D2, D3) -> agrees
  C3 writing 1 to an INTR_STATE field clears the interrupt (1 yes, 0 no): stated 1, design 1 (D4) -> agrees
  C4 WKUP_THOLD_HI holds bits 63:32 of the threshold (1 yes, 0 no): stated 1, design 1 (D5, D6) -> agrees
  C5 WKUP_THOLD_HI holds bits 31:0 of the threshold (1 yes, 0 no): stated 1, design 0 (D7, D8) -> disagrees
  C6 writing 0 to WDOG_REGWEN locks the watchdog configuration (1 yes, 0 no): stated 1, design 1 (D9, D10) -> agrees

RESULT: 5 agree, 1 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R5 is still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
