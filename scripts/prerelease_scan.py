#!/usr/bin/env python3
"""Pre-release security scan.

Fails the build when the package contains something that must never ship to a
government tenant. This is a gate, not a linter — a FAIL means do not export.

Run:  python3 scripts/prerelease_scan.py
Exit: 0 pass (warnings allowed) · 1 fail
"""
import os, re, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", ".figma", "data",
             # Vendored prior art and the input handoffs. Never exported, never
             # imported, kept only so a decision can be traced to what it came
             # from — and they necessarily quote the strings they forbid.
             "reference", "handoffs"}
# Path-anchored, not name-anchored: a directory called "archive" anywhere else
# in the tree is still scanned. Superseded documentation lives here with a
# header naming what replaced it, and a superseded document necessarily quotes
# the endpoints and structures it was superseded FOR. Nothing here is on the
# packaging path.
SKIP_PATHS = {os.path.join(ROOT, "docs", "archive")}
# These files name prohibited strings in order to prohibit them. Excluding a
# rule would weaken the gate for everyone; excluding the four documents that
# define the gate does not. Nothing here is imported into Power Platform.
SKIP_FILES = {"prerelease_scan.py", "security-manifest.yaml",
              "connector-allowlist.yaml", "SECURITY_PROMPTS.md",
              "security-open-issue.md", "CLAUDE_CODE_HANDOFF.md"}
TEXT_EXT = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".ps1", ".fx",
            ".tsx", ".ts", ".js", ".html", ".css", ".py", ".xml", ".pa"}

# An inline, auditable exception. A line that NAMES a prohibited string in
# order to prohibit it is not a violation, but skipping whole files to allow it
# would weaken the gate for everything else in them. So the exception is
# declared at the line, carries a reason, and shows up in the summary:
#
#     | SharePoint admin | *.sharepoint.com | ...   <!-- prerelease: allow CLD-03 the endpoint table IS the policy -->
#
# Only WARN-able intent is expressible this way; the scanner still counts and
# reports every one, so an exception cannot be added quietly.
# prerelease: allow XXX-00 <reason>
# The rule id, then a reason. The reason is REQUIRED and must be substantive:
# an exception nobody explained is an exception nobody can review, and the
# whole point of preferring inline markers over whole-file skips was that each
# one stays auditable. A marker with no reason FAILS the scan.
ALLOW_RE = re.compile(r"prerelease:\s*allow\s+([A-Z]{3}-\d{2})\b[ \t]*([^\n]*)")
MIN_ALLOW_REASON = 12

