# Data sources

Eight SharePoint lists, connected through the `mfops_sharepointonline`
connection reference. The site URL comes from the
`mfops_MF_SharePointSiteURL` environment variable and is never typed into a
formula.

```
MF Installation
MF Facility
MF EOM Requirement
MF EOM Item
MF EOM Submission
MF Unmatched File
MF Security Mapping
MF EOM Audit
```

## Delegation

`MF EOM Item` grows fast: ~204 facilities × ~4 facility requirements × 12
months, plus installation- and contract-scope rows. That crosses 5,000 within
the first year.

- Index `Installation_ID`, `Facility_ID`, `Reporting_Period` and
  `Requirement_ID` **before** the list crosses 5,000. You cannot index after.
  The provisioning script does this.
- Filter on `Reporting_Period` first in every query. It is the most selective
  column and keeps the result set delegable.
- Never `Filter()` on a calculated or non-delegable expression. Put the
  computation in the flow, store it, filter on the stored column. This is why
  `Status_Code` is a stored number and not computed in the gallery.
- `MF EOM Audit` is append-only and will be the largest list. Never bind a
  gallery directly to it; query by `Entity_ID`.

The app holds no copies of these records beyond the session collections set in
`App.OnStart`.
