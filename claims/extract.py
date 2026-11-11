#!/usr/bin/env python3
# Copyright 2026 Nan Fang
# SPDX-License-Identifier: Apache-2.0
"""Ask an open-weights language model which register facts each selected sentence states.

The model reads one sentence at a time (with its IP, its section heading, and the names of
the registers and fields it mentions) and answers in a fixed JSON form, enforced by a
grammar during generation. It is asked for four kinds of fact only, each of which a
program can check against the register description:

  reset_value      the value a register or field has after reset
  software_access  read-write, read-only, write-1-to-clear, ...
  width_bits       the number of bits of a field or register
  locked_by        the register that, once cleared, blocks writes to this one

The model is told to use only what the sentence states. It is not given reset values,
access types or locks, so it cannot copy the answer from the description.

Generation is greedy (temperature 0). The model file, its checksum, the llama.cpp binding
version and a checksum of the prompt are recorded with the answers.

Needs llama-cpp-python and a GGUF model file (see claims/README.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

PROPERTIES = ["reset_value", "software_access", "width_bits", "locked_by"]
ACCESS_WORDS = ["read-write", "read-only", "write-only", "write-1-to-clear", "write-1-to-set",
                "write-0-to-clear", "read-to-clear"]

SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "register": {"type": "string"},
                    "field": {"type": "string"},
                    "property": {"type": "string", "enum": PROPERTIES},
                    "value": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["register", "field", "property", "value", "quote"],
            },
        },
    },
    "required": ["claims"],
}

PROMPT_VERSION = 3

SYSTEM = f"""You read one sentence from the hand-written documentation of a hardware block and \
list the register facts that the sentence states.

Record a claim only for these four properties, and only when the sentence itself states it:
- reset_value: the value a register or field has after reset. The sentence must say so with \
words such as "reset", "default", "initial" or "power-on", for example "resets to 0", "is 1 \
by default", "is disabled after reset". Value: a number, decimal or 0x hexadecimal. For a \
one-bit field, enabled or set is 1, disabled or cleared is 0.
- software_access: the access type of a register or field. The sentence must name the type \
("read-only", "write-only", "read/write") or say what a software write does to the register's \
own value ("writing 1 clears it", "write 0 to acknowledge it", "writes are ignored"). Value: \
one of {", ".join(ACCESS_WORDS)}.
- width_bits: the number of bits of the register or field itself, for example "the 12-bit \
prescaler field". Value: a number.
- locked_by: a register that, once cleared, stops software from writing this register, for \
example "writes to X are disabled by clearing Y". Value: the name of the locking register.

Rules:
- Use only what the sentence states. Do not use your own knowledge of this or similar \
hardware, and do not guess a property from what a register is used for.
- A value that software writes as a step of a procedure ("write 0x1 to X to enable it") is \
not a reset value.
- Saying that software reads or writes a register does not state its access type. Setting or \
clearing a field as a step of a procedure is how any read-write field is written: it states an \
access type only if the sentence says that the write has a special effect on the field, such \
as clearing it when 1 is written.
- A lock register does not lock itself: locked_by is a property of the registers it protects, \
and only of those the sentence names.
- The width of data, of a part of a write, or of a value range is not the width of a field.
- A sentence that only says what software should do, or how the hardware behaves, has no \
claims. Most sentences have none.
- register: a register name from the list given with the sentence. field: a field name from \
that list, or "" when the claim is about the whole register.
- quote: the exact words of the sentence that state the claim, including the words that name \
the property or its effect ("reset", "default", "read-only", "clear", "acknowledge", "12-bit", \
"lock"). A program checks every claim and rejects a quote without such words.
- If the sentence states none of the four properties, answer {{"claims": []}}.

Examples (from an invented block):

Block: demo. Registers named: CFG (fields: en, mode); STATUS (fields: busy)
Sentence: `CFG.en` resets to 1, and `STATUS` is read-only.
Answer: {{"claims": [{{"register": "CFG", "field": "en", "property": "reset_value", \
"value": "1", "quote": "`CFG.en` resets to 1"}}, {{"register": "STATUS", "field": "", \
"property": "software_access", "value": "read-only", "quote": "`STATUS` is read-only"}}]}}

