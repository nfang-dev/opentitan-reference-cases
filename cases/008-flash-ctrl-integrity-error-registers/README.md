# Case 008: flash_ctrl: where transmission integrity errors are recorded

| | |
|---|---|
| Module | `flash_ctrl` (embedded flash controller; template in hw/ip_templates) |
| Setting | The register and field in which each transmission integrity error is recorded |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | Program integrity errors are recorded in the registers the document names but under another field name; the life cycle read integrity error is in another register |
| Machine-readable record | [`case.json`](case.json) |

## Question

The theory of operation names a register and field for three integrity errors: in program data from software, in data the life cycle management interface reads, and in program data from that interface. Does each register have that field, and does the design record the error there?

Each setting is recorded as `1` if the statement holds for the design and `0` if it does not.

## Written requirement

| ID | File and line | What it says |
|---|---|---|
| R1 | `hw/ip_templates/flash_ctrl/doc/theory_of_operation.md:189` | For program operations from software: "... an error is registered in `ERR_CODE.PROG_INTG_ERR`." |
| R2 | `hw/ip_templates/flash_ctrl/doc/theory_of_operation.md:190` | "An error is also registered in `STD_FAULT_STATUS.PROG_INTG_ERR` to indicate that a fatal fault has occurred." |
| R3 | `hw/ip_templates/flash_ctrl/doc/theory_of_operation.md:200` | For life cycle management reads: "If an integrity error is seen, it is registered in `FAULT_STATUS.LCMGR_INTG_ERR`." |
| R4 | `hw/ip_templates/flash_ctrl/doc/theory_of_operation.md:203` | For life cycle management program operations: "... an error is registered in `FAULT_STATUS.PROG_INTG_ERR`." |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip_templates/flash_ctrl/data/flash_ctrl.hjson.tpl:1426` | `ERR_CODE.prog_err`: "Flash program has an error. This could be a program integrity error". |
| D2 | `hw/ip_templates/flash_ctrl/rtl/flash_ctrl_prog.sv:154` | The program controller reports a program integrity error as its `prog_err`. |
| D3 | `hw/ip_templates/flash_ctrl/rtl/flash_ctrl_arb.sv:226` | For an operation software started, the arbiter passes the controller's errors to software (`sw_err_o`); for one the life cycle interface started, to hardware (`hw_err_o`, line 212). |
| D4 | `hw/ip_templates/flash_ctrl/rtl/flash_ctrl.sv.tpl:1083` | Software-initiated errors set `ERR_CODE.prog_err`. |
| D5 | `hw/ip_templates/flash_ctrl/data/flash_ctrl.hjson.tpl`, lines 1385 to 1461 | No field of `ERR_CODE` has `intg` in its name. |
| D6 | `hw/ip_templates/flash_ctrl/data/flash_ctrl.hjson.tpl:1479` | `STD_FAULT_STATUS.prog_intg_err`: "a program data transmission integrity error". |
| D7 | `hw/ip_templates/flash_ctrl/rtl/flash_ctrl.sv.tpl:1135` | Set by the program integrity check, whoever started the operation. |
| D8 | `hw/ip_templates/flash_ctrl/data/flash_ctrl.hjson.tpl`, lines 1533 to 1640 | No field of `FAULT_STATUS` has `intg` in its name; the life cycle interface's read integrity error reaches only `STD_FAULT_STATUS` (D10). |
| D9 | `hw/ip_templates/flash_ctrl/data/flash_ctrl.hjson.tpl:1492` | `STD_FAULT_STATUS.lcmgr_intg_err`: an integrity error "during a life cycle management interface read". |
| D10 | `hw/ip_templates/flash_ctrl/rtl/flash_ctrl.sv.tpl:1137` | The interface's integrity error reaches only this field. |
| D11 | `hw/ip_templates/flash_ctrl/data/flash_ctrl.hjson.tpl:1571` | `FAULT_STATUS.prog_err`: "The flash life cycle management interface encountered a program error. This could be a program integrity error". |
| D12 | `hw/ip_templates/flash_ctrl/rtl/flash_ctrl.sv.tpl:1113` | Hardware-initiated errors set `FAULT_STATUS.prog_err`. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | A program integrity error in an operation software started is recorded in `ERR_CODE` (R1) | 1 | 1 (D1, D2, D3, D4) | agrees |
| C2 | `ERR_CODE` has a field named `PROG_INTG_ERR` (R1) | 1 | 0 (D5) | disagrees |
| C3 | `STD_FAULT_STATUS.PROG_INTG_ERR` records a program integrity error (R2) | 1 | 1 (D6, D7) | agrees |
| C4 | `FAULT_STATUS` has a field for a life cycle management read integrity error (R3) | 1 | 0 (D8) | disagrees |
| C5 | A field named `LCMGR_INTG_ERR` records that error (R3) | 1 | 1 (D9, D10) | agrees |
| C6 | A program integrity error in an operation the life cycle interface started is recorded in `FAULT_STATUS` (R4) | 1 | 1 (D2, D3, D11, D12) | agrees |
| C7 | `FAULT_STATUS` has a field named `PROG_INTG_ERR` (R4) | 1 | 0 (D8) | disagrees |

## Which evidence is independent

D1, D5, D6, D8, D9 and D11 are in `flash_ctrl.hjson.tpl`, from which each top's register description, register RTL and `registers.md` are generated; those generated files are not counted as more evidence.
D2, D3, D4, D7, D10 and D12 are in the hand-written RTL (`flash_ctrl.sv.tpl` is a template written by hand).
R1 to R4 are in the hand-written template document; each top's generated copy has the same lines.

## Finding

Each error is recorded where the document says only in part.
A program integrity error in an operation software started is recorded in `ERR_CODE` and in `STD_FAULT_STATUS.PROG_INTG_ERR`, as R1 and R2 say, but `ERR_CODE`'s field is `PROG_ERR`, not `PROG_INTG_ERR`.
In an operation the life cycle management interface started, it is recorded in `FAULT_STATUS`, as R4 says, again as `PROG_ERR`: `FAULT_STATUS` has no integrity field.
A read integrity error of that interface is recorded in a field named `LCMGR_INTG_ERR`, as R3 says, but in `STD_FAULT_STATUS`, not `FAULT_STATUS`.
Software that reads the field R1, R3 or R4 names finds no such field in that register.

This case was found by the name checks in [`claims/`](../../claims/README.md).

## Ambiguities

- R1 and R4 could be read as naming the error rather than a field. At this revision the program controller sets `prog_err` only for a program integrity error (D2), so the fields they would then mean are `ERR_CODE.PROG_ERR` and `FAULT_STATUS.PROG_ERR`; the field names written still do not exist.

## Missing information

This case reads the register description and the RTL that sets the fields; it does not simulate an integrity error.

## Out of scope

- Which alert each error raises.
- Each top's `flash_ctrl` is generated from this template; the fields compared here are the same in every generated copy at this revision.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/008-flash-ctrl-integrity-error-registers/case.json
python3 tools/check_case.py cases/008-flash-ctrl-integrity-error-registers/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 a program integrity error in an operation software started is recorded in ERR_CODE (1 yes, 0 no): stated 1, design 1 (D1, D2, D3, D4) -> agrees
  C2 ERR_CODE has a field named PROG_INTG_ERR (1 yes, 0 no): stated 1, design 0 (D5) -> disagrees
  C3 STD_FAULT_STATUS.PROG_INTG_ERR records a program integrity error (1 yes, 0 no): stated 1, design 1 (D6, D7) -> agrees
  C4 FAULT_STATUS has a field for a life cycle management read integrity error (1 yes, 0 no): stated 1, design 0 (D8) -> disagrees
  C5 a field named LCMGR_INTG_ERR records a life cycle management read integrity error (1 yes, 0 no): stated 1, design 1 (D9, D10) -> agrees
  C6 a program integrity error in an operation the life cycle management interface started is recorded in FAULT_STATUS (1 yes, 0 no): stated 1, design 1 (D2, D3, D11, D12) -> agrees
  C7 FAULT_STATUS has a field named PROG_INTG_ERR (1 yes, 0 no): stated 1, design 0 (D8) -> disagrees

RESULT: 4 agree, 3 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

R1, R3 and R4 are still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. Not reported upstream.
