# The review tool against the labeled reference cases

Each labeled claim of cases 001 to 012 is compared with what `review.py scan` reports for the requirement lines the claim comes from.

- Same outcome as the label: 4
- Different outcome: 1
- Requirement not found by the tool: 5
- Outside the tool's scope (not a reset value): 46

| Claim | Setting | Label | Tool | Result |
|---|---|---|---|---|
| 001-C1 | MIO_OUTSEL_<k>.OUT after reset | agrees | - | not found |
| 001-C2 | MIO_OUTSEL_<k>.OUT after reset | disagrees | disagrees | same |
| 001-C3 | MIO_OUTSEL_<k>.OUT after reset | agrees | agrees | same |
| 002-C1 | INT_STATE_READ_ENABLE after reset | agrees | - | not found |
| 002-C2 | INT_STATE_HALT_ENABLE after reset | agrees | - | not found |
| 002-C3 | per-instance write enable after reset | unresolved | - | not found |
| 003-C1 | MIO_PAD_SLEEP_EN_<k>.EN after reset | agrees | agrees | same |
| 003-C2 | DIO_PAD_SLEEP_EN_<k>.EN after reset | agrees | agrees | same |
| 004-C1 | creator root key can be loaded again before the next reset (1 yes, 0 no) | disagrees | - | outside scope |
| 004-C2 | creator root key can be loaded again before the next reset (1 yes, 0 no) | agrees | - | outside scope |
| 004-C3 | creator root key can be loaded again before the next reset (1 yes, 0 no) | agrees | - | outside scope |
| 005-C1 | a detected break raises an interrupt (1 yes, 0 no) | agrees | - | outside scope |
| 005-C2 | after a break interrupt, no further one until the RX line has been high (1 yes, 0 no) | agrees | - | outside scope |
| 005-C3 | software can read the current break status from a STATUS bit (1 yes, 0 no) | disagrees | - | outside scope |
| 005-C4 | INTR_STATE has a field named BREAK (1 yes, 0 no) | disagrees | - | outside scope |
| 006-C1 | value written to CMD to start an operation | disagrees | - | outside scope |
| 006-C2 | value written to CMD to start an operation | disagrees | - | outside scope |
| 006-C3 | value written to CMD to start an operation | agrees | - | outside scope |
| 006-C4 | CMD has a field named start (1 yes, 0 no) | disagrees | - | outside scope |
| 007-C1 | CMD has a field named mode (1 yes, 0 no) | disagrees | - | outside scope |
| 007-C2 | CFG_SHADOWED has a field named mode that sets the hashing mode (1 yes, 0 no) | agrees | - | outside scope |
| 007-C3 | STATUS has a field named squeeze (1 yes, 0 no) | disagrees | - | outside scope |
| 007-C4 | STATUS has a bit that is 1 once absorbing is complete (1 yes, 0 no) | agrees | - | outside scope |
| 008-C1 | a program integrity error in an operation software started is recorded in ERR_CODE (1 yes, 0 no) | agrees | - | outside scope |
| 008-C2 | ERR_CODE has a field named PROG_INTG_ERR (1 yes, 0 no) | disagrees | - | outside scope |
| 008-C3 | STD_FAULT_STATUS.PROG_INTG_ERR records a program integrity error (1 yes, 0 no) | agrees | - | outside scope |
| 008-C4 | FAULT_STATUS has a field for a life cycle management read integrity error (1 yes, 0 no) | disagrees | - | outside scope |
| 008-C5 | a field named LCMGR_INTG_ERR records a life cycle management read integrity error (1 yes, 0 no) | agrees | - | outside scope |
| 008-C6 | a program integrity error in an operation the life cycle management interface started is recorded in FAULT_STATUS (1 yes, 0 no) | agrees | - | outside scope |
| 008-C7 | FAULT_STATUS has a field named PROG_INTG_ERR (1 yes, 0 no) | disagrees | - | outside scope |
| 009-C1 | a register named CLASSA_ACCUM_THRESH exists (1 yes, 0 no) | disagrees | - | outside scope |
| 009-C2 | a register named CLASSA_PHASE0_CYC exists (1 yes, 0 no) | disagrees | - | outside scope |
| 009-C3 | escalation signal 0 of a class is enabled after reset (1 yes, 0 no) | agrees | name not in design | different: name not in design |
| 009-C4 | the control register has a field named E0_EN (1 yes, 0 no) | disagrees | name not in design | outside scope |
| 009-C5 | escalation phase in which signal 0 is asserted, after reset | agrees | - | not found |
| 009-C6 | the control register has a field named E0_MAP (1 yes, 0 no) | disagrees | - | outside scope |
| 009-C7 | the control register has a field named REGWEN (1 yes, 0 no) | disagrees | - | outside scope |
| 009-C8 | writing 0 to a lock bit locks the class configuration (1 yes, 0 no) | agrees | - | outside scope |
| 009-C9 | a register named PING_TIMER_EN exists (1 yes, 0 no) | disagrees | - | outside scope |
| 009-C10 | writing 1 to the ping timer enable register enables the ping timer (1 yes, 0 no) | agrees | - | outside scope |
| 010-C1 | writing COMMAND while STATUS.READY is 0 sets an ERROR_STATUS bit (1 yes, 0 no) | agrees | - | outside scope |
| 010-C2 | ERROR_STATUS has a field named CMDERR (1 yes, 0 no) | disagrees | - | outside scope |
| 010-C3 | ERROR_STATUS has fields named OVERFLOW, UNDERFLOW, CMDINVAL, CSIDINVAL and ACCESSINVAL (1 yes, 0 no) | agrees | - | outside scope |
| 010-C4 | an ERROR_STATUS bit is cleared by writing 1 to it (1 yes, 0 no) | agrees | - | outside scope |
| 011-C1 | FDATA has 1-bit fields READB, RCONT, START, STOP and NAKOK (1 yes, 0 no) | agrees | - | outside scope |
| 011-C2 | width of FDATA.FBYTE in bits | agrees | - | outside scope |
| 011-C3 | TIMING4 has a field named T_STO (1 yes, 0 no) | disagrees | - | outside scope |
| 011-C4 | the stop setup time is set in TIMING4 (1 yes, 0 no) | agrees | - | outside scope |
| 011-C5 | FIFO_CTRL has a field named FMTILVL (1 yes, 0 no) | disagrees | - | outside scope |
| 011-C6 | writing 1 to FIFO_CTRL.FMTRST resets the format FIFO (1 yes, 0 no) | agrees | - | outside scope |
| 012-C1 | width of WKUP_CTRL.prescaler in bits | agrees | - | outside scope |
| 012-C2 | writing 0 to WKUP_CAUSE clears the wake-up request (1 yes, 0 no) | agrees | - | outside scope |
| 012-C3 | writing 1 to an INTR_STATE field clears the interrupt (1 yes, 0 no) | agrees | - | outside scope |
| 012-C4 | WKUP_THOLD_HI holds bits 63:32 of the threshold (1 yes, 0 no) | agrees | - | outside scope |
| 012-C5 | WKUP_THOLD_HI holds bits 31:0 of the threshold (1 yes, 0 no) | disagrees | - | outside scope |
| 012-C6 | writing 0 to WDOG_REGWEN locks the watchdog configuration (1 yes, 0 no) | agrees | - | outside scope |

