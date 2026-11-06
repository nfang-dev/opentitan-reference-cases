# Review: Is escalation signal 0 of alert class A enabled by default (CLASSA_CTRL_SHADOWED.E0_EN)?

OpenTitan revision `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Passages of the earlier revision `63c8a5025a0b02f50c3502e8ae0653cfd4a36ff9` were searched too, ranked below every current passage, and not used for the check.

**Outcome: name not in design.** A statement names a register or field that the design does not define under that name; see the closest design names.

## 1. Passages found

BM25 over 3350 passages of hand-written documentation; the first 5 current passages:

| # | Passage | Section | Score |
|---|---|---|---|
| 1 | `hw/ip_templates/alert_handler/doc/programmers_guide.md` lines 46–55 | Programmer's Guide > Initialization | 54.36 |
| 2 | `hw/top_earlgrey/ip_autogen/alert_handler/doc/theory_of_operation.md` lines 406–414 | Theory of Operation > Design Details > Programmable Escalation Protocol | 39.49 |
| 3 | `hw/ip_templates/alert_handler/doc/programmers_guide.md` lines 33–44 | Programmer's Guide > Initialization | 31.81 |
| 4 | `hw/ip_templates/alert_handler/doc/programmers_guide.md` lines 85–91 | Programmer's Guide > Interrupt Handling | 30.64 |
| 5 | `hw/ip_templates/alert_handler/doc/programmers_guide.md` lines 66–72 | Programmer's Guide > Interrupt Handling | 28.65 |

## 2. Statements that give a value, and the design

- **name not in design** — `hw/ip_templates/alert_handler/doc/programmers_guide.md` line 53 (prose):
  > - Determine whether to enable the escalation signal, and set the `CLASSA_CTRL_SHADOWED.E0_EN` bit accordingly (default is enabled).
  - Register: `CLASSA_CTRL_SHADOWED.E0_EN` (named in the sentence).
  - Stated value: enabled.
  - Not a design name. Closest design names: `classa_ctrl_shadowed.en_e0`.
  - If `classa_ctrl_shadowed.en_e0` is meant: design reset value 1 (`hw/top_earlgrey/ip_autogen/alert_handler/rtl/alert_handler_reg_top.sv` line 13258), so the value agrees.

### Sentences about reset or defaults that the tool could not check

No value, or no single register, could be identified in these; a reviewer should read them.

- `hw/top_earlgrey/ip_autogen/alert_handler/doc/theory_of_operation.md` line 409: "Each of the four escalation severity outputs (0 - 3) are by default configured to be asserted during the corresponding phase, e.g., severity 0 in phase 0,  severity 1 in phase 1, etc."

## 3. What this check does not cover

- Statements that describe a value only in words such as "high-Z" or "enabled for all instances" are not compared; nor are statements whose register cannot be identified from a code-style name in the sentence or just above it.
- The design value is the register's reset value in the generated register RTL. It comes from the same register description as registers.md, so it is not independent of it, and it does not show what the rest of the logic does with the value. A behavior check (simulation) is needed for that; see `behavior/` for one.
- Passages ranked below the first few are not read; a statement elsewhere in the documentation may say something different. `review.py scan` checks every statement.