# (id, severity, pattern, message)
RULES = [
    # ---- secrets: always FAIL -------------------------------------------
    ("SEC-01", "FAIL", r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{3,}",
     "Hardcoded password"),
    ("SEC-02", "FAIL", r"(?i)\b(client_?secret|api[_-]?key|access[_-]?token|bearer)\s*[:=]\s*['\"][^'\"]{8,}",
     "Hardcoded secret, API key or token"),
    ("SEC-03", "FAIL", r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
     "Private key material"),
    ("SEC-04", "FAIL", r"(?i)connectionstring\s*[:=].*(password|pwd)=",
     "Connection string containing a credential"),

    # ---- commercial cloud: FAIL ----------------------------------------
    ("CLD-01", "FAIL", r"make\.powerapps\.com|flow\.microsoft\.com(?!\.us)",
     "Commercial Power Platform endpoint. This deployment is DoD: "
     "make.apps.appsplatform.us, flow.appsplatform.us."),
    ("CLD-02", "FAIL", r"app\.powerbi\.com",
     "Commercial Power BI endpoint. Government uses a different service URL."),
    ("CLD-03", "FAIL", r"\.sharepoint\.com(?!\.)",
     "Commercial SharePoint host. GCC High is .sharepoint.us; this "
     "deployment's DoD tenant is .dps.mil"),
    ("CLD-04", "FAIL", r"azurewebsites\.net",
     "Commercial Azure endpoint"),

    # ---- hardcoded destinations: FAIL ----------------------------------
    # Both government SharePoint hosts. The rule was written when the cloud was
    # assumed to be GCC High (.sharepoint.us). This tenant is DoD, where sites
    # live on .dps.mil — so the rule as written would have watched the one host
    # a leak could not occur on and missed the one it could.
    # /teams/ as well as /sites/. A Teams-backed site -- which every private
    # channel is -- lives under /teams/, so a rule watching only /sites/ misses
    # exactly the URLs the four production portfolios actually use.
    # Every government SharePoint host, every site path shape. sharepoint.<tld>
    # rather than sharepoint.us: GCC High is .us, commercial is .com, and a
    # rule naming only the clouds we expect is a rule that misses the one we
    # did not. /teams/ as well as /sites/ because every private channel is a
    # Teams-backed site, and the four production portfolios are private
    # channels -- the rule spent this whole build watching the one path shape
    # they do not use.
    ("URL-01", "FAIL",
     r"https://[a-z0-9.-]+\.(sharepoint\.[a-z]{2,}|dps\.mil)/(sites|teams)/(?!<)",
     "Hardcoded government SharePoint site. Bind it from an environment "
     "variable — MF_SharePointSiteURL, or MF_Portfolio{n}_SiteURL for a "
     "portfolio destination. A real site URL in source is a destination leak."),
    ("URL-02", "FAIL",
     r"(?i)DAFMissionFeeding-(Legacy_)?Portfolio[1-4]\s*(/|\\|\.)",
     "A portfolio site slug used as a path. The four portfolios are four "
     "separate site collections bound at import; a slug in a path is a "
     "destination built by pattern, which is how Portfolio 2 breaks."),

    # ---- prohibited connectors: FAIL ------------------------------------
    ("CON-01", "FAIL", r"shared_(webcontents|dropbox|googledrive|onedrive)\b",
     "Prohibited connector reference"),
    # "Send an HTTP request to SharePoint" is an action OF THE SHAREPOINT
    # CONNECTOR, and it is the provisioning route this deployment depends on --
    # PowerShell is unavailable on the target network. The prohibited thing is
    # the HTTP connector, which is a different connector entirely.
    #
    # The rule is TIGHTENED rather than the file exempted: an exemption would
    # also silence a real HTTP connector added to that file later, which is
    # exactly the finding the rule exists for. A negative lookahead keeps the
    # rule watching every other phrasing.
    ("CON-02", "WARN",
     r"Web\.Contents\s*\(|\bHTTP\s+request\b(?!\s+to\s+SharePoint)",
     "HTTP connector usage. Prohibited in R1 unless separately approved. "
     "The SharePoint connector's own 'Send an HTTP request to SharePoint' "
     "action is NOT this and does not fire here."),

    # ---- security bypass: FAIL ------------------------------------------
    ("BYP-01", "FAIL", r"(?i)(bypass_?security|disable_?auth|skip_?auth|isAdmin\s*=\s*true)",
     "Security bypass"),
    ("BYP-02", "FAIL", r"(?i)(role_?override|user_?role_?override|impersonate_?user)\s*[:=]\s*(true|1|\"|')",
     "Role override or impersonation"),
    ("BYP-03", "FAIL", r"User\(\)\.Email\s*=\s*\"[a-z0-9._%-]+@",
     "Authorisation compared against a literal email address. Use MF_User_Access."),

    # ---- external runtime dependencies ----------------------------------
    ("DEP-01", "FAIL", r"fonts\.googleapis\.com|fonts\.gstatic\.com",
     "External font CDN. Blocked on .mil and a supply-chain dependency. "
     "Production font is Segoe UI Variable."),
    ("DEP-02", "FAIL", r"(google-analytics|googletagmanager|mixpanel|sentry\.io|posthog)",
     "External telemetry"),
    ("DEP-03", "WARN", r"cdn\.jsdelivr\.net|unpkg\.com|cdnjs\.cloudflare\.com",
     "Public CDN runtime dependency"),

    # ---- CUI and protected data: FAIL -----------------------------------
    ("CUI-01", "FAIL", r"\b\d{3}-\d{2}-\d{4}\b", "Possible SSN"),
    ("CUI-02", "FAIL", r"(?i)\bEDIPI\s*[:=]\s*\d", "EDIPI value"),
    ("CUI-03", "FAIL", r"(?i)\bDoDAAC\s*[:=]\s*['\"]?[A-Z0-9]{6}",
     "Populated DoDAAC. Schema-ready and blank only; enrich inside the "
     "authorised environment."),
    ("CUI-04", "FAIL", r"\b(?:\d[ -]*?){13,16}\b(?=.*(?i:card|gpc|account))",
     "Possible payment card or account number"),
    ("CUI-05", "WARN", r"(?i)\bfund\s*cite\s*[:=]\s*\S",
     "Possible fund cite"),

    # ---- fabricated identity --------------------------------------------
    ("IDN-01", "WARN", r"(?i)\b(admin|test|demo|mock)@(us\.af\.mil|example\.)",
     "Placeholder account. Must not reach production."),
    # A fabricated address in a REAL namespace is the worse half of this
    # problem, and the rule above missed it: it only watched four prefixes, so
    # five demo personas shipped with surnames in the us.af.mil namespace in a
    # PUBLIC repository. A reader cannot tell a fixture from a real person's UPN, and
    # a made-up name can collide with a real one. Demo identities belong in
    # example.mil, which exists for this.
    ("IDN-02", "FAIL", r"[A-Za-z0-9._%+-]+@(us\.af\.mil|mail\.mil|us\.army\.mil|navy\.mil)",
     "An address in a real .mil namespace. Real or fabricated, it must not be "
     "committed: use example.mil for fixtures and bind real identities in the "
     "tenant."),

    # ---- dev flags on ----------------------------------------------------
    ("FLG-01", "FAIL", r"(?i)(DeveloperTools|DebugPanel|MockData|RoleSimulator|SyntheticUsers)\s*[:=]\s*(true|TRUE|\"TRUE\")",
     "Development feature enabled. All must default false in production."),
    ("FLG-02", "FAIL", r"(?i)EnvironmentMode\s*[:=]\s*['\"]?(DEV|TEST)",
     "Non-production environment mode in the release package"),
    ("FLG-03", "WARN", r"(?i)(EnableAIBuilder|EnableGenerativeAI|EnableExternalAI)\s*[:=]\s*(true|TRUE)",
     "AI feature enabled. Must be off by default in R1."),
]

