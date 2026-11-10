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
| `hw_reset` | After reset, every register reads its specified reset value. Registers whose description specifies no reset value (often ones driven directly by hardware) are reported as such, not as passes. |
| `rw` | Writing data gives the read-back each field's access type predicts (read-write fields take the data, read-only fields keep their value, write-1-to-clear fields clear the bits written as 1, ...). Round 1 writes random data and round 2 its inverse, so every bit is written both as 0 and as 1. |
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
| `lock`: one register protected by a lock register written even when locked | `regwen_lock` |

These are deliberately inserted faults, reported separately from results on the unchanged design. The `lock` change applies only to IPs that have a lock register; for the others it is reported as not applicable and skipped.

The check found a weakness in the first version of `rw`, which wrote random data in both rounds: on rv_timer, a 1-bit field made read-only was not detected, because both random values happened to write 0 to it, the field's reset value. Writing the inverse in round 2 fixed it.

## Results

| IP | Registers | `hw_reset` | `rw` | `regwen_lock` | `alert_test_lock` | Changes detected |
|---|---|---|---|---|---|---|
| uart | 13 | pass: 9 checked; 2 with no specified value; 2 excluded by OpenTitan | pass: 5 registers; 8 not tested | no lock registers | pass | 3 of 3 |
| gpio | 114 | pass: 3 checked; 108 with no specified value; 3 excluded | pass: 2 registers; 112 not tested | no lock registers | pass | 3 of 3 |
| rv_timer | 10 | pass: 9 checked; 1 with no specified value | pass: 8 registers; 2 not tested | no lock registers | pass | 3 of 3 |
| aon_timer | 14 | pass: 13 checked; 1 with no specified value | pass: 11 registers; 3 not tested | pass: the 3 registers `WDOG_REGWEN` protects | pass | 4 of 4 |
| i2c | 32 | pass: 22 checked; 3 with no specified value; 7 excluded | pass: 20 registers; 12 not tested | no lock registers | pass | 3 of 3 |

Coverage differs a lot between IPs. Most gpio registers are implemented outside the register block, have no reset value in the description, and are excluded by OpenTitan from write tests, so this flow checks little of gpio beyond its alert test.

### Registers in a second clock domain (aon_timer)

Most aon_timer registers live in the always-on clock domain, which is slower than the bus clock. Software does not read them directly: each has a bus-side copy (`prim_reg_cdc` in OpenTitan) with its own reset value, refreshed from the register only after a write completes.

The `resval` change shows what that means for `hw_reset`. It set the reset value of `WKUP_CTRL.enable` to 1 in the always-on register only. A read of `WKUP_CTRL` right after reset still returned 0, the bus-side copy. The change was caught only through its effects: the wake-up counter was running (`WKUP_COUNT_LO` read 5) and the wake-up interrupt and cause were set.

So for these registers `hw_reset` checks the bus-side copy, not the register that drives the hardware. In OpenTitan both reset values are generated by reggen from the same description, so they agree unless the generated RTL is changed.

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
- For registers in another clock domain, a read right after reset shows the bus-side copy (see aon_timer above).
- OpenTitan's own register tests run in its UVM environment with commercial simulators; this flow is a smaller, open-source check, not a replacement for them.
