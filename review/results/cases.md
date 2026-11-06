# The review tool against the labeled reference cases

Each labeled claim of cases 001 to 004 is compared with what `review.py scan` reports for the requirement lines the claim comes from.

- Same outcome as the label: 4
- Different outcome: 0
- Requirement not found by the tool: 4
- Outside the tool's scope (not a reset value): 3

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

## Statements the tool found outside the reference cases (8)

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
- **name not in design** — `hw/ip_templates/alert_handler/doc/programmers_guide.md` line 53 (prose):
  > - Determine whether to enable the escalation signal, and set the `CLASSA_CTRL_SHADOWED.E0_EN` bit accordingly (default is enabled).
  - Register: `CLASSA_CTRL_SHADOWED.E0_EN` (named in the sentence).
  - Stated value: enabled.
  - Not a design name. Closest design names: `classa_ctrl_shadowed.en_e0`.
  - If `classa_ctrl_shadowed.en_e0` is meant: design reset value 1 (`hw/top_earlgrey/ip_autogen/alert_handler/rtl/alert_handler_reg_top.sv` line 13258), so the value agrees.
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