Block: demo. Registers named: EVENT (fields: flag); CFG (fields: en, mode); LOCK (fields: lock)
Sentence: To clear `EVENT.flag`, write 1 to it; the 4-bit `mode` field of `CFG` cannot be \
changed once `LOCK` is cleared.
Answer: {{"claims": [{{"register": "EVENT", "field": "flag", "property": "software_access", \
"value": "write-1-to-clear", "quote": "To clear `EVENT.flag`, write 1 to it"}}, \
{{"register": "CFG", "field": "mode", "property": "width_bits", "value": "4", \
"quote": "the 4-bit `mode` field"}}, {{"register": "CFG", "field": "mode", \
"property": "locked_by", "value": "LOCK", "quote": "cannot be changed once `LOCK` is cleared"}}]}}

Block: demo. Registers named: CFG (fields: en, mode); STATUS (fields: busy)
Sentence: Write `0x1` to `CFG.en` to start, then read `STATUS` until it is 0.
Answer: {{"claims": []}}

Block: demo. Registers named: CFG (fields: en, mode); LOCK (fields: lock)
Sentence: Stop the block by clearing `CFG.en`, and lock the configuration by writing 0 to `LOCK`.
Answer: {{"claims": []}}

Block: demo. Registers named: DATA (fields: data)
Sentence: The upper 8 bits of a `DATA` write select which of the lower 8 bits change.
Answer: {{"claims": []}}
"""


def user_message(s: dict) -> str:
    regs = "; ".join(f"{r} (fields: {', '.join(f)})" for r, f in s["registers"].items())
    return (f"Block: {s['ip']}. Section: {s['heading'] or '(none)'}. Registers named: {regs}\n"
            f"Sentence: {s['text']}\nAnswer:")


def prompt_sha256() -> str:
    text = SYSTEM + json.dumps(SCHEMA, sort_keys=True) + user_message(
        {"ip": "", "heading": "", "registers": {}, "text": ""})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse(raw: str) -> tuple[list[dict], str | None]:
    """The claims in a model answer, and an error if the answer is not in the fixed form."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [], f"not JSON: {e}"
    claims = data.get("claims") if isinstance(data, dict) else None
    if not isinstance(claims, list):
        return [], "no claims list"
    out = []
    for c in claims:
        if not isinstance(c, dict) or c.get("property") not in PROPERTIES:
            return [], f"malformed claim: {c!r}"
        out.append({k: str(c.get(k, "")).strip() for k in
                    ("register", "field", "property", "value", "quote")})
    return out, None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sentences", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True, help="GGUF file (first part if split)")
    ap.add_argument("--model-name", required=True, help="where the model file comes from")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0, help="only the first N sentences")
    ap.add_argument("--threads", type=int, default=0)
    args = ap.parse_args(argv)

    import llama_cpp  # imported here so the rest of the module needs no third-party package

    sentences = json.loads(args.sentences.read_text(encoding="utf-8"))
    todo = sentences["sentences"][:args.limit or None]
    llm = llama_cpp.Llama(model_path=str(args.model), n_ctx=4096, seed=0, verbose=False,
                          n_threads=args.threads or None)
    model_files = sorted(args.model.parent.glob(args.model.name.split("-00001-of-")[0] + "*"))
    meta = {
        "opentitan_revision": sentences["opentitan_revision"],
        "model": args.model_name,
        "model_files": {p.name: file_sha256(p) for p in model_files},
        "llama_cpp_python": llama_cpp.__version__,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "temperature": 0,
    }
    answers = []
    for i, s in enumerate(todo, 1):
        t0 = time.time()
        out = llm.create_chat_completion(
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": user_message(s)}],
            response_format={"type": "json_object", "schema": SCHEMA},
            temperature=0.0, top_k=1, max_tokens=600, seed=0)
        raw = out["choices"][0]["message"]["content"] or ""
        claims, error = parse(raw)
        answers.append({"id": s["id"], "ip": s["ip"], "claims": claims, "error": error,
                        "raw": raw, "seconds": round(time.time() - t0, 1)})
        print(f"[{i}/{len(todo)}] {s['id']}: {len(claims)} claims"
              + (f" ({error})" if error else ""), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Timings vary between runs; they are kept apart from the answers so that the answers of
    # two runs can be compared directly.
    timings = {a["id"]: a.pop("seconds") for a in answers}
    timings["total"] = round(sum(timings.values()), 1)
    args.out.write_text(json.dumps({**meta, "answers": answers}, indent=1) + "\n",
                        encoding="utf-8")
    (args.out.with_suffix(".timings.json")).write_text(json.dumps(timings, indent=1) + "\n",
                                                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
