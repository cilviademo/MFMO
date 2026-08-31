import { useState } from "react"
import { TopBar, TabStrip, Btn, TextLink, Icons, BASE_TABS, PM_TABS, IDENTITY } from "../components/ui"
import type { Screen, StatusType, Role } from "../components/ui"
import {
  getPeriodDates, generatePeriodOptions, suspenseLabel, formatDate, formatDateWithDay, datesMatch,
} from "../utils/dates"

interface CalEvent {
  id: string
  label: string
  status: StatusType
  description: string
  isNominal?: boolean  // true = muted/dashed treatment (nominal date marker)
  authored?: boolean   // true = PM-authored event (solid border, edit/remove controls)
}

const STATUS_COLOR: Record<StatusType, string> = {
  open: "var(--status-open-text)",
  late: "var(--status-late-text)",
  overdue: "var(--status-overdue-text)",
  correction: "var(--status-overdue-text)",
  review: "var(--status-review-text)",
  accepted: "var(--status-accepted-text)",
  "not-req": "var(--status-na-text)",
}

const STATUS_BG: Record<StatusType, string> = {
  open: "var(--status-open-bg)",
  late: "var(--status-late-bg)",
  overdue: "var(--status-overdue-bg)",
  correction: "var(--status-overdue-bg)",
  review: "var(--status-review-bg)",
  accepted: "var(--status-accepted-bg)",
  "not-req": "var(--status-na-bg)",
}

// Demo date: Sep 7 2026
const DEMO_TODAY = new Date(2026, 8, 7)

// Generate events for the August 2026 demo period
// (For a fully dynamic calendar, events would be generated per selected period;
// submission events come from data. Here the data portion is demo-hardcoded.)
function buildDemoEvents(periodYear: number, periodMonth: number): Record<number, CalEvent[]> {
  const pd = getPeriodDates(periodYear, periodMonth)
  const nomSame = datesMatch(pd.nominalInitial, pd.effectiveInitial)

  // Day-offset helper: days since Aug 1 (period start)
  // day 1 = first day of period month
  const offset = (d: Date) => {
    const base = new Date(periodYear, periodMonth, 1)
    return Math.round((d.getTime() - base.getTime()) / 86400000) + 1
  }

  const events: Record<number, CalEvent[]> = {}
  const add = (day: number, ev: CalEvent) => {
    if (!events[day]) events[day] = []
    events[day].push(ev)
  }

  // Period close
  add(offset(pd.periodClose), {
    id: "close",
    label: `${formatDate(pd.periodClose)} period closes`,
    status: "open",
    description: `Reporting period for ${periodMonth === 7 ? "August" : ""} ${periodYear} closes. No further submissions accepted after midnight.`,
  })

  // Nominal initial suspense (muted, dashed) — only when different from effective
  if (!nomSame) {
    add(offset(pd.nominalInitial), {
      id: "init-nominal",
      label: "Initial suspense (nominal)",
      status: "late",
      description: `Nominal initial suspense date. Falls on a non-duty day — effective suspense is ${formatDateWithDay(pd.effectiveInitial)}.`,
      isNominal: true,
    })
  }

  // Effective initial suspense
  add(offset(pd.effectiveInitial), {
    id: "init-effective",
    label: nomSame ? "Initial suspense" : "Initial suspense — effective",
    status: "late",
    description: `Initial suspense date for all ${periodYear} EOM packages. Installations not yet submitted are now late.`,
  })

  // Final call
  add(offset(pd.nominalFinal), {
    id: "final",
    label: "Final call",
    status: "overdue",
    description: "Final call deadline. Any package not submitted by midnight is overdue. No extensions without PM approval.",
  })

  // Quarterly 1038 — only for periods ending Dec/Mar/Jun/Sep
  if (pd.isQuarterlyPeriod) {
    add(offset(pd.effectiveInitial), {
      id: "1038",
      label: `1038 due (Q${pd.fiscalQuarter})`,
      status: "open",
      description: `Quarterly AF Form 1038 due for Q${pd.fiscalQuarter}.`,
    })
  }

  // EOY requirements — only for September period
  if (pd.isEOYPeriod) {
    add(offset(pd.nominalFinal), {
      id: "eoy",
      label: "EOY MFR and inventory",
      status: "open",
      description: "End-of-year management review and physical inventory required for September period.",
    })
  }

  // Demo submission events (data-driven in production)
  if (periodYear === 2026 && periodMonth === 7) {
    add(35, { id: "e-1119-sub", label: "1119 submitted",  status: "review",    description: "AF Form 1119 submitted by JBSA Lackland." })
    add(36, { id: "e-gpc-sub",  label: "GPC submitted",   status: "accepted",  description: "GPC Bank Statement accepted — JBSA Lackland." })
    // PM-authored demo event: day offset 40 = Sep 9
    add(40, {
      id: "pm-assess-prep",
      label: "Assessment prep",
      status: "open",
      description: "Internal preparation for September assessment. PM authored.",
      authored: true,
    })
  }

  return events
}

