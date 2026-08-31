import { TopBar, TabStrip, StatusChip, Btn, TextLink, ProgressBar, Icons } from "../components/ui"
import type { Screen, StatusType } from "../components/ui"
import { getPeriodDates, suspenseLabel, formatDate, formatDateWithDay, datesMatch } from "../utils/dates"

interface ActionItem {
  code: string
  name: string
  situation: string
  action: "submit" | "resubmit"
}

interface ReviewItem {
  code: string
  name: string
  submitted: string
}

interface AcceptedItem {
  code: string
  name: string
  accepted: string
}

function SectionHead({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: "11px",
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.06em",
      color: "var(--secondary)",
      marginBottom: "0",
      paddingBottom: "8px",
      borderBottom: "1px solid var(--border)",
    }}>
      {children}
    </div>
  )
}

interface BaseHomeProps {
  hasCorrection?: boolean
  narrow?: boolean
  nav: (s: Screen) => void
}

// Demo date: Sep 7 2026 (Labor Day — used throughout the prototype)
const DEMO_TODAY = new Date(2026, 8, 7) // month is 0-indexed

const PERIOD_DATES = getPeriodDates(2026, 7) // August 2026

const ACTION_ITEMS_NORMAL: ActionItem[] = []
const ACTION_ITEMS_CORRECTION: ActionItem[] = [
  {
    code: "SF 1080",
    name: "Voucher for Transfers",
    situation: "Late — final call 10 Sep",
    action: "submit",
  },
  {
    code: "SAIIT",
    name: "Sales, Adjustments, Invoices, Inventory and Transfers",
    situation: "Returned · Wrong reporting period",
    action: "resubmit",
  },
]

const REVIEW_ITEMS: ReviewItem[] = [
  { code: "1119", name: "AF Form 1119 Feeding Summary", submitted: "4 Sep 09:14" },
]

const ACCEPTED_ITEMS: AcceptedItem[] = [
  { code: "GPC",     name: "GPC Bank Statement",                                      accepted: "3 Sep" },
  { code: "SF 1080", name: "Voucher for Transfers",                                   accepted: "2 Sep" },
  { code: "SAIIT",   name: "Sales, Adjustments, Invoices, Inventory and Transfers",   accepted: "1 Sep" },
]

const TABS_BASE = [
  { id: "home", label: "Home" },
  { id: "package", label: "My Package", badge: 2 },
  { id: "calendar", label: "Calendar" },
]

// ── Mini calendar card ────────────────────────────────────────────────────────

// August 2026: starts Saturday (day-of-week index 6 in Sun-first grid)
const AUG_START_DOW = 6
const AUG_DAYS = 31

