# Security prompts — Claude Code and Figma

**They need different prompts, and the split is lopsided.** Of the seventy items
in the research, roughly sixty are Claude Code's and eight are Figma's. Figma
cannot implement a security control; it can only represent one. Sending the full
directive to Figma produces a prototype that *looks* secure, which is worse than
one that doesn't, because it invites everyone to assume the work is done.

Two prompts below. Send the first to Claude Code, the second to Figma.

---

## Before either: one finding the research implies but does not state

Item 5 — *Power Apps UI filtering is not access control* — is correct and is the
most important line in the document. Its consequence for this specific build has
not been said out loud:

**The data layer does not currently enforce installation scope, and the
confirmed folder structure prevents it from doing so.**

The structure is **four separate SharePoint site collections**, one per
portfolio, each with a Monthly Data Call folder, fiscal year, then month. Every
base user with access to a portfolio's library can see every
other base's documents in that channel — in Teams, in SharePoint, and through
any client that speaks to the library. The app can show a DFAC manager only
Lackland. SharePoint will still hand them Creech's 1119 if they browse to it.

So the claim "base user sees only their installation" is true of the app and
false of the system. That gap is a finding an ISSM will identify, and it is a
data-layer decision, not something Claude Code can fix in Power Fx.

Three options, in order of preference:

1. **Item-level permissions on the evidence library**, broken inheritance per
   installation folder, driven by Entra security groups. Works with the current
   structure. Requires SharePoint admin support and unique-permission scale
   review — SharePoint has practical limits on unique permission scopes per
   library.
2. **One library per portfolio, folder per installation, group per
   installation.** Cleaner permission story, more provisioning.
3. **Accept portfolio-level visibility as the boundary** and document it as a
   risk decision with the AO. Legitimate if the information is not protected and
   the AO agrees — but it must be a decision on paper, not an accident.

The manifest currently reads `data_layer_permissions_verified: false`. It stays
false until one of those three is chosen and implemented.

---

# Prompt 1 — for Claude Code

