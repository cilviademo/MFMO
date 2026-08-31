import { useState } from "react"
import { TopBar, TabStrip, Table, StatusChip, TextLink, Icons, Select, PM_TABS, IDENTITY } from "../components/ui"
import type { Screen, Col, StatusType, Role } from "../components/ui"

interface OverviewRow {
  id: string
  installation: string
  facility: string
  requirement: string
  submitted: string
  status: StatusType
  owner: "AFSVC" | "Installation"
  age: string
}

const ALL_ROWS: OverviewRow[] = [
  { id: "1",  installation: "JBSA Lackland",    facility: "Live Oak",            requirement: "1119",    submitted: "4 Sep",  status: "review",     owner: "AFSVC",        age: "3d" },
  { id: "2",  installation: "JBSA Lackland",    facility: "Flight Kitchen (FK)", requirement: "SAIIT",   submitted: "2 Sep",  status: "correction", owner: "Installation", age: "5d" },
  { id: "3",  installation: "JBSA Lackland",    facility: "Chapman",             requirement: "SF 1080", submitted: "—",      status: "overdue",    owner: "Installation", age: "11d" },
  { id: "4",  installation: "Minot AFB (2.0)",  facility: "Dakota Inn DFAC",     requirement: "1119",    submitted: "3 Sep",  status: "review",     owner: "AFSVC",        age: "4d" },
  { id: "6",  installation: "Fairchild AFB",    facility: "Ross DFAC",           requirement: "1119",    submitted: "5 Sep",  status: "review",     owner: "AFSVC",        age: "2d" },
  { id: "7",  installation: "Andersen AB",      facility: "DFAC",                requirement: "GPC",     submitted: "1 Sep",  status: "accepted",   owner: "AFSVC",        age: "6d" },
  { id: "9",  installation: "Creech AFB",       facility: "DFAC",                requirement: "1119",    submitted: "4 Sep",  status: "review",     owner: "AFSVC",        age: "3d" },
  { id: "10", installation: "Creech AFB",       facility: "DFAC",                requirement: "GPC",     submitted: "3 Sep",  status: "accepted",   owner: "AFSVC",        age: "4d" },
  { id: "11", installation: "Creech AFB",       facility: "DFAC",                requirement: "SAIIT",   submitted: "6 Sep",  status: "review",     owner: "AFSVC",        age: "1d" },
  { id: "13", installation: "JBSA Lackland",    facility: "Amigo",               requirement: "SAIIT",   submitted: "1 Sep",  status: "accepted",   owner: "AFSVC",        age: "6d" },
  { id: "14", installation: "Altus AFB",        facility: "Hangar 97",           requirement: "SAIIT",   submitted: "4 Sep",  status: "review",     owner: "AFSVC",        age: "3d" },
]

// Portfolio data (worst first = lowest % first)
const PORTFOLIO_ROWS = [
  { id: "4", label: "Portfolio 4", accepted: 29, total: 47 },
  { id: "2", label: "Portfolio 2", accepted: 38, total: 48 },
  { id: "1", label: "Portfolio 1", accepted: 44, total: 50 },
  { id: "3", label: "Portfolio 3", accepted: 41, total: 43 },
]

const AGGREGATE = { accepted: 148, awaiting: 14, corrections: 7, overdue: 3, total: 172 }

const PORTFOLIO_OPTIONS = [
  { value: "all", label: "All portfolios" },
  { value: "1", label: "Portfolio 1" },
  { value: "2", label: "Portfolio 2" },
  { value: "3", label: "Portfolio 3" },
  { value: "4", label: "Portfolio 4" },
]

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "action", label: "Action required" },
  { value: "review", label: "Awaiting review" },
  { value: "accepted", label: "Accepted" },
  { value: "correction", label: "Corrections" },
  { value: "overdue", label: "Overdue" },
]

const REQ_OPTIONS = [
  { value: "all", label: "All requirements" },
  { value: "1119", label: "1119" },
  { value: "SF1080", label: "SF 1080" },
  { value: "SAIIT", label: "SAIIT" },
  { value: "GPC", label: "GPC" },
]

const INSTALL_OPTIONS = [
  { value: "", label: "" },
  { value: "altus", label: "Altus AFB" },
  { value: "andersen", label: "Andersen AB" },
  { value: "creech", label: "Creech AFB" },
  { value: "fairchild", label: "Fairchild AFB" },
  { value: "lackland", label: "JBSA Lackland" },
  { value: "minot-20", label: "Minot AFB (2.0)" },
]

