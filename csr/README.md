# Register tests on complete IPs (Verilator and cocotb)

Every OpenTitan IP has registers that software uses to configure and observe it. Their specified behavior is in the IP's register description (`data/<ip>.hjson`): each field's reset value, its software access type (read-write, read-only, write-1-to-clear, ...) and the lock register, if any, that protects it.
This part checks that the **complete IP**, not just its generated register block, behaves as that description says, in an open-source simulation flow that runs in CI.

```
<ip>.hjson ──reggen──> expected behavior (reset values, access types, locks, OpenTitan's exclusions)
<ip>.sv ──gen_harness.py──> harness: clocks, resets, a register port, every other input held inactive
                     │
             FuseSoC + Verilator + cocotb
                     │
     hw_reset · rw · regwen_lock · alert_test_lock  ──>  results/<ip>.json
```

## What is tested

| Test | Checks |
|---|---|
| `hw_reset` | After reset, every register reads its specified reset value. |
| `rw` | Writing random data, twice, gives the read-back each field's access type predicts (read-write fields take the data, read-only fields keep their value, write-1-to-clear fields clear the bits written as 1, ...). |
| `regwen_lock` | Once a lock register is cleared, the registers it protects ignore writes. |
| `alert_test_lock` | Writing `ALERT_TEST` raises an alert on the IP's alert output; after its `regwen` field is cleared, the same write does not. |

Choices that keep the results comparable with OpenTitan's own register tests:

- **Expected values come from OpenTitan's register tool.** `regmodel.py` reads the register description with reggen, the library OpenTitan uses to generate the register RTL, documentation and verification models.
- **OpenTitan's exclusions are followed.** A register or field tagged `excl:<test>:<kind>` in the description is left out the way OpenTitan's own register tests leave it out (encodings from `hw/dv/sv/dv_base_reg/dv_base_reg_pkg.sv`).
- **The complete IP is simulated.** Registers implemented outside the register block, such as status registers, read what the hardware drives.

What `rw` does not try to predict, and therefore does not check, is reported per register as "not tested":
- registers implemented outside the register block;
- lock registers (checked by `regwen_lock`);
- `ALERT_TEST` (checked by `alert_test_lock`);
- registers OpenTitan excludes from writes;
- fields that hardware can also change.

## Does it detect errors?

`run.py --mutate` makes one deliberate change to a copy of the IP's register RTL, runs the tests and restores the file. The run passes only if the intended test fails:

| Change | Must be detected by |
|---|---|
| `resval`: the reset value of one read-write field flipped | `hw_reset` |
| `access`: one read-write field made read-only | `rw` |
| `regwen`: `ALERT_TEST` writes no longer gated by its lock | `alert_test_lock` |

These are deliberately inserted faults, reported separately from results on the unchanged design.

## Results

| IP | Registers | `hw_reset` | `rw` | `regwen_lock` | `alert_test_lock` | Changes detected |
|---|---|---|---|---|---|---|
| uart | 13 | pass (11 checked, 2 excluded by OpenTitan) | pass (5 registers, 2 rounds; 8 not tested) | no lock registers | pass | 3 of 3 |

Two random seeds per IP; each seed also randomizes every state that reset does not set.
The results are in [`results/`](results), produced by CI and compared with the committed files on every run.

## Running

Needs Verilator 5.006 or newer and Python 3.10 or newer.

```sh
pip install -r csr/requirements.txt
./csr/fetch_opentitan.sh opentitan                 # OpenTitan hw/ and util/ at the recorded revision
python3 csr/run.py --opentitan opentitan --out out --expect csr/results
python3 csr/run.py --opentitan opentitan --out out --seed 1 --mutate resval --expect csr/results
```

Add an IP by listing it in [`ips.json`](ips.json), with any input that must not be held at zero (for example, a UART receive line idles high).

## Limitations

- Only the register interface is exercised; the IP's function (sending a byte, counting time) is not.
- Inputs other than clocks, resets and the register bus are held at one inactive value; behavior that depends on them is not covered.
- `rw` checks only fields whose read-back can be predicted without a model of the hardware.
- Verilator simulates two states; unknown (X) values cannot be observed.
- OpenTitan's own register tests run in its UVM environment with commercial simulators; this flow is a smaller, open-source check, not a replacement for them.