```
GOVERNMENT SECURITY DIRECTIVE — MISSION FEEDING OPERATIONS

This directive is binding on the source package. Where it conflicts with an
earlier instruction, this wins.

Read security/security-manifest.yaml, security/connector-allowlist.yaml and
docs/security-open-issue.md first. Run scripts/prerelease_scan.py before any
export; a FAIL means do not export.

==================================================
1. THE FRAME
==================================================

Build a package that arrives pre-hardened, contains no secrets or protected
data, exposes every environment-specific value as configuration, implements
application-layer controls, generates audit evidence, and fails closed until
the destination environment is bound.

Do not claim the package is compliant, STIG-compliant, or authorised. Import
success is not authorisation to operate. RMF registration, control assessment
and the AO decision are lifecycle activities on the .mil side, and using an
authorised Microsoft platform does not authorise this application.

Target GCC High and DoD. These are different clouds with different maker, flow,
admin, SharePoint and Power BI endpoints. Support both; hard-code neither.

==================================================
2. NO HARDCODED DESTINATIONS, NO SECRETS
==================================================

Every environment-specific value is an environment variable or a configuration
record with a BLANK default:

  MF_CloudEnvironment · MF_SharePointSiteURL · MF_SubmissionLibrary
  MF_ConfigSiteURL · MF_PowerBIReportURL · MF_SupportURL

No production URL in Power Fx. No commercial endpoint anywhere — not
make.powerapps.com, not app.powerbi.com, not *.sharepoint.com, not
azurewebsites.net. The scanner fails on all of them.

Never package a password, token, client secret, API key, service-account
credential, certificate, CAC identifier, EDIPI, DoDAAC, DoDAAD, account number,
fund cite or contract-sensitive value. Credentials live in connection
references bound at import, never in configuration.

If required configuration is missing at startup, enter CONFIGURATION_REQUIRED
and block all writes. Do not guess a destination.

==================================================
3. IDENTITY AND AUTHORISATION
==================================================

Do not build authentication. No login screen, no password field, no PIN, no
"select a user" control, no simulated CAC. Identity comes from Entra
Government. The app consumes User().Email and nothing else.

The QRG POC column is a display name. It is never an identity, never a
permission, and never the source of an email address.

Authorisation is deny by default, through MF_User_Access:

  User_UPN · Role · Installation_ID · Portfolio_ID · Scope_Type
  Effective_From · Effective_To · Active_Flag · Approved_By · Approval_Date

Roles: BASE_SUBMITTER · BASE_MANAGER · AFSVC_REVIEWER ·
AFSVC_PORTFOLIO_MANAGER · AFSVC_OPERATIONS · APP_ADMIN · APP_AUDITOR.

Centralise the checks — fnCanViewInstallation, fnCanSubmit, fnCanReview,
fnCanAdmin. Never compare User().Email against a literal address in a screen.

FAIL CLOSED, always:
  no mapping                -> NO ACCESS, with a request-access route
  scope unresolvable        -> ACCESS_SCOPE_UNRESOLVED
  configuration missing     -> CONFIGURATION_REQUIRED
  write unconfirmed by flow -> SUBMISSION_NOT_CONFIRMED

Never downgrade a security failure into permissive behaviour.

==================================================
4. THE APP IS NOT THE BOUNDARY
==================================================

Visible = false is not security. Filter() is not security. Microsoft is
explicit: hiding a record in Power Apps does not remove the user's permission
to the underlying SharePoint data.

Put this warning in the README and the deployment runbook:

  APP_SECURITY_FILTERS_ARE_NOT_A_DATA_SECURITY_BOUNDARY

Deployment must configure SharePoint permissions that mirror the app's scope
model. Until that is done, the app's scope claim is presentational.

See docs/security-open-issue.md — the current folder structure gives every base
user visibility of their whole portfolio site, which the app cannot fix.

==================================================
5. SYSTEM-DERIVED FIELDS
==================================================

A user may never write, from any control:

  User_UPN · Role · Installation_ID authorisation · Portfolio_ID
  Reviewer identity · Accepted_By · Status · Status_Code · Version_No
  Authority_Status · any audit author or timestamp

Derive all of them server-side from authenticated identity and runtime values.
A user typing a reviewer name into an official audit record is a finding.

Validate before every write: installation exists, requirement exists, period
valid, requirement applies to that installation and facility, file present,
comment present on return, QC reason from the approved list.

==================================================
6. CONNECTORS
==================================================

R1 uses SharePoint, and conditionally Office 365 Users, Outlook and Power BI.
Prohibited: HTTP, HTTP with Entra ID, custom connectors, Dropbox, Google Drive,
consumer OneDrive, third-party SaaS, external AI, AI Builder.

New connectors are disabled by default in GCC High and DoD until an
administrator reviews them, so every conditional connector must degrade
gracefully — if Outlook is unapproved, notifications turn off and nothing else
breaks.

The allowlist in security/connector-allowlist.yaml is application governance.
It does not replace tenant DLP and must not be described as if it does.

==================================================
7. FILES
==================================================

Allowlist: .pdf .xlsx .docx .csv. Reject executables and scripts. Never trust
the filename, the extension alone, or a client-supplied MIME type.

Never execute uploaded content — no macros, no server-side formula evaluation,
no embedded scripts, no unsafe HTML rendering.

MF_MaxUploadSizeMB is configuration, not a constant.

Store the internal SharePoint URL and the file identifier. Never create an
anonymous or "anyone with the link" sharing URL. That capability does not exist
in this app.

==================================================
8. AUDIT
==================================================

Every mission-relevant state transition writes to MF_App_Event_Log with
Correlation_ID and App_Version. Purview covers platform activity; this covers
business activity. Neither replaces the other, and Purview user-activity
auditing requires tenant configuration — put it on the deployment checklist,
not in Power Fx.

Do not log document contents or protected values.

==================================================
9. ERRORS
==================================================

User-facing:

  We couldn't save your submission. No data was changed.
  Reference: MF-20260831-A7F4

Never surface an HTTP status, a token, a list GUID, a site URL, a connector
message or a stack trace. Technical detail goes to the log with a correlation
ID the user can quote.

Security messages are plain: "You don't currently have access to this
installation. [Request access]" — not "403" and not "RBAC scope failure".

==================================================
10. CUI
==================================================

Build the framework, do not assume the designation. CUI applies only where an
authorised category and authority exist, and a legacy sensitivity marking is
not equivalent to CUI.

  Information_Protection_Level · CUI_Flag (default false) · CUI_Category
  CUI_Banner_Marking (blank) · Limited_Dissemination_Control · CUI_Authority
  CUI_Designation_Source · CUI_Designated_By · CUI_Designation_Date

cmpInformationBanner renders nothing when CUI_Flag is false. Never generate a
marking from an inferred data type.

Protected fields — DODAAC, DODAAD, Official_POC_UPN, Org_Box_Email,
Contract_ID, Accounting_Code — exist as nullable columns and ship blank. They
are populated only inside the authorised environment.

==================================================
11. NO DEV FEATURE SHIPS ON
==================================================

DeveloperTools · DebugPanel · MockData · RoleSimulator · SyntheticUsers ·
BypassSecurity · AllowManualIdentity · ShowHiddenRecords · AIBuilder — all
false in the release package. EnvironmentMode is PROD.

The role simulator in the prototype must never become a production access path.

==================================================
12. DELEGATION IS A SECURITY CONTROL
==================================================

Never ClearCollect an enterprise list and filter locally. That is a wrong
answer, a performance problem, and unnecessary data in client memory at the
same time. Reduce at the server first: authorised installation, portfolio,
reporting period, status, current version.

==================================================
13. RETENTION AND DELETION
==================================================

Normal users cannot hard-delete evidence. Use Active · Superseded · Returned ·
Rejected · Retired. A correction creates v2 and leaves v1 intact.

Determine whether EOM submissions, EOY inventory evidence, QC decisions and
audit history are official records and what disposition schedule applies. Do
not implement a convenient "delete after N days".

==================================================
14. WHAT TO PRODUCE
==================================================

  security/security-manifest.yaml        (exists — keep it accurate)
  security/connector-allowlist.yaml      (exists)
  security/role-matrix.csv
  security/cui-schema.md
  deployment/pre-import-checklist.md
  deployment/import-runbook.md
  deployment/post-import-checklist.md
  deployment/gcc-high-profile.md
  deployment/dod-profile.md
  docs/security-open-issue.md            (the data-layer gap)
  docs/rmf/  system-description · data-flow · architecture ·
             external-connections · security-control-mapping ·
             information-types · data-classification · configuration-baseline ·
             test-plan · known-risks · poam-template · continuous-monitoring
  docs/records-management.md
  docs/privacy-assessment.md
  tests/authorization-tests.md
  tests/security-tests.md
  CHANGELOG.md · RELEASE_NOTES.md · ROLLBACK.md

Map design decisions to NIST SP 800-53 families: AC, AU, CM, IA, SC, SI, SA,
RA, CP, PL, PT. Do not claim 800-171 or CMMC as the baseline — those govern CUI
in nonfederal systems and the Defense Industrial Base, not an internal DAF
application. The chain here is FISMA -> DoDI 8500.01 -> DoDI 8510.01 -> RMF /
800-53 -> DISA SRGs and STIGs -> DAF and local AO.

==================================================
15. THE GATE
==================================================

scripts/prerelease_scan.py must PASS before export. It currently passes.

Release is blocked if the package contains a secret, a commercial endpoint, a
hardcoded production URL, a prohibited connector, a security bypass, a role
override, a mock identity, an enabled dev flag, an external font or telemetry
dependency, populated protected data, or a missing rollback path.

The scan checks the package. It says nothing about the tenant. DLP, tenant
isolation, Conditional Access, SharePoint permissions, Purview retention,
records schedule, privacy determination, STIG applicability and RMF
authorisation are deployment-side and belong on the post-import checklist, not
in the app.
```

