# Reset-value review: from a question to a checked answer

The other parts of this repository each do one step: [`retrieval/`](../retrieval/README.md) finds the documentation passage that answers a question, the [cases](../cases) link a statement to design evidence, and [`behavior/`](../behavior/README.md) simulates the design.
This tool runs the steps one after another for one kind of question, a register's value after reset, and writes a report a reviewer can follow:

```
question
  -> 1. passages of the hand-written documentation that answer it (BM25, current revision first)
  -> 2. statements in those passages that give a reset or default value, and the register they are about
  -> 3. the register's reset value in the design (register RTL), with file and line
  -> 4. comparison: agrees, disagrees, name not in design, or not checkable
  -> report: passages and revision, statements, design evidence, outcome, what was not checked
```

It uses only the Python standard library and no language model.

## Usage

```sh
./behavior/fetch_hw.sh opentitan-hw                 # OpenTitan hw/ at the recorded revision
./retrieval/fetch_docs.sh otdocs-earlier earlier    # optional: an earlier revision's documentation

python3 review/review.py ask "In pinmux, what does an MIO pad output after reset if software has not programmed its MIO_OUTSEL register?" \
  --opentitan opentitan-hw --earlier otdocs-earlier --out report.md
python3 review/review.py scan --opentitan opentitan-hw --out scan.md --json scan.json
python3 review/review.py cases --scan scan.json --out cases.md
```

## How each step works

1. **Passages.** BM25 ranks the passages of the [retrieval corpus](../retrieval/README.md#corpus). With `--earlier`, passages of the earlier revision are searched too but ranked below every current passage; they are listed in the report and not used.
   The first five current passages are read.
2. **Statements** ([`statements.py`](statements.py)). A statement is a sentence with a reset or default cue ("reset value", "resets to", "default is", "after reset", "by default", "(default)", ...) and a value (a number, or "enabled", "disabled", "cleared", "all fields are set"), or a table row marked "(default)" whose header names the register.
   The register is a name written in code style (`` `NAME` ``) in the sentence; if there is none, the name on the nearest line above in the same section, as long as that line names only one. How the register was found is written in the report.
   If a sentence names a register that the design does not have, the statement is reported with the closest design names rather than attributed to another register.
3. **Design** ([`design_index.py`](design_index.py)). Reset values come from the module's generated register RTL (`*_reg_top.sv`: the `RESVAL` of each register field), or from `*_reg_pkg.sv` for registers implemented outside the register block. A name like `MIO_OUTSEL` matches all of its instances (`MIO_OUTSEL_0` to `MIO_OUTSEL_46`).
4. **Comparison.** The report gives every statement with its file and line, the stated value, the design value with its file and line, and the outcome.
   If the question names a register, every other statement about it in the same module's documentation is checked too.
   Sentences in the passages that mention reset or a default but could not be checked are listed for a reviewer to read.

## Examples

Five questions, in [`examples/`](examples):

| Question | Outcome |
|---|---|
| [pinmux MIO output after reset](examples/01-pinmux-mio-outsel.md) (case 001) | disagrees: the value table's default is 0, the design resets `MIO_OUTSEL` to 2; the next sentence states 2 and agrees |
| [pinmux sleep enable after reset](examples/02-pinmux-sleep-enable.md) (case 003) | agrees |
| [csrng internal-state enables after reset](examples/03-csrng-int-state-enables.md) (case 002) | not checked: the sentence "After reset, reading, writing and halting are enabled for all instances." names no register and gives no number; the report points to it |
| [alert handler escalation enable](examples/04-alert-handler-escalation-enable.md) | name not in design: the guide writes `CLASSA_CTRL_SHADOWED.E0_EN`, the design field is `EN_E0`; its reset value 1 matches "enabled" |
| [SPI_HOST interrupt enables after reset](examples/05-spi-host-interrupt-enables.md) | agrees |

## Results

### Against the labeled reference cases

[`results/cases.md`](results/cases.md) compares the scan with the 11 labeled claims of cases 001 to 004:

| Result | Claims |
|---|---|
| Same outcome as the label | 4 (001-C2 disagrees, 001-C3, 003-C1, 003-C2) |
| Different outcome | 0 |
| Not found by the tool | 4 (001-C1: "all MIO outputs are high-Z" gives no number; 002-C1 to C3: no register named) |
| Outside the tool's scope | 3 (case 004 is about an operation, not a reset value) |

### Every statement in the documentation

[`results/scan.md`](results/scan.md) checks the whole documentation.
Of 203 sentences that mention reset or a default, 11 lines give 12 statements the tool can compare.
Each of the 12 was read against the source: in all 12 the register and the value were taken correctly.

| Outcome | Statements | What they are |
|---|---|---|
| agrees | 8 | edn, spi_host (2), racl_ctrl, alert_handler, pinmux (3) |
| disagrees | 1 | the pinmux table default of case 001 (fix proposed in lowRISC/opentitan#32161) |
| name not in design | 3 | pinmux `periph_insel` twice (a table header and the sentence after it): the design register is `MIO_PERIPH_INSEL`; lowRISC/opentitan#32162 corrects the name in the sentence above the table, not in the table header; alert_handler `CLASSA_CTRL_SHADOWED.E0_EN`: the design field is `EN_E0` (not reported upstream yet) |

What the tool misses: of the 191 remaining sentences, 15 name a register of the design.
Reading them, 8 do state a reset or default value that the tool cannot translate: an enumeration name (otbn `STATUS` is `BUSY_SEC_WIPE_INT`), a multi-bit boolean constant (rram_ctrl `MuBi4False`), a timing ("a half `SCK` cycle by default", spi_host, three times), a byte order (hmac), a pin state (sysrst_ctrl), and "high-Z" (pinmux).
The other 7 describe internal counters or status, not a register's reset value.
The 176 sentences that name no register in code style were not read one by one; cases 001 and 002 show that some of them do state reset values.

## Limitations

- One kind of question: a register's value after reset. Other requirements, such as case 004's, are out of scope.
- Values written in words other than enabled/disabled/cleared/all set are not translated, so such statements are listed for a person rather than checked.
- The design value comes from the register RTL generated from the same register description as `registers.md`; it is what the hardware resets to, but not what the logic then does with it (for that, see [`behavior/`](../behavior/README.md)).
- The tool reads code-style names only; a statement that names its register in plain words is not attributed.
- The statements were checked against a single OpenTitan revision; the earlier revision is used only for retrieval.
