import { useState } from "react"
import { TopBar, TabStrip, Table, StatusChip, TextLink, Icons, PM_TABS, IDENTITY } from "../components/ui"
import type { Screen, Col, StatusType, Role } from "../components/ui"

interface QueueRow {
  id: string
  installation: string
  facility: string
  requirement: string
  submitted: string
  by: string
  status: StatusType
  age: string
}

const ROWS: QueueRow[] = [
  { id: "1",  installation: "JBSA Lackland",    facility: "Live Oak",            requirement: "1119",  submitted: "4 Sep 09:14", by: "SrA Kim, P.",       status: "review", age: "3d" },
  { id: "2",  installation: "Minot AFB (2.0)",  facility: "Dakota Inn DFAC",     requirement: "1119",  submitted: "3 Sep 11:20", by: "MSgt. Okafor, T.",   status: "review", age: "4d" },
  { id: "3",  installation: "Fairchild AFB",    facility: "Ross DFAC",           requirement: "1119",  submitted: "5 Sep 08:44", by: "SrA Garcia, R.",     status: "review", age: "2d" },
  { id: "4",  installation: "Creech AFB",       facility: "DFAC",                requirement: "1119",  submitted: "4 Sep 14:02", by: "A1C Patel, N.",      status: "review", age: "3d" },
  { id: "5",  installation: "Creech AFB",       facility: "DFAC",                requirement: "SAIIT", submitted: "6 Sep 07:55", by: "A1C Patel, N.",      status: "review", age: "1d" },
  { id: "6",  installation: "JBSA Lackland",    facility: "Flight Kitchen (FK)", requirement: "GPC",   submitted: "2 Sep 16:10", by: "SrA Kim, P.",        status: "review", age: "5d" },
  { id: "7",  installation: "Altus AFB",        facility: "Hangar 97",           requirement: "SAIIT", submitted: "6 Sep 10:15", by: "SrA Lopez, M.",      status: "review", age: "1d" },
  { id: "8",  installation: "Altus AFB",        facility: "Hangar 97",           requirement: "GPC",   submitted: "5 Sep 14:22", by: "SrA Lopez, M.",      status: "review", age: "2d" },
  { id: "9",  installation: "Andersen AB",      facility: "DFAC",                requirement: "1119",  submitted: "4 Sep 08:30", by: "TSgt. Cruz, R.",     status: "review", age: "3d" },
  { id: "10", installation: "JBSA Lackland",    facility: "Amigo",               requirement: "SAIIT", submitted: "3 Sep 15:40", by: "SrA Kim, P.",        status: "review", age: "4d" },
  { id: "11", installation: "Minot AFB (2.0)",  facility: "Dakota Inn DFAC",     requirement: "SAIIT", submitted: "3 Sep 09:05", by: "MSgt. Okafor, T.",   status: "review", age: "4d" },
  { id: "12", installation: "Fairchild AFB",    facility: "Ross DFAC",           requirement: "SAIIT", submitted: "2 Sep 11:50", by: "SrA Garcia, R.",     status: "review", age: "5d" },
  { id: "13", installation: "Andersen AB",      facility: "DFAC",                requirement: "GPC",   submitted: "1 Sep 16:05", by: "TSgt. Cruz, R.",     status: "review", age: "6d" },
]

const PAGE_SIZE = 7

function ageDays(age: string): number {
  return parseInt(age, 10)
}

