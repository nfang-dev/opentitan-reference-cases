# Register facts in the documentation: read by an AI model, checked by programs

The register tests in [`csr/`](../csr/README.md) check the hardware against the register description (`<ip>.hjson`). But engineers also read the hand-written documentation: the README, the theory of operation and the programmer's guide. Sentences there state register facts too, for example "software acknowledges it by writing 0 to `WKUP_CAUSE`". Nothing checks those sentences against the description.

Rules find such facts only when they are written in a fixed form. The [review tool](../review/README.md) finds reset values written with cues like "resets to" or "(default)", and finds none in the documents of the five IPs tested in `csr/`. The facts these documents do state are written in free form.

This part lets an open-weights language model read the sentences, and lets programs do the checking:

```
hand-written docs ──sentences.py──> sentences that name a register (deterministic)
                                        │
                     extract.py: an open-weights model, run on a CPU in CI,
                     answers in a fixed JSON form: register, field, property, value, quote
                                        │
<ip>.hjson ──reggen──> check.py: is the quote in the sentence, and does it state the property?
csr/results ─────────>           does the register exist? does the value match the description?
                                        │
                     results/<prompt>/check.md, every claim reviewed against its sentence
```

The model reads; it does not decide. Every claim it makes is checked by a program, and every claim is also reviewed against its sentence, so that the report can say how often the model reads correctly.

## What the model is asked

For each sentence, the model gets the IP name, the section heading, the sentence, and the names of the registers it mentions with their field names. It is asked for four kinds of fact, each of which a program can check against the description:

| Property | Example | Checked against |
|---|---|---|
| `reset_value` | "`CFG.en` resets to 1" | the field's reset value |
| `software_access` | "writing 1 clears it" | the field's access type (rw1c, ...) |
| `width_bits` | "the 12-bit prescaler field" | the field's width |
| `locked_by` | "cannot be changed once `LOCK` is cleared" | the register's lock register |

It is not given reset values, access types or locks, so it cannot copy the answer from the description. The prompt is in [`extract.py`](extract.py); its examples use an invented block, not OpenTitan. The model is [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) (Apache-2.0), 4-bit quantized, run with llama.cpp at temperature 0, with its answers held to a JSON schema by a grammar. No paid API is used.

## How claims are checked

[`check.py`](check.py), in order:

1. The quote must occur in the sentence (*quote not in sentence*), and contain a word that can state the property: "reset", "default" or "initial" for a reset value; "read-only", "clear", "acknowledge", ... for an access type; "bit" or "width" for a width; "lock", "regwen", "protect", ... for a lock (*quote does not state the property*). This rejects, for example, "writing `0x1` to `CTRL.TX`" as a reset value.
2. The register must be one the sentence names (*register not named in sentence*), and it and the field must exist in the description (*not in description*).
3. The value is compared with the description: *agrees* or *disagrees*. If the description has no single value (no reset value, or fields with different access types), *not checkable*.
4. If the register tests in `csr/` checked the same property in simulation and it passed, the report says that the hardware matches the description too.

Every claim was then reviewed against its sentence: does the sentence state this property, with this value, for this register? The reviews are in `results/<prompt>/review.json`, and each report counts them.

## Results

Five IPs (uart, gpio, rv_timer, aon_timer, i2c), 202 sentences that name a register. All 202 were read through to find the facts they state explicitly: 17, all access types and widths, for example "acknowledges it by software writing 0 to `WKUP_CAUSE`" (write-0-to-clear) and "the 12-bit `WKUP_CTRL.prescaler` field". **All 17 agree with the register description.** No sentence in these documents states a reset value or a lock in a checkable way.

How the model and the checks did:

| | Prompt 1 (trial) | Prompt 2 | Prompt 3 |
|---|---|---|---|
| Sentences read | first 25 | 203 | 202 |
| Claims made | 30 | 109 | 74 |
| Read correctly | 1 | 16 | 17 |
| Explicit facts found | 1 of 1 | 16 of 16 | 17 of 17 |
| Accepted by the checks | 5 | 18 | 25 |
| ... of which read correctly | 1 | 10 | 14 |
| Correct readings rejected by the checks | 0 | 6 | 3 |
| Disagreements with the description | 0 | 4 | 8 |
| ... of which the documentation was wrong | | 0 | 0 |

What this shows:

