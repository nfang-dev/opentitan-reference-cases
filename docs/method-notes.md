# Method notes

These notes record what changed in the method as it was applied to more cases, as planned: repeat the method on a second module and write down what had to change.

## From case 001 (pinmux) to case 002 (csrng)

Case 001 checked one setting against three statements about it. Case 002 is in a different module and its statement covers three settings at once. Moving to it required these changes.

| Area | Case 001 | What case 002 needed | Change made |
|---|---|---|---|
| Unit of comparison | One setting, one expected value; each statement compared with it. | One sentence covers three settings (read, write and halt enables), each with its own design evidence. | The case format (schema 2) records separate **claims**: a setting, the statements it comes from, the stated value, and the design evidence that decides it. |
| Outcomes | Agree or disagree. | The statement about writing names a register and a control field that do not exist, so it can be neither confirmed nor refuted. | Added a third outcome, **unresolved**, and a field for the **missing information** that would resolve it. |
| Evidence types | A quoted line, or a pattern that must match every register instance. | Showing that a register does not exist. | Added **absent** evidence: a pattern that must not match. |
| Translating the statement into a value | The statement named the value directly ("high-Z", "2"). | "Enabled for all instances" depends on how many instances there are. | Recorded the parameter (`NumApps = 3`) as evidence, so the translation to `0x7` can be checked. |
| Locating repeated text | Each quoted line was unique enough to search for. | `resval: 0x7` appears more than once in `csrng.hjson`, and the register name also appears as a field name. | A design line can be located as the first match **after an anchor** line, such as the register's description. The anchor must be unique, and the checker reports when it is not. |
| Interpreting a mismatch | The surrounding text and the design agreed, so the table was clearly the outlier. | The documentation was added recently, while the module was being changed. | Looked at the commit history of the guide and the register definition before deciding on a label. A static comparison alone cannot tell whether documentation is ahead of an unmerged design change or out of date. |
| Recorded labels | The finding was described in prose. | With several claims per case, the expected outcome of each needs to be explicit. | Each claim has a **label**; the checker fails (exit 2) when a recomputed outcome no longer matches it, for example after the documentation is fixed upstream. |

What carried over unchanged: quoting requirements by file and line from hand-written documents; checking every generated register flop rather than one; stating which evidence is generated from the same source and therefore not independent; and recording conditions, ambiguities and what is out of scope.

## Case 003 (pinmux, agreeing statement)

Case 003 reused the method without further changes. It was chosen because the statement agrees with the design: a set of reference cases needs agreeing statements as well as disagreeing ones, so that a later check can be measured for false alarms as well as for findings.

## Current set

| Outcome | Claims |
|---|---|
| agrees | 001-C1, 001-C3, 002-C1, 002-C2, 003-C1, 003-C2 |
| disagrees | 001-C2 |
| unresolved | 002-C3 |