function AgeBuckets() {
  const counts = { "0-1": 0, "2-3": 0, "4-5": 0, "6+": 0 }
  for (const row of ROWS) {
    const d = ageDays(row.age)
    if (d <= 1) counts["0-1"]++
    else if (d <= 3) counts["2-3"]++
    else if (d <= 5) counts["4-5"]++
    else counts["6+"]++
  }

  const buckets: { label: string; count: number; color: string }[] = [
    { label: "0–1 day",   count: counts["0-1"], color: "var(--status-accepted-text, #22c55e)" },
    { label: "2–3 days",  count: counts["2-3"], color: "var(--status-open-text, #60a5fa)" },
    { label: "4–5 days",  count: counts["4-5"], color: "var(--status-late-text, #f59e0b)" },
    { label: "6+ days",   count: counts["6+"],  color: counts["6+"] > 0 ? "var(--status-late-text, #f59e0b)" : "var(--secondary)" },
  ]

  const max = Math.max(...buckets.map(b => b.count), 1)

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "2px", padding: "16px 20px" }}>
      <div style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.08em", color: "var(--secondary)", marginBottom: "12px", textTransform: "uppercase" }}>
        Age Distribution
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {buckets.map(b => (
          <div key={b.label} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ width: "60px", fontSize: "11px", color: "var(--secondary)", flexShrink: 0 }}>{b.label}</div>
            <div style={{ flex: 1, background: "var(--border)", borderRadius: "2px", height: "8px", overflow: "hidden" }}>
              <div style={{
                width: `${(b.count / max) * 100}%`,
                height: "8px",
                background: b.color,
                borderRadius: "2px",
                transition: "width 0.3s ease",
              }} />
            </div>
            <div style={{ width: "40px", fontSize: "11px", color: "var(--secondary)", textAlign: "right", flexShrink: 0 }}>{b.count}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: "11px", color: "var(--secondary)", marginTop: "10px", opacity: 0.7 }}>
        Items aged 4 days or more are highlighted.
      </div>
    </div>
  )
}

export default function ReviewQueue({ nav, role = "pm" }: { nav: (s: Screen) => void; role?: Role }) {
  const ident = IDENTITY.pm
  const [page, setPage] = useState(0)
  const totalPages = Math.ceil(ROWS.length / PAGE_SIZE)
  const pageRows = ROWS.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE)

  const cols: Col<QueueRow>[] = [
    {
      key: "installation",
      header: "Installation",
      render: row => (
        <div>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>{row.installation}</div>
          <div style={{ fontSize: "12px", color: "var(--secondary)" }}>{row.facility}</div>
        </div>
      ),
    },
    {
      key: "req",
      header: "Requirement",
      width: "100px",
      render: row => (
        <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text)", fontFamily: "'JetBrains Mono', 'Courier New', monospace" }}>
          {row.requirement}
        </span>
      ),
    },
    {
      key: "submitted",
      header: "Submitted",
      width: "130px",
      render: row => <span style={{ fontSize: "12px", color: "var(--secondary)" }}>{row.submitted}</span>,
    },
    {
      key: "by",
      header: "By",
      width: "140px",
      render: row => <span style={{ fontSize: "12px", color: "var(--secondary)" }}>{row.by}</span>,
    },
    {
      key: "status",
      header: "Status",
      width: "155px",
      render: row => <StatusChip status={row.status} />,
    },
    {
      key: "age",
      header: "Age",
      width: "60px",
      align: "center",
      render: row => (
        <span style={{
          fontSize: "12px",
          color: ageDays(row.age) >= 4 ? "var(--status-late-text)" : "var(--secondary)",
          fontWeight: ageDays(row.age) >= 4 ? 600 : 400,
        }}>
          {row.age}
        </span>
      ),
    },
    {
      key: "action",
      header: "",
      width: "80px",
      align: "right",
      render: () => (
        <TextLink onClick={() => nav("review-correction")} style={{ fontSize: "12px" }}>
          Review <Icons.ChevronRight size={11} />
        </TextLink>
      ),
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip tabs={PM_TABS} active="review" onChange={id => {
        if (id === "overview") nav("afsvc-overview")
        if (id === "installations") nav("installation")
        if (id === "calendar") nav("calendar")
        if (id === "admin") nav("admin")
      }} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "24px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px" }}>
              Review queue
            </h1>
            <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
              August 2026 · 14 submissions awaiting review · oldest 6 days
            </div>
          </div>
        </div>

        <AgeBuckets />

        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "2px" }}>
          <Table cols={cols} rows={pageRows} rowHeight={44} />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
          <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
            Showing {pageRows.length} of {ROWS.length} · Items aged 4 days or more are highlighted.
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <TextLink
              onClick={() => setPage(p => Math.max(0, p - 1))}
              style={{ fontSize: "12px", opacity: page === 0 ? 0.35 : 1, pointerEvents: page === 0 ? "none" : "auto" }}
            >
              ← Prev
            </TextLink>
            <span style={{ fontSize: "12px", color: "var(--secondary)" }}>
              Page {page + 1} of {totalPages}
            </span>
            <TextLink
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              style={{ fontSize: "12px", opacity: page === totalPages - 1 ? 0.35 : 1, pointerEvents: page === totalPages - 1 ? "none" : "auto" }}
            >
              Next →
            </TextLink>
          </div>
        </div>
      </div>
    </div>
  )
}
