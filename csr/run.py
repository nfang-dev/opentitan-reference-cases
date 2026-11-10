#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Run the register tests on complete OpenTitan IPs with Verilator and cocotb.

  run.py --opentitan DIR --out DIR [--ip NAME]... [--seed N]... [--mutate KIND] [--expect DIR]

For each IP in ips.json: export the register model with reggen, generate the harness,
list the IP's sources with FuseSoC, build with Verilator, run the tests and write
<out>/<ip>.json.

--mutate makes one deliberate change to a copy of the IP's register RTL, runs the tests and
restores the file. The run then succeeds only if the tests detect the change:
  resval  the reset value of one field          -> hw_reset must fail
  access  one read-write field made read-only   -> rw must fail
  regwen  ALERT_TEST's write no longer gated    -> alert_test_lock must fail
  lock    one register no longer gated by its lock register -> regwen_lock must fail
          (only for IPs that have lock registers)
--expect compares the new observations with committed ones.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import gen_harness  # noqa: E402
import regmodel  # noqa: E402

TESTS = ["hw_reset", "rw", "regwen_lock", "alert_test_lock"]
MUTATION_DETECTED_BY = {"resval": "hw_reset", "access": "rw", "regwen": "alert_test_lock",
                        "lock": "regwen_lock"}


class NotApplicable(ValueError):
    """The IP has nothing this mutation can change (for example, no lock registers)."""


def config() -> dict:
    return {c["ip"]: c for c in json.loads((HERE / "ips.json").read_text(encoding="utf-8"))["ips"]}


def revision() -> str:
    return json.loads((HERE / "ips.json").read_text(encoding="utf-8"))["opentitan_revision"]


def reg_top(ot: Path, cfg: dict) -> Path:
    return ot / Path(cfg["top"]).parent / f"{cfg['ip']}_reg_top.sv"


# ------------------------------------------------------------------ mutations

def _instance_params(text: str, inst: str) -> tuple[int, int]:
    """Span of the parameter block of the prim_subreg instance u_<inst>."""
    end = text.index(f") u_{inst} (")
    start = text.rindex("prim_subreg", 0, end)
    return start, end


def mutate(text: str, model: dict, kind: str) -> tuple[str, str]:
    """Apply one deliberate change; returns the new text and a description."""
    if kind == "lock":
        for reg in model["registers"]:
            if not reg["regwen"] or reg["hwext"]:
                continue
            p, lock = reg["name"].lower(), reg["regwen"].lower()
            for old, new in (
                    (f"assign {p}_gated_we = {p}_we & {lock}_qs;", f"assign {p}_gated_we = {p}_we;"),
                    (f"assign {p}_gated_we = {p}_we && {lock}_qs;", f"assign {p}_gated_we = {p}_we;")):
                if old in text:
                    return text.replace(old, new), f"{reg['name']} writes no longer gated by {reg['regwen']}"
            inst = f") u_{p}_cdc ("
            if inst in text:
                start = text.index(inst)
                end = text.index(");", start)
                block = text[start:end]
                old = f".src_regwen_i ({lock}_qs)"
                if old in block:
                    block = block.replace(old, ".src_regwen_i (1'b1)")
                    return text[:start] + block + text[end:], \
                        f"{reg['name']} writes no longer gated by {reg['regwen']}"
        raise NotApplicable("no register protected by a lock register")
    if kind == "regwen":
        old = "assign alert_test_gated_we = alert_test_we && alert_test_regwen_qs;"
        if old not in text:
            raise ValueError("no ALERT_TEST write gating found")
        return text.replace(old, "assign alert_test_gated_we = alert_test_we;"), \
            "ALERT_TEST writes no longer gated by its regwen field"
    for reg in model["registers"]:
        if reg["hwext"] or reg["shadowed"] or regmodel.excluded(reg["tags"], "CsrAllTests", 7):
            continue
        for f in reg["fields"]:
            if f["swaccess"] != "rw" or f["hwaccess"] in ("hrw", "hwo") or f["tags"]:
                continue
            inst = reg["name"].lower() if len(reg["fields"]) == 1 else \
                f"{reg['name'].lower()}_{f['name'].lower()}"
            if f") u_{inst} (" not in text:
                continue
            s, e = _instance_params(text, inst)
            block = text[s:e]
            if kind == "resval":
                m = re.search(r"\.RESVAL\s*\(\s*(\d+)'h\s*([0-9a-fA-F_]+)\s*\)", block)
                if not m or kind == "resval" and regmodel.excluded(reg["tags"], "CsrHwResetTest", 1):
                    continue
                new_val = int(m.group(2).replace("_", ""), 16) ^ 1
                block2 = block[:m.start()] + f".RESVAL  ({m.group(1)}'h{new_val:x})" + block[m.end():]
                desc = f"reset value of {reg['name']}.{f['name']} changed from " \
                       f"{int(m.group(2).replace('_', ''), 16)} to {new_val}"
            else:
                if "SwAccessRW)" not in block:
                    continue
                block2 = block.replace("SwAccessRW)", "SwAccessRO)")
                desc = f"{reg['name']}.{f['name']} made read-only"
            return text[:s] + block2 + text[e:], desc
    raise ValueError(f"no field found for mutation {kind}")


# ------------------------------------------------------------------ build and run

def file_lists(eda: dict, work_root: Path) -> tuple[list[str], list[str]]:
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


def test_outcomes(results_xml: Path) -> dict:
    out = {}
    for case in ET.parse(results_xml).getroot().iter("testcase"):
        failed = case.find("failure") is not None or case.find("error") is not None
        out[case.get("name")] = "fail" if failed else "pass"
    return out


