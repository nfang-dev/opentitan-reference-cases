# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""cocotb tests for case 001: what the Earl Grey pinmux drives on its muxed pads after reset.

Run through run.py, which builds the harness (tb_top.sv) with Verilator and sets:
  OT_ROOT        OpenTitan checkout the harness was built from
  OBSERVED_JSON  file the observations of this run are written to
"""

import json
import os
import re
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly

CLK_NS = 10       # clk_i period
CLK_AON_NS = 40   # clk_aon_i period; only its ratio to clk_i matters here
RESET_CYCLES = 10
SAMPLE_AFTER = (1, 10, 100)   # clk_i cycles after reset release

REG_PKG = "hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_pkg.sv"
OBSERVED = {}


def outsel_offsets():
    """MIO_OUTSEL_<k> register offsets, read from the generated register package."""
    text = (Path(os.environ["OT_ROOT"]) / REG_PKG).read_text(encoding="utf-8")
    found = re.findall(r"PINMUX_MIO_OUTSEL_(\d+)_OFFSET = \d+'h\s*([0-9a-fA-F]+);", text)
    offsets = {int(k): int(v, 16) for k, v in found}
    return [offsets[k] for k in range(len(offsets))]


def pads(value, width):
    """Indices of the pads whose bit is 1."""
    return [k for k in range(width) if (value >> k) & 1]


def record(test, data):
    OBSERVED[test] = data
    Path(os.environ["OBSERVED_JSON"]).write_text(json.dumps(OBSERVED, indent=2) + "\n",
                                                 encoding="utf-8")


async def start_clocks(dut):
    cocotb.start_soon(Clock(dut.clk_i, CLK_NS, units="ns").start())
    cocotb.start_soon(Clock(dut.clk_aon_i, CLK_AON_NS, units="ns").start())


def drive_inputs(dut):
    """Inputs other than clocks and resets. Peripherals drive 1 with output enable 1 on every
    muxed output, so a pad that selects any peripheral would be driven high."""
    width = len(dut.periph_to_mio_i)
    dut.reg_req_i.value = 0
    dut.reg_we_i.value = 0
    dut.reg_addr_i.value = 0
    dut.reg_wdata_i.value = 0
    dut.lc_hw_debug_en_i.value = 0
    dut.lc_dft_en_i.value = 0
    dut.strap_en_i.value = 0
    dut.sleep_en_i.value = 0
    dut.periph_to_mio_i.value = (1 << width) - 1
    dut.periph_to_mio_oe_i.value = (1 << width) - 1
    dut.mio_in_i.value = 0


async def pulse_reset(dut):
    """Assert both resets on a falling clk_i edge, hold RESET_CYCLES cycles, release on a
    falling edge. Returns what the pads showed at the end of the reset."""
    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 0
    dut.rst_aon_ni.value = 0
    await ClockCycles(dut.clk_i, RESET_CYCLES, rising=False)
    during = sample(dut)
    dut.rst_ni.value = 1
    dut.rst_aon_ni.value = 1
    return during


def sample(dut):
    """Pad outputs, read on a falling clk_i edge, where the design's outputs are settled."""
    n = len(dut.mio_oe_o)
    oe, out = int(dut.mio_oe_o.value), int(dut.mio_out_o.value)
    return {"driven_pads": pads(oe, n), "driven_high_pads": pads(oe & out, n),
            "alert": int(dut.alert_o.value)}