MANIFEST_CHECKS = [
    ("MAN-01", "application.contains_secrets", False),
    ("MAN-02", "application.contains_cui", False),
    ("MAN-03", "cloud.commercial_cloud_supported", False),
    ("MAN-04", "authentication.local_authentication", "prohibited"),
    ("MAN-05", "authorization.default", "deny"),
    ("MAN-06", "authorization.fail_closed", True),
    ("MAN-07", "cui.default_cui_flag", False),
    ("MAN-08", "release.debug_mode", False),
    ("MAN-09", "release.bypass_security", False),
    ("MAN-10", "data.destructive_user_delete", False),
    ("MAN-11", "rmf.ato_claimed", False),
]

# A required artifact has to say something. 200 bytes is well under any real
# document and well over an accidental heading.
MIN_ARTIFACT_BYTES = 200

REQUIRED_FILES = [
    "security/security-manifest.yaml",
    "security/connector-allowlist.yaml",
    "docs/DEPLOYMENT.md",
    "docs/accessibility.md",
    "CHANGELOG.md",
    "ROLLBACK.md",
    "deployment/site-bindings.md",
    "deployment/DEPENDENCY_MANIFEST.md",
]


def walk():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in SKIP_DIRS
                   and os.path.join(base, d) not in SKIP_PATHS]
        for f in files:
            if f in SKIP_FILES:
                continue
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                yield os.path.join(base, f)


ARCHIVE_EXT = (".msapp", ".zip", ".msapr")


