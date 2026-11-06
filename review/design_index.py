#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Reset values of every register and field of a module, read from its register RTL.

reggen generates <block>_reg_top.sv from the module's register description. Each register
starts with a comment "// R[<register>]: V(<external>)", each field of a multi-field
register with "//   F[<field>]: <msb>:<lsb>", and each stored field is a prim_subreg
instance whose RESVAL parameter is the reset value. Registers implemented outside the
register block (V(True)) have no RESVAL there; their reset values come from the
<PREFIX>_<REGISTER>[_<FIELD>]_RESVAL parameters of <block>_reg_pkg.sv.

Values found here are generated from the same register description as registers.md, so
they are not independent of it; they are what the hardware resets to.

Uses only the Python standard library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

TOPS = ("top_earlgrey", "top_darjeeling", "top_englishbreakfast")

R_RE = re.compile(r"^\s*// R\[(\w+)\]: V\((True|False)\)")
F_RE = re.compile(r"^\s*//\s+F\[(\w+)\]: (\d+):(\d+)")
DW_RE = re.compile(r"\.DW\s*\(\s*(\d+)\s*\)")
RESVAL_RE = re.compile(r"\.RESVAL\s*\(\s*\d+'h\s*([0-9a-fA-F_]+)\s*\)")
INST_RE = re.compile(r"^\s*\)\s*u_(\w+)\s*\(")
PKG_RESVAL_RE = re.compile(r"parameter logic \[(\d+):0\] (\w+)_RESVAL = \d+'h\s*([0-9a-fA-F_]+);")
PKG_OFFSET_RE = re.compile(r"parameter logic \[[^\]]+\] (\w+)_OFFSET = ")


@dataclass
class Field:
    name: str | None          # None for the single field of a one-field register
    lsb: int | None
    width: int | None
    value: int | None
    file: str
    line: int


@dataclass
class Register:
    name: str
    external: bool
    fields: list[Field] = field(default_factory=list)

    def value(self) -> int | None:
        """Register value after reset: the field value for a one-field register, otherwise
        the fields combined at their bit positions."""
        if len(self.fields) == 1:
            return self.fields[0].value
        if any(f.value is None or f.lsb is None for f in self.fields):
            return None
        return sum(f.value << f.lsb for f in self.fields)

    def width(self) -> int | None:
        if len(self.fields) == 1:
            return self.fields[0].width
        if any(f.lsb is None or f.width is None for f in self.fields):
            return None
        return max(f.lsb + f.width for f in self.fields)


@dataclass
class Entry:
    """One lookup key: a register, or a register and field."""
    key: str
    value: int | None
    width: int | None
    file: str
    line: int


def design_dirs(root: Path, doc_rel: str) -> list[Path]:
    """The rtl directory that holds the register RTL for the module a document describes."""
    parts = doc_rel.split("/")
    if parts[1] == "ip":
        return [root / "hw/ip" / parts[2] / "rtl"]
    if parts[1] == "ip_templates":
        for top in TOPS:
            d = root / "hw" / top / "ip_autogen" / parts[2] / "rtl"
            if d.is_dir():
                return [d]
        return []
    return [root / "hw" / parts[1] / "ip_autogen" / parts[3] / "rtl"]


def parse_reg_top(text: str, rel: str) -> list[Register]:
    regs: list[Register] = []
    cur: Register | None = None
    cur_field: tuple[str, int, int] | None = None
    dw = resval = None
    for no, line in enumerate(text.splitlines(), start=1):
        m = R_RE.match(line)
        if m:
            cur = Register(m.group(1), m.group(2) == "True")
            regs.append(cur)
            cur_field = None
            continue
        m = F_RE.match(line)
        if m and cur is not None:
            cur_field = (m.group(1), int(m.group(2)), int(m.group(3)))
            if cur.external:
                msb, lsb = cur_field[1], cur_field[2]
                cur.fields.append(Field(cur_field[0], lsb, msb - lsb + 1, None, rel, no))
            continue
        m = DW_RE.search(line)
        if m:
            dw = int(m.group(1))
        m = RESVAL_RE.search(line)
        if m:
            resval = (int(m.group(1).replace("_", ""), 16), no)
        m = INST_RE.match(line)
        if m and cur is not None and resval is not None:
            name, lsb = (cur_field[0], cur_field[2]) if cur_field else (None, None)
            cur.fields.append(Field(name, lsb, dw, resval[0], rel, resval[1]))
            dw = resval = None
            cur_field = None
    return regs