async def reg_access(dut, addr, write=False, wdata=0):
    """One register read or write. Returns (read data, bus error)."""
    await FallingEdge(dut.clk_i)
    dut.reg_addr_i.value = addr
    dut.reg_we_i.value = int(write)
    dut.reg_wdata_i.value = wdata
    dut.reg_req_i.value = 1
    for _ in range(100):
        await ReadOnly()
        granted = int(dut.reg_gnt_o.value) == 1
        await FallingEdge(dut.clk_i)   # a rising edge has passed
        if granted:
            break
    else:
        raise AssertionError(f"register request to 0x{addr:x} was not accepted")
    dut.reg_req_i.value = 0
    for _ in range(100):
        await ReadOnly()
        if int(dut.reg_rvalid_o.value) == 1:
            return int(dut.reg_rdata_o.value), int(dut.reg_error_o.value)
        await FallingEdge(dut.clk_i)
    raise AssertionError(f"no response to the register request to 0x{addr:x}")


async def read_outsel(dut):
    values, errors = [], []
    for k, addr in enumerate(outsel_offsets()):
        data, err = await reg_access(dut, addr)
        values.append(data & 0x7f)
        if err:
            errors.append(k)
    return values, errors


@cocotb.test()
async def reset_then_sample(dut):
    """After reset, before software writes MIO_OUTSEL, no muxed pad is driven."""
    drive_inputs(dut)
    dut.rst_ni.value = 1
    dut.rst_aon_ni.value = 1
    await start_clocks(dut)
    await ClockCycles(dut.clk_i, 2, rising=False)
    before = sample(dut)   # state from random initial values, before any reset

    during = await pulse_reset(dut)
    after = {}
    waited = 0
    for n in SAMPLE_AFTER:
        await ClockCycles(dut.clk_i, n - waited, rising=False)
        waited = n
        after[str(n)] = sample(dut)
    await FallingEdge(dut.clk_i)
    values, errors = await read_outsel(dut)

    record("reset_then_sample", {
        "before_reset": {"driven_pad_count": len(before["driven_pads"])},
        "end_of_reset": during,
        "after_reset_release": after,
        "mio_outsel_read": {"values": sorted(set(values)), "count": len(values),
                            "bus_errors": errors},
    })
    for n, s in after.items():
        assert s["driven_pads"] == [], f"{n} cycles after reset, driven pads: {s['driven_pads']}"
        assert s["alert"] == 0
    assert set(values) == {2}, f"MIO_OUTSEL values after reset: {sorted(set(values))}"
    assert errors == []


@cocotb.test()
async def outsel_zero_drives_low(dut):
    """Control: with MIO_OUTSEL = 0, the value the guide's table marks as the default, every
    muxed pad is driven low. This is what the pads would show after reset if that row were right."""
    await start_clocks(dut)
    await FallingEdge(dut.clk_i)
    drive_inputs(dut)
    for addr in outsel_offsets():
        _, err = await reg_access(dut, addr, write=True, wdata=0)
        assert err == 0
    values, errors = await read_outsel(dut)
    await ClockCycles(dut.clk_i, 2, rising=False)
    s = sample(dut)

    n_pads = len(dut.mio_oe_o)
    record("outsel_zero_drives_low", {
        "mio_outsel_read": {"values": sorted(set(values)), "count": len(values),
                            "bus_errors": errors},
        "after_write": {"driven_pad_count": len(s["driven_pads"]),
                        "driven_high_pads": s["driven_high_pads"], "alert": s["alert"]},
    })
    assert set(values) == {0}
    assert s["driven_pads"] == list(range(n_pads))
    assert s["driven_high_pads"] == []


@cocotb.test()
async def reset_restores(dut):
    """A second reset, after software changed MIO_OUTSEL, returns every pad to not driven."""
    await start_clocks(dut)
    await FallingEdge(dut.clk_i)
    drive_inputs(dut)
    await pulse_reset(dut)
    await ClockCycles(dut.clk_i, 10, rising=False)
    s = sample(dut)
    await FallingEdge(dut.clk_i)
    values, errors = await read_outsel(dut)

    record("reset_restores", {
        "after_reset_release": {"10": s},
        "mio_outsel_read": {"values": sorted(set(values)), "count": len(values),
                            "bus_errors": errors},
    })
    assert s["driven_pads"] == []
    assert set(values) == {2}
