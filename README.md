# OpenTitan reference cases

Hand-checked reference cases that link a written requirement in [OpenTitan](https://github.com/lowRISC/opentitan)'s documentation to the design code that implements it.

Each case records, for one setting inside the chip:

- the written statements about its value after reset, with file and line;
- the design evidence for its actual reset value, with file and line;
- which pieces of evidence are generated from the same input, and so are not independent;
- the expected value, the conditions under which it applies, ambiguities and what is out of scope;
- the finding: whether the documentation and the design agree.

Every case is pinned to an OpenTitan revision and comes with a script that anyone can run to confirm each piece of evidence and the finding.
The cases are meant to serve as labeled examples for evaluating later automated checks and requirement search.

## Cases

| Case | Module | Setting | Result |
|---|---|---|---|
| [001](cases/001-pinmux-mio-outsel-reset/README.md) | pinmux | `MIO_OUTSEL_<k>.OUT` after reset | Documentation table disagrees with the design and with its own text |

## Method

1. **Choose a setting** with a definite value after reset, and find a statement about that value in a document that is written by hand rather than generated.
2. **Freeze the revision** of OpenTitan used for the case.
3. **Locate the design evidence**: the register definition, the generated register RTL and the logic that gives the value its meaning.
4. **Record what is generated from the same input.** In OpenTitan, `reggen` produces both the register RTL and `registers.md` from one `.hjson` file, so their agreement is expected and is not treated as independent evidence.
5. **Record the expected value and its conditions**, plus anything the documents leave unclear and anything the case does not cover.
6. **Write `case.json`** and confirm it with `tools/check_case.py`.

## Re-running a case

Requires Python 3.10 or newer and git; no other dependencies.

```sh
# Fetch only the OpenTitan files the case refers to, at the recorded revision (a few MB).
./tools/fetch_opentitan.sh cases/001-pinmux-mio-outsel-reset/case.json opentitan

# Confirm every piece of evidence and print the finding.
python3 tools/check_case.py cases/001-pinmux-mio-outsel-reset/case.json --opentitan opentitan
```

`check_case.py` exits with 0 when all evidence is confirmed, 2 when evidence cannot be found at the given revision, and, with `--fail-on-inconsistency`, 1 when a written requirement disagrees with the design.
If the checkout is at a different revision, the script searches for each quoted line and reports where it moved.

## Tests

```sh
python3 -m unittest discover -s tests -v
# Also check the cases against a real checkout:
OPENTITAN_DIR=opentitan python3 -m unittest discover -s tests -v
```

CI runs both on every push.

## License

Apache-2.0. Copyright 2026 Nan Fang.
Not affiliated with or endorsed by lowRISC or the OpenTitan project.
