import { useState } from "react"
import { TopBar, TabStrip, Icons, PM_TABS, IDENTITY, TextLink } from "../components/ui"
import type { Screen, Role } from "../components/ui"

// Only observable configuration and data health — no fabricated infrastructure
interface CheckRow {
  id: string
  level: "healthy" | "attention" | "error"
  label: string
  detail?: string
  actionLabel?: string | null  // null = no action button; string = custom label; undefined = "Dismiss"
  actionTarget?: Screen | null
}

const APP_CHECKS: CheckRow[] = [
  {
    id: "1",
    level: "healthy",
    label: "All active Legacy requirements have scope and frequency set.",
  },
  {
    id: "2",
    level: "attention",
    label: "3 installations missing facility mapping.",
    detail: `Fairchild AFB (2 facilities) and Andersen AB (1 facility) are listed in the installation register but have no facility records linked. Submissions from these facilities will fail classification until facility records are created.`,
    actionLabel: "Go to Facility Registry →",
    actionTarget: "admin" as const,
  },
  {
    id: "3",
    level: "healthy",
    label: "August 2026 package generation completed for 43 of 43 Legacy installations.",
  },
  {
    id: "3b",
    level: "attention",
    label: "6 installations not yet onboarded to the system.",
    detail: `Six Legacy installations have not completed onboarding. Their packages cannot be submitted until onboarding is finished. Contact each installation's admin to complete the setup checklist.`,
    actionLabel: null,
    actionTarget: null,
  },
  {
    id: "4",
    level: "healthy",
    label: "0 duplicate expected items detected across all portfolios.",
  },
  {
    id: "5",
    level: "attention",
    label: "2 submissions need manual classification.",
    detail: `Two recently uploaded files could not be automatically matched to a requirement. They appear in the Exceptions queue and are not visible to installations until classified.\n\nTo resolve: go to Review → Exceptions and assign each file to its requirement manually.`,
  },
  {
    id: "6",
    level: "healthy",
    label: "Reconciliation last completed 18 minutes ago. No discrepancies.",
  },
  {
    id: "7",
    level: "attention",
    label: "Reminder notifications are disabled for Portfolio 3.",
    detail: `Automated suspense reminder notifications for Portfolio 3 (Minot AFB (2.0), Minot AFB (MAF)) are turned off. Installations will not receive standard 7-day and 2-day pre-suspense reminders.\n\nTo resolve: go to Administration → Notifications and enable reminders for Portfolio 3.`,
  },
  {
    id: "8",
    level: "healthy",
    label: "September 2026 is configured as the next open reporting period.",
  },
]

// Tenant security — never rendered "Healthy". Requires tenant admin verification.
const TENANT_ROWS = [
  { id: "t1", label: "Power Platform DLP policy" },
  { id: "t2", label: "Tenant isolation" },
  { id: "t3", label: "Purview audit retention" },
  { id: "t4", label: "SharePoint permissions" },
]

const LEVEL_COLOR = {
  healthy: "var(--status-accepted-text)",
  attention: "var(--status-late-text)",
  error: "var(--status-overdue-text)",
}
const LEVEL_BG = {
  healthy: "var(--status-accepted-bg)",
  attention: "var(--status-late-bg)",
  error: "var(--status-overdue-bg)",
}
const LEVEL_BORDER = {
  healthy: "var(--status-accepted-border)",
  attention: "var(--status-late-border)",
  error: "var(--status-overdue-border)",
}
const LEVEL_LABEL = { healthy: "Healthy", attention: "Attention", error: "Error" }

function LevelIcon({ level }: { level: CheckRow["level"] }) {
  if (level === "healthy") return <Icons.Check size={13} />
  if (level === "attention") return <Icons.Warning size={13} />
  return <Icons.AlertCircle size={13} />
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: "11px",
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.07em",
      color: "var(--secondary)",
      marginBottom: "8px",
    }}>
      {children}
    </div>
  )
}

