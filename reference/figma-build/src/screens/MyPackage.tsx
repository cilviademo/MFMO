import { useState } from "react"
import { TopBar, TabStrip, Panel, Table, StatusChip, Btn, TextLink, Icons } from "../components/ui"
import type { Screen, Col, StatusType } from "../components/ui"
import { getPeriodDates, suspenseLabel, formatDate } from "../utils/dates"

interface PkgRow {
  id: string
  code: string
  name: string
  freq: string
  status: StatusType
  submittedDate: string | null  // date only (or with time)
  qcNote: string | null         // QC event shown below chip in Status column
  actionLabel: string
  actionTarget: Screen | null
}

const pd = getPeriodDates(2026, 7) // August 2026

const ROWS: PkgRow[] = [
  {
    id: "1",
    code: "1119",
    name: "AF Form 1119 Feeding Summary",
    freq: "Monthly / Facility",
    status: "review",
    submittedDate: "4 Sep 09:14",
    qcNote: null,
    actionLabel: "Open",
    actionTarget: null,
  },
  {
    id: "2",
    code: "SF 1080",
    name: "Voucher for Transfers",
    freq: "Monthly / Installation",
    status: "late",
    submittedDate: null,
    qcNote: null,
    actionLabel: "Submit",
    actionTarget: "submit",
  },
  {
    id: "3",
    code: "SAIIT",
    name: "Sales, Adjustments, Invoices, Inventory and Transfers",
    freq: "Monthly / Facility",
    status: "correction",
    submittedDate: "2 Sep",
    qcNote: "returned 2 Sep",
    actionLabel: "Submit correction",
    actionTarget: "submit",
  },
  {
    id: "4",
    code: "GPC",
    name: "GPC Bank Statement",
    freq: "Monthly / Installation",
    status: "accepted",
    submittedDate: "3 Sep",
    qcNote: null,
    actionLabel: "Open",
    actionTarget: null,
  },
  {
    id: "5",
    code: "1119-1",
    name: "AF Form 1119-1 Field Feeding",
    freq: "Conditional / Facility",
    status: "not-req",
    submittedDate: null,
    qcNote: null,
    actionLabel: "",
    actionTarget: null,
  },
]

const FILTERS = ["All", "Action required", "Under review", "Complete"] as const
type Filter = typeof FILTERS[number]

const TABS_BASE = [
  { id: "home", label: "Home" },
  { id: "package", label: "My Package", badge: 2 },
  { id: "calendar", label: "Calendar" },
]

function suspenseCellValue(row: PkgRow): string {
  if (row.status === "not-req") return "—"
  return suspenseLabel(pd.nominalInitial, pd.effectiveInitial) + " · Final call " + formatDate(pd.nominalFinal)
}

export default function MyPackage({ nav }: { nav: (s: Screen) => void }) {
  const [filter, setFilter] = useState<Filter>("All")

  const filtered = ROWS.filter(r => {
    if (filter === "Action required") return r.status === "overdue" || r.status === "correction" || r.status === "late"
    if (filter === "Under review") return r.status === "review"
    if (filter === "Complete") return r.status === "accepted" || r.status === "not-req"
    return true
  })

  const cols: Col<PkgRow>[] = [
    {
      key: "req",
      header: "Requirement",
      render: row => (
        <div>
          <div style={{
            fontSize: "13px",
            fontWeight: 700,
            color: "var(--text)",
            fontFamily: "'JetBrains Mono', 'Courier New', monospace",
            marginBottom: "2px",
          }}>
            {row.code}
          </div>
          <div style={{ fontSize: "12px", color: "var(--secondary)" }}>{row.name}</div>
          <div style={{ fontSize: "11px", color: "var(--secondary)", marginTop: "1px" }}>{row.freq}</div>
        </div>
      ),
    },
    {
      key: "suspense",
      header: "Suspense",
      width: "250px",
      render: row => (
        <span style={{
          fontSize: "12px",
          color: (row.status === "overdue" || row.status === "late") ? "var(--status-overdue-text)" : "var(--secondary)",
          fontWeight: (row.status === "overdue" || row.status === "late") ? 600 : 400,
        }}>
          {suspenseCellValue(row)}
        </span>
      ),
    },
    {
      key: "submitted",
      header: "Submitted",
      width: "130px",
      render: row => (
        <span style={{
          fontSize: "12px",
          color: row.submittedDate ? "var(--secondary)" : "var(--border)",
        }}>
          {row.submittedDate ?? "—"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "190px",
      render: row => (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <StatusChip status={row.status} />
          {row.qcNote && (
            <span style={{ fontSize: "11px", color: "var(--status-overdue-text)", fontWeight: 600 }}>
              {row.qcNote}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "action",
      header: "",
      width: "140px",
      align: "right",
      render: row => row.actionLabel ? (
        <TextLink onClick={() => row.actionTarget && nav(row.actionTarget)} style={{ fontSize: "13px" }}>
          {row.actionLabel}
          <Icons.ChevronRight size={12} />
        </TextLink>
      ) : null,
    },
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar
        period="August 2026"
        userName="SrA Kim, P."
        userRole="Base Accountant, JBSA Lackland"
        userInitials="PK"
      />
      <TabStrip
        tabs={TABS_BASE}
        active="package"
        onChange={id => {
          if (id === "home") nav("base-home")
          if (id === "calendar") nav("calendar")
        }}
      />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "24px" }}>

        {/* Heading */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px", lineHeight: 1.2 }}>
              My Package
            </h1>
            <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
              JBSA Lackland · Legacy / APF · August 2026 EOM
              {" · Due "}{suspenseLabel(pd.nominalInitial, pd.effectiveInitial)}
              {" · Final call "}{formatDate(pd.nominalFinal)}
            </div>
          </div>
          <Btn variant="primary" onClick={() => nav("submit")}>
            <Icons.Upload size={14} />
            Submit document
          </Btn>
        </div>

        {/* Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "0" }}>
          <span style={{
            fontSize: "12px",
            color: "var(--secondary)",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            marginRight: "12px",
          }}>
            Show
          </span>
          {FILTERS.map((f, i) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                height: "28px",
                padding: "0 12px",
                background: filter === f ? "var(--accent)" : "var(--surface)",
                color: filter === f ? "#fff" : "var(--secondary)",
                border: "1px solid var(--border)",
                borderRight: i < FILTERS.length - 1 ? "none" : "1px solid var(--border)",
                borderRadius: i === 0 ? "4px 0 0 4px" : i === FILTERS.length - 1 ? "0 4px 4px 0" : "0",
                fontSize: "12px",
                fontWeight: filter === f ? 600 : 400,
                cursor: "pointer",
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Table */}
        <Panel>
          <Table
            cols={cols}
            rows={filtered}
            rowHeight={52}
            emptyMessage="No documents in this view."
          />
        </Panel>

        {/* 1119-1 note */}
        <div style={{
          fontSize: "12px",
          color: "var(--secondary)",
          padding: "8px 0",
          borderTop: "1px solid var(--border)",
        }}>
          <strong>1119-1</strong> (AF Form 1119-1 Field Feeding) is not required for August 2026. Field feeding supplements are conditional and generated only when your unit conducts field operations. Contact your Portfolio Manager if this changes.
        </div>
      </div>
    </div>
  )
}
