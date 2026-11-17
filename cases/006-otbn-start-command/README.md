# Case 006: otbn: the command that starts an operation

| | |
|---|---|
| Module | `otbn` (OpenTitan Big Number accelerator) |
| Setting | The value host software writes to the `CMD` register to start executing the program in OTBN's instruction memory |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | The theory of operation agrees with the design; two README sentences name a field and value that do not exist |
| Machine-readable record | [`case.json`](case.json) |

## Question

How does host software start an OTBN operation: by writing 1 to `CMD.start`, or by writing the `EXECUTE` command to `CMD`?

C1 to C3 record the value written to `CMD` (hexadecimal). C4 records `1` if `CMD` has a field named `start` and `0` if it does not.

## Written requirement

| ID | File and line | What it says | Value it implies |
|---|---|---|---:|
| R1 | `hw/ip/otbn/README.md:126` | "All read-write (RW) CSRs are set to 0 when OTBN starts an operation (when 1 is written to `CMD.start`)." | 0x1 |
| R2 | `hw/ip/otbn/README.md:807` | "The `MOD` and `ACC` WSRs are set to 0 when OTBN starts an operation (when 1 is written to `CMD.start`)." | 0x1 |
| R3 | `hw/ip/otbn/doc/theory_of_operation.md:265` | "The `EXECUTE` command starts the execution of the application contained in OTBN's instruction memory." Line 263: commands are issued by writing to `CMD`. | 0xd8 (EXECUTE's value, from D1) |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/otbn/data/otbn.hjson:507` | `CMD.cmd` value table: `0xd8` is `EXECUTE`, "Starts the execution of the program stored in the instruction memory". |
| D2 | `hw/ip/otbn/rtl/otbn_pkg.sv:99` | `CmdExecute = 8'hd8`. |
| D3 | `hw/ip/otbn/rtl/otbn.sv:895` | When `CMD` is written (line 893), only `CmdExecute` sets `start_d`. |
| D4 | `hw/ip/otbn/data/otbn.hjson:492` | "Unrecognized commands are ignored." Writing 1 does nothing. |
| D5 | `hw/ip/otbn/data/otbn.hjson` | No field is named `start`. |
| D6 | `hw/ip/otbn/data/otbn.hjson:500` | `CMD`'s only field is `cmd`, bits 7:0. |

## Claims

| ID | Setting | Stated | Design | Label |
|---|---|---:|---:|---|
| C1 | Value written to `CMD` to start an operation (R1) | 0x1 | 0xd8 (D1 to D4) | disagrees |
| C2 | Value written to `CMD` to start an operation (R2) | 0x1 | 0xd8 (D1 to D4) | disagrees |
| C3 | Value written to `CMD` to start an operation (R3) | 0xd8 | 0xd8 (D1 to D4) | agrees |
| C4 | `CMD` has a field named `start` (R1, R2) | 1 | 0 (D5, D6) | disagrees |

## Which evidence is independent

D1, D4, D5 and D6 are in `otbn.hjson`, from which `reggen` generates the register RTL and `registers.md`; those generated files are not counted as more evidence.
D2 and D3 are hand-written RTL.
R1 to R3 are hand-written.

## Finding

The theory of operation says an operation starts when the `EXECUTE` command is written to `CMD`, and the design starts one only when `CMD` is written with `0xd8`, `EXECUTE`'s value.
Two README sentences instead say an operation starts "when 1 is written to `CMD.start`".
`CMD` has no `start` field: its only field is the 8-bit `cmd`, and values that are not a command, such as 1, are ignored.
Software written from R1 or R2 would not start OTBN.

This case was found by the name checks in [`claims/`](../../claims/README.md).

## Ambiguities

- R1 and R2 mention `CMD.start` only to say when the clearing happens. A reader who knows the `CMD` register may read them as "when an operation starts"; a reader who does not would write 1.

## Missing information

This case reads the register description and the command decoding; it does not simulate a write to `CMD`. What R1 and R2 are mainly about (which registers are cleared when an operation starts) is not checked.

## Out of scope

- The other commands (`SEC_WIPE_DMEM`, `SEC_WIPE_IMEM`, `RESUME`), which the documents describe consistently with the table in D1.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/006-otbn-start-command/case.json
python3 tools/check_case.py cases/006-otbn-start-command/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 value written to CMD to start an operation: stated 0x1, design 0xd8 (D1, D2, D3, D4) -> disagrees
  C2 value written to CMD to start an operation: stated 0x1, design 0xd8 (D1, D2, D3, D4) -> disagrees
  C3 value written to CMD to start an operation: stated 0xd8, design 0xd8 (D1, D2, D3, D4) -> agrees
  C4 CMD has a field named start (1 yes, 0 no): stated 1, design 0 (D5, D6) -> disagrees

RESULT: 1 agree, 3 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

Both README sentences are still present on OpenTitan's `master` branch as of 2026-11-16, and the case gives the same outcomes there. On master, R1's sentence has been extended with an exception for `MAI_CTRL.OPERATION` but still says "when 1 is written to `CMD.start`". Not reported upstream.
