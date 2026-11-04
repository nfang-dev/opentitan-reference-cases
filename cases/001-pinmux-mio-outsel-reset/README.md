# Case 001: pinmux MIO output select value after reset

| | |
|---|---|
| Module | `pinmux` (pin multiplexer) |
| Setting | `MIO_OUTSEL_<k>.OUT`, one register per muxed I/O pad |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | The documentation contradicts itself; one statement disagrees with the design |
| Machine-readable record | [`case.json`](case.json) |

## Question

After reset, before software configures the pin multiplexer, what does each muxed I/O pad (MIO) output?
The programmers' guide answers this in three places. Does the design match all of them?

## Written requirement

`hw/ip_templates/pinmux/doc/programmers_guide.md`, section "Pinmux Configuration".
The same file is copied unchanged into each top (`hw/top_<top>/ip_autogen/pinmux/doc/`).

| ID | Line | What it says | Value it implies |
|---|---:|---|---:|
| R1 | 34 | "Upon POR, the `pinmux` state is such that all MIO outputs are high-Z" | 2 (high-Z) |
| R2 | 48 | In the `mio_outsel` value table, the row for `0` reads "Constant zero (default)" | 0 (drive low) |
| R3 | 53 | "The global default at reset is `2`" | 2 (high-Z) |

The table (lines 46 to 51) defines the values: `0` constant zero, `1` constant one, `2` high-Z, `3 + k` peripheral output `k`.

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip_templates/pinmux/data/pinmux.hjson.tpl:542` | The `OUT` field of the `MIO_OUTSEL` multireg (line 526) has `resval: 2`. Every top's register definition is rendered from this template. |
| D2 | `hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` | All 47 `MIO_OUTSEL` register flops have `.RESVAL (7'h2)`. |
| D3 | `hw/top_darjeeling/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` | All 12 `MIO_OUTSEL` register flops have `.RESVAL (3'h2)`. |
| D4 | `hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux.sv:491` and `:501` | The output-enable mux is `{periph_to_mio_oe_i, 1'b0, 1'b1, 1'b1}`, so index 2 selects output enable 0: the pad is not driven (high-Z). |

English Breakfast was also checked (47 flops, all reset to 2) but is not recorded as separate evidence.

## Which evidence is independent

The register reset value in the RTL (D2, D3) and the "Reset default: `0x2`" line in each top's generated `registers.md` are both produced by `reggen` from the same `pinmux.hjson`.
They agree by construction, so their agreement says nothing about whether the value is the intended one.
The programmers' guide is written by hand, so R1 to R3 are the independent statements of intent checked here.

## Expected behavior after reset

`MIO_OUTSEL_<k>.OUT = 2`, so pad `k` has output enable 0 (high-Z), under these conditions:

- immediately after the pinmux register reset, before software writes `MIO_OUTSEL`;
- `MIO_PAD_SLEEP_STATUS_<k>` is 0 (its reset value), so the pad output comes from the `MIO_OUTSEL` selection and not from the sleep retention registers.

## Finding

R1 and R3 agree with the design. R2 does not: the table marks value `0` (constant zero, pad driven low) as the default, while the reset value is `2` (high-Z), as the text immediately before and after the table also says.
A reader who relies on the table would expect the pads to be driven low after reset, when in fact they are not driven.

## Ambiguities

- R1 to R3 speak of "POR" and "at reset" without saying which resets are meant. The design applies the reset value whenever the pinmux register reset is asserted.
- R3 says individual defaults can be overridden at design time. No top at this revision overrides `MIO_OUTSEL`; every instance resets to 2.

## Out of scope

- Pads that `pinmux_strap_sampling` can route to a JTAG TAP, depending on the life-cycle state and straps. For those pads, the final pad output is not decided by `MIO_OUTSEL` alone.
- A simulation of the pad outputs after reset. This is the planned behavioral check for this case.

## Re-run this case

```sh
./tools/fetch_opentitan.sh cases/001-pinmux-mio-outsel-reset/case.json opentitan
python3 tools/check_case.py cases/001-pinmux-mio-outsel-reset/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Written requirements vs design:
  R1: states 2, design 2 -> agrees
  R2: states 0, design 2 -> DISAGREES
  R3: states 2, design 2 -> agrees

RESULT: documentation and design disagree (R2)
```

## Status

A documentation fix has been proposed upstream: [lowRISC/opentitan#32161](https://github.com/lowRISC/opentitan/pull/32161).
