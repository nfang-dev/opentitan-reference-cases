# Case 009: alert_handler: register and field names in the class configuration steps

| | |
|---|---|
| Module | `alert_handler` (alert handler; template in hw/ip_templates) |
| Setting | The registers and fields the programmer's guide tells software to set when configuring an alert class |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | Every value and behavior the steps describe agrees with the design; six of the names are wrong |
| Machine-readable record | [`case.json`](case.json) |

## Question

The programmer's guide lists the steps to configure alert class A at startup and to enable the ping timer. Do the registers and fields it names exist, and do the defaults and behaviors it describes match the design?

C3 and C5 record a value after reset; the other settings are recorded as `1` if the statement holds for the design and `0` if it does not.

## Written requirement

| ID | File and line | What it says |
|---|---|---|
| R1 | `hw/ip_templates/alert_handler/doc/programmers_guide.md:44` | "Set `CLASSA_ACCUM_THRESH` accordingly." |
| R2 | `hw/ip_templates/alert_handler/doc/programmers_guide.md:50` | "Determine length of each escalation phase by setting `CLASSA_PHASE0_CYC` accordingly" |
| R3 | `hw/ip_templates/alert_handler/doc/programmers_guide.md:53` | "... set the `CLASSA_CTRL_SHADOWED.E0_EN` bit accordingly (default is enabled)." |
| R4 | `hw/ip_templates/alert_handler/doc/programmers_guide.md:55` | "... program it via the `CLASSA_CTRL_SHADOWED.E0_MAP` values if it needs to be changed from the default mapping (0->0, 1->1, 2->2, 3->3)." |
| R5 | `hw/ip_templates/alert_handler/doc/programmers_guide.md:57` | "Optionally lock the class configuration by writing 0 to `CLASSA_CTRL_SHADOWED.REGWEN`." |
| R6 | `hw/ip_templates/alert_handler/doc/programmers_guide.md:59` | "... enable the ping timer mechanism by writing 1 to `PING_TIMER_EN`." |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson` | No register named `CLASSA_ACCUM_THRESH`; it is `CLASSA_ACCUM_THRESH_SHADOWED` (line 929). |
| D2 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson` | No register named `CLASSA_PHASE0_CYC`; it is `CLASSA_PHASE0_CYC_SHADOWED` (line 986). |
| D3 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson`, 4 instances | `EN_E0` ("Enable escalation signal 0") resets to 1 in each class. |
| D4 | `hw/ip_templates/alert_handler/rtl/alert_handler_reg_wrap.sv.tpl:242` | The hand-written register wrapper reads the field as `en_e0`. |
| D5 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson` | No field named `E0_EN`. |
| D6 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson`, 4 instances | `MAP_E0` resets to phase 0 in each class (`MAP_E1` to `MAP_E3` reset to 1, 2 and 3). |
| D7 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson` | No field named `E0_MAP`. |
| D8 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson` | No field named `REGWEN` in any register; `CLASSA_CTRL_SHADOWED`'s fields are `EN`, `LOCK`, `EN_E0` to `EN_E3` and `MAP_E0` to `MAP_E3`. |
| D9 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson:798` | `CLASSA_REGWEN` ("Lock bit for Class A configuration") is cleared by writing 0. |
| D10 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson:815` | `CLASSA_CTRL_SHADOWED` is locked by `CLASSA_REGWEN`, as are the class's other configuration registers. |
| D11 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson` | No register named `PING_TIMER_EN`; it is `PING_TIMER_EN_SHADOWED` (line 577). |
| D12 | `hw/top_earlgrey/ip_autogen/alert_handler/data/alert_handler.hjson:590` | `PING_TIMER_EN_SHADOWED`: "Setting this to 1 enables the ping timer mechanism." |
| D13 | `hw/ip_templates/alert_handler/rtl/alert_handler_reg_wrap.sv.tpl:201` | The register drives the ping enable. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | A register named `CLASSA_ACCUM_THRESH` exists (R1) | 1 | 0 (D1) | disagrees |
| C2 | A register named `CLASSA_PHASE0_CYC` exists (R2) | 1 | 0 (D2) | disagrees |
| C3 | Escalation signal 0 is enabled after reset (R3) | 1 | 1 (D3, D4) | agrees |
| C4 | The control register has a field named `E0_EN` (R3) | 1 | 0 (D5) | disagrees |
| C5 | Phase in which signal 0 is asserted, after reset (R4) | 0 | 0 (D6) | agrees |
| C6 | The control register has a field named `E0_MAP` (R4) | 1 | 0 (D7) | disagrees |
| C7 | The control register has a field named `REGWEN` (R5) | 1 | 0 (D8) | disagrees |
| C8 | Writing 0 to a lock bit locks the class configuration (R5) | 1 | 1 (D9, D10) | agrees |
| C9 | A register named `PING_TIMER_EN` exists (R6) | 1 | 0 (D11) | disagrees |
| C10 | Writing 1 to the ping timer enable register enables the ping timer (R6) | 1 | 1 (D12, D13) | agrees |

