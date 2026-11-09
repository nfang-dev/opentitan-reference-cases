#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Expected register behavior of an IP, read with OpenTitan's own register tool (reggen).

The expected values come from the IP's register description (<ip>.hjson) through reggen,
the library OpenTitan uses to generate its register RTL, documentation and verification
models, so the tests check the hardware against the specification as OpenTitan reads it.

Exclusions follow OpenTitan's own tags ("excl:<test>:<kind>" on a register or field), with
the bit encodings of hw/dv/sv/dv_base_reg/dv_base_reg_pkg.sv, so a register OpenTitan's
own register tests leave out is left out here too.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# csr_test_type_e and csr_excl_type_e in dv_base_reg_pkg.sv
TESTS = {"CsrHwResetTest": 0x1, "CsrRwTest": 0x2, "CsrBitBashTest": 0x4,
         "CsrAliasingTest": 0x8, "CsrMemWalkTest": 0x10, "CsrNonInitTests": 0xE,
         "CsrAllTests": 0xF}
EXCLS = {"CsrNoExcl": 0x0, "CsrExclInitCheck": 0x1, "CsrExclWriteCheck": 0x2,
         "CsrExclCheck": 0x3, "CsrExclWrite": 0x4, "CsrExclAll": 0x7}
INIT_CHECK, WRITE_CHECK, WRITE = 0x1, 0x2, 0x4


def excluded(tags: list[str], test: str, kind: int) -> bool:
    for tag in tags:
        parts = tag.split(":")
        if len(parts) == 3 and parts[0] == "excl":
            if TESTS.get(parts[1], 0) & TESTS[test] and EXCLS.get(parts[2], 0) & kind:
                return True
    return False


def load(root: Path, hjson: str) -> dict:
    sys.path.insert(0, str(root / "util"))
    from reggen.ip_block import IpBlock  # noqa: E402
    block = IpBlock.from_path(str(root / hjson), [])
    if None not in block.reg_blocks:
        raise ValueError(f"{hjson}: no unnamed register interface")
    regs = []
    for r in block.reg_blocks[None].flat_regs:
        regs.append({
            "name": r.name,
            "offset": r.offset,
            "hwext": bool(r.hwext),
            "shadowed": bool(r.shadowed),
            "regwen": r.regwen,
            "tags": list(r.tags),
            "fields": [{
                "name": f.name,
                "lsb": f.bits.lsb,
                "width": f.bits.width(),
                "swaccess": f.swaccess.key,
                "hwaccess": f.hwaccess.key,
                "resval": f.resval if isinstance(f.resval, int) and not isinstance(f.resval, bool)
                else (int(f.resval) if isinstance(f.resval, bool) else None),
                "tags": list(getattr(f, "tags", []) or []),
            } for f in r.fields],
        })
    return {"ip": block.name, "hjson": hjson, "registers": regs}


if __name__ == "__main__":
    print(json.dumps(load(Path(sys.argv[1]), sys.argv[2]), indent=1))
