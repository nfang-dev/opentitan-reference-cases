# Review: In pinmux, what does an MIO pad output after reset if software has not programmed its MIO_OUTSEL register?

OpenTitan revision `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Passages of the earlier revision `63c8a5025a0b02f50c3502e8ae0653cfd4a36ff9` were searched too, ranked below every current passage, and not used for the check.

**Outcome: disagrees.** At least one statement gives a value that differs from the design's reset value.

## 1. Passages found

BM25 over 3350 passages of hand-written documentation; the first 5 current passages:

| # | Passage | Section | Score |
|---|---|---|---|
| 1 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 55–57 | Programmer's Guide > Pinmux Configuration | 44.89 |
| 2 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 34–53 | Programmer's Guide > Pinmux Configuration | 39.31 |
| 3 | `hw/top_earlgrey/ip_autogen/pinmux/doc/theory_of_operation.md` lines 65–74 | Theory of Operation > Muxing Matrix | 34.92 |
| 4 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 5–13 | Programmer's Guide > Pad Attributes | 34.73 |
| 5 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 72–78 | Programmer's Guide > Sleep Features | 32.94 |

## 2. Statements that give a value, and the design

- **name not in design** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 40 (table row):
  > 0                     | Constant zero (default)
  - Register: `periph_insel` (table header, line 38).
  - Stated value: 0.
  - Not a design name. Closest design names: `mio_periph_insel`.
  - If `mio_periph_insel` is meant: design reset value 0 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 7401), so the value agrees.
- **name not in design** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 44 (prose):
  > The global default at reset is `0`, but the default of individual signals can be overridden at design time, if needed.
  - Register: `periph_insel` (named on line 38 above).
  - Stated value: 0.
  - Not a design name. Closest design names: `mio_periph_insel`.
  - If `mio_periph_insel` is meant: design reset value 0 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 7401), so the value agrees.
- **disagrees** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 48 (table row):
  > 0                     | Constant zero (default)
  - Register: `mio_outsel` (table header, line 46).
  - Stated value: 0.
  - Design reset value: 2 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 12012, 47 instances).
- **agrees** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 53 (prose):
  > The global default at reset is `2`, but the default of individual signals can be overridden at design time, if needed.
  - Register: `mio_outsel` (named on line 46 above).
  - Stated value: 2.
  - Design reset value: 2 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 12012, 47 instances).

### Other statements about `mio_outsel` in the same modules' documentation

None.

### Sentences about reset or defaults that the tool could not check

No value, or no single register, could be identified in these; a reviewer should read them.

- `hw/ip_templates/pinmux/doc/programmers_guide.md` line 34: "Upon POR, the `pinmux` state is such that all MIO outputs are high-Z, and all MIO peripheral inputs are tied off to 0."
- `hw/top_earlgrey/ip_autogen/pinmux/doc/theory_of_operation.md` line 73: "Likewise, the output select signals `mio_outsel[*]` can also be used to constantly drive an output pin to 0/1 or to put it into high-Z state (default)."
- `hw/ip_templates/pinmux/doc/programmers_guide.md` line 13: "The following pad attributes are supported by this register layout by default:"

## 3. What this check does not cover

- Statements that describe a value only in words such as "high-Z" or "enabled for all instances" are not compared; nor are statements whose register cannot be identified from a code-style name in the sentence or just above it.
- The design value is the register's reset value in the generated register RTL. It comes from the same register description as registers.md, so it is not independent of it, and it does not show what the rest of the logic does with the value. A behavior check (simulation) is needed for that; see `behavior/` for one.
- Passages ranked below the first few are not read; a statement elsewhere in the documentation may say something different. `review.py scan` checks every statement.