def fill_external(regs: list[Register], pkg_text: str, rel: str) -> None:
    """Take reset values of external registers from the RESVAL parameters of the package."""
    lines = pkg_text.splitlines()
    params = {}
    for no, line in enumerate(lines, start=1):
        m = PKG_RESVAL_RE.search(line)
        if m:
            params[m.group(2)] = (int(m.group(3).replace("_", ""), 16), int(m.group(1)) + 1, no)
    offsets = [m.group(1) for line in lines for m in [PKG_OFFSET_RE.search(line)] if m]
    for reg in regs:
        if not reg.external:
            continue
        up = reg.name.upper()
        prefixes = {o[: -len(up) - 1] for o in offsets if o.endswith("_" + up)}
        for prefix in prefixes:
            for f in reg.fields:
                name = f"{prefix}_{up}_{f.name.upper()}" if f.name else f"{prefix}_{up}"
                if name in params:
                    f.value, f.width, f.line, f.file = params[name][0], params[name][1], params[name][2], rel
            if not reg.fields and f"{prefix}_{up}" in params:
                v, w, no = params[f"{prefix}_{up}"]
                reg.fields.append(Field(None, 0, w, v, rel, no))


class DesignIndex:
    """Reset values of the registers of one module, looked up by the names documents use."""

    def __init__(self, entries: list[Entry]):
        self.entries = {e.key: e for e in entries}

    @classmethod
    def for_document(cls, root: Path, doc_rel: str) -> "DesignIndex":
        entries: list[Entry] = []
        for d in design_dirs(root, doc_rel):
            for top in sorted(d.glob("*_reg_top.sv")):
                rel = top.relative_to(root).as_posix()
                regs = parse_reg_top(top.read_text(encoding="utf-8"), rel)
                pkg = top.with_name(top.name.replace("_reg_top.sv", "_reg_pkg.sv"))
                if pkg.is_file():
                    fill_external(regs, pkg.read_text(encoding="utf-8"),
                                  pkg.relative_to(root).as_posix())
                entries.extend(entries_of(regs))
        return cls(entries)

    def lookup(self, name: str) -> list[Entry]:
        """Entries a written name refers to: the exact register or register_field, or every
        instance of a multi-register (name_0, name_1, ...)."""
        key = normalize(name)
        if not key:
            return []
        if key in self.entries:
            return [self.entries[key]]
        reg, _, fld = key.partition(".")
        if fld:
            pat = re.compile(rf"^{re.escape(reg)}(?:_\d+)?\.{re.escape(fld)}(?:_\d+)?$")
            found = [e for k, e in self.entries.items() if pat.match(k)]
            if found:
                return found
            # A one-field register has no separate field entry: use the register, but only
            # if no instance of it has named fields.
            regs = self.lookup(reg)
            named = re.compile(rf"^{re.escape(reg)}(?:_\d+)?\.")
            if regs and not any(named.match(k) for k in self.entries):
                return regs
            return []
        pat = re.compile(rf"^{re.escape(reg)}_\d+$")
        return [e for k, e in self.entries.items() if pat.match(k)]

    def fields_of(self, key: str) -> list[Entry]:
        return [e for k, e in self.entries.items() if k.startswith(key + ".")]

    def near(self, name: str) -> list[str]:
        """Names close to a written name that is not found as written: registers that end
        with it, or fields of the named register made of the same words in another order."""
        norm = normalize(name)
        reg, _, fld = norm.partition(".")
        if fld:
            words = set(fld.split("_"))
            regs = {re.sub(r"_\d+$", "", e.key.split(".")[0]) for e in self.lookup(reg)}
            fields = sorted({f"{r}.{_base(k.split('.')[1])}"
                             for r in regs for k in self.entries
                             if k.startswith(r) and "." in k
                             and set(_base(k.split(".")[1]).split("_")) == words})
            if fields:
                return fields[:5]
        key = norm.replace(".", "_")
        base = re.sub(r"_\d+$", "", key)
        names = sorted({re.sub(r"_\d+$", "", k) for k in self.entries
                        if "." not in k and (k.endswith("_" + key) or k.endswith("_" + base)
                                             or re.match(rf"^\w+_{re.escape(base)}_\d+$", k))})
        return names[:5]


def entries_of(regs: list[Register]) -> list[Entry]:
    out = []
    for reg in regs:
        if not reg.fields:
            continue
        first = reg.fields[0]
        out.append(Entry(reg.name, reg.value(), reg.width(), first.file, first.line))
        for f in reg.fields:
            if f.name:
                out.append(Entry(f"{reg.name}.{f.name}", f.value, f.width, f.file, f.line))
    return out


def _base(name: str) -> str:
    """A name without a trailing multi-register index."""
    return re.sub(r"_\d+$", "", name)


def normalize(name: str) -> str:
    """Lower-case register name; register.field kept with a dot; indices like [*] dropped."""
    name = re.sub(r"\[[^\]]*\]", "", name.strip().strip("`")).lower()
    name = re.sub(r"^\w+_reg2hw\.", "", name)
    return name if re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?", name) else ""