const DAY_NAMES = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]

// Add a date dialog
interface AddDateDialogProps {
  onClose: () => void
}

function AddDateDialog({ onClose }: AddDateDialogProps) {
  const [type, setType] = useState("")
  const [title, setTitle] = useState("")
  const [date, setDate] = useState("")
  const [showEndDate, setShowEndDate] = useState(false)
  const [endDate, setEndDate] = useState("")
  const [appliesTo, setAppliesTo] = useState("This portfolio")

  const canSubmit = type !== "" && title.trim() !== "" && date !== ""

  const inputStyle: React.CSSProperties = {
    width: "100%",
    height: "32px",
    padding: "0 8px",
    background: "var(--bg)",
    border: "1px solid var(--border)",
    borderRadius: "4px",
    fontSize: "13px",
    color: "var(--text)",
    boxSizing: "border-box",
  }

  const labelStyle: React.CSSProperties = {
    fontSize: "12px",
    fontWeight: 600,
    color: "var(--secondary)",
    marginBottom: "4px",
    display: "block",
  }

  return (
    // Backdrop
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      {/* Dialog */}
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "6px",
          width: "420px",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.28)",
        }}
      >
        <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text)" }}>
          Add a date
        </div>

        {/* Type */}
        <div>
          <label style={labelStyle}>Type</label>
          <select
            value={type}
            onChange={e => setType(e.target.value)}
            style={{ ...inputStyle, cursor: "pointer" }}
          >
            <option value="">Select type…</option>
            <option value="Correction due">Correction due</option>
            <option value="Assessment">Assessment</option>
            <option value="Data call">Data call</option>
            <option value="Reminder">Reminder</option>
          </select>
        </div>

        {/* Title */}
        <div>
          <label style={labelStyle}>Title</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Enter title"
            style={inputStyle}
          />
        </div>

        {/* Date */}
        <div>
          <label style={labelStyle}>Date</label>
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            style={inputStyle}
          />
          {/* End date toggle */}
          <div style={{ marginTop: "8px" }}>
            {!showEndDate ? (
              <button
                onClick={() => setShowEndDate(true)}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  cursor: "pointer",
                  fontSize: "12px",
                  color: "var(--accent)",
                  fontWeight: 600,
                }}
              >
                + end date
              </button>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={labelStyle}>Spans to</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  style={inputStyle}
                />
              </div>
            )}
          </div>
        </div>

        {/* Applies to */}
        <div>
          <label style={labelStyle}>Applies to</label>
          <select
            value={appliesTo}
            onChange={e => setAppliesTo(e.target.value)}
            style={{ ...inputStyle, cursor: "pointer" }}
          >
            <option value="This portfolio">This portfolio</option>
            <option value="One installation">One installation</option>
            <option value="One facility">One facility</option>
          </select>
        </div>

        {/* Buttons */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <Btn variant="subtle" onClick={onClose}>
            Cancel
          </Btn>
          <Btn
            variant="primary"
            onClick={() => { if (canSubmit) onClose() }}
            style={{ opacity: canSubmit ? 1 : 0.4, cursor: canSubmit ? "pointer" : "not-allowed" }}
          >
            Add date
          </Btn>
        </div>
      </div>
    </div>
  )
}

interface CalendarProps {
  nav: (s: Screen) => void
  role?: Role
  showAddDate?: boolean
}

