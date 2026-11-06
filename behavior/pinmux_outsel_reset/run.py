#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Build the case 001 harness with Verilator and run the cocotb tests.

  run.py --opentitan DIR --out observed.json [--seed N]... [--faulty] [--expect FILE]

--faulty first changes the reset value of every MIO_OUTSEL register in the checkout's
pinmux_reg_top.sv from 2 to 0 (the value the guide's table marks as the default), runs, and
restores the file. The run then succeeds only if the tests detect the change.
--expect compares the observations with a committed result file and fails if they differ.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CASE = REPO / "cases" / "001-pinmux-mio-outsel-reset" / "case.json"
CORE = "nfang:check:pinmux_outsel_reset_tb:0.1"
TEST_MODULE = "test_pinmux_outsel_reset"
CHIP = "hw/top_earlgrey/rtl/autogen/chip_earlgrey_asic.sv"
REG_TOP = "hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_top.sv"
REG_PKG = "hw/top_earlgrey/ip_autogen/pinmux/rtl/pinmux_reg_pkg.sv"

TESTS = ["reset_then_sample", "outsel_zero_drives_low", "reset_restores"]
# Outcome that shows a faulty reset value was detected.
FAULTY_EXPECTED = {"reset_then_sample": "fail", "outsel_zero_drives_low": "pass",
                   "reset_restores": "fail"}

CONDITIONS = {
    "top": "Earl Grey; pad configuration PinmuxTargetCfg from " + CHIP,
    "resets": "rst_ni (also rst_sys_ni) and rst_aon_ni asserted together on a falling clk_i "
              "edge, held for 10 clk_i cycles, released together on a falling edge",
    "clocks": "clk_i 10 ns, clk_aon_i 40 ns",
    "sampling": "pad outputs read on falling clk_i edges, 1, 10 and 100 cycles after release",
    "life_cycle": "lc_hw_debug_en, lc_dft_en, lc_hw_debug_clr, lc_check_byp_en and "
                  "lc_escalate_en Off; strap_en_i 0, so the TAP straps are not sampled",
    "sleep": "sleep_en_i 0; MIO_PAD_SLEEP_STATUS keeps its reset value",
    "peripherals": "every muxed peripheral output drives 1 with output enable 1",
    "initial_state": "Verilator two-state simulation; state that reset does not set starts "
                     "from random values (--x-initial unique, +verilator+rand+reset+2)",
}


def revision_of_case() -> str:
    return json.loads(CASE.read_text(encoding="utf-8"))["opentitan_revision"]


def checkout_revision(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def extract_target_cfg(chip_text: str) -> str:
    """The pad index localparams and PinmuxTargetCfg, unchanged, from chip_earlgrey_asic.sv."""
    lines = chip_text.splitlines()
    start = next(i for i, line in enumerate(lines) if "localparam int Tap0PadIdx" in line)
    cfg = next(i for i, line in enumerate(lines)
               if i > start and "localparam pinmux_pkg::target_cfg_t PinmuxTargetCfg" in line)
    end = next(i for i, line in enumerate(lines) if i > cfg and line.strip() == "};")
    return "\n".join(lines[start:end + 1]) + "\n"


def n_mio_pads(reg_pkg_text: str) -> int:
    return int(re.search(r"parameter int NMioPads = (\d+);", reg_pkg_text).group(1))


OUTSEL_RESVAL = re.compile(r"(\.RESVAL\s*\(\d+'h)2(\),\s*\.Mubi\s*\(1'b0\)\s*\)\s*u_mio_outsel_\d+\s*\()")


def make_faulty(reg_top_text: str, expected: int) -> str:
    """Change the reset value of every MIO_OUTSEL register from 2 to 0."""
    text, count = OUTSEL_RESVAL.subn(r"\g<1>0\g<2>", reg_top_text)
    if count != expected:
        raise ValueError(f"expected {expected} MIO_OUTSEL registers, changed {count}")
    return text


def file_lists(eda: dict, work_root: Path) -> tuple[list[str], list[str]]:
    """Sources (Verilator configuration files first) and include directories from an EDA API
    file written by FuseSoC."""
    vlt, sources, includes = [], [], []
    for f in eda["files"]:
        path = (work_root / f["name"]).resolve()
        kind = f.get("file_type", "")
        if f.get("is_include_file"):
            inc = (work_root / f["include_path"]).resolve() if f.get("include_path") else path.parent
            if str(inc) not in includes:
                includes.append(str(inc))
        elif kind == "vlt":
            vlt.append(str(path))
        elif kind.startswith(("systemVerilogSource", "verilogSource")):
            sources.append(str(path))
    return vlt + sources, includes


def fusesoc_setup(ot: Path, work_root: Path) -> dict:
    if work_root.exists():
        shutil.rmtree(work_root)
    subprocess.run(["fusesoc", "--cores-root", str(ot), "--cores-root", str(HERE), "run",
                    "--setup", "--target", "default", "--tool", "verilator",
                    "--work-root", str(work_root),
                    "--mapping", "lowrisc:prim_generic:all:0.1", CORE], check=True)
    eda_file = next(work_root.glob("*.eda.yml"))
    return yaml.safe_load(eda_file.read_text(encoding="utf-8"))


def test_outcomes(results_xml: Path) -> dict:
    out = {}
    for case in ET.parse(results_xml).getroot().iter("testcase"):
        failed = case.find("failure") is not None or case.find("error") is not None
        out[case.get("name")] = "fail" if failed else "pass"
    return out


def tool_versions() -> dict:
    import cocotb
    verilator = subprocess.run(["verilator", "--version"], capture_output=True,
                               text=True).stdout.strip()
    return {"verilator": verilator, "cocotb": cocotb.__version__}


def run(ot: Path, build: Path, seeds: list[int]) -> dict:
    from cocotb.runner import get_runner

    gen = build / "gen"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "pinmux_target_cfg.svh").write_text(
        extract_target_cfg((ot / CHIP).read_text(encoding="utf-8")), encoding="utf-8")
    work_root = build / "fusesoc"
    eda = fusesoc_setup(ot, work_root)
    sources, includes = file_lists(eda, work_root)

    runner = get_runner("verilator")
    runner.build(
        verilog_sources=sources,
        includes=[str(gen)] + includes,
        hdl_toplevel="tb_top",
        build_args=["-Wno-fatal", "-Wno-lint", "-Wno-style",
                    "--x-assign", "unique", "--x-initial", "unique"],
        build_dir=str(build / "sim"),
        timescale=("1ns", "1ps"),
        always=True,
    )
    per_seed = {}
    for seed in seeds:
        test_dir = build / f"seed{seed}"
        test_dir.mkdir(parents=True, exist_ok=True)
        observed = test_dir / "observed.json"
        observed.unlink(missing_ok=True)
        results = runner.test(
            test_module=TEST_MODULE,
            hdl_toplevel="tb_top",
            build_dir=str(build / "sim"),
            test_dir=str(test_dir),
            results_xml=str(test_dir / "results.xml"),
            plusargs=["+verilator+rand+reset+2", f"+verilator+seed+{seed}"],
            extra_env={"OT_ROOT": str(ot), "OBSERVED_JSON": str(observed),
                       "RANDOM_SEED": str(seed)},
        )
        per_seed[str(seed)] = {
            "tests": test_outcomes(Path(results)),
            "observed": json.loads(observed.read_text(encoding="utf-8")) if observed.exists() else {},
        }
    return per_seed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--opentitan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--build", type=Path, default=REPO / "build" / "behavior" / "pinmux_outsel_reset")
    ap.add_argument("--seed", type=int, action="append", dest="seeds")
    ap.add_argument("--faulty", action="store_true")
    ap.add_argument("--expect", type=Path)
    args = ap.parse_args()
    ot = args.opentitan.resolve()
    seeds = args.seeds or [1, 2, 3]

    revision = revision_of_case()
    actual = checkout_revision(ot)
    if actual and actual != revision:
        print(f"OpenTitan checkout is at {actual}, case 001 records {revision}", file=sys.stderr)
        return 1

    reg_top = ot / REG_TOP
    original = reg_top.read_text(encoding="utf-8")
    variant = "unchanged"
    build = args.build
    if args.faulty:
        expected = n_mio_pads((ot / REG_PKG).read_text(encoding="utf-8"))
        reg_top.write_text(make_faulty(original, expected), encoding="utf-8")
        variant = (f"faulty copy: the reset value of all {expected} MIO_OUTSEL registers in "
                   f"{REG_TOP} changed from 2 to 0")
        build = build.with_name(build.name + "_faulty")
    try:
        per_seed = run(ot, build, seeds)
    finally:
        reg_top.write_text(original, encoding="utf-8")

    result = {
        "opentitan_revision": revision,
        "design": variant,
        "tools": tool_versions(),
        "conditions": CONDITIONS,
        "seeds": per_seed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    want = FAULTY_EXPECTED if args.faulty else {t: "pass" for t in TESTS}
    ok = True
    for seed, r in per_seed.items():
        print(f"seed {seed}: {r['tests']}")
        if r["tests"] != want:
            print(f"seed {seed}: expected {want}", file=sys.stderr)
            ok = False
    if args.expect:
        committed = json.loads(args.expect.read_text(encoding="utf-8"))
        for key in ("opentitan_revision", "design", "conditions", "seeds"):
            if committed.get(key) != result[key]:
                print(f"'{key}' differs from {args.expect}", file=sys.stderr)
                ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