def walk_archives():
    """Tracked archive-like artifacts. A leak inside a ZIP is still a leak,
    and the first canvas build proved it: the .msapp shipped signed Azure Blob
    URLs and a donor tenant identifier that no text-file scan could see. An
    archive is never exempt merely because Git calls it binary."""
    # tests/fixtures is the one exemption, for the same reason SKIP_FILES
    # exempts the documents that define the gate: the fixture archives exist
    # to prove these rules FIRE, so they necessarily contain what the rules
    # forbid. They are never on the packaging path, and the tests that consume
    # them assert the violations are detected.
    fixture_dir = os.path.join(ROOT, "tests", "fixtures")
    # Deliberately WIDER than the text walk: dist/ is skipped for text because
    # build outputs restate their sources, but built ARCHIVES are the shipped
    # artifacts themselves -- the donor residue lived in dist/canvas while
    # every text scan read PASS. Only vendored prior art and the fixture
    # specimens stay out.
    archive_skip = {".git", "node_modules", "__pycache__", "reference",
                    "handoffs"}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs
                   if d not in archive_skip
                   and os.path.join(base, d) not in SKIP_PATHS]
        if os.path.abspath(base).startswith(fixture_dir):
            continue
        for f in files:
            if f.lower().endswith(ARCHIVE_EXT):
                yield os.path.join(base, f)


def _scanned_tree_digests():
    """SHA-256 of every file the scan's walks can reach, plus the fixture
    specimens. An archive entry BYTE-IDENTICAL to one of these is a verbatim
    packaging of a file whose verdict the flat scan already owns -- its
    inline exception markers included, which whole-entry matching cannot see.
    Identical bytes, identical verdict. Anything modified, renamed-with-new-
    content, or foreign (donor scaffolding, platform output, planted residue)
    matches nothing here and is scanned in full."""
    import hashlib
    digests = set()
    skip = {".git", "node_modules", "__pycache__", "dist"}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            p = os.path.join(base, f)
            try:
                with open(p, "rb") as fh:
                    digests.add(hashlib.sha256(fh.read()).hexdigest())
            except OSError:
                continue
    return digests


def scan_archives():
    """Apply every content rule to every entry of every tracked archive."""
    import hashlib
    import zipfile
    hits = []
    tree = _scanned_tree_digests()
    for path in walk_archives():
        rel = os.path.relpath(path, ROOT)
        try:
            z = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile):
            hits.append(("FAIL", "ARC-00", rel, 0,
                         "archive cannot be opened for inspection; an "
                         "uninspectable artifact does not ship", ""))
            continue
        with z:
            for entry in z.namelist():
                blob = z.read(entry)
                if hashlib.sha256(blob).hexdigest() in tree:
                    continue  # verbatim copy of an already-scanned file
                text = blob.decode("utf-8", "ignore")
                for rid, sev, pat, msg in RULES:
                    m = re.search(pat, text)
                    if m:
                        raw = text[max(0, m.start() - 20):m.start() + 60]
                        snippet = "".join(c for c in raw
                                          if c.isprintable())[:90]
                        hits.append((sev, rid, f"{rel}!{entry}", 0, msg,
                                     snippet))
                # Archive-only rules: the residue classes the first canvas
                # build shipped. Signed SAS fragments and cloud-storage hosts
                # have no business in any artifact of this project.
                for rid, needle, msg in (
                        ("ARC-01", "blob.core.windows.net",
                         "Azure Blob storage URL inside an archive entry"),
                        ("ARC-02", "sig=",
                         "SAS signature fragment inside an archive entry"),
                        ("ARC-03", "sktid=",
                         "tenant identifier in a signed URL inside an "
                         "archive entry"),
                        ("ARC-04", ".windows.net",
                         "windows.net host inside an archive entry")):
                    if needle in text:
                        hits.append(("FAIL", rid, f"{rel}!{entry}", 0, msg,
                                     needle))
    return hits


def scan_content():
    hits, allowed = [], []
    hits.extend(scan_archives())
    for path in walk():
        rel = os.path.relpath(path, ROOT)
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        lines = text.splitlines()
        for rid, sev, pat, msg in RULES:
            for m in re.finditer(pat, text):
                line = text[:m.start()].count("\n") + 1
                source = lines[line - 1]
                snippet = source.strip()[:90]
                # An inline exception must name THIS rule on THIS line, and it
                # must give a reason. It is recorded and reported, never silent.
                exception = next((a for a in ALLOW_RE.finditer(source)
                                  if a.group(1) == rid), None)
                if exception:
                    reason = _clean_reason(exception.group(2))
                    if len(reason) < MIN_ALLOW_REASON:
                        # An unexplained exception is worse than no exception:
                        # it silences a rule and leaves nothing to review.
                        hits.append(("FAIL", "EXC-01", rel, line,
                                     f"Inline exception for {rid} gives no reason. "
                                     f"Write 'prerelease: allow {rid} <why this "
                                     f"line is not the thing the rule is for>'.",
                                     snippet))
                        continue
                    allowed.append((rid, rel, line, reason))
                    continue
                hits.append((sev, rid, rel, line, msg, snippet))
    return hits, allowed


