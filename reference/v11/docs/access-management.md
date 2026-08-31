# Access management — implementation instruction

Two roles in the interface, capability in flags underneath. This is what goes
into the solution package, not a design brief.

Read `security/role-matrix.csv` and `security/SECURITY_PROMPTS.md` before
implementing. Nothing here overrides the deny-by-default and fail-closed rules.

---

## 1. The model

```
Role                  BASE_USER | PORTFOLIO_MANAGER
Job_Title             display only, never a permission
Can_QC                review submissions
Can_Submit_On_Behalf  upload something that arrived by email
Can_Edit_Requirements change the catalogue, thresholds, configuration
Can_Grant_Access      grant or revoke PORTFOLIO_MANAGER
Grant_Scope           None | Portfolio | Enterprise
```

**Everyone is BASE_USER automatically.** CAC identifies them, the GAL gives the
installation, and nobody is provisioned. That was settled earlier and does not
change.

**PORTFOLIO_MANAGER is granted**, and `Can_Grant_Access` defaults **FALSE** even
for people who hold it.

### Why the flags are not folded into the role

If every Portfolio Manager can grant Portfolio Manager, the role self-propagates.
One grant, and from then on the population can only grow — no holder needs
anyone's approval to expand it. That is a privilege escalation path and it is the
first thing an ISSM will ask about.

Splitting `Can_Edit_Requirements` from `Can_QC` matters for a different reason:
reviewing a 1119 and changing what a 1119 *is* are different jobs. Someone who
returns a document for the wrong reporting period should not, by the same
credential, be able to change the reporting period rule.

Neither split costs the user anything. The interface still shows two roles.

---

## 2. Named formulas

Add to `App.Formulas`. Nothing derives a permission anywhere else.

```
gblRole          = First(gblMyScope).Role;
gblJobTitle      = First(gblMyScope).Job_Title;

gblIsPM          = gblRole = "PORTFOLIO_MANAGER";
gblCanQC         = CountRows(Filter(gblMyScope, Can_QC = true)) > 0;
gblCanOnBehalf   = CountRows(Filter(gblMyScope, Can_Submit_On_Behalf = true)) > 0;
gblCanEditConfig = CountRows(Filter(gblMyScope, Can_Edit_Requirements = true)) > 0;
gblCanGrant      = CountRows(Filter(gblMyScope, Can_Grant_Access = true)) > 0;
gblGrantScope    = First(Sort(gblMyScope,
                     Switch(Grant_Scope, "Enterprise",1, "Portfolio",2, "None",3))).Grant_Scope;

// Who this person may act on. Enterprise sees everyone; Portfolio sees their
// own portfolio; anyone else sees nobody.
gblGrantablePopulation =
    Switch( gblGrantScope,
        "Enterprise", Filter('MF Security Mapping', Active_Flag = true),
        "Portfolio",  Filter('MF Security Mapping', Active_Flag = true,
                             Portfolio_ID = gblMyPortfolio),
        Blank()
    );
```

`gblRole` is a display fact. Every gate reads a flag.

---

## 3. Navigation

Tabs are filtered, never disabled. A base user does not see a greyed-out Review
tab; the tab does not exist. Nothing in the interface advertises a capability the
user does not hold.

```
NavTabs.Items =
Filter(
    Table(
        { Id: "home",          Label: "Home",          Show: true },
        { Id: "package",       Label: "My Package",    Show: Not(gblIsPM) },
        { Id: "overview",      Label: "Overview",      Show: gblIsPM },
        { Id: "review",        Label: "Review",        Show: gblCanQC },
        { Id: "installations", Label: "Installations", Show: gblIsPM },
        { Id: "calendar",      Label: "Calendar",      Show: true },
        { Id: "admin",         Label: "Admin",         Show: gblCanEditConfig Or gblCanGrant }
    ),
    Show
)
```

Base user gets three tabs. A Portfolio Manager with neither admin flag gets four,
not five — the Admin tab appears only when there is something in it.

---

## 4. Screen — scrAccessManagement

Visible when `gblCanGrant`. It is a section of Admin, not a top-level
destination.

```
ACCESS MANAGEMENT                                    Portfolio 2

2 access requests pending                       [ Review requests → ]

[ search people ]        Role [ All ▾ ]        Status [ All ▾ ]

Name            Installation      Role                Granted    Expires
Kim, P.         JBSA Lackland     Base user           —          —
Torres, M.      JBSA Lackland     Portfolio Manager   4 Aug 26   —
Whitfield, J.   Minot AFB         Portfolio Manager   12 Jul 26  1 Oct 26 · temporary
```

`galPeople.Items` filters `gblGrantablePopulation` server-side on `Portfolio_ID`,
which is indexed. Never `ClearCollect` the mapping list — it grows with the
enterprise.

Row action is a text link: `Grant Portfolio Manager →` or `Revoke →`.

An expiring grant shows the date and the word *temporary* in secondary text. A
grant expiring within 14 days shows amber.

---

## 5. Grant

```
GRANT PORTFOLIO MANAGER
Torres, M. · JBSA Lackland

Scope      [ Portfolio 2 ▾ ]      (locked to own portfolio unless Enterprise)
Duration   ( ) Permanent   ( ) Until [ date ]
Reason     [ required ]

This person will be able to review submissions and manage the registry.
They will not be able to grant this role to others.

[ Cancel ]  [ Grant ]
```