## Which evidence is independent

D1 to D3 and D5 to D12 are in Earl Grey's `alert_handler.hjson`, generated from the template `alert_handler.hjson.tpl`; the register RTL and `registers.md` are generated from the same input and are not counted as more evidence.
D4 and D13 are in the hand-written register wrapper template.
R1 to R6 are in the hand-written template document; Earl Grey's generated copy has the same lines.

## Finding

Every setting the steps describe agrees with the design: escalation signals are enabled after reset, the default mapping starts with phase 0 for signal 0, writing 0 to the class lock bit locks the configuration, and writing 1 enables the ping timer.
But six names are wrong. Three registers have been renamed with a `_SHADOWED` suffix (`CLASSA_ACCUM_THRESH`, `CLASSA_PHASE0_CYC`, `PING_TIMER_EN`); the fields are `EN_E0` and `MAP_E0`, not `E0_EN` and `E0_MAP`; and the class lock is the register `CLASSA_REGWEN`, not a field of `CLASSA_CTRL_SHADOWED`.
The links in R1, R2 and R6 point to anchors that `registers.md` does not have.

This case was found by the name checks in [`claims/`](../../claims/README.md).

## Ambiguities

- The names are close enough that a reader is likely to find the right register or field; R5's "`CLASSA_CTRL_SHADOWED.REGWEN`" is the furthest from the design, since the lock is a separate register.

## Missing information

This case reads the register description and the register wrapper; it does not simulate the alert handler.

## Out of scope

- `CLASSA_CLR` in the interrupt handling steps (line 85), which has the same renaming (the register is `CLASSA_CLR_SHADOWED`).
- Shadowed registers must be written twice; the documents say so elsewhere.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/009-alert-handler-class-config-names/case.json
python3 tools/check_case.py cases/009-alert-handler-class-config-names/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 a register named CLASSA_ACCUM_THRESH exists (1 yes, 0 no): stated 1, design 0 (D1) -> disagrees
  C2 a register named CLASSA_PHASE0_CYC exists (1 yes, 0 no): stated 1, design 0 (D2) -> disagrees
  C3 escalation signal 0 of a class is enabled after reset (1 yes, 0 no): stated 1, design 1 (D3, D4) -> agrees
  C4 the control register has a field named E0_EN (1 yes, 0 no): stated 1, design 0 (D5) -> disagrees
  C5 escalation phase in which signal 0 is asserted, after reset: stated 0, design 0 (D6) -> agrees
  C6 the control register has a field named E0_MAP (1 yes, 0 no): stated 1, design 0 (D7) -> disagrees
  C7 the control register has a field named REGWEN (1 yes, 0 no): stated 1, design 0 (D8) -> disagrees
  C8 writing 0 to a lock bit locks the class configuration (1 yes, 0 no): stated 1, design 1 (D9, D10) -> agrees
  C9 a register named PING_TIMER_EN exists (1 yes, 0 no): stated 1, design 0 (D11) -> disagrees
  C10 writing 1 to the ping timer enable register enables the ping timer (1 yes, 0 no): stated 1, design 1 (D12, D13) -> agrees

RESULT: 4 agree, 6 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R1 to R6 are still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
