import shieldSrc from "../imports/AFSVC_Shield.png"
import { Icons, ProgressBar } from "../components/ui"
import type { Screen, Role } from "../components/ui"

// Cycle dates — August 2026 EOM
// Demo: today is 7 Sep 2026 (between initial suspense and final call)
const CYCLE = {
  period: "AUGUST 2026 EOM",
  dates: [
    { label: "Reporting period closed", date: "31 Aug", state: "past" as const },
    { label: "Initial suspense", date: "5 Sep", state: "past" as const },
    { label: "Final call", date: "10 Sep", state: "next" as const },
  ],
  // Base user view — JBSA Lackland, Portfolio 2
  base: {
    label: "Your package",
    submitted: 4,
    total: 5,
    detail: "1 awaiting AFSVC review · 1 not yet submitted",
  },
}

function TimelineDot({ state }: { state: "past" | "next" | "future" }) {
  const color =
    state === "past" ? "rgba(255,255,255,0.25)" :
    state === "next" ? "#ffffff" :
    "rgba(255,255,255,0.55)"
  return (
    <div style={{
      width: "8px",
      height: "8px",
      borderRadius: "50%",
      background: state === "next" ? "#fff" : "transparent",
      border: `1.5px solid ${color}`,
      flexShrink: 0,
      marginTop: "2px",
    }} />
  )
}

interface LaunchProps {
  nav: (s: Screen) => void
  role: Role
}

export default function Launch({ nav, role }: LaunchProps) {
  const homeScreen: Screen = role === "pm" ? "afsvc-overview" : "base-home"
  return (
    <div style={{
      minHeight: "100%",
      background: "#001D3D",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gridTemplateRows: "1fr auto",
    }}>

      {/* ── Left: identity ── */}
      <div style={{
        padding: "80px 64px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: "0",
      }}>
        {/* AFSVC Shield — unaltered, with clear space = ¼ height = 27px */}
        <div style={{
          marginBottom: "27px",
          alignSelf: "flex-start",
        }}>
          <img
            src={shieldSrc}
            alt="Air Force Services Center emblem"
            style={{
              height: "108px",
              width: "auto",
              display: "block",
            }}
          />
        </div>

        {/* Product name */}
        <div style={{
          fontSize: "48px",
          fontWeight: 300,
          color: "#ffffff",
          lineHeight: 1.1,
          letterSpacing: "-0.01em",
          marginBottom: "12px",
        }}>
          AFSVC Mission Feeding
        </div>

        <div style={{
          fontSize: "16px",
          fontWeight: 400,
          color: "rgba(255,255,255,0.90)",
          lineHeight: 1.5,
          marginBottom: "4px",
        }}>
          DAF Mission Feeding monthly document
        </div>
        <div style={{
          fontSize: "16px",
          fontWeight: 400,
          color: "rgba(255,255,255,0.90)",
          lineHeight: 1.5,
          marginBottom: "20px",
        }}>
          tracking and submissions
        </div>

        <div style={{
          fontSize: "14px",
          fontWeight: 400,
          color: "rgba(255,255,255,0.70)",
          marginBottom: "48px",
        }}>
          AFSVC/VMF
        </div>

        {/* Single primary action */}
        <div>
          <button
            onClick={() => nav(homeScreen)}
            style={{
              background: "#ffffff",
              color: "#001D3D",
              border: "none",
              borderRadius: "4px",
              fontSize: "15px",
              fontWeight: 700,
              padding: "0 32px",
              height: "40px",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              letterSpacing: "0.02em",
            }}
          >
            Enter
            <Icons.ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* ── Right: current cycle panel ── */}
      <div style={{
        padding: "80px 64px 80px 40px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}>
        <div style={{
          background: "#ffffff",
          border: "1px solid #d1d1d1",
          borderRadius: "2px",
          padding: "28px",
          maxWidth: "360px",
        }}>
          {/* Period header */}
          <div style={{
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            color: "#616161",
            marginBottom: "24px",
          }}>
            {CYCLE.period}
          </div>

          {/* Vertical timeline */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0", marginBottom: "28px" }}>
            {CYCLE.dates.map((d, i) => {
              const isNext = d.state === "next"
              const isPast = d.state === "past"
              const isLast = i === CYCLE.dates.length - 1

              return (
                <div key={i} style={{ display: "flex", gap: "14px", position: "relative" }}>
                  {/* Left: dot + connecting rule */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: "8px" }}>
                    <div style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: isNext ? "#0f548c" : isPast ? "#d1d1d1" : "#d1d1d1",
                      border: isNext ? "none" : "1.5px solid #d1d1d1",
                      flexShrink: 0,
                      marginTop: "4px",
                    }} />
                    {!isLast && (
                      <div style={{
                        width: "1px",
                        flex: 1,
                        minHeight: "20px",
                        background: "#e0e0e0",
                        margin: "4px 0",
                      }} />
                    )}
                  </div>

                  {/* Right: date + label */}
                  <div style={{
                    paddingBottom: isLast ? "0" : "16px",
                    flex: 1,
                  }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: "10px", flexWrap: "wrap" }}>
                      <span style={{
                        fontSize: "13px",
                        fontWeight: isNext ? 700 : 400,
                        color: isNext ? "#0f548c" : isPast ? "#adadad" : "#242424",
                        whiteSpace: "nowrap",
                        fontVariantNumeric: "tabular-nums",
                        minWidth: "44px",
                      }}>
                        {d.date}
                      </span>
                      <span style={{
                        fontSize: "13px",
                        fontWeight: isNext ? 600 : 400,
                        color: isNext ? "#242424" : isPast ? "#adadad" : "#616161",
                      }}>
                        {d.label}
                      </span>
                      {isNext && (
                        <span style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          color: "#0f548c",
                          background: "#eff6fc",
                          border: "1px solid #0f548c",
                          borderRadius: "2px",
                          padding: "1px 6px",
                        }}>
                          3 days
                        </span>
                      )}
                    </div>
                    {isPast && d.label === "Initial suspense" && (
                      <div style={{ fontSize: "11px", color: "#8a5300", marginTop: "2px" }}>
                        Passed — initial deadline was 5 Sep
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Package summary — base user view */}
          <div style={{
            borderTop: "1px solid #e8e8e8",
            paddingTop: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
            }}>
              <span style={{ fontSize: "12px", fontWeight: 600, color: "#616161", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                {CYCLE.base.label}
              </span>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#242424" }}>
                {CYCLE.base.submitted} of {CYCLE.base.total} submitted
              </span>
            </div>
            <ProgressBar value={CYCLE.base.submitted} max={CYCLE.base.total} />
            <div style={{ fontSize: "12px", color: "#616161", lineHeight: 1.5 }}>
              {CYCLE.base.detail}
            </div>
          </div>
        </div>
      </div>

      {/* ── Footer — spans both columns ── */}
      <div style={{
        gridColumn: "1 / -1",
        display: "flex",
        alignItems: "center",
        padding: "16px 64px",
        borderTop: "1px solid rgba(255,255,255,0.08)",
      }}>
        <span style={{
          fontSize: "12px",
          color: "rgba(255,255,255,0.40)",
          letterSpacing: "0.03em",
        }}>
          Version 0.6.0 · August 2026
        </span>
      </div>
    </div>
  )
}
