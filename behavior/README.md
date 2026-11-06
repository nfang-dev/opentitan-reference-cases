# Behavior checks

The reference cases compare written statements with design code.
A behavior check goes one step further: it simulates the design and observes what it does.

## Case 001: what the pinmux drives on its muxed pads after reset

[Case 001](../cases/001-pinmux-mio-outsel-reset/README.md) found that the pinmux programmers' guide states two different reset defaults for `MIO_OUTSEL`: high-Z (value 2) in its text and "constant zero" (value 0) in its table.
The register reset value in the design is 2.
This check simulates the Earl Grey pinmux and observes the pad outputs themselves.

### What is simulated

- **Design**: the Earl Grey `pinmux` from OpenTitan revision [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7), unchanged, with its register block and every module it depends on, as listed by its FuseSoC core.
  The pad configuration (`PinmuxTargetCfg`) is copied unchanged from `hw/top_earlgrey/rtl/autogen/chip_earlgrey_asic.sv` at build time.
- **Harness**: [`tb_top.sv`](pinmux_outsel_reset/tb_top.sv) connects clocks, resets and a register access port, and holds every other input at an inactive value.
  Register accesses carry bus integrity, generated the way a bus host does, so the register block accepts them.
- **Tests**: [`test_pinmux_outsel_reset.py`](pinmux_outsel_reset/test_pinmux_outsel_reset.py), written with [cocotb](https://www.cocotb.org/) and run with [Verilator](https://www.veripool.org/verilator/).

| Test | What it does | Expected |
|---|---|---|
| `reset_then_sample` | Applies reset, then reads the output enable of all 47 muxed pads 1, 10 and 100 clock cycles after reset is released, and reads all 47 `MIO_OUTSEL` registers. | No pad driven; every register 2 |
| `outsel_zero_drives_low` | Writes 0 to every `MIO_OUTSEL` register (the value the guide's table marks as the default) and reads the pads. | Every pad driven low |
| `reset_restores` | Applies reset again after software has changed `MIO_OUTSEL`. | No pad driven; every register 2 |

The second test shows what the pads would look like after reset if the table's default were right; the first shows what they do.

### Conditions

- Resets `rst_ni` (also used as `rst_sys_ni`) and `rst_aon_ni` asserted together for 10 cycles of `clk_i` and released together.
- Clocks: `clk_i` 10 ns, `clk_aon_i` 40 ns.
- Life-cycle debug and DFT enables Off; the TAP straps are not sampled. Under other life-cycle states, some pads can be routed to a JTAG TAP; that is not covered.
- Sleep is not requested, so `MIO_PAD_SLEEP_STATUS` keeps its reset value.
- Every peripheral drives 1 with output enable 1 on every muxed output, so a pad that selected any peripheral would show up as driven high.
- Scan roles come from OpenTitan's open-source placeholder `hw/top_earlgrey/rtl/scan_role_pkg.sv`.
- Verilator simulates two states (0 and 1) and does not model unknown (X) values. To make sure that a pass comes from the reset and not from a lucky starting state, every state that reset does not set starts from random values (`--x-initial unique`, `+verilator+rand+reset+2`), and the tests run with three seeds.

### Results

Run in CI ([run 42145993490](https://github.com/nfang-dev/opentitan-reference-cases/actions/runs/42145993490)) with Verilator 5.020 and cocotb 1.9.2; recorded in [`results/observed.json`](pinmux_outsel_reset/results/observed.json).

| Seed | Pads driven before the first reset (random state) | Pads driven 1, 10, 100 cycles after reset | `MIO_OUTSEL` after reset | Pads driven low after writing 0 | Pads driven after the second reset |
|---|---|---|---|---|---|
| 1 | 26 of 47 | 0, 0, 0 | all 47 read 2 | 47 of 47 | 0 |
| 2 | 34 of 47 | 0, 0, 0 | all 47 read 2 | 47 of 47 | 0 |
| 3 | 29 of 47 | 0, 0, 0 | all 47 read 2 | 47 of 47 | 0 |

No register access returned an error and the bus integrity alert stayed low in every run.

After reset the muxed pads are not driven, which matches the guide's text (high-Z) and not its table (constant zero).

### Does the check detect a wrong reset value?

`run.py --faulty` changes the reset value of all 47 `MIO_OUTSEL` registers in a copy of `pinmux_reg_top.sv` from 2 to 0, runs the same tests, and restores the file.
With that change, all 47 pads are driven low from the end of reset onwards, `reset_then_sample` and `reset_restores` fail, and `outsel_zero_drives_low` still passes ([`results/observed_faulty.json`](pinmux_outsel_reset/results/observed_faulty.json)).
The check therefore detects the behavior that the table's default would produce.
This is a deliberately inserted fault, kept separate from the real finding.

### What this does not show

- It observes the outputs of the `pinmux` module, not the physical pads: the pad ring, pad attributes and the analog behavior of an undriven pad are not simulated.
- One top (Earl Grey) and one life-cycle condition (debug and DFT off).
- A two-state simulator cannot show an output that is unknown (X) after reset; the random starting state reduces, but does not remove, that limitation.
- OpenTitan's container image installs Verilator 4.210 (`util/container/Dockerfile`); this check uses Verilator 5.020, because cocotb 1.9 needs Verilator 5.

### Re-running

Needs Verilator 5.006 or newer, Python 3.10 or newer and git.

```sh
pip install -r behavior/requirements.txt
./behavior/fetch_hw.sh opentitan-hw          # OpenTitan hw/ at the case's revision (about 200 MB)
python3 behavior/pinmux_outsel_reset/run.py --opentitan opentitan-hw --out observed.json \
  --expect behavior/pinmux_outsel_reset/results/observed.json
python3 behavior/pinmux_outsel_reset/run.py --opentitan opentitan-hw --faulty --seed 1 \
  --out observed_faulty.json --expect behavior/pinmux_outsel_reset/results/observed_faulty.json
```

`--expect` compares the new observations with the recorded ones and fails if they differ.
CI runs both commands whenever these files change ([workflow](../.github/workflows/behavior-check.yml)).
