# OpenTitan reference cases

Hand-checked reference cases that link a written requirement in [OpenTitan](https://github.com/lowRISC/opentitan)'s documentation to the design code that implements it.

Each case records, for one statement in a hand-written document:

- the statement, with file and line;
- the design evidence for the settings it describes, with file and line;
- which pieces of evidence are generated from the same input, and so are not independent;
- one **claim** per setting: what the statement says, what the design shows, and a recorded label (**agrees**, **disagrees** or **unresolved**);
- the conditions under which the claim applies, ambiguities, missing information and what is out of scope.

Every case is pinned to an OpenTitan revision and comes with a script that anyone can run to confirm each piece of evidence and recompute each claim's outcome.
The cases are meant to serve as labeled examples for evaluating later automated checks and requirement search.

## Cases

| Case | Module | Statement | Claims |
|---|---|---|---|
| [001](cases/001-pinmux-mio-outsel-reset/README.md) | pinmux | MIO output select value after reset | 2 agree, 1 disagrees |
| [002](cases/002-csrng-int-state-enables-reset/README.md) | csrng | Internal-state read, write and halt enables after reset | 2 agree, 1 unresolved |
| [003](cases/003-pinmux-pad-sleep-enable-reset/README.md) | pinmux | Pad sleep behavior enable after reset | 2 agree (control case) |

All cases use OpenTitan revision [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03).

## Method

1. **Choose a statement** in a hand-written (not generated) document about a setting's value after reset.
2. **Freeze the revision** of OpenTitan used for the case.
3. **Identify the settings** the statement covers and translate the statement into a value for each, recording any parameter the translation depends on.
4. **Locate the design evidence**: the register definition, every generated register flop, and the logic that gives the value its meaning. If a setting the statement names does not exist, record that as evidence too.
5. **Record what is generated from the same input.** In OpenTitan, `reggen` produces both the register RTL and `registers.md` from one `.hjson` file, so their agreement is expected and is not treated as independent evidence.
6. **Label each claim** as agrees, disagrees or unresolved, and record the conditions, ambiguities, missing information and what is out of scope. Check the history of the documents before labeling a mismatch, since documentation can describe work that is not merged yet.
7. **Write `case.json`** and confirm it with `tools/check_case.py`.

[`docs/method-notes.md`](docs/method-notes.md) records what had to change in the method when it was applied to a second module.

## Re-running the cases

Requires Python 3.10 or newer and git; no other dependencies.

```sh
# Fetch only the OpenTitan files the cases refer to, at the recorded revision (a few MB).
./tools/fetch_opentitan.sh opentitan

# Confirm every piece of evidence and recompute every claim.
python3 tools/check_case.py cases/*/case.json --opentitan opentitan
```

`check_case.py` exits with 0 when all evidence is confirmed and every outcome matches its recorded label, and with 2 when a case needs review: evidence cannot be found at the given checkout, or an outcome no longer matches its label (for example, after the documentation is fixed upstream).
With `--fail-on-inconsistency` it exits with 1 when any claim does not agree.
If the checkout is at a different revision, the script searches for each quoted line and reports where it moved.

## Tests

```sh
python3 -m unittest discover -s tests -v
# Also check the cases against a real checkout:
OPENTITAN_DIR=opentitan python3 -m unittest discover -s tests -v
```

CI runs both on every push.

## Upstream

- Case 001: documentation fix proposed in [lowRISC/opentitan#32161](https://github.com/lowRISC/opentitan/pull/32161).
- Case 002: no change proposed; the documentation may describe work in progress.

## License

Apache-2.0. Copyright 2026 Nan Fang.
Not affiliated with or endorsed by lowRISC or the OpenTitan project.
