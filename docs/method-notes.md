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

## Case 004 (keymgr_dpe, a module not used while developing the method)

Cases 001 to 003 were written while the method was being developed. Case 004 applies it to keymgr_dpe, which was not used before, to see what has to change for a different kind of statement.

| Area | Cases 001 to 003 | What case 004 needed | Change made |
|---|---|---|---|
| Kind of statement | A register's value after reset. | Whether an operation can repeat something before the next reset. | The setting is encoded as 1 (it can) or 0 (it cannot), and the encoding is written into the case's conditions. The case format and the checker did not change. |
| Meaning of a design value | The value is read from the design file (a reset value). | The design shows an operation and its rejection conditions, not a number. | The value 1 attached to each design line is the case's reading of that line, recorded in its note. The checker confirms that the lines are present at the revision; it does not derive the 1 itself. This is weaker than reading a reset value, and the case says so. |
| Independent evidence | Generated register flops, plus the logic that gives a value its meaning. | The deciding evidence is hand-written control logic (`keymgr_dpe_ctrl.sv`), independent of the documentation. | Recorded which evidence is generated (the register description) and which is hand-written. |
| Conflicting statements | The guide disagreed with the design in one place. | One document makes four statements about the same behavior, and one disagrees with the other three. | Compared the document with an earlier revision to find which statement was updated and which was left behind, and recorded the narrow reading under which the outdated statement could still be read as true. |

## Current set

| Outcome | Claims |
|---|---|
| agrees | 001-C1, 001-C3, 002-C1, 002-C2, 003-C1, 003-C2, 004-C2, 004-C3 |
| disagrees | 001-C2, 004-C1 |
| unresolved | 002-C3 |