function AdminSubNav({ nav }: { nav: (s: Screen) => void }) {
  return (
    <div style={{ display: "flex", gap: "0", borderBottom: "1px solid var(--border)", background: "var(--surface)", padding: "0 40px" }}>
      {[
        { label: "System health", screen: "admin" as Screen, active: true },
        { label: "Access management", screen: "access-mgmt" as Screen, active: false },
      ].map(item => (
        <button
          key={item.screen}
          onClick={() => nav(item.screen)}
          style={{
            background: "none",
            border: "none",
            borderBottom: item.active ? "2px solid var(--accent)" : "2px solid transparent",
            color: item.active ? "var(--accent)" : "var(--secondary)",
            fontSize: "13px",
            fontWeight: item.active ? 600 : 400,
            padding: "0 0 10px",
            marginRight: "24px",
            cursor: "pointer",
            marginBottom: "-1px",
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

export default function AdminHealth({ nav, role = "pm" }: { nav: (s: Screen) => void; role?: Role }) {
  const ident = IDENTITY.pm
  const [expanded, setExpanded] = useState<string | null>("2")

  const attentionCount = APP_CHECKS.filter(c => c.level === "attention").length
  const errorCount = APP_CHECKS.filter(c => c.level === "error").length

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip tabs={PM_TABS} active="admin" onChange={id => {
        if (id === "overview") nav("afsvc-overview")
        if (id === "review") nav("review-queue")
        if (id === "installations") nav("installation")
        if (id === "calendar") nav("calendar")
      }} />
      <AdminSubNav nav={nav} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "32px" }}>

        {/* Page heading */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px" }}>
              System health
            </h1>
            <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
              Administration · Configuration and data health
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
            {attentionCount > 0 && (
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                background: LEVEL_BG.attention,
                color: LEVEL_COLOR.attention,
                border: `1px solid ${LEVEL_BORDER.attention}`,
                borderRadius: "2px",
                fontSize: "11px",
                fontWeight: 700,
                padding: "4px 10px",
              }}>
                <Icons.Warning size={12} />
                {attentionCount} attention {attentionCount > 1 ? "items" : "item"}
              </span>
            )}
            {errorCount > 0 && (
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                background: LEVEL_BG.error,
                color: LEVEL_COLOR.error,
                border: `1px solid ${LEVEL_BORDER.error}`,
                borderRadius: "2px",
                fontSize: "11px",
                fontWeight: 700,
                padding: "4px 10px",
              }}>
                <Icons.AlertCircle size={12} />
                {errorCount} {errorCount > 1 ? "errors" : "error"}
              </span>
            )}
          </div>
        </div>

        {/* ── APPLICATION HEALTH ── */}
        <div>
          <SectionHeading>Application Health</SectionHeading>
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "2px",
            overflow: "hidden",
          }}>
            {APP_CHECKS.map((check, i) => {
              const isOpen = expanded === check.id
              const hasDetail = !!check.detail
              return (
                <div key={check.id}>
                  <div
                    onClick={() => hasDetail && setExpanded(isOpen ? null : check.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "0 20px",
                      height: "44px",
                      borderBottom: (i < APP_CHECKS.length - 1 || isOpen) ? "1px solid var(--border)" : "none",
                      cursor: hasDetail ? "pointer" : "default",
                      background: check.level !== "healthy" && !isOpen ? LEVEL_BG[check.level] : "transparent",
                    }}
                  >
                    <span style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      fontSize: "11px",
                      fontWeight: 700,
                      letterSpacing: "0.02em",
                      color: LEVEL_COLOR[check.level],
                      border: `1px solid ${LEVEL_BORDER[check.level]}`,
                      background: LEVEL_BG[check.level],
                      borderRadius: "2px",
                      padding: "2px 8px",
                      width: "90px",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}>
                      <LevelIcon level={check.level} />
                      {LEVEL_LABEL[check.level]}
                    </span>
                    <span style={{
                      fontSize: "13px",
                      color: "var(--text)",
                      fontWeight: check.level !== "healthy" ? 600 : 400,
                      flex: 1,
                    }}>
                      {check.label}
                    </span>
                    {hasDetail && (
                      <div style={{
                        color: "var(--secondary)",
                        transform: isOpen ? "rotate(180deg)" : "none",
                        transition: "transform 0.15s",
                        flexShrink: 0,
                      }}>
                        <Icons.ChevronDown size={14} />
                      </div>
                    )}
                  </div>

                  {isOpen && hasDetail && (
                    <div style={{
                      borderBottom: i < APP_CHECKS.length - 1 ? "1px solid var(--border)" : "none",
                      borderLeft: `3px solid ${LEVEL_BORDER[check.level]}`,
                      background: LEVEL_BG[check.level],
                      padding: "20px 24px",
                    }}>
                      <div style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        color: LEVEL_COLOR[check.level],
                        marginBottom: "10px",
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                      }}>
                        <LevelIcon level={check.level} />
                        Attention — action required
                      </div>
                      <div style={{
                        fontSize: "13px",
                        color: "var(--text)",
                        lineHeight: 1.7,
                        maxWidth: "680px",
                        whiteSpace: "pre-line",
                      }}>
                        {check.detail}
                      </div>
                      <div style={{ marginTop: "14px", display: "flex", gap: "8px", alignItems: "center" }}>
                        {check.actionLabel !== null && (
                          check.actionLabel ? (
                            <TextLink onClick={() => setExpanded(null)} style={{ fontSize: "13px", fontWeight: 600 }}>
                              {check.actionLabel}
                            </TextLink>
                          ) : (
                            <button onClick={() => setExpanded(null)} style={{
                              background: "transparent",
                              border: "1px solid var(--border)",
                              borderRadius: "4px",
                              fontSize: "13px",
                              fontWeight: 400,
                              color: "var(--text)",
                              padding: "0 16px",
                              height: "30px",
                              cursor: "pointer",
                            }}>
                              Dismiss
                            </button>
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* ── TENANT SECURITY ── */}
        <div>
          <SectionHeading>Tenant Security</SectionHeading>
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "2px",
            overflow: "hidden",
          }}>
            {/* Section note */}
            <div style={{
              padding: "10px 20px",
              fontSize: "12px",
              color: "var(--secondary)",
              borderBottom: "1px solid var(--border)",
              lineHeight: 1.5,
            }}>
              These controls are managed at the tenant level and cannot be verified from within this application.
              Confirm their status with your tenant administrator.
            </div>
            {TENANT_ROWS.map((row, i) => (
              <div
                key={row.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "0 20px",
                  height: "44px",
                  borderBottom: i < TENANT_ROWS.length - 1 ? "1px solid var(--border)" : "none",
                  background: "transparent",
                }}
              >
                {/* Neutral chip — no status color */}
                <span style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--secondary)",
                  border: "1px solid var(--border)",
                  background: "var(--bg)",
                  borderRadius: "2px",
                  padding: "2px 8px",
                  width: "90px",
                  justifyContent: "center",
                  flexShrink: 0,
                }}>
                  External
                </span>
                <span style={{ fontSize: "13px", color: "var(--text)", flex: 1 }}>
                  {row.label}
                </span>
                <span style={{ fontSize: "12px", color: "var(--secondary)", fontStyle: "italic" }}>
                  Requires tenant admin verification
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
          Application Health reflects the current state of SharePoint lists and configuration data — not infrastructure monitoring.
        </div>
      </div>
    </div>
  )
}