export default function CalendarScreen({ nav, role = "base", showAddDate = false }: CalendarProps) {
  const isBase = role === "base"
  const tabs = isBase ? BASE_TABS : PM_TABS
  const ident = isBase ? IDENTITY.base : IDENTITY.pm

  // Period selector — rolling window relative to demo today
  const periodOptions = generatePeriodOptions(DEMO_TODAY)
  const defaultPeriod = periodOptions.find(o => o.year === 2026 && o.month === 7)!
  const [selectedPeriod, setSelectedPeriod] = useState(defaultPeriod)

  const pd = getPeriodDates(selectedPeriod.year, selectedPeriod.month)
  const nomSame = datesMatch(pd.nominalInitial, pd.effectiveInitial)

  // Calendar grid: show selected month + overflow from following month
  const periodYear = selectedPeriod.year
  const periodMonth = selectedPeriod.month
  const firstDay = new Date(periodYear, periodMonth, 1).getDay()  // 0=Sun
  const daysInMonth = new Date(periodYear, periodMonth + 1, 0).getDate()

  // Build cell array: null=blank, positive=day-in-period, negative=overflow
  const cells: (number | null)[] = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  for (let d = 1; cells.length % 7 !== 0 || cells.length < (firstDay + daysInMonth + 7); d++) {
    if (d > 20) break
    cells.push(daysInMonth + d) // overflow: day offset from month start
  }
  while (cells.length % 7 !== 0) cells.push(null)

  const weeks: (number | null)[][] = []
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))

  const events = buildDemoEvents(periodYear, periodMonth)

  // offset: day number within period (1 = first of month, daysInMonth+1 = first of next)
  const getEvents = (day: number): CalEvent[] => events[day] ?? []

  const [selectedDay, setSelectedDay] = useState<number | null>(() => {
    // Default: effective initial suspense
    const base = new Date(periodYear, periodMonth, 1)
    return Math.round((pd.effectiveInitial.getTime() - base.getTime()) / 86400000) + 1
  })

  const [addDateOpen, setAddDateOpen] = useState(showAddDate)

  const selectedEvents = selectedDay ? getEvents(selectedDay) : []

  const isToday = (day: number): boolean => {
    const d = new Date(periodYear, periodMonth, day)
    return datesMatch(d, DEMO_TODAY)
  }

  const MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
  ]

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip tabs={tabs} active="calendar" onChange={id => {
        if (id === "home") nav("base-home")
        if (id === "package") nav("my-package")
        if (id === "overview") nav("afsvc-overview")
        if (id === "review") nav("review-queue")
        if (id === "installations") nav("installation")
        if (id === "admin") nav("admin")
      }} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "20px" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: 0 }}>
            {MONTH_NAMES[periodMonth]} {periodYear}
          </h1>

          {/* Period selector — generated rolling window */}
          <select
            value={selectedPeriod.value}
            onChange={e => {
              const opt = periodOptions.find(o => o.value === e.target.value)
              if (opt) {
                setSelectedPeriod(opt)
                setSelectedDay(null)
              }
            }}
            style={{
              height: "30px",
              padding: "0 8px",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "4px",
              fontSize: "12px",
              color: "var(--text)",
              cursor: "pointer",
            }}
          >
            {periodOptions.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <div style={{ flex: 1 }} />
          {/* PM: no "+ Add a date" in header — it lives in the side panel */}
          <div style={{ display: "flex", gap: "4px" }}>
            <button
              onClick={() => {
                const prev = periodOptions[periodOptions.findIndex(o => o.value === selectedPeriod.value) - 1]
                if (prev) { setSelectedPeriod(prev); setSelectedDay(null) }
              }}
              style={{
                width: "30px", height: "30px", background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "4px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text)",
              }}
            >
              <Icons.ChevronLeft size={14} />
            </button>
            <button
              onClick={() => {
                const now = periodOptions.find(o => o.year === DEMO_TODAY.getFullYear() && o.month === DEMO_TODAY.getMonth())
                if (now) { setSelectedPeriod(now); setSelectedDay(null) }
              }}
              style={{
                height: "30px", padding: "0 12px", background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "4px", cursor: "pointer", fontSize: "12px", fontWeight: 600, color: "var(--text)",
              }}
            >
              Today
            </button>
            <button
              onClick={() => {
                const next = periodOptions[periodOptions.findIndex(o => o.value === selectedPeriod.value) + 1]
                if (next) { setSelectedPeriod(next); setSelectedDay(null) }
              }}
              style={{
                width: "30px", height: "30px", background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "4px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text)",
              }}
            >
              <Icons.ChevronRight size={14} />
            </button>
          </div>
          {/* Month/Agenda segmented */}
          <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: "4px", overflow: "hidden" }}>
            {["Month", "Agenda"].map((v, i) => (
              <button key={v} style={{
                height: "30px", padding: "0 14px",
                background: i === 0 ? "var(--accent)" : "var(--surface)",
                color: i === 0 ? "#fff" : "var(--text)",
                border: "none",
                borderRight: i === 0 ? "1px solid var(--border)" : "none",
                cursor: "pointer", fontSize: "12px", fontWeight: i === 0 ? 600 : 400,
              }}>
                {v}
              </button>
            ))}
          </div>
        </div>

        {/* Key dates legend — shows nominal vs effective distinction */}
        <div style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          padding: "10px 0",
          borderBottom: "1px solid var(--border)",
          fontSize: "12px",
        }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--secondary)", fontWeight: 600 }}>
            <Icons.Calendar size={11} />
            {formatDate(pd.periodClose)} — Period closes
          </span>
          {!nomSame && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--status-late-text)", fontWeight: 600, opacity: 0.6 }}>
              <Icons.Calendar size={11} />
              {formatDate(pd.nominalInitial)} — Initial suspense (nominal)
            </span>
          )}
          <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--status-late-text)", fontWeight: 600 }}>
            <Icons.Calendar size={11} />
            {nomSame ? formatDate(pd.nominalInitial) : formatDateWithDay(pd.effectiveInitial)} — Initial suspense{!nomSame ? " — effective" : ""}
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--status-overdue-text)", fontWeight: 600 }}>
            <Icons.Calendar size={11} />
            {formatDate(pd.nominalFinal)} — Final call
          </span>
          {pd.isQuarterlyPeriod && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--status-open-text)", fontWeight: 600 }}>
              <Icons.Calendar size={11} />
              1038 quarterly
            </span>
          )}
        </div>

        {/* Grid + side panel */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: "24px", alignItems: "start" }}>

          {/* Calendar grid */}
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "2px",
            overflow: "hidden",
          }}>
            {/* Day headers */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", borderBottom: "1px solid var(--border)" }}>
              {DAY_NAMES.map((d, i) => (
                <div key={d} style={{
                  height: "30px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "11px",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                  color: "var(--secondary)",
                  borderRight: i < 6 ? "1px solid var(--border)" : "none",
                }}>
                  {d}
                </div>
              ))}
            </div>

            {weeks.map((week, wi) => (
              <div key={wi} style={{
                display: "grid",
                gridTemplateColumns: "repeat(7, 1fr)",
                borderBottom: wi < weeks.length - 1 ? "1px solid var(--border)" : "none",
              }}>
                {week.map((day, di) => {
                  if (day === null) {
                    return (
                      <div key={di} style={{
                        minHeight: "80px",
                        borderRight: di < 6 ? "1px solid var(--border)" : "none",
                        background: "var(--bg)",
                      }} />
                    )
                  }
                  const evs = getEvents(day)
                  const isCurrentMonth = day <= daysInMonth
                  const today = isCurrentMonth && isToday(day)
                  const selected = selectedDay === day
                  const dNum = isCurrentMonth ? day : day - daysInMonth
                  const visible = evs.slice(0, 3)
                  const overflow = evs.length - 3

                  return (
                    <div
                      key={di}
                      onClick={() => setSelectedDay(day)}
                      style={{
                        minHeight: "80px",
                        padding: "4px",
                        borderRight: di < 6 ? "1px solid var(--border)" : "none",
                        cursor: "pointer",
                        background: selected ? "var(--status-open-bg)" : !isCurrentMonth ? "var(--bg)" : "transparent",
                        borderTop: today ? "2px solid var(--accent)" : "none",
                      }}
                    >
                      <div style={{
                        fontSize: "12px",
                        color: today ? "var(--accent)" : !isCurrentMonth ? "var(--secondary)" : "var(--text)",
                        fontWeight: today ? 700 : 400,
                        marginBottom: "4px",
                      }}>
                        {!isCurrentMonth && <span style={{ fontSize: "10px", color: "var(--secondary)" }}>
                          {new Date(periodYear, periodMonth + 1, 1).toLocaleString("en-US", { month: "short" })}{" "}
                        </span>}
                        {dNum}
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                        {visible.map(ev => (
                          <div key={ev.id} style={{
                            borderLeft: ev.isNominal
                              ? `2.5px dashed ${STATUS_COLOR[ev.status]}`
                              : `2.5px solid ${STATUS_COLOR[ev.status]}`,
                            background: ev.isNominal
                              ? "transparent"
                              : STATUS_BG[ev.status],
                            padding: "1px 4px",
                            fontSize: "10px",
                            color: STATUS_COLOR[ev.status],
                            fontWeight: 600,
                            opacity: ev.isNominal ? 0.55 : ev.authored ? 0.9 : 1,
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            borderRadius: "0 1px 1px 0",
                          }}>
                            {ev.label}
                          </div>
                        ))}
                        {overflow > 0 && (
                          <div style={{ fontSize: "10px", color: "var(--accent)", fontWeight: 600, paddingLeft: "4px" }}>
                            +{overflow} more
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ))}
          </div>

          {/* Side panel */}
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "2px",
            position: "sticky",
            top: 0,
          }}>
            <div style={{
              padding: "0 16px",
              height: "44px",
              display: "flex",
              alignItems: "center",
              borderBottom: "1px solid var(--border)",
              fontSize: "13px",
              fontWeight: 600,
              color: "var(--text)",
            }}>
              {selectedDay
                ? selectedDay <= daysInMonth
                  ? `${new Date(periodYear, periodMonth, selectedDay).toLocaleString("en-US", { month: "short", day: "numeric" })}`
                  : `${new Date(periodYear, periodMonth + 1, selectedDay - daysInMonth).toLocaleString("en-US", { month: "short", day: "numeric" })}`
                : "Select a day"
              }
            </div>

            {/* Suspense summary in panel */}
            {!nomSame && selectedDay === null && (
              <div style={{
                padding: "10px 16px",
                borderBottom: "1px solid var(--border)",
                fontSize: "12px",
                color: "var(--secondary)",
                lineHeight: 1.5,
              }}>
                <span style={{ color: "var(--text)", fontWeight: 600 }}>Suspense</span>
                <br />
                <span style={{ opacity: 0.6 }}>Nominal: {formatDate(pd.nominalInitial)} (non-duty day)</span>
                <br />
                <span style={{ color: "var(--status-late-text)", fontWeight: 600 }}>Effective: {formatDateWithDay(pd.effectiveInitial)}</span>
              </div>
            )}

            <div style={{ padding: "12px 16px" }}>
              {isBase ? (
                /* Base user: existing behavior */
                selectedEvents.length === 0 ? (
                  <div style={{ fontSize: "13px", color: "var(--secondary)", padding: "12px 0" }}>
                    No deadlines on this day.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {selectedEvents.map(ev => (
                      <div key={ev.id} style={{
                        borderLeft: ev.isNominal
                          ? `3px dashed ${STATUS_COLOR[ev.status]}`
                          : `3px solid ${STATUS_COLOR[ev.status]}`,
                        background: ev.isNominal ? "transparent" : STATUS_BG[ev.status],
                        padding: "10px 12px",
                        borderRadius: "0 2px 2px 0",
                        opacity: ev.isNominal ? 0.7 : 1,
                      }}>
                        <div style={{ fontSize: "13px", fontWeight: 700, color: STATUS_COLOR[ev.status], marginBottom: "4px" }}>
                          {ev.label}
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--secondary)", lineHeight: 1.5 }}>
                          {ev.description}
                        </div>
                      </div>
                    ))}
                    <Btn
                      variant="subtle"
                      style={{ marginTop: "4px", width: "100%", justifyContent: "center", fontSize: "12px", height: "28px" }}
                      onClick={() => nav("my-package")}
                    >
                      View package
                    </Btn>
                  </div>
                )
              ) : (
                /* PM user: Add a date button + event list with edit/remove controls */
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <Btn
                    variant="primary"
                    style={{ width: "100%", justifyContent: "center", fontSize: "12px", height: "30px" }}
                    onClick={() => setAddDateOpen(true)}
                  >
                    <Icons.Plus size={13} />
                    Add a date
                  </Btn>

                  {selectedEvents.length === 0 ? (
                    <div style={{ fontSize: "13px", color: "var(--secondary)", padding: "4px 0" }}>
                      No deadlines on this day.
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {selectedEvents.map(ev => (
                        <div key={ev.id} style={{
                          borderLeft: ev.isNominal
                            ? `3px dashed ${STATUS_COLOR[ev.status]}`
                            : `3px solid ${STATUS_COLOR[ev.status]}`,
                          background: ev.isNominal ? "transparent" : STATUS_BG[ev.status],
                          padding: "10px 12px",
                          borderRadius: "0 2px 2px 0",
                          opacity: ev.isNominal ? 0.7 : 1,
                        }}>
                          <div style={{ display: "flex", alignItems: "baseline", gap: "8px", flexWrap: "wrap", marginBottom: "4px" }}>
                            <span style={{ fontSize: "13px", fontWeight: 700, color: STATUS_COLOR[ev.status] }}>
                              {ev.label}
                            </span>
                            {ev.authored && (
                              <>
                                <TextLink onClick={() => {}} style={{ fontSize: "11px" }}>Edit</TextLink>
                                <TextLink onClick={() => {}} style={{ fontSize: "11px", color: "var(--status-overdue-text)" }}>Remove</TextLink>
                              </>
                            )}
                          </div>
                          <div style={{ fontSize: "12px", color: "var(--secondary)", lineHeight: 1.5 }}>
                            {ev.description}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add a date dialog */}
      {addDateOpen && <AddDateDialog onClose={() => setAddDateOpen(false)} />}
    </div>
  )
}
