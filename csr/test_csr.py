# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Register tests for a complete OpenTitan IP, run with cocotb on the harness from
gen_harness.py. Expected behavior comes from the register model written by regmodel.py.

  hw_reset         every register reads its specified reset value after reset
  rw               writes take effect as each field's software access type says
  regwen_lock      a register protected by a lock register ignores writes once locked
  alert_test_lock  ALERT_TEST raises an alert, and stops doing so once its lock is cleared

Set by run.py:
  CSR_MODEL    register model (JSON)
  CSR_PORTS    clock and reset port names (JSON list)
  CSR_RESULTS  file the observations are written to
"""

import json
import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly

import regmodel

MODEL = json.loads(Path(os.environ["CSR_MODEL"]).read_text(encoding="utf-8"))
PORTS = json.loads(os.environ["CSR_PORTS"])
CLOCKS = [p for p in PORTS if p.startswith("clk")]
RESETS = [p for p in PORTS if p.startswith("rst")]
RESULTS = {}

# Access types whose read-back after a write can be predicted from the value before the
# write and the value written.
PREDICT = {
    "rw": lambda old, d: d, "ro": lambda old, d: old, "wo": lambda old, d: 0,
    "rw1c": lambda old, d: old & ~d, "rw1s": lambda old, d: old | d,
    "rw0c": lambda old, d: old & d, "r0w1c": lambda old, d: 0,
}


def period(name: str) -> int:
    return 40 if "aon" in name else 10


def record(test, data):
    RESULTS[test] = data
    Path(os.environ["CSR_RESULTS"]).write_text(json.dumps(RESULTS, indent=1) + "\n",
                                                encoding="utf-8")


def mask_of(f):
    return ((1 << f["width"]) - 1) << f["lsb"]


def get(value, f):
    return (value >> f["lsb"]) & ((1 << f["width"]) - 1)


def start_clocks(dut):
    for c in CLOCKS:
        cocotb.start_soon(Clock(getattr(dut, c), period(c), units="ns").start())


async def reset(dut):
    """Assert all resets together and release them together (clocks already running)."""
    dut.reg_req_i.value = 0
    dut.reg_we_i.value = 0
    dut.reg_addr_i.value = 0
    dut.reg_wdata_i.value = 0
    for r in RESETS:
        getattr(dut, r).value = 1
    await ClockCycles(dut.clk_i, 2, rising=False)
    for r in RESETS:
        getattr(dut, r).value = 0
    await ClockCycles(dut.clk_i, 10 * max(period(c) for c in CLOCKS) // 10, rising=False)
    for r in RESETS:
        getattr(dut, r).value = 1
    await ClockCycles(dut.clk_i, 20, rising=False)


async def access(dut, addr, write=False, wdata=0):
    """One register read or write; returns (read data, bus error)."""
    await FallingEdge(dut.clk_i)
    dut.reg_addr_i.value = addr
    dut.reg_we_i.value = int(write)
    dut.reg_wdata_i.value = wdata
    dut.reg_req_i.value = 1
    for _ in range(1000):
        await ReadOnly()
        granted = int(dut.reg_gnt_o.value) == 1
        await FallingEdge(dut.clk_i)
        if granted:
            break
    else:
        raise AssertionError(f"request to 0x{addr:x} not accepted")
    dut.reg_req_i.value = 0
    for _ in range(1000):
        await ReadOnly()
        if int(dut.reg_rvalid_o.value) == 1:
            return int(dut.reg_rdata_o.value), int(dut.reg_error_o.value)
        await FallingEdge(dut.clk_i)
    raise AssertionError(f"no response from 0x{addr:x}")


async def write(dut, reg, data):
    """Write a register; shadowed registers take a value written twice in a row."""
    _, err = await access(dut, reg["offset"], True, data)
    if reg["shadowed"]:
        _, err2 = await access(dut, reg["offset"], True, data)
        err |= err2
    return err


def lock_registers():
    return {r["regwen"] for r in MODEL["registers"] if r["regwen"]}


def rw_eligible(reg, test="CsrRwTest"):
    """A register whose read-back after a write can be predicted without modelling the
    hardware: not excluded from writes, not implemented outside the register block, not a
    lock register, not ALERT_TEST (writing it raises alerts), and no field that clears on
    read."""
    if regmodel.excluded(reg["tags"], test, regmodel.WRITE):
        return False
    if reg["hwext"] or reg["name"] in lock_registers() or reg["name"] == "ALERT_TEST":
        return False
    return all(f["swaccess"] != "rc" for f in reg["fields"])


def check_mask(reg, test):
    """Bits compared in a write-read check: fields not excluded from checks, not updated by
    hardware, and with a predictable access type."""
    if regmodel.excluded(reg["tags"], test, regmodel.WRITE_CHECK):
        return 0
    m = 0
    for f in reg["fields"]:
        if regmodel.excluded(f["tags"], test, regmodel.WRITE_CHECK):
            continue
        if f["hwaccess"] in ("hrw", "hwo") or f["swaccess"] not in PREDICT:
            continue
        m |= mask_of(f)
    return m


def write_data(reg, old, rand, test):
    """Random data, with fields excluded from writes kept at their current value."""
    data = rand.getrandbits(32)
    for f in reg["fields"]:
        if regmodel.excluded(f["tags"], test, regmodel.WRITE):
            data = (data & ~mask_of(f)) | (old & mask_of(f))
    return data


def predict(reg, old, data):
    value = 0
    for f in reg["fields"]:
        fn = PREDICT.get(f["swaccess"])
        if fn:
            value |= (fn(get(old, f), get(data, f)) & ((1 << f["width"]) - 1)) << f["lsb"]
    return value


@cocotb.test()
async def hw_reset(dut):
    """Every register not excluded by OpenTitan reads its specified reset value."""
    start_clocks(dut)
    await reset(dut)
    rows, failures = [], []
    for reg in MODEL["registers"]:
        if regmodel.excluded(reg["tags"], "CsrHwResetTest", regmodel.INIT_CHECK):
            rows.append({"register": reg["name"], "result": "excluded by OpenTitan"})
            continue
        mask = expected = 0
        for f in reg["fields"]:
            if f["resval"] is None or regmodel.excluded(f["tags"], "CsrHwResetTest",
                                                        regmodel.INIT_CHECK):
                continue
            mask |= mask_of(f)
            expected |= f["resval"] << f["lsb"]
        value, err = await access(dut, reg["offset"])
        ok = not err and (value & mask) == (expected & mask)
        result = "pass" if ok else "fail"
        if ok and mask == 0:
            result = "no reset value specified"
        rows.append({"register": reg["name"], "read": hex(value), "expected": hex(expected),
                     "mask": hex(mask), "bus_error": err, "result": result})
        if not ok:
            failures.append(reg["name"])
    record("hw_reset", {"registers": rows, "failures": failures})
    assert not failures, f"reset values differ: {failures}"


@cocotb.test()
async def rw(dut):
    """Writes take effect as each field's software access type says (two rounds)."""
    start_clocks(dut)
    await reset(dut)
    rand = random.Random(int(os.environ.get("RANDOM_SEED", "1")))
    rows, failures = [], []
    for round_ in (1, 2):
        for reg in MODEL["registers"]:
            if not rw_eligible(reg):
                if round_ == 1:
                    rows.append({"register": reg["name"], "result": "not tested"})
                continue
            old, _ = await access(dut, reg["offset"])
            data = write_data(reg, old, rand, "CsrRwTest")
            werr = await write(dut, reg, data)
            new, rerr = await access(dut, reg["offset"])
            mask = check_mask(reg, "CsrRwTest")
            want = predict(reg, old, data)
            ok = not werr and not rerr and (new & mask) == (want & mask)
            rows.append({"register": reg["name"], "round": round_, "wrote": hex(data),
                         "read": hex(new), "expected": hex(want), "mask": hex(mask),
                         "result": "pass" if ok else "fail"})
            if not ok:
                failures.append(f"{reg['name']} (round {round_})")
    record("rw", {"registers": rows, "failures": failures})
    assert not failures, f"write-read mismatches: {failures}"


