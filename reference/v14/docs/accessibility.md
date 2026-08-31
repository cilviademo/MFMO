# Accessibility — a build gate, not a review step

Section 508 applies to software developed, maintained, procured or used by
federal agencies. Web software maps to WCAG 2.x A and AA plus the software
criteria. Accessibility is built into the lifecycle, not added at the end, so
these are acceptance tests that block release.

## Rules for this app

**Status is never communicated by colour alone.** Every status carries a text
label and, in the data, a `Status_Semantic` string. A green square on its own is
a defect. This is why `Status_Semantic` exists on both `MF_EOM_Item` and
`MF_EOM_Status`.

**Use native modern controls.** Do not build a fake combo box out of a gallery
and a button, a custom table from labels, or a tab strip from rectangles.
Microsoft warns specifically about composite controls assembled where a native
one exists, and they are the most common cause of a screen reader announcing
nothing useful.

| Need | Use | Never |
|---|---|---|
| Selection | native Combobox / Dropdown | gallery + button |
| Tabular data | modern Table | gallery of labels |
| Status | modern Badge with text | coloured rectangle |
| Confirmation | modern Dialog | overlaid rectangle group |
| Action | native Button | clickable icon with no label |

**Responsive layout via containers.** Auto-layout horizontal and vertical
containers, never absolute X/Y positioning.

```
scrHome
└── conRoot            (vertical, fill parent)
    ├── conHeader      (horizontal, fixed height)
    ├── conBody        (horizontal, flexible)
    │   ├── conNav     (fixed width, collapses under 700px)
    │   └── conContent (flexible)
    └── conFooter
```

`Button.X = 475` and `Gallery.Width = App.Width - 423` are the signature of a
brittle app and they break at 200% zoom.

## Acceptance tests

- [ ] Every interactive control reachable by keyboard alone, in logical order
- [ ] Visible focus indicator on every control
- [ ] `AccessibleLabel` set on every control conveying meaning
- [ ] Text contrast at least 4.5:1
- [ ] No status conveyed by colour alone anywhere
- [ ] Screen reader announces status chips as text
- [ ] Usable at 200% zoom with no horizontal scrolling
- [ ] Errors announced, tied to the field, and written in plain language
- [ ] Form fields have programmatic labels, not adjacent text only
- [ ] Document links describe the document, not "click here"
- [ ] Power Apps Accessibility Checker returns zero errors before each release

## Error copy

Never expose a status code. Say what happened and what to do.

| Situation | Message |
|---|---|
| No matching requirement | We found the file but couldn't tell which requirement it satisfies. Send it to review? |
| Comment missing on return | Add a comment explaining what needs correcting. |
| Suspense missing | Set a date for the corrected document. |
| Read-only mode | The app is read-only while we finish maintenance. You can view status but not submit. |
| No scope mapping | Your account isn't mapped to a facility yet. Contact your Portfolio Manager. |