- **The model finds the facts, and much more that is not there.** It found every explicit fact, but most of its claims were wrong. The common errors: a value written as a step of a procedure taken as a reset value ("write `0x1` to `CTRL.TX`"), a mention of reading or writing a register taken as its access type, a condition ("if `TIMEOUT_CTRL.EN` is deasserted") taken as a value, and once a negation read the wrong way round ("it doesn't clear by writing to the bit" read as write-1-to-clear).
- **The checks do most of the filtering.** Under prompt 2 they rejected 91 of 109 claims; 85 of those were wrong. The instructions alone changed little: on the 25 trial sentences, prompt 2 made 29 claims against prompt 1's 30.
- **Every disagreement was a misreading.** None of the 12 disagreements in prompts 2 and 3 was a documentation error. A disagreement is something for a person to look at, not a finding.
- **The word check trades one error for another.** Prompt 2's quotes often left out the word that states the property, so 6 correct readings were rejected. Prompt 3 asks for those words in the quote: correct readings rejected fell to 3, but more misreadings that contain "clear" passed, and disagreements rose from 4 to 8.

How the prompts were developed: prompt 1 was tried on the first 25 sentences. Prompt 2 was written after reviewing that trial and run on all 203 sentences, so 178 of them had not been seen. Prompt 3 was written after reviewing prompt 2 on all sentences, so its numbers are not a measurement on unseen sentences. Prompt 3 also stopped splitting sentences at colons, which had cut a list item from the register it was about (hence 202 sentences).

The reports: [prompt 1](results/prompt1_trial/check.md), [prompt 2](results/prompt2/check.md), [prompt 3](results/prompt3/check.md).

## Names checked without the model

Two checks on the same documents need no model at all, and run in the same report:

- every field written as `REGISTER.FIELD` is looked up in the description;
- every link to a register's entry in `registers.md` must go to the register its text names.

They found six places where the documentation names something the description does not have. All six are still present on OpenTitan's master branch as of November 10, 2026.

| Where | Written | In the description |
|---|---|---|
| uart theory of operation, lines 159–161 | `STATUS.BREAK` ("the current break status can be read from the `STATUS.BREAK` bit") | STATUS has no break bit: its fields are TXFULL, RXFULL, TXEMPTY, TXIDLE, RXIDLE, RXEMPTY |
| uart theory of operation, lines 160–161 | `INTR_STATE.BREAK` | the interrupt field is `rx_break_err` |
| rv_timer theory of operation, lines 9, 21, 27 | `CFG0.prescaler` | the field is `prescale` |
| i2c programmer's guide, lines 56 and 101 | `TIMING4.T_STO` | the field is `TSU_STO` |
| i2c programmer's guide, line 139 | `FIFO_CTRL.FMTILVL` | FIFO_CTRL has no such field; the format FIFO threshold is `HOST_FIFO_CONFIG.FMT_THRESH` |
| aon_timer theory of operation, line 32 | a link with text `WKUP_THOLD_HI` for bits 31:0 | the link goes to `WKUP_THOLD_LO`, the register that holds bits 31:0 |

The uart one matters most: it tells software to read a status bit that the hardware does not have.

## Running

The model step needs about 5 GB of disk and runs on a CPU. On GitHub's standard runner, prompt 2 took 24 minutes for 203 sentences and prompt 3 took 36 minutes for 202.

```sh
pip install -r claims/requirements.txt
./csr/fetch_opentitan.sh opentitan
python claims/sentences.py --opentitan opentitan --out out/sentences.json
# download qwen2.5-7b-instruct-q4_k_m-0000{1,2}-of-00002.gguf from Qwen/Qwen2.5-7B-Instruct-GGUF
python claims/extract.py --sentences out/sentences.json \
  --model qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf --model-name Qwen2.5-7B-Instruct --out out/answers.json
python claims/check.py --opentitan opentitan --sentences out/sentences.json --answers out/answers.json --out out/check.md
```

The [workflow](../.github/workflows/claims.yml) runs all of this whenever these files change, and compares the model's answers with the committed ones (`compare.py`). CI re-checks the committed answers of every prompt on every push and compares the reports, so the checking step is reproduced exactly. Each results folder records the model files' checksums, the llama.cpp binding version and a checksum of the prompt.

A second run of prompt 3 on a fresh runner ([run 42943981338](https://github.com/nfang-dev/opentitan-reference-cases/actions/runs/42943981338)) gave the same answers for all 202 sentences, byte for byte.

## Limitations

- Five IPs and 17 explicit facts: enough to see how the model and the checks behave, not to measure them precisely.
- Only sentences that name a register are read; a fact stated about "this field" in a sentence that names no register is missed. A register written with a placeholder index (`PER_PIN_IO_i`) is not recognized.
- Only four kinds of fact are asked for. Behavior ("the interrupt fires when ...") is not checked.
- The word check is a simple list of words. It rejects correct readings whose quote lacks them and lets through misreadings whose quote has them.
- The model is small enough to run on a CPU in CI. A larger model may read better; the checks and the review would stay the same.
- The reviews are judgements about what each sentence states, recorded with a reason for each claim so that they can be checked.