def _clean_reason(raw):
    """Strip the comment closers a marker picks up from its host syntax."""
    return raw.strip().rstrip("-->").rstrip("*/").rstrip("#").strip(" \t-*/<>").strip()


def get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return "__MISSING__"
        cur = cur[part]
    return cur


def tiny_yaml(text):
    """Enough YAML for this manifest: nested maps, scalars, inline lists."""
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line.startswith("- "):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.split("#")[0].strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            node = {}
            parent[key.strip()] = node
            stack.append((indent, node))
        else:
            if val.lower() in ("true", "false"):
                v = val.lower() == "true"
            elif val.startswith("["):
                v = [x.strip() for x in val.strip("[]").split(",") if x.strip()]
            else:
                v = val.strip("'\"")
            parent[key.strip()] = v
    return root


def main():
    print("Mission Feeding Operations — pre-release security scan\n" + "=" * 58)
    fails, warns = [], []

    hits, allowed = scan_content()
    for sev, rid, rel, line, msg, snip in hits:
        (fails if sev == "FAIL" else warns).append(
            f"  [{rid}] {rel}:{line}\n        {msg}\n        > {snip}")

    mpath = os.path.join(ROOT, "security", "security-manifest.yaml")
    if not os.path.exists(mpath):
        fails.append("  [MAN-00] security/security-manifest.yaml is missing")
    else:
        man = tiny_yaml(open(mpath, encoding="utf-8").read())
        for rid, key, expected in MANIFEST_CHECKS:
            actual = get(man, key)
            if actual != expected:
                fails.append(f"  [{rid}] manifest {key} = {actual!r}, must be {expected!r}")

    # Existence was never the question. ROLLBACK.md shipped as a zero-byte file
    # and passed a check that only asked whether the path resolved -- which is
    # exactly the shape of failure this whole scan exists to prevent, in the
    # scan itself.
    for rf in REQUIRED_FILES:
        full = os.path.join(ROOT, rf)
        if not os.path.exists(full):
            fails.append(f"  [REQ-01] required release artifact missing: {rf}")
            continue
        try:
            with open(full, encoding="utf-8", errors="ignore") as fh:
                body = fh.read()
        except OSError as exc:
            fails.append(f"  [REQ-01] required release artifact unreadable: {rf} ({exc})")
            continue
        substantive = [ln for ln in body.splitlines()
                       if ln.strip() and not ln.lstrip().startswith("#")]
        if len(body.strip()) < MIN_ARTIFACT_BYTES or not substantive:
            fails.append(
                f"  [REQ-02] required release artifact is empty or a stub: {rf}\n"
                f"        {len(body.strip())} bytes, {len(substantive)} substantive line(s). "
                f"A rollback procedure nobody wrote is not a rollback procedure.")

    if allowed:
        # Reported every run, so an exception cannot be added quietly and a
        # reviewer sees the whole set in one place.
        print(f"\nALLOWED BY INLINE EXCEPTION ({len(allowed)})")
        for rid, rel, line, reason in allowed:
            print(f"  [{rid}] {rel}:{line}\n        {reason}")

    if warns:
        print(f"\nWARN ({len(warns)})")
        for w in warns:
            print(w)
    if fails:
        print(f"\nFAIL ({len(fails)})")
        for f in fails:
            print(f)
        print("\n" + "=" * 58)
        print("RELEASE BLOCKED. Do not export the solution.")
        return 1

    print(f"\nPASS — no blocking findings. {len(warns)} warning(s).")
    print("\nThis scan checks the PACKAGE. It says nothing about the tenant.")
    print("DLP, tenant isolation, Conditional Access, SharePoint permissions,")
    print("Purview retention, records schedule, privacy review, STIG")
    print("applicability and RMF authorisation are deployment-side and are")
    print("verified by deployment/post-import-checklist.md.")
    print("\nIMPORT SUCCESS IS NOT AUTHORISATION TO OPERATE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