## Statements the tool found outside the reference cases (7)

- **agrees** — `hw/ip/edn/doc/theory_of_operation.md` line 86 (prose):
  > The reset value is `0`, which means no `generate` commands are issued.
  - Register: `MAX_NUM_REQS_BETWEEN_RESEEDS` (named on line 85 above).
  - Stated value: 0.
  - Design reset value: 0 (`hw/ip/edn/rtl/edn_reg_top.sv` line 961).
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
- **agrees** — `hw/ip_templates/racl_ctrl/doc/programmers_guide.md` line 14 (prose):
  > Interrupts are disabled by default but can be enabled via the `INTR_ENABLE` register.
  - Register: `INTR_ENABLE` (named in the sentence).
  - Stated value: 0.
  - Design reset value: 0 (`hw/top_darjeeling/ip_autogen/racl_ctrl/rtl/racl_ctrl_reg_top.sv` line 442).
- **agrees** — `hw/top_earlgrey/ip_autogen/alert_handler/doc/theory_of_operation.md` line 389 (prose):
  > The interrupt timeout is disabled if this is set to 0 (default).
  - Register: `CLASSA_TIMEOUT_CYC_SHADOWED` (named on line 388 above).
  - Stated value: 0.
  - Design reset value: 0 (`hw/top_earlgrey/ip_autogen/alert_handler/rtl/alert_handler_reg_top.sv` line 13687).