---

# Prompt 2 — for Figma

Short by design. Figma's entire security contribution is making the states
visible and not inventing reassurance.

```
SECURITY STATES — MISSION FEEDING OPERATIONS

Add these to the existing build. Do not redesign anything.

1. NO SIGN-IN, EVER
No login screen, no password field, no PIN, no "select a user" control, no
simulated CAC prompt. The user is already identified. The role selector in the
prototype is a test harness and must be visibly labelled as one — a dark strip
outside the app frame, never a control inside it.

2. FAIL-CLOSED SCREENS — three new frames
Design these as ordinary, calm screens. They are not errors.

  NO ACCESS
    "Your account isn't mapped to an installation yet."
    [ Request access ]  [ Contact your Portfolio Manager ]

  SCOPE UNRESOLVED
    "We couldn't verify which installation you work at."
    Reference: MF-20260831-A7F4
    [ Request access ]

  CONFIGURATION REQUIRED  (admin only)
    "This environment hasn't been configured yet."
    A checklist of what is unset. No data visible anywhere on the screen.

None of these shows a portfolio total, an installation name, or any record.
Failing closed means showing nothing, not showing a locked-looking dashboard.

3. REQUEST ACCESS FLOW — one frame
  Installation [ search ] · Reason [ text ] · Needed until [ date ]
  "Your Portfolio Manager will review this."
Plus a pending state on the No Access screen: "Requested 2 Sep · awaiting
review."

4. ERROR MESSAGES CARRY NO INTERNALS
Never show an HTTP status, a URL, a GUID, a token, a connector name or a stack
trace. The pattern is:

  We couldn't save your submission. No data was changed.
  Reference: MF-20260831-A7F4

The reference is selectable so a user can quote it. That is the only technical
element on screen.

5. ADMIN HEALTH SPLITS IN TWO
Two sections with a visible divider and different treatment:

  APPLICATION HEALTH — things the app observes
    3 installations missing facility mapping
    August generation completed for 41 of 43 installations
    2 submissions need classification

  TENANT SECURITY — things the app cannot observe
    Power Platform DLP        Requires tenant admin verification
    Tenant isolation          Requires tenant admin verification
    Purview audit retention   Requires tenant admin verification
    SharePoint permissions    Requires tenant admin verification

Tenant rows are neutral gray with no status chip. Never render them "Healthy" —
a fabricated green there is worse than no row at all.

6. ENVIRONMENT BANNERS
A thin full-width strip above the top bar, only when not normal production:

  PILOT ENVIRONMENT
  READ ONLY — MAINTENANCE

Neutral background, dark text, no icon, no colour alarm. Nothing in normal
production.

7. CUI BANNER COMPONENT — designed, rendering nothing
Build cmpInformationBanner with a blank marking string and show it in the
component library only. Do not place it on a screen. Do not invent a marking.
Most Mission Feeding information is not CUI, and a decorative CUI banner is a
policy error, not a design flourish.

8. THINGS THAT MUST NOT APPEAR
No DoDAAC, DoDAAD, account number, fund cite, contract identifier, org box,
personal contact detail or CAC identifier — not populated, not as an empty
labelled row, not as a lock icon, not as a note. If the value cannot be shown,
the row does not exist.

No external fonts. The build currently loads Inter from Google Fonts; that CDN
is a release blocker. Production font is Segoe UI Variable — note Inter as a
Figma substitute in the file, not as a dependency.

9. FRAMES TO ADD
No Access · Scope Unresolved · Configuration Required · Request Access ·
Admin Health with the tenant split · Read-only banner state.

Six frames.
```

---

## Files added to the repo

```
security/security-manifest.yaml      machine-readable claims, verified by the scanner
security/connector-allowlist.yaml    R1 connector discipline with fallbacks
scripts/prerelease_scan.py           executable gate — currently PASS
```

The scanner has thirty rules across secrets, commercial endpoints, hardcoded
destinations, prohibited connectors, security bypasses, external dependencies,
protected data and dev flags, plus eleven assertions against the manifest.

It found one hit on its first run: `configuration/app-config.csv` contained the
string `app.powerbi.com` inside a description *warning against* hardcoding it.
That is the rule working as intended — a scanner that reasons about intent is a
scanner that can be talked into a pass. The description was reworded.
