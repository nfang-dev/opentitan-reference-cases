# Case 004: keymgr_dpe: loading the creator root key again before the next reset

| | |
|---|---|
| Module | `keymgr_dpe` (key manager with DICE protection environment support) |
| Setting | Whether software can place the creator root key (UDS) into a key slot again after the first advance call, before the next reset |
| OpenTitan revision | [`0ea5236fe749`](https://github.com/lowRISC/opentitan/tree/0ea5236fe749e70ba18f56ba19c4be982ef46da7) (2026-11-03) |
| Result | One statement disagrees with the design and with three other statements in the same document |
| Machine-readable record | [`case.json`](case.json) |

## Question

After the first advance call has latched the creator root key and keymgr_dpe is `Available`, can software load the creator root key into a slot again before the next reset?

The setting is recorded as `1` if it can (subject to the checks the design makes) and `0` if it cannot.

## Written requirement

`hw/ip/keymgr_dpe/doc/theory_of_operation.md`

| ID | Line | What it says | Value it implies |
|---|---:|---|---:|
| R1 | 85 | "The latching of the root key can only happen once until the keymgr_DPE is reset." | 0 |
| R2 | 145 | "This initial latching can be repeated with the _Load Root Key_ operation unless locked with the `LOAD_ROOT_KEY_LOCK` register." | 1 |
| R3 | 241 | The creator root key "is latched by the first advance call and can be loaded by an explicit software request." | 1 |
| R4 | 270 | Software sets the lock registers "once the respective root key is no longer needed in the current boot, so that later boot stages cannot reload it." | 1 |

## Design

| ID | Location | What it shows |
|---|---|---|
| D1 | `hw/ip/keymgr_dpe/data/keymgr_dpe.hjson:588` | `CONTROL_SHADOWED.OPERATION` value 5 is "Load root key": "Loads the root key into the key manager. Can be disabled by LOAD_ROOT_KEY_LOCK if needed." |
| D2 | `hw/ip/keymgr_dpe/data/keymgr_dpe.hjson:1406` | `LOAD_ROOT_KEY_LOCK.LOCK` (write 1 to set, reset value 0): "Write 1 to disable the `load root key` operation until the next reset." |
| D3 | `hw/ip/keymgr_dpe/rtl/keymgr_dpe_ctrl.sv:174` | The control logic decodes the operation: `load_req = op_req & (op_i == OpDpeLoadRootKey)`. |
| D4 | `hw/ip/keymgr_dpe/rtl/keymgr_dpe_ctrl.sv:750` | A load is rejected only if the root key is not valid, the destination slot is already valid, `LOAD_ROOT_KEY_LOCK` is set, or the destination slot is out of range (lines 750 to 753). None of these depends on an earlier latch. |

## Which evidence is independent

D1 and D2 are register descriptions in `keymgr_dpe.hjson`; `reggen` generates the register RTL and `registers.md` from them, so those generated files are not counted as more evidence.
D3 and D4 are hand-written control logic and do not derive from the documentation.
R1 to R4 are hand-written.

## History

- R1 was already present at the revision of 2026-05-01 (`63c8a5025a0b`, line 75).
  At that revision the Advance section also said "This initial latching can only be done once until the next power cycle."
- Upstream change `ec3f9a694` (2026-10-06, "Document load (secondary) root key operations") replaced that sentence with R2 and added the section that holds R3 and R4.
  R1 was left unchanged.
- R1 is still present on OpenTitan's `master` branch as of 2026-11-05 (now line 86).

## Finding

R2 to R4 describe a Load Root Key operation that repeats the latch until software sets `LOAD_ROOT_KEY_LOCK`, and the design provides that operation and its lock.
R1 says the latch can happen only once until reset. It disagrees with the design and with the rest of the document.
A reader who relies on R1 could conclude that the creator root key cannot be reloaded within a boot, and so that setting `LOAD_ROOT_KEY_LOCK` is unnecessary.

## Ambiguities

- R1 could be read narrowly as describing only the latch performed during the transition from `Reset` to `Available`, which happens once per reset because the state machine leaves `Reset` only once. The document does not draw that distinction: R2 calls the Load Root Key operation a repetition of the same latching.
- A load is rejected while the destination slot is valid (D4). Software must erase the slot or choose another empty slot first; the documents state this as a general load condition (line 265), not specifically for reloading the creator root key.

## Missing information

This case compares the operation's decoding and rejection conditions with the documents. It does not simulate a load after the first advance.

## Out of scope

- The secondary root key and `LOAD_SECONDARY_ROOT_KEY_LOCK`, which the documents describe consistently.
- Whether a top-level design or its software restricts the operation; keymgr_dpe is instantiated in Darjeeling, whose software is not examined here.

## Re-run this case

```sh
./tools/fetch_opentitan.sh opentitan cases/004-keymgr-dpe-root-key-reload/case.json
python3 tools/check_case.py cases/004-keymgr-dpe-root-key-reload/case.json --opentitan opentitan
```

Expected output at the recorded revision ends with:

```
Claims:
  C1 creator root key can be loaded again before the next reset (1 yes, 0 no): stated 0, design 1 (D1, D2, D3, D4) -> disagrees
  C2 creator root key can be loaded again before the next reset (1 yes, 0 no): stated 1, design 1 (D1, D2, D3, D4) -> agrees
  C3 creator root key can be loaded again before the next reset (1 yes, 0 no): stated 1, design 1 (D1, D2, D3, D4) -> agrees

RESULT: 2 agree, 1 disagree, 0 unresolved; all outcomes match the recorded labels
```

## Status

No upstream change proposed yet.
