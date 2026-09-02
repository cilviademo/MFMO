# MF Ops — blank-slate provisioning kit (revision 3)

For a pilot provisioned ENTIRELY by hand onto a BLANK site: delete any
existing MF lists, click two small flows together, run BUILD, run
VERIFY, sign the audit, then load configuration. Email-safe: no
scripts, no binaries — everything runs inside Power Automate.

| File | What it is |
|---|---|
| `SCHEMA-PAYLOADS.json` | 17 lists / 286 columns / 90 indexes, every REST payload, generated from the schema authority — pasted once into each flow |
| `FLOW-BUILD.md` | the BUILD flow, click by click — 4 action shapes, no branches, fail-stop by design |
| `FLOW-VERIFY.md` | the read-only audit flow — no CSV loads before its YES line |
| `SHA256SUMS.txt` | integrity manifest |

Order: verify this kit's hashes → delete existing MF lists (BUILD
runbook lists the 17 names) → build both flows → run BUILD → run
VERIFY → record the audit → **delete both flows** → continue with the
manual kit's CSV import.

Offline proof: every payload in this kit was replayed against a mock
SharePoint that enforces create-order, rejects duplicate internal
names, and derives internal names the way SharePoint does — final
state 17/286/90, zero `_x0020_` names, and the
VERIFY audit renders YES against that state
(`tests/test_blankslate_kit.py`). The live run in your tenant is
**NOT TESTABLE LOCALLY**; these flows have NOT been executed in Power
Automate, and this kit does not claim otherwise.