// Key dates for the mini grid (using day-of-month offset from Aug 1):
// Aug 31 = offset 30 (0-indexed), Sep 5 = offset 35, Sep 7 = offset 37, Sep 8 = offset 38, Sep 10 = offset 40
function buildMiniGridCells() {
  const cells: (number | null)[] = []
  for (let i = 0; i < AUG_START_DOW; i++) cells.push(null) // leading blanks
  for (let d = 1; d <= AUG_DAYS; d++) cells.push(d)       // August
  for (let d = 1; d <= 14; d++) cells.push(AUG_DAYS + d)  // September overflow
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

const MINI_CELLS = buildMiniGridCells()

// Returns status-colour bar for a cell day (1=Aug1 … 45=Sep14)
type BarStyle = { color: string; opacity?: number; borderStyle?: string }
function getBarStyle(day: number): BarStyle | null {
  if (day === 31) return { color: "var(--secondary)", opacity: 0.6 }               // Aug 31: period closes (past, muted)
  if (day === 36) return { color: "var(--status-late-text)", opacity: 0.45, borderStyle: "dashed" } // Sep 5: nominal (muted)
  if (day === 39) return { color: "var(--status-late-text)" }                        // Sep 8: effective initial (amber)
  if (day === 41) return { color: "var(--status-overdue-text)" }                     // Sep 10: final call (red)
  return null
}

function isToday(day: number): boolean {
  // Today in demo: Sep 7 = day 38 (Aug has 31 days, Sep 7 = 31+7=38)
  return day === 38
}

function MiniCalendarCard({ nav, narrow }: { nav: (s: Screen) => void; narrow?: boolean }) {
  const pd = PERIOD_DATES
  const nomInit = pd.nominalInitial
  const effInit = pd.effectiveInitial
  const nomFinal = pd.nominalFinal

  const initLabel = datesMatch(nomInit, effInit)
    ? formatDate(nomInit)
    : `${formatDate(nomInit)} · effective ${formatDateWithDay(effInit)}`

  // Countdown from demo today (Sep 7) to Sep 10 = 3 days
  const daysToFinal = Math.round((nomFinal.getTime() - DEMO_TODAY.getTime()) / 86400000)

  const DAY_LETTERS = ["S", "M", "T", "W", "T", "F", "S"]
  const weeks: (number | null)[][] = []
  for (let i = 0; i < MINI_CELLS.length; i += 7) {
    weeks.push(MINI_CELLS.slice(i, i + 7))
  }

  const CELL = 28

  return (
    <div style={{
      border: "1px solid var(--border)",
      borderRadius: "2px",
      background: "var(--surface)",
      marginBottom: "24px",
      display: "flex",
      flexDirection: narrow ? "column" : "row",
    }}>
      {/* Left: mini grid */}
      <div style={{
        width: narrow ? "100%" : "40%",
        borderRight: narrow ? "none" : "1px solid var(--border)",
        borderBottom: narrow ? "1px solid var(--border)" : "none",
        padding: "12px",
        flexShrink: 0,
      }}>
        <div style={{
          fontSize: "11px",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--secondary)",
          marginBottom: "8px",
        }}>
          August 2026
        </div>
        {/* Day letter headers */}
        <div style={{ display: "grid", gridTemplateColumns: `repeat(7, ${CELL}px)` }}>
          {DAY_LETTERS.map((l, i) => (
            <div key={i} style={{
              width: CELL,
              height: 18,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "10px",
              fontWeight: 600,
              color: "var(--secondary)",
              opacity: 0.7,
            }}>
              {l}
            </div>
          ))}
        </div>
        {/* Weeks */}
        {weeks.map((week, wi) => (
          <div key={wi} style={{ display: "grid", gridTemplateColumns: `repeat(7, ${CELL}px)` }}>
            {week.map((day, di) => {
              if (day === null) {
                return <div key={di} style={{ width: CELL, height: CELL }} />
              }
              const isAug = day <= 31
              const dayNum = isAug ? day : day - 31
              const bar = getBarStyle(day)
              const today = isToday(day)
              return (
                <div
                  key={di}
                  style={{
                    width: CELL,
                    height: CELL,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    position: "relative",
                    borderTop: today ? "2px solid var(--accent)" : "none",
                  }}
                >
                  <span style={{
                    fontSize: "11px",
                    color: today
                      ? "var(--accent)"
                      : isAug
                        ? "var(--text)"
                        : "var(--secondary)",
                    fontWeight: today ? 700 : (bar ? 600 : 400),
                    opacity: !isAug && !bar && !today ? 0.5 : 1,
                  }}>
                    {dayNum}
                  </span>
                  {bar && (
                    <div style={{
                      position: "absolute",
                      bottom: 3,
                      left: "15%",
                      right: "15%",
                      height: 3,
                      borderRadius: 2,
                      background: bar.color,
                      opacity: bar.opacity ?? 1,
                      borderBottom: bar.borderStyle === "dashed" ? `2px dashed ${bar.color}` : undefined,
                      backgroundClip: bar.borderStyle === "dashed" ? "unset" : undefined,
                      ...(bar.borderStyle === "dashed" ? { background: "none" } : {}),
                    }} />
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>

      {/* Right: agenda */}
      <div style={{
        flex: 1,
        padding: "14px 18px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}>
        <div>
          <div style={{
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--secondary)",
            marginBottom: "12px",
          }}>
            August 2026 EOM
          </div>

          {/* Row 1: period close — past */}
          <div style={{
            display: "flex",
            alignItems: "baseline",
            gap: "12px",
            marginBottom: "8px",
            opacity: 0.6,
          }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text)", minWidth: "44px" }}>31 Aug</span>
            <span style={{ fontSize: "12px", color: "var(--secondary)", flex: 1 }}>Reporting period closed</span>
            <span style={{ fontSize: "12px", color: "var(--status-accepted-text)", fontWeight: 600 }}>✓</span>
          </div>

          {/* Row 2: initial suspense — passed (nominal past, effective tomorrow) */}
          <div style={{
            display: "flex",
            alignItems: "baseline",
            gap: "12px",
            marginBottom: "8px",
            opacity: 0.65,
          }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text)", minWidth: "44px" }}>5 Sep</span>
            <span style={{ fontSize: "12px", color: "var(--secondary)", flex: 1 }}>
              Initial suspense
              {!datesMatch(nomInit, effInit) && (
                <span style={{ color: "var(--status-late-text)", fontWeight: 600 }}>
                  {" "}· effective {formatDateWithDay(effInit)}
                </span>
              )}
            </span>
            <span style={{ fontSize: "11px", color: "var(--secondary)", fontWeight: 600 }}>passed</span>
          </div>

          {/* Row 3: final call — next, emphasised */}
          <div style={{
            display: "flex",
            alignItems: "baseline",
            gap: "12px",
          }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text)", minWidth: "44px" }}>10 Sep</span>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text)", flex: 1 }}>Final call</span>
            <span style={{
              fontSize: "11px",
              fontWeight: 700,
              color: "var(--status-late-text)",
              background: "var(--status-late-bg)",
              border: "1px solid var(--status-late-border)",
              borderRadius: "3px",
              padding: "1px 6px",
            }}>
              {daysToFinal} {daysToFinal === 1 ? "day" : "days"}
            </span>
          </div>
        </div>

        <div style={{ marginTop: "12px" }}>
          <TextLink onClick={() => nav("calendar")} style={{ fontSize: "12px" }}>
            Open calendar <Icons.ChevronRight size={11} />
          </TextLink>
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function BaseHome({ hasCorrection = false, narrow = false, nav }: BaseHomeProps) {
  const actionItems = hasCorrection ? ACTION_ITEMS_CORRECTION : ACTION_ITEMS_NORMAL

  const submitted = hasCorrection ? 3 : 4
  const total = 5
  const accepted = hasCorrection ? 1 : 3
  const awaitingReview = 1
  const missing = 0

  const packageStatus: StatusType = hasCorrection ? "correction" : "review"

  const pd = PERIOD_DATES
  const initSuspense = suspenseLabel(pd.nominalInitial, pd.effectiveInitial)
  const finalCall = formatDate(pd.nominalFinal)

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "var(--bg)",
    }}>
      <TopBar
        period="August 2026"
        userName="SrA Kim, P."
        userRole="Base Accountant, JBSA Lackland"
        userInitials="PK"
      />
      <TabStrip tabs={TABS_BASE} active="home" onChange={id => {
        if (id === "package") nav("my-package")
        if (id === "calendar") nav("calendar")
      }} />

      <div style={{
        flex: 1,
        overflow: "auto",
        padding: narrow ? "24px 20px" : "40px",
        maxWidth: narrow ? "100%" : undefined,
      }}>

        {/* Plain-text header */}
        <div style={{ marginBottom: "32px" }}>
          <h1 style={{
            fontSize: "32px",
            fontWeight: 300,
            color: "var(--text)",
            margin: "0 0 4px",
            lineHeight: 1.2,
          }}>
            JBSA Lackland
          </h1>
          <div style={{ fontSize: "16px", fontWeight: 600, color: "var(--text)", marginBottom: "6px" }}>
            August 2026 EOM
          </div>
          <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
            Legacy / APF &nbsp;·&nbsp; Portfolio 2 &nbsp;·&nbsp;{" "}
            <span style={{ color: "var(--text)" }}>Due {initSuspense}</span>
            &nbsp;·&nbsp; Final call {finalCall}
          </div>
        </div>

        {/* Package strip */}
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          padding: "16px 20px",
          marginBottom: "24px",
        }}>
          <div style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: "20px",
            flexWrap: narrow ? "wrap" : "nowrap",
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                marginBottom: "6px",
              }}>
                <span style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--secondary)",
                }}>
                  August EOM Package
                </span>
                <span style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  color: packageStatus === "correction"
                    ? "var(--status-overdue-text)"
                    : "var(--status-review-text)",
                }}>
                  {packageStatus === "correction" ? "Correction required" : "In review"}
                </span>
              </div>
              <div style={{
                fontSize: "13px",
                color: "var(--secondary)",
                marginBottom: "10px",
              }}>
                {submitted} of {total} submitted
                {` · ${accepted} accepted`}
                {awaitingReview > 0 && ` · ${awaitingReview} awaiting AFSVC`}
                {missing > 0 && (
                  <span style={{ color: "var(--status-overdue-text)", fontWeight: 600 }}>
                    {` · ${missing} missing`}
                  </span>
                )}
              </div>
              <ProgressBar value={accepted} max={total} />
            </div>
            <div style={{
              display: "flex",
              gap: "8px",
              flexShrink: 0,
              alignItems: "flex-start",
            }}>
              <Btn variant="primary" onClick={() => nav("submit")}>
                <Icons.Upload size={14} />
                Submit document
              </Btn>
              <Btn variant="subtle" onClick={() => nav("my-package")}>
                Open package
              </Btn>
            </div>
          </div>
        </div>

        {/* Calendar card — below package strip, above sections */}
        <MiniCalendarCard nav={nav} narrow={narrow} />

        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>

          {/* ACTION REQUIRED */}
          {actionItems.length > 0 && (
            <div>
              <SectionHead>Action required</SectionHead>
              <div style={{ display: "flex", flexDirection: "column" }}>
                {actionItems.map((item, i) => (
                  <div key={item.code} style={{
                    display: "flex",
                    alignItems: narrow ? "flex-start" : "center",
                    flexDirection: narrow ? "column" : "row",
                    justifyContent: "space-between",
                    gap: "8px",
                    padding: "12px 0",
                    borderBottom: i < actionItems.length - 1 ? "1px solid var(--border)" : "none",
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                        <span style={{
                          fontSize: "13px",
                          fontWeight: 700,
                          color: "var(--text)",
                          fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                        }}>
                          {item.code}
                        </span>
                        <span style={{ fontSize: "13px", color: "var(--secondary)" }}>
                          {item.name}
                        </span>
                      </div>
                      <div style={{
                        fontSize: "13px",
                        color: "var(--status-overdue-text)",
                        fontWeight: 600,
                        marginTop: "3px",
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                      }}>
                        <Icons.AlertCircle size={12} />
                        {item.situation}
                      </div>
                    </div>
                    <Btn
                      variant={item.action === "resubmit" ? "primary" : "secondary"}
                      onClick={() => nav("submit")}
                      style={{ flexShrink: 0 }}
                    >
                      {item.action === "resubmit" ? "Submit correction" : "Submit"}
                    </Btn>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* WAITING ON AFSVC */}
          {REVIEW_ITEMS.length > 0 && (
            <div>
              <SectionHead>Waiting on AFSVC</SectionHead>
              <div>
                {REVIEW_ITEMS.map((item, i) => (
                  <div key={item.code} style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "12px 0",
                    borderBottom: i < REVIEW_ITEMS.length - 1 ? "1px solid var(--border)" : "none",
                    flexWrap: narrow ? "wrap" : "nowrap",
                  }}>
                    <StatusChip status="review" />
                    <div style={{ flex: 1 }}>
                      <span style={{
                        fontSize: "13px",
                        fontWeight: 700,
                        color: "var(--text)",
                        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                        marginRight: "10px",
                      }}>
                        {item.code}
                      </span>
                      <span style={{ fontSize: "13px", color: "var(--secondary)" }}>
                        {item.name}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--secondary)", whiteSpace: "nowrap" }}>
                      Submitted {item.submitted}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ACCEPTED */}
          {ACCEPTED_ITEMS.length > 0 && (
            <div>
              <SectionHead>Accepted</SectionHead>
              <div>
                {ACCEPTED_ITEMS.map((item, i) => (
                  <div key={item.code} style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "12px 0",
                    borderBottom: i < ACCEPTED_ITEMS.length - 1 ? "1px solid var(--border)" : "none",
                  }}>
                    <StatusChip status="accepted" />
                    <div style={{ flex: 1 }}>
                      <span style={{
                        fontSize: "13px",
                        fontWeight: 700,
                        color: "var(--text)",
                        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                        marginRight: "10px",
                      }}>
                        {item.code}
                      </span>
                      <span style={{ fontSize: "13px", color: "var(--secondary)" }}>
                        {item.name}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--status-accepted-text)", fontWeight: 600 }}>
                      Accepted {item.accepted}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Correction detail block */}
          {hasCorrection && (
            <div style={{
              background: "var(--status-overdue-bg)",
              border: "1px solid var(--status-overdue-border)",
              borderLeft: "3px solid var(--status-overdue-border)",
              borderRadius: "0 2px 2px 0",
              padding: "16px 20px",
            }}>
              <div style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "var(--status-overdue-text)",
                marginBottom: "8px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}>
                <Icons.AlertCircle size={12} />
                SAIIT — Correction required
              </div>
              <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text)", marginBottom: "4px" }}>
                Wrong reporting period
              </div>
              <div style={{ fontSize: "13px", color: "var(--secondary)", marginBottom: "12px" }}>
                <strong style={{ color: "var(--text)", fontStyle: "normal" }}>AFSVC comment</strong>
                <br />
                <em>"The uploaded SAIIT reflects July. Submit the August review."</em>
              </div>
              <div style={{ fontSize: "12px", color: "var(--secondary)", marginBottom: "12px" }}>
                Returned 9 Sep 2026
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <Btn variant="primary" onClick={() => nav("submit")}>Submit correction</Btn>
                <Btn variant="subtle">Open previous submission</Btn>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
