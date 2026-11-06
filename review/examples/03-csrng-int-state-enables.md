# Review: After reset, is reading and halting the csrng internal state enabled for every application instance, as set by INT_STATE_READ_ENABLE and INT_STATE_HALT_ENABLE?

OpenTitan revision `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Passages of the earlier revision `63c8a5025a0b02f50c3502e8ae0653cfd4a36ff9` were searched too, ranked below every current passage, and not used for the check.

**Outcome: not checked.** No passage found gives a reset or default value in a form the tool can compare (a number, or enabled/disabled/cleared for a named register). Read the passages listed; the question needs a person to decide.

## 1. Passages found

BM25 over 3350 passages of hand-written documentation; the first 5 current passages:

| # | Passage | Section | Score |
|---|---|---|---|
| 1 | `hw/ip/csrng/doc/programmers_guide.md` lines 149–155 | Programmer's Guide > Endianness and Known-Answer Tests > Internal-State Save and Restore | 74.66 |
| 2 | `hw/ip/csrng/doc/programmers_guide.md` lines 132–142 | Programmer's Guide > Endianness and Known-Answer Tests > Internal-State Save and Restore | 51.31 |
| 3 | `hw/ip/csrng/doc/programmers_guide.md` lines 156–156 | Programmer's Guide > Endianness and Known-Answer Tests > Internal-State Save and Restore | 49.59 |
| 4 | `hw/ip/csrng/doc/programmers_guide.md` lines 144–147 | Programmer's Guide > Endianness and Known-Answer Tests > Internal-State Save and Restore | 48.32 |
| 5 | `hw/ip/csrng/doc/programmers_guide.md` lines 130–130 | Programmer's Guide > Endianness and Known-Answer Tests > Internal-State Save and Restore | 47.54 |

## 2. Statements that give a value, and the design

None in these passages.

### Other statements about `int_state_halt_enable`, `int_state_read_enable` in the same modules' documentation

None.

### Sentences about reset or defaults that the tool could not check

No value, or no single register, could be identified in these; a reviewer should read them.

- `hw/ip/csrng/doc/programmers_guide.md` line 155: "After reset, reading, writing and halting are enabled for all instances."

## 3. What this check does not cover

- Statements that describe a value only in words such as "high-Z" or "enabled for all instances" are not compared; nor are statements whose register cannot be identified from a code-style name in the sentence or just above it.
- The design value is the register's reset value in the generated register RTL. It comes from the same register description as registers.md, so it is not independent of it, and it does not show what the rest of the logic does with the value. A behavior check (simulation) is needed for that; see `behavior/` for one.
- Passages ranked below the first few are not read; a statement elsewhere in the documentation may say something different. `review.py scan` checks every statement.