export default function AFSVCOverview({ nav, role = "pm" }: { nav: (s: Screen) => void; role?: Role }) {
  const ident = IDENTITY.pm
  const [period, setPeriod] = useState("August 2026")
  const [portfolio, setPortfolio] = useState("all")
  const [statusFilter, setStatusFilter] = useState("action")
  const [reqFilter, setReqFilter] = useState("all")
  const [search, setSearch] = useState("")

  const filtered = ALL_ROWS.filter(r => {
    if (search && !r.installation.toLowerCase().includes(search.toLowerCase()) &&
        !r.facility.toLowerCase().includes(search.toLowerCase())) return false
    if (reqFilter !== "all" && r.requirement !== reqFilter) return false
    if (statusFilter === "action" && r.status !== "overdue" && r.status !== "correction" && r.status !== "late") return false
    if (statusFilter === "review" && r.status !== "review") return false
    if (statusFilter === "accepted" && r.status !== "accepted") return false
    if (statusFilter === "correction" && r.status !== "correction") return false
    if (statusFilter === "overdue" && r.status !== "overdue") return false
    return true
  })

  const ownerColor = (o: "AFSVC" | "Installation") =>
    o === "AFSVC" ? "var(--status-review-text)" : "var(--status-overdue-text)"

  const pct = Math.round((AGGREGATE.accepted / AGGREGATE.total) * 100)
  const acceptedW = (AGGREGATE.accepted / AGGREGATE.total) * 100
  const awaitingW = (AGGREGATE.awaiting / AGGREGATE.total) * 100
  const correctionsW = (AGGREGATE.corrections / AGGREGATE.total) * 100
  const overdueW = (AGGREGATE.overdue / AGGREGATE.total) * 100

  const cols: Col<OverviewRow>[] = [
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
      key: "requirement",
      header: "Requirement",
      width: "90px",
      render: row => (
        <span style={{
          fontSize: "13px",
          fontWeight: 700,
          color: "var(--text)",
          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
        }}>
          {row.requirement}
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
          color: row.submitted === "—" ? "var(--border)" : "var(--secondary)",
        }}>
          {row.submitted}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "155px",
      render: row => <StatusChip status={row.status} />,
    },
    {
      key: "owner",
      header: "Action owner",
      width: "110px",
      render: row => (
        <span style={{
          fontSize: "12px",
          fontWeight: 600,
          color: ownerColor(row.owner),
        }}>
          {row.owner}
        </span>
      ),
    },
    {
      key: "age",
      header: "Age",
      width: "60px",
      align: "center",
      render: row => (
        <span style={{ fontSize: "12px", color: "var(--secondary)" }}>{row.age}</span>
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
      <TopBar period={period} onPeriodChange={setPeriod} userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip
        tabs={PM_TABS}
        active="overview"
        onChange={id => {
          if (id === "review") nav("review-queue")
          if (id === "installations") nav("installation")
          if (id === "calendar") nav("calendar")
          if (id === "admin") nav("admin")
        }}
      />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "24px" }}>

        {/* Heading */}
        <div>
          <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px", lineHeight: 1.2 }}>
            Overview
          </h1>
          <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
            {period} · Legacy / APF · All installations
          </div>
        </div>

        {/* Full-width metric strip */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          background: "var(--surface)",
        }}>
          {[
            { label: "Accepted",       value: "148", color: "var(--status-accepted-text)" },
            { label: "Awaiting review", value: "14",  color: "var(--status-review-text)" },
            { label: "Corrections",    value: "7",   color: "var(--status-overdue-text)" },
            { label: "Overdue",        value: "3",   color: "var(--status-overdue-text)" },
          ].map((t, i) => (
            <div key={i} style={{
              padding: "16px 20px",
              borderRight: i < 3 ? "1px solid var(--border)" : "none",
            }}>
              <div style={{
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                color: "var(--secondary)",
                marginBottom: "6px",
              }}>
                {t.label}
              </div>
              <div style={{
                fontSize: "28px",
                fontWeight: 300,
                color: t.color,
                lineHeight: 1.1,
              }}>
                {t.value}
              </div>
            </div>
          ))}
        </div>

        {/* Completion progress bar */}
        <div style={{ marginTop: "-16px" }}>
          {/* Above-bar label */}
          <div style={{
            fontSize: "11px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--secondary)",
            marginBottom: "6px",
          }}>
            AUGUST 2026 · {AGGREGATE.accepted} of {AGGREGATE.total} items accepted · {pct}%
          </div>

          {/* Segmented bar */}
          <div style={{
            display: "flex",
            height: "8px",
            borderRadius: "2px",
            overflow: "hidden",
            gap: "1px",
            background: "var(--border)",
          }}>
            <button
              onClick={() => setStatusFilter("accepted")}
              title="Accepted"
              style={{
                width: `${acceptedW}%`,
                height: "100%",
                background: "var(--status-accepted-bg)",
                border: "none",
                cursor: "pointer",
                padding: 0,
                flexShrink: 0,
                outline: statusFilter === "accepted" ? "2px solid var(--accent)" : "none",
                outlineOffset: "1px",
              }}
            />
            <button
              onClick={() => setStatusFilter("review")}
              title="Awaiting review"
              style={{
                width: `${awaitingW}%`,
                height: "100%",
                background: "var(--status-review-bg)",
                border: "none",
                cursor: "pointer",
                padding: 0,
                flexShrink: 0,
                outline: statusFilter === "review" ? "2px solid var(--accent)" : "none",
                outlineOffset: "1px",
              }}
            />
            <button
              onClick={() => setStatusFilter("correction")}
              title="Corrections"
              style={{
                width: `${correctionsW}%`,
                height: "100%",
                background: "var(--status-overdue-bg)",
                border: "none",
                cursor: "pointer",
                padding: 0,
                flexShrink: 0,
                outline: statusFilter === "correction" ? "2px solid var(--accent)" : "none",
                outlineOffset: "1px",
              }}
            />
            <button
              onClick={() => setStatusFilter("overdue")}
              title="Overdue"
              style={{
                width: `${overdueW}%`,
                height: "100%",
                background: "color-mix(in srgb, var(--status-overdue-bg) 70%, #000 30%)",
                border: "none",
                cursor: "pointer",
                padding: 0,
                flexShrink: 0,
                outline: statusFilter === "overdue" ? "2px solid var(--accent)" : "none",
                outlineOffset: "1px",
              }}
            />
          </div>

          {/* Below-bar legend */}
          <div style={{
            fontSize: "11px",
            color: "var(--secondary)",
            marginTop: "5px",
            display: "flex",
            gap: "12px",
          }}>
            <span>accepted {AGGREGATE.accepted}</span>
            <span>·</span>
            <span>awaiting {AGGREGATE.awaiting}</span>
            <span>·</span>
            <span>corrections {AGGREGATE.corrections}</span>
            <span>·</span>
            <span>overdue {AGGREGATE.overdue}</span>
          </div>
        </div>

        {/* Filter toolbar */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          padding: "8px 12px",
        }}>
          <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
            <div style={{ position: "absolute", left: "8px", color: "var(--secondary)", pointerEvents: "none" }}>
              <Icons.Search size={14} />
            </div>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search installations…"
              style={{
                height: "32px",
                paddingLeft: "28px",
                paddingRight: "10px",
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "4px",
                fontSize: "13px",
                color: "var(--text)",
                fontFamily: "inherit",
                width: "200px",
              }}
            />
          </div>
          <Select value={portfolio} onChange={setPortfolio} options={PORTFOLIO_OPTIONS} />
          <Select value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
          <Select value={reqFilter} onChange={setReqFilter} options={REQ_OPTIONS} />
          <button
            onClick={() => { setSearch(""); setPortfolio("all"); setStatusFilter("action"); setReqFilter("all") }}
            style={{
              background: "none",
              border: "none",
              color: "var(--accent)",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              padding: "0 4px",
            }}
          >
            Reset
          </button>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: "12px", color: "var(--secondary)" }}>
            {filtered.length} {filtered.length === 1 ? "result" : "results"}
          </span>
        </div>

        {/* Portfolio comparison */}
        <div>
          <div style={{
            fontSize: "11px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--secondary)",
            marginBottom: "8px",
          }}>
            Portfolio Comparison
          </div>
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "2px",
            padding: "6px 0",
          }}>
            {PORTFOLIO_ROWS.map(p => {
              const rowPct = Math.round((p.accepted / p.total) * 100)
              const isSelected = portfolio === p.id
              return (
                <button
                  key={p.id}
                  onClick={() => setPortfolio(isSelected ? "all" : p.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    width: "100%",
                    height: "32px",
                    padding: "0 16px",
                    background: isSelected ? "color-mix(in srgb, var(--accent) 8%, transparent)" : "none",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  {/* Label */}
                  <span style={{
                    fontSize: "12px",
                    color: isSelected ? "var(--accent)" : "var(--text)",
                    fontWeight: isSelected ? 600 : 400,
                    width: "90px",
                    flexShrink: 0,
                  }}>
                    {p.label}
                  </span>

                  {/* Mini progress bar */}
                  <div style={{
                    width: "200px",
                    height: "8px",
                    borderRadius: "2px",
                    background: "var(--border)",
                    flexShrink: 0,
                    overflow: "hidden",
                  }}>
                    <div style={{
                      width: `${rowPct}%`,
                      height: "100%",
                      background: "var(--accent)",
                      borderRadius: "2px",
                    }} />
                  </div>

                  {/* Percentage */}
                  <span style={{
                    fontSize: "13px",
                    fontWeight: 700,
                    color: isSelected ? "var(--accent)" : "var(--text)",
                    width: "36px",
                    flexShrink: 0,
                  }}>
                    {rowPct}%
                  </span>

                  {/* Fraction */}
                  <span style={{
                    fontSize: "12px",
                    color: "var(--secondary)",
                  }}>
                    {p.accepted} of {p.total}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Dense table */}
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
        }}>
          <Table
            cols={cols}
            rows={filtered}
            rowHeight={44}
            emptyMessage={"No documents awaiting your review.\nAll submissions in this view have been processed."}
          />
        </div>
      </div>
    </div>
  )
}