@cocotb.test()
async def regwen_lock(dut):
    """Once its lock register is cleared, a protected register ignores writes."""
    if not lock_registers():
        record("regwen_lock", {"result": "not applicable: no register has a lock register"})
        return
    start_clocks(dut)
    await reset(dut)
    regs = {r["name"]: r for r in MODEL["registers"]}
    rows, failures = [], []
    for lock in sorted(lock_registers()):
        lr = regs[lock]
        f = lr["fields"][0]
        locking = 0 if f["swaccess"] == "rw0c" else (1 << f["lsb"])
        await write(dut, lr, locking)
        lv, _ = await access(dut, lr["offset"])
        protected = [r for r in MODEL["registers"] if r["regwen"] == lock and not r["hwext"]]
        for reg in protected:
            old, _ = await access(dut, reg["offset"])
            data = ~old & 0xFFFFFFFF
            await write(dut, reg, data)
            new, _ = await access(dut, reg["offset"])
            mask = check_mask(reg, "CsrRwTest")
            ok = (new & mask) == (old & mask) and get(lv, f) == 0
            rows.append({"lock": lock, "lock_read": hex(lv), "register": reg["name"],
                         "before": hex(old), "wrote": hex(data), "after": hex(new),
                         "mask": hex(mask), "result": "pass" if ok else "fail"})
            if not ok:
                failures.append(reg["name"])
    record("regwen_lock", {"registers": rows, "failures": failures})
    assert not failures, f"writes not blocked by their lock: {failures}"


@cocotb.test()
async def alert_test_lock(dut):
    """Writing ALERT_TEST raises an alert; after its regwen field is cleared, it does not."""
    regs = {r["name"]: r for r in MODEL["registers"]}
    at = regs.get("ALERT_TEST")
    lockf = next((f for f in at["fields"] if f["name"] == "regwen"), None) if at else None
    if not lockf:
        record("alert_test_lock", {"result": "not applicable"})
        return
    alerts = sum(mask_of(f) for f in at["fields"] if f is not lockf)
    keep = mask_of(lockf)

    start_clocks(dut)
    await reset(dut)
    await access(dut, at["offset"], True, keep)            # lock field stays 1, no alert bit
    await ClockCycles(dut.clk_i, 20, rising=False)
    quiet = int(dut.alert_o.value)
    await access(dut, at["offset"], True, alerts | keep)   # unlocked: raises an alert
    await ClockCycles(dut.clk_i, 20, rising=False)
    unlocked = int(dut.alert_o.value)

    await reset(dut)
    await access(dut, at["offset"], True, 0)                # clears the lock field
    await access(dut, at["offset"], True, alerts | keep)   # locked: must not raise an alert
    await ClockCycles(dut.clk_i, 20, rising=False)
    locked = int(dut.alert_o.value)

    ok = quiet == 0 and unlocked == 1 and locked == 0
    record("alert_test_lock", {"alert_before_write": quiet, "alert_after_write_unlocked": unlocked,
                               "alert_after_write_locked": locked,
                               "result": "pass" if ok else "fail"})
    assert ok, f"alert: before {quiet}, unlocked write {unlocked}, locked write {locked}"
