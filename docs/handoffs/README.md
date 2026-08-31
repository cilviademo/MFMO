# Handoffs — received inputs, kept as received

These are the documents this build was written from. **They are inputs, not
current architecture**, and they are kept unmodified so that any decision in the
live tree can be traced to what it came from.

Where a handoff and the live tree disagree, **the live tree is current** and
`docs/DECISION_LOG.md` says what changed and why. Do not implement from a
handoff without checking the decision log first.

| File | What it is |
|---|---|
| `MASTER_HANDOFF_2026-08-31.md` | The broadest document: full data model, UX direction, pilot and acceptance criteria, `.mil`/DoW security material. Supersedes the consolidated MASTER, now in `docs/archive/`. |
| `CODEX_BUILD_HANDOFF.md` | The execution prompt and gates. **Still authoritative on engineering discipline** — one engine, delegable queries, no fabricated artifacts — because nothing later revisits those. Not an authority on the domain. |
| `RECONCILIATION.md` | Not a handoff. The decision record: corrections C1–C35, with the reasoning. |

## Known-superseded statements in these files

Both handoffs predate 31 Aug 2026 and record two facts that are now known
wrong. They are **not** corrected in place, because a received document edited
after the fact stops being evidence of anything.

* **Tenant cloud "UNKNOWN — GCC High or DoD".** It is **DoD** —
  `usaf.dps.mil` / `dod.teams.microsoft.us`, PAC CLI `UsGovDod`. Every GCC High
  endpoint in either document is wrong for this deployment.
  `docs/government-environment-mode.md` is current.
* **"One Teams site, four portfolio channels."** The four portfolios are **four
  separate SharePoint site collections**, with four different root folder names
  and one inconsistent slug. `deployment/site-bindings.md` is current.

The later `reference/v14/ACTION_DOCUMENT.md` corrects both, and is the top of
the authority order in `docs/DECISION_LOG.md`.
