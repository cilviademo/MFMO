import { TopBar, TabStrip, Table, StatusChip, Panel, TextLink, Btn, MetricStrip, Icons, PM_TABS, IDENTITY } from "../components/ui"
import type { Screen, Col, StatusType, Role } from "../components/ui"

interface FacilityRow {
  id: string
  facility: string
  requirement: string
  submitted: string
  status: StatusType
  owner: "AFSVC" | "Installation"
}

const ROWS: FacilityRow[] = [
  { id: "1", facility: "Live Oak",          requirement: "1119",    submitted: "4 Sep",  status: "review",     owner: "AFSVC" },
  { id: "2", facility: "Live Oak",          requirement: "SAIIT",   submitted: "2 Sep",  status: "correction", owner: "Installation" },
  { id: "3", facility: "Live Oak",          requirement: "SF 1080", submitted: "—",      status: "late",       owner: "Installation" },
  { id: "4", facility: "Flight Kitchen (FK)", requirement: "1119",  submitted: "3 Sep",             status: "accepted",   owner: "AFSVC" },
  { id: "5", facility: "Flight Kitchen (FK)", requirement: "SAIIT", submitted: "3 Sep",             status: "review",     owner: "AFSVC" },
  { id: "6", facility: "Amigo",             requirement: "1119",    submitted: "—",                 status: "late",       owner: "Installation" },
  { id: "7", facility: "Amigo",             requirement: "SAIIT",   submitted: "—",                 status: "late",       owner: "Installation" },
]

export default function InstallationWorkspace({ nav, role = "pm" }: { nav: (s: Screen) => void; role?: Role }) {
  const ident = IDENTITY.pm
  const cols: Col<FacilityRow>[] = [
    {
      key: "facility",
      header: "Facility",
      render: row => (
        <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>{row.facility}</span>
      ),
    },
    {
      key: "req",
      header: "Requirement",
      width: "100px",
      render: row => (
        <span style={{ fontSize: "13px", fontWeight: 700, fontFamily: "'JetBrains Mono', 'Courier New', monospace", color: "var(--text)" }}>
          {row.requirement}
        </span>
      ),
    },
    {
      key: "submitted",
      header: "Submitted",
      width: "130px",
      render: row => (
        <span style={{ fontSize: "12px", color: row.submitted === "—" ? "var(--border)" : "var(--secondary)" }}>
          {row.submitted}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "180px",
      render: row => (
        <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
          <StatusChip status={row.status} />
          {row.status === "correction" && row.submitted !== "—" && (
            <span style={{ fontSize: "11px", color: "var(--status-overdue-text)", fontWeight: 600 }}>
              returned {row.submitted}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "owner",
      header: "Action owner",
      width: "110px",
      render: row => (
        <span style={{
          fontSize: "12px",
          fontWeight: 600,
          color: row.owner === "AFSVC" ? "var(--status-review-text)" : "var(--status-overdue-text)",
        }}>
          {row.owner}
        </span>
      ),
    },
    {
      key: "action",
      header: "",
      width: "80px",
      align: "right",
      render: row => (
        <TextLink onClick={() => nav("review-queue")} style={{ fontSize: "12px" }}>
          {row.status === "review" ? "Review" : "Open"}
          <Icons.ChevronRight size={11} />
        </TextLink>
      ),
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip tabs={PM_TABS} active="installations" onChange={id => {
        if (id === "overview") nav("afsvc-overview")
        if (id === "review") nav("review-queue")
        if (id === "calendar") nav("calendar")
        if (id === "admin") nav("admin")
      }} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "24px" }}>

        {/* Breadcrumb */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--secondary)" }}>
          <TextLink onClick={() => nav("afsvc-overview")} style={{ fontSize: "12px" }}>Overview</TextLink>
          <Icons.ChevronRight size={11} />
          <span>JBSA Lackland</span>
        </div>

        {/* Heading */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px" }}>
              JBSA Lackland
            </h1>
            <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
              Portfolio 2 · Legacy / APF · August 2026 EOM · 3 facilities
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <Btn variant="subtle">
              <Icons.History size={14} />
              Activity log
            </Btn>
            <Btn variant="subtle">
              <Icons.ExternalLink size={14} />
              Open EOM folder
            </Btn>
          </div>
        </div>

        {/* Metric strip */}
        <MetricStrip tiles={[
          { label: "Expected items", value: "12", context: "this period" },
          { label: "Submitted", value: "7", context: "of 12 expected" },
          { label: "Accepted", value: "1", context: "by AFSVC" },
          { label: "Overdue / Late", value: "3", context: "need base action" },
        ]} />

        {/* Suspense */}
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          padding: "12px 20px",
          display: "flex",
          gap: "32px",
          alignItems: "center",
          flexWrap: "wrap",
        }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--secondary)", marginBottom: "3px" }}>
              Initial suspense
            </div>
            <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--status-overdue-text)" }}>
              5 Sep 2026 — passed
            </div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--secondary)", marginBottom: "3px" }}>
              Final call
            </div>
            <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--status-late-text)" }}>
              10 Sep 2026 · 1 day remaining
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <StatusChip status="late" />
        </div>

        {/* Completion bar */}
        {(() => {
          const accepted = ROWS.filter(r => r.status === "accepted").length
          const review   = ROWS.filter(r => r.status === "review").length
          const correction = ROWS.filter(r => r.status === "correction").length
          const overdue  = ROWS.filter(r => r.status === "overdue" || r.status === "late").length
          const total    = ROWS.length
          const pct      = Math.round((accepted / total) * 100)
          const seg = (n: number, bg: string) => ({
            flex: n,
            height: "8px",
            background: n > 0 ? bg : "transparent",
            borderRadius: "2px",
          })
          return (
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "2px", padding: "12px 20px" }}>
              <div style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase" as const, letterSpacing: "0.05em", color: "var(--secondary)", marginBottom: "6px" }}>
                JBSA Lackland · {accepted} of {total} items accepted · {pct}%
              </div>
              <div style={{ display: "flex", gap: "1px", borderRadius: "2px", overflow: "hidden", marginBottom: "6px" }}>
                <div style={seg(accepted, "var(--status-accepted-bg)")} />
                <div style={seg(review, "var(--status-review-bg)")} />
                <div style={seg(correction, "var(--status-overdue-bg)")} />
                <div style={seg(overdue, "var(--status-late-bg)")} />
                <div style={seg(total - accepted - review - correction - overdue, "var(--border)")} />
              </div>
              <div style={{ fontSize: "11px", color: "var(--secondary)", display: "flex", gap: "12px" }}>
                <span><span style={{ color: "var(--status-accepted-text)", fontWeight: 600 }}>{accepted}</span> accepted</span>
                <span><span style={{ color: "var(--status-review-text)", fontWeight: 600 }}>{review}</span> awaiting</span>
                {correction > 0 && <span><span style={{ color: "var(--status-overdue-text)", fontWeight: 600 }}>{correction}</span> correction</span>}
                {overdue > 0 && <span><span style={{ color: "var(--status-late-text)", fontWeight: 600 }}>{overdue}</span> overdue/late</span>}
              </div>
            </div>
          )
        })()}

        {/* Requirements table */}
        <Panel title="Requirements">
          <Table cols={cols} rows={ROWS} rowHeight={44} />
        </Panel>
      </div>
    </div>
  )
}
