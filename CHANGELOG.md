# Changelog

All versions use OpenTitan revision [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03).

## v0.1.1 (2026-11-16)

More reference cases, and the name checks run on every IP.

- **Reference cases:** eight new cases, 005 to 012 (uart, otbn, kmac, flash_ctrl, alert_handler, spi_host, i2c, aon_timer). There are now 12 cases in 11 modules, with 56 labeled claims: 33 agree, 22 disagree, 1 unresolved. Every case gives the same outcomes at the recorded revision and on OpenTitan's master branch of 2026-11-16. Cases 005 to 012 were chosen from the findings of the name checks, so most of their disagreements are wrong names; each also records the statements around the finding that agree.
- **Case checker:** a pattern that is absent can now decide a setting ("the register has no such field" is 0), and an absence can be checked within one register's definition.
- **Name checks on all 46 IPs** with a register description ([`claims/names.py`](claims/names.py)): 60 findings, each classified. 37 are register or field names that the description does not have (32 still on master), 1 a link to the wrong register, 18 links in the wrong form, 3 deliberate shorthands and 1 not a register reference.
- **Documentation claims:** a second run of prompt 3 on a fresh runner gave the same answers for all 202 sentences.
- **Review tool:** compared with the 56 claims of all 12 cases.
- 64 unit tests.

Not changed: the 70 retrieval questions. A comparison report across methods is planned for v0.2.0.

## v0.1.0 (2026-11-10)

First tagged version: reference cases 001 to 004, the pinmux behavior check, the retrieval comparison, the reset-value review tool, register tests on five complete modules, and documentation claims read by an open-weights model and checked against the register description.
