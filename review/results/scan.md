# Scan: reset and default values stated in the documentation

OpenTitan revision `0ea5236fe749e70ba18f56ba19c4be982ef46da7`. Every hand-written document in the retrieval corpus was read; 12 statements give a value the tool can compare.

| Outcome | Statements |
|---|---|
| disagrees | 1 |
| name not in design | 3 |
| agrees | 8 |

## disagrees

- **disagrees** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 48 (table row):
  > 0                     | Constant zero (default)
  - Register: `mio_outsel` (table header, line 46).
  - Stated value: 0.
  - Design reset value: 2 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 12012, 47 instances).

## name not in design

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

## agrees

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
- **agrees** — `hw/ip_templates/pinmux/doc/programmers_guide.md` line 53 (prose):
  > The global default at reset is `2`, but the default of individual signals can be overridden at design time, if needed.
  - Register: `mio_outsel` (named on line 46 above).
  - Stated value: 2.
  - Design reset value: 2 (`hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv` line 12012, 47 instances).
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