def run_ip(ot: Path, cfg: dict, build: Path, seeds: list[int]) -> dict:
    from cocotb.runner import get_runner

    ip = cfg["ip"]
    model = regmodel.load(ot, cfg["hjson"])
    gen = build / "gen"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "model.json").write_text(json.dumps(model, indent=1), encoding="utf-8")

    top = ot / cfg["top"]
    packages = {p.stem: p.read_text(encoding="utf-8") for p in top.parent.glob("*_pkg.sv")}
    ip_core = gen_harness.core_name((ot / cfg["core"]).read_text(encoding="utf-8"))
    sv, ports = gen_harness.harness(ip, top.read_text(encoding="utf-8"), packages)
    for port, value in cfg.get("tie", {}).items():
        sv, n = re.subn(rf"(\.{port} \()[^)]*(\))", rf"\g<1>{value}\g<2>", sv)
        sv = sv.replace(f"//   {port}: '0", f"//   {port}: {value}")
        if n != 1:
            raise ValueError(f"{ip}: cannot tie {port}")
    (gen / f"tb_{ip}.sv").write_text(sv, encoding="utf-8")
    (gen / f"tb_{ip}.core").write_text(gen_harness.core_file(ip, ip_core), encoding="utf-8")

    work_root = build / "fusesoc"
    if work_root.exists():
        shutil.rmtree(work_root)
    subprocess.run(["fusesoc", "--cores-root", str(ot), "--cores-root", str(gen), "run",
                    "--setup", "--target", "default", "--tool", "verilator",
                    "--work-root", str(work_root),
                    "--mapping", "lowrisc:prim_generic:all:0.1",
                    f"nfang:csr:tb_{ip}:0.1"], check=True)
    import yaml
    eda = yaml.safe_load(next(work_root.glob("*.eda.yml")).read_text(encoding="utf-8"))
    sources, includes = file_lists(eda, work_root)

    runner = get_runner("verilator")
    runner.build(verilog_sources=sources, includes=includes, hdl_toplevel=f"tb_{ip}",
                 build_args=["-Wno-fatal", "-Wno-lint", "-Wno-style",
                             "--x-assign", "unique", "--x-initial", "unique"],
                 build_dir=str(build / "sim"), timescale=("1ns", "1ps"), always=True)
    per_seed = {}
    for seed in seeds:
        test_dir = build / f"seed{seed}"
        test_dir.mkdir(parents=True, exist_ok=True)
        observed = test_dir / "observed.json"
        observed.unlink(missing_ok=True)
        results = runner.test(
            test_module="test_csr", hdl_toplevel=f"tb_{ip}", build_dir=str(build / "sim"),
            test_dir=str(test_dir), results_xml=str(test_dir / "results.xml"),
            plusargs=["+verilator+rand+reset+2", f"+verilator+seed+{seed}"],
            extra_env={"CSR_MODEL": str(gen / "model.json"), "CSR_PORTS": json.dumps(ports),
                       "CSR_RESULTS": str(observed), "RANDOM_SEED": str(seed),
                       "PYTHONPATH": str(HERE)})
        per_seed[str(seed)] = {
            "tests": test_outcomes(Path(results)),
            "observed": json.loads(observed.read_text(encoding="utf-8")) if observed.exists() else {},
        }
    return {"ip": ip, "registers": len(model["registers"]), "harness_ties": [
        line[4:] for line in sv.splitlines() if line.startswith("//   ")], "seeds": per_seed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--opentitan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--build", type=Path, default=REPO / "build" / "csr")
    ap.add_argument("--ip", action="append", dest="ips")
    ap.add_argument("--seed", type=int, action="append", dest="seeds")
    ap.add_argument("--mutate", choices=sorted(MUTATION_DETECTED_BY))
    ap.add_argument("--expect", type=Path)
    args = ap.parse_args()
    ot = args.opentitan.resolve()
    cfgs = config()
    ips = args.ips or list(cfgs)
    seeds = args.seeds or [1, 2]
    args.out.mkdir(parents=True, exist_ok=True)
    ok = True
    for ip in ips:
        cfg = cfgs[ip]
        build = args.build / (ip + (f"_{args.mutate}" if args.mutate else ""))
        rt = reg_top(ot, cfg)
        original = rt.read_text(encoding="utf-8")
        change = "unchanged"
        if args.mutate:
            try:
                text, change = mutate(original, regmodel.load(ot, cfg["hjson"]), args.mutate)
            except NotApplicable as e:
                print(f"{ip}: mutation {args.mutate} not applicable: {e}")
                continue
            rt.write_text(text, encoding="utf-8")
        try:
            result = run_ip(ot, cfg, build, seeds)
        finally:
            rt.write_text(original, encoding="utf-8")
        result = {"opentitan_revision": revision(), "design": change, **result}
        name = f"{ip}_{args.mutate}.json" if args.mutate else f"{ip}.json"
        (args.out / name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        for seed, r in result["seeds"].items():
            print(f"{ip} seed {seed}: {r['tests']}")
            if args.mutate:
                if r["tests"].get(MUTATION_DETECTED_BY[args.mutate]) != "fail":
                    print(f"{ip}: mutation '{change}' not detected", file=sys.stderr)
                    ok = False
            elif any(v != "pass" for v in r["tests"].values()):
                ok = False
        if args.expect and (args.expect / name).exists():
            committed = json.loads((args.expect / name).read_text(encoding="utf-8"))
            for key in ("opentitan_revision", "design", "seeds"):
                if committed.get(key) != result[key]:
                    print(f"{name}: '{key}' differs from the committed result", file=sys.stderr)
                    ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
