# Review: What sleep behavior does a pinmux pad have after reset when its MIO_PAD_SLEEP_EN bit is not set?

OpenTitan revision `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Passages of the earlier revision `63c8a5025a0b02f50c3502e8ae0653cfd4a36ff9` were searched too, ranked below every current passage, and not used for the check.

**Outcome: agrees.** Every statement found agrees with the design's reset value.

## 1. Passages found

BM25 over 3350 passages of hand-written documentation; the first 5 current passages:

| # | Passage | Section | Score |
|---|---|---|---|
| 1 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 72–78 | Programmer's Guide > Sleep Features | 59.87 |
| 2 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 61–70 | Programmer's Guide > Sleep Features | 55.79 |
| 3 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 80–82 | Programmer's Guide > Sleep Features | 50.53 |
| 4 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 55–57 | Programmer's Guide > Pinmux Configuration | 38.98 |
| 5 | `hw/ip_templates/pinmux/doc/programmers_guide.md` lines 5–13 | Programmer's Guide > Pad Attributes | 36.34 |

## 2. Statements that give a value, and the design

- **agrees** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 66 (table row):
  > 0                             | -                              | Drive (default)
  - Register: `dio_pad_sleep_en` (table header, line 64).
  - Stated value: 0.
  - Design reset value: 0 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 32865, 16 instances).
- **agrees** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 66 (table row):
  > 0                             | -                              | Drive (default)
  - Register: `mio_pad_sleep_en` (table header, line 64).
  - Stated value: 0.
  - Design reset value: 0 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 28832, 47 instances).

### Other statements about `mio_pad_sleep_en` in the same modules' documentation

None.

### Sentences about reset or defaults that the tool could not check

No value, or no single register, could be identified in these; a reviewer should read them.

- `hw/ip_templates/pinmux/doc/programmers_guide.md` line 13: "The following pad attributes are supported by this register layout by default:"

## 3. What this check does not cover

- Statements that describe a value only in words such as "high-Z" or "enabled for all instances" are not compared; nor are statements whose register cannot be identified from a code-style name in the sentence or just above it.
- The design value is the register's reset value in the generated register RTL. It comes from the same register description as registers.md, so it is not independent of it, and it does not show what the rest of the logic does with the value. A behavior check (simulation) is needed for that; see `behavior/` for one.
- Passages ranked below the first few are not read; a statement elsewhere in the documentation may say something different. `review.py scan` checks every statement.