The consequence line is not decoration. Someone granting a role should see what
it includes, and the line changes if `Can_Grant_Access` is being set.

```
// btnGrant.OnSelect
If( !gblCanGrant,
    Notify("You don't have permission to grant access.", NotificationType.Error),

    IsBlank(txtReason.Text),
    Notify("A reason is required.", NotificationType.Error),

    rdoDuration.Selected.Value = "Until" And IsBlank(dtUntil.SelectedDate),
    Notify("Set a date, or choose Permanent.", NotificationType.Error),

    // Scope is derived, never taken from a control the grantor can widen.
    With( { scope: If( gblGrantScope = "Enterprise",
                       cmbScope.Selected.Portfolio_ID, gblMyPortfolio ) },

        Patch( 'MF Security Mapping', galPeople.Selected,
            { Role: "PORTFOLIO_MANAGER",
              Can_QC: true,
              Can_Submit_On_Behalf: true,
              Can_Edit_Requirements: false,   // granted separately, never here
              Can_Grant_Access: false,        // never propagates
              Grant_Scope: "None",
              Portfolio_ID: scope,
              Grant_Type: "Manual",
              Granted_By: gblCurrentUser.Email,
              Granted_Date: Now(),
              Expires_Date: If( rdoDuration.Selected.Value = "Until",
                                dtUntil.SelectedDate, Blank() ) } );

        LogEvent( "ACCESS_GRANTED", "Success",
                  galPeople.Selected.UPN & " -> PORTFOLIO_MANAGER, scope " & scope
                  & ", " & txtReason.Text );

        Notify("Access granted.", NotificationType.Success)
    )
)
```

**Three things this deliberately does.** `Can_Grant_Access` and
`Can_Edit_Requirements` are written FALSE, never inherited. Scope is derived from
the grantor's own scope, not read from a control they could widen. And the write
is a `Patch` to an existing mapping row, not a create — everyone already has one.

---

## 6. Revoke

```
REVOKE PORTFOLIO MANAGER
Whitfield, J. · Minot AFB

They will lose the ability to review submissions and see other installations
in Portfolio 3. They keep base user access to Minot AFB.

Reason  [ required ]

[ Cancel ]  [ Revoke ]
```

Revoking sets `Role: "BASE_USER"` and every flag FALSE, `Grant_Scope: "None"`,
and clears `Granted_By`, `Granted_Date` and `Expires_Date`. It never deactivates
the row — the person keeps base access to their own installation. Revoking a role
is not removing someone from the system.

---

## 7. Expiry

Add to EOM-03, nightly:

```
for each mapping where Expires_Date < today and Role = PORTFOLIO_MANAGER:
    set Role = BASE_USER, all capability flags FALSE, Grant_Scope = None
    log ACCESS_EXPIRED
    notify the person and the original grantor  (if notifications enabled)
```

Run it before the status recalculation. A grant that expired overnight should not
survive one more day of review activity.

Seven days before expiry, log `ACCESS_EXPIRING` and surface it on the Access
Management screen. Do not auto-extend.

---

## 8. Requests

`MF_Access_Request` already exists. Wire it to this screen.

A pending request shows requester, home installation, requested installation,
reason, needed-until date, and `[ Approve ]` `[ Deny ]`. Approving runs the same
grant logic. Denying requires a reason.

A request may only be approved by someone whose `Grant_Scope` covers the
requested installation. A Portfolio 2 manager cannot approve a Portfolio 3
request, and the request does not appear in their queue.

---

## 9. Audit

Every access event writes to `MF_App_Event_Log`:

```
ACCESS_GRANTED · ACCESS_REVOKED · ACCESS_EXPIRED · ACCESS_EXPIRING
ACCESS_REQUESTED · ACCESS_APPROVED · ACCESS_DENIED
```

Each carries actor UPN, target UPN, previous role, new role, scope, duration and
reason, plus `Correlation_ID` and `App_Version`.

Access changes are the events an inspection asks about first, and reconstructing
them from SharePoint version history afterward is miserable.

---

## 10. Tests

- [ ] A new user with no mapping row gets BASE_USER for their GAL installation
- [ ] A base user sees three tabs; Review, Installations and Admin do not exist
      in the DOM, not merely hidden
- [ ] A base user cannot reach Access Management by deep link
- [ ] A PM without `Can_Grant_Access` sees no Access Management section
- [ ] A PM with `Grant_Scope = Portfolio` sees only their own portfolio's people
- [ ] A granted PM has `Can_Grant_Access = FALSE` — verify in the list, not the UI
- [ ] A granted PM has `Can_Edit_Requirements = FALSE`
- [ ] Grant without a reason is blocked
- [ ] Temporary grant without a date is blocked
- [ ] Expiry reverts the role overnight and logs it
- [ ] Revoke leaves base access to the person's own installation intact
- [ ] A Portfolio 2 manager never sees a Portfolio 3 request
- [ ] Every grant, revoke, expiry, approval and denial appears in the event log
- [ ] **SharePoint permissions independently prevent a base user reading another
      installation's evidence** — see `docs/security-open-issue.md`

The last one is not an app test and it will not pass yet. It is on the list so it
is not forgotten.
