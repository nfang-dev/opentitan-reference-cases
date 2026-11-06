# Review: After reset, which SPI_HOST error and event interrupts are enabled by ERROR_ENABLE and EVENT_ENABLE?

OpenTitan revision `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Passages of the earlier revision `63c8a5025a0b02f50c3502e8ae0653cfd4a36ff9` were searched too, ranked below every current passage, and not used for the check.

**Outcome: agrees.** Every statement found agrees with the design's reset value.

## 1. Passages found

BM25 over 3350 passages of hand-written documentation; the first 5 current passages:

| # | Passage | Section | Score |
|---|---|---|---|
| 1 | `hw/ip/spi_host/doc/programmers_guide.md` lines 33–37 | Programmer's Guide > Initializing the IP > Interrupt configuration | 38.79 |
| 2 | `hw/ip/spi_host/doc/programmers_guide.md` lines 39–44 | Programmer's Guide > Initializing the IP > Interrupt configuration | 37.99 |
| 3 | `hw/ip/spi_host/doc/programmers_guide.md` lines 149–153 | Programmer's Guide > Issuing Transactions > Reading Back the Device Response | 33.71 |
| 4 | `hw/ip/spi_host/doc/theory_of_operation.md` lines 597–606 | API Details > Interrupt Aggregation > Error Interrupt Conditions | 32.58 |
| 5 | `hw/ip/spi_host/doc/theory_of_operation.md` lines 629–634 | API Details > Other Registers > SPI_HOST Enable | 31.71 |

## 2. Statements that give a value, and the design

- **agrees** — `hw/ip/spi_host/doc/programmers_guide.md` line 37 (prose):
  > At reset all fields in `ERROR_ENABLE` are set, indicating that all error classes will trigger an interrupt.
  - Register: `ERROR_ENABLE` (named in the sentence).
  - Stated value: all set.
  - Design reset value: every field all ones (`hw/ip/spi_host/rtl/spi_host_reg_top.sv` line 1332).
- **agrees** — `hw/ip/spi_host/doc/programmers_guide.md` line 40 (prose):
  > At reset all fields in this register are cleared, meaning all event interrupts are disabled, and thus all transactions must be managed by polling the status register.
  - Register: `EVENT_ENABLE` (named on line 39 above).
  - Stated value: 0.
  - Design reset value: 0 (`hw/ip/spi_host/rtl/spi_host_reg_top.sv` line 1644).

### Other statements about `error_enable`, `event_enable` in the same modules' documentation

None.

### Sentences about reset or defaults that the tool could not check

No value, or no single register, could be identified in these; a reviewer should read them.

- `hw/ip/spi_host/doc/theory_of_operation.md` line 601: "By default all error events will trigger an `error` interrupt."
- `hw/ip/spi_host/doc/theory_of_operation.md` line 629: "The SPI_HOST IP state machine is disabled on reset."

## 3. What this check does not cover

- Statements that describe a value only in words such as "high-Z" or "enabled for all instances" are not compared; nor are statements whose register cannot be identified from a code-style name in the sentence or just above it.
- The design value is the register's reset value in the generated register RTL. It comes from the same register description as registers.md, so it is not independent of it, and it does not show what the rest of the logic does with the value. A behavior check (simulation) is needed for that; see `behavior/` for one.
- Passages ranked below the first few are not read; a statement elsewhere in the documentation may say something different. `review.py scan` checks every statement.
