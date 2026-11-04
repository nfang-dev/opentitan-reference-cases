# Case 003: pinmux pad sleep behavior enable after reset

| | |
|---|---|
| Module | `pinmux` (pin multiplexer) |
| Settings | `MIO_PAD_SLEEP_EN_<k>.EN` and `DIO_PAD_SLEEP_EN_<k>.EN` |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | Documentation and design agree (control case) |
| Machine-readable record | [`case.json`](case.json) |

## Purpose

This is a control case: a written statement that agrees with the design.
When later checks are evaluated on these reference cases, cases like this one show whether a check raises false alarms.

## Question

What sleep behavior does each pad have after reset, before software configures it?

## Written requirement

`hw/ip_templates/pinmux/doc/programmers_guide.md`, section "Sleep Features" (copied unchanged into each top).

| ID | Line | What it says |
|---|---:|---|
| R1 | 66 | First row of the sleep behavior table: sleep enable `0`, sleep mode `-`, behavior "Drive (default)". The table covers both MIO and DIO pads. |
| R2 | 72 | "Note that if the behavior is set to "Drive", the sleep mode will not be activated upon sleep entry." |

So the default sleep enable is 0, and with enable 0 no sleep behavior is applied when the chip enters sleep.

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip_templates/pinmux/data/pinmux.hjson.tpl:813` | `MIO_PAD_SLEEP_EN.EN` resets to 0. |
| D2 | `hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` | All 47 `MIO_PAD_SLEEP_EN` flops in Earl Grey reset to 0. |
| D3 | `hw/top_darjeeling/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` | All 12 `MIO_PAD_SLEEP_EN` flops in Darjeeling reset to 0. |
| D4 | `hw/ip_templates/pinmux/data/pinmux.hjson.tpl:925` | `DIO_PAD_SLEEP_EN.EN` resets to 0. |
| D5 | `hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` | All 16 `DIO_PAD_SLEEP_EN` flops in Earl Grey reset to 0. |
| D6 | `hw/top_darjeeling/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` | All 73 `DIO_PAD_SLEEP_EN` flops in Darjeeling reset to 0. |
| D7 | `hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux.sv:517` | An MIO pad's sleep status is set on sleep entry only if its sleep enable is 1; otherwise the pad keeps its normal output (lines 495 to 501). |
| D8 | `hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux.sv:553` | The same gating for DIO pads. |

## Which evidence is independent

The register flops (D2, D3, D5, D6) and the reset values in `registers.md` are generated from the same `pinmux.hjson`, rendered from the template (D1, D4).
The programmers' guide is written by hand and is the independent requirement.

## Claims

| Claim | Setting | Stated | Design | Label |
|---|---|---|---|---|
| C1 | `MIO_PAD_SLEEP_EN_<k>.EN` after reset | 0 (R1, R2) | 0 (D1, D2, D3) | agrees |
| C2 | `DIO_PAD_SLEEP_EN_<k>.EN` after reset | 0 (R1, R2) | 0 (D4, D5, D6) | agrees |

## Finding

The guide marks Drive (sleep enable 0) as the default sleep behavior.
The design agrees: every MIO and DIO sleep enable resets to 0 in both tops checked, and with enable 0 a pad's sleep status is never set on sleep entry.

## Ambiguities

- `MIO_PAD_SLEEP_MODE` resets to 2, which the table lists as the High-Z behavior for sleep enable 1. A reader could take the mode's reset value for the default behavior; the table's `-` in the first row makes clear that the mode is ignored while the enable is 0.

## Other observations

- Line 61 of the same guide has a malformed link, "via the (registers.md#mio_pad_sleep_en)", with the link text missing. It does not affect this case.

## Out of scope

- Behavior on sleep entry and exit, which depends on the power manager's sleep request. A simulation would be needed to observe it.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/003-pinmux-pad-sleep-enable-reset/case.json
python3 tools/check_case.py cases/003-pinmux-pad-sleep-enable-reset/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 MIO_PAD_SLEEP_EN_<k>.EN after reset: stated 0, design 0 (D1, D2, D3) -> agrees
  C2 DIO_PAD_SLEEP_EN_<k>.EN after reset: stated 0, design 0 (D4, D5, D6) -> agrees

RESULT: 2 agree, 0 disagree, 0 unresolved; all outcomes match the recorded labels
```
