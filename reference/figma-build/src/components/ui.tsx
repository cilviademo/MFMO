import { ReactNode, CSSProperties, JSX } from "react"

// ─── Types ────────────────────────────────────────────────────────────────────

// 6-state model. Colour resolves ownership at a glance:
//   open      → Blue    (window open, nobody acts yet)
//   late      → Amber   (initial suspense passed, BASE acts)
//   overdue   → Red     (final call passed, BASE acts)
//   correction→ Red     (returned for correction, BASE acts)
//   review    → Yellow  (awaiting AFSVC review, AFSVC acts)
//   accepted  → Green   (done)
//   not-req   → Gray    (not required this period)
export type StatusType =
  | "open"
  | "late"
  | "overdue"
  | "correction"
  | "review"
  | "accepted"
  | "not-req"

export type Screen =
  | "launch"
  | "base-home"
  | "base-correction"
  | "submit"
  | "my-package"
  | "afsvc-overview"
  | "review-queue"
  | "review-correction"
  | "installation"
  | "calendar"
  | "admin"
  | "access-mgmt"
  | "empty-state"
  | "base-768"
  | "review-768"
  | "base-home-pm"
  | "no-access"
  | "scope-unresolved"
  | "config-required"
  | "request-access"
  | "admin-banner"
  | "calendar-add-date"

export type Role = "base" | "pm"

export const IDENTITY: Record<Role, { userName: string; userRole: string; userInitials: string }> = {
  base: { userName: "SrA Kim, P.",  userRole: "Base Accountant, JBSA Lackland",  userInitials: "PK" },
  pm:   { userName: "Torres, M.",   userRole: "Portfolio Manager, Portfolio 2",   userInitials: "TM" },
}

export const BASE_TABS = [
  { id: "home",     label: "Home" },
  { id: "package",  label: "My Package", badge: 2 },
  { id: "calendar", label: "Calendar" },
]

export const PM_TABS = [
  { id: "overview",      label: "Overview" },
  { id: "review",        label: "Review", badge: 14 },
  { id: "installations", label: "Installations" },
  { id: "calendar",      label: "Calendar" },
  { id: "admin",         label: "Admin" },
]

// ─── Real document codes ──────────────────────────────────────────────────────

export const DOCS = {
  "1119": { code: "1119", name: "AF Form 1119 Feeding Summary", freq: "Monthly", scope: "Facility" },
  "SF 1080": { code: "SF 1080", name: "Voucher for Transfers", freq: "Monthly", scope: "Installation" },
  "SAIIT": { code: "SAIIT", name: "Sales, Adjustments, Invoices, Inventory and Transfers", freq: "Monthly", scope: "Facility" },
  "GPC": { code: "GPC", name: "GPC Bank Statement", freq: "Monthly", scope: "Installation" },
  "1119-1": { code: "1119-1", name: "AF Form 1119-1 Field Feeding", freq: "Conditional", scope: "Facility" },
  "1038": { code: "1038", name: "AF Form 1038", freq: "Quarterly", scope: "Installation" },
} as const

// ─── Fluent-style outline SVG icons ──────────────────────────────────────────

export const Icons = {
  Check: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2.5,8.5 6,12 13.5,4.5" />
    </svg>
  ),
  Warning: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7.1 2.5L1.5 12.5h13L8.9 2.5a1.03 1.03 0 00-1.8 0z" />
      <line x1="8" y1="6.5" x2="8" y2="9.5" />
      <circle cx="8" cy="11.5" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  ),
  Circle: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="5.5" />
    </svg>
  ),
  Clock: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="5.5" />
      <polyline points="8,5 8,8.5 10.5,10.5" />
    </svg>
  ),
  Lock: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="7.5" width="10" height="7" rx="1.5" />
      <path d="M5 7.5V5.5a3 3 0 016 0v2" />
    </svg>
  ),
  Minus: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <line x1="3.5" y1="8" x2="12.5" y2="8" />
    </svg>
  ),
  ChevronRight: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6,3.5 10,8 6,12.5" />
    </svg>
  ),
  ChevronLeft: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="10,3.5 6,8 10,12.5" />
    </svg>
  ),
  ChevronDown: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3.5,6 8,10 12.5,6" />
    </svg>
  ),
  Document: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3.5 2h6l3 3v9.5H3.5V2z" />
      <polyline points="9.5,2 9.5,5 12.5,5" />
      <line x1="5.5" y1="8" x2="10.5" y2="8" />
      <line x1="5.5" y1="10.5" x2="10.5" y2="10.5" />
    </svg>
  ),
  Upload: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="5.5,6 8,3 10.5,6" />
      <line x1="8" y1="3" x2="8" y2="11" />
      <path d="M2.5 12.5h11" />
    </svg>
  ),
  AlertCircle: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="6" />
      <line x1="8" y1="5.5" x2="8" y2="8.5" />
      <circle cx="8" cy="10.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  ),
  Person: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="5.5" r="3" />
      <path d="M2 13.5c0-3.3 2.7-6 6-6s6 2.7 6 6" />
    </svg>
  ),
  ExternalLink: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 3H3.5A1.5 1.5 0 002 4.5v8A1.5 1.5 0 003.5 14h8A1.5 1.5 0 0013 12.5V9" />
      <polyline points="10,2 14,2 14,6" />
      <line x1="7.5" y1="8.5" x2="14" y2="2" />
    </svg>
  ),
  History: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2.5 8a5.5 5.5 0 1011 0 5.5 5.5 0 00-11 0" />
      <polyline points="8,5.5 8,8.5 10,10" />
      <polyline points="2.5,5.5 2.5,8 4.5,8" />
    </svg>
  ),
  Plus: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <line x1="8" y1="2.5" x2="8" y2="13.5" />
      <line x1="2.5" y1="8" x2="13.5" y2="8" />
    </svg>
  ),
  Filter: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="2,4 14,4" />
      <polyline points="4,8 12,8" />
      <polyline points="6,12 10,12" />
    </svg>
  ),
  Search: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="6.5" cy="6.5" r="4.5" />
      <line x1="10" y1="10" x2="14" y2="14" />
    </svg>
  ),
  Shield: ({ size = 32 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 3L4 8v8c0 7.5 5.3 13.8 12 15.5C22.7 29.8 28 23.5 28 16V8L16 3z" />
      <polyline points="10,16 14,20 22,12" />
    </svg>
  ),
  Globe: ({ size = 32 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="16" cy="16" r="12" />
      <path d="M16 4c-4 4-6 8-6 12s2 8 6 12" />
      <path d="M16 4c4 4 6 8 6 12s-2 8-6 12" />
      <line x1="4" y1="16" x2="28" y2="16" />
      <path d="M5.5 10h21M5.5 22h21" />
    </svg>
  ),
  Calendar: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="3" width="13" height="11.5" rx="1" />
      <line x1="5" y1="1.5" x2="5" y2="4.5" />
      <line x1="11" y1="1.5" x2="11" y2="4.5" />
      <line x1="1.5" y1="7" x2="14.5" y2="7" />
    </svg>
  ),
  Help: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="6" />
      <path d="M6 6.5a2 2 0 113.5 1.3C9 8.3 8 9 8 10" />
      <circle cx="8" cy="12" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  ),
  Download: ({ size = 16 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="5.5,8 8,11 10.5,8" />
      <line x1="8" y1="3" x2="8" y2="11" />
      <path d="M2.5 12.5h11" />
    </svg>
  ),
}

// ─── Status chip ──────────────────────────────────────────────────────────────

const STATUS_MAP: Record<StatusType, { label: string; key: string; Icon: () => JSX.Element }> = {
  open:       { label: "Window open",     key: "open",     Icon: () => <Icons.Circle size={10} /> },
  late:       { label: "Late",            key: "late",     Icon: () => <Icons.Warning size={10} /> },
  overdue:    { label: "Overdue",         key: "overdue",  Icon: () => <Icons.AlertCircle size={10} /> },
  correction: { label: "Correction needed", key: "overdue",  Icon: () => <Icons.AlertCircle size={10} /> },
  review:     { label: "Awaiting review", key: "review",   Icon: () => <Icons.Clock size={10} /> },
  accepted:   { label: "Accepted",        key: "accepted", Icon: () => <Icons.Check size={10} /> },
  "not-req":  { label: "Not required",    key: "na",       Icon: () => <Icons.Minus size={10} /> },
}

export function StatusChip({ status }: { status: StatusType }) {
  const cfg = STATUS_MAP[status]
  const k = cfg.key
  const { Icon } = cfg
  return (
    <span style={{
      color: `var(--status-${k}-text)`,
      background: `var(--status-${k}-bg)`,
      border: `1px solid var(--status-${k}-border)`,
      borderRadius: "2px",
      fontSize: "11px",
      fontWeight: 600,
      letterSpacing: "0.02em",
      padding: "2px 7px 2px 5px",
      display: "inline-flex",
      alignItems: "center",
      gap: "4px",
      whiteSpace: "nowrap",
      userSelect: "none",
    }}>
      <Icon />
      {cfg.label}
    </span>
  )
}

// ─── Buttons ─────────────────────────────────────────────────────────────────

export function Btn({
  variant = "primary",
  children,
  onClick,
  disabled,
  style: s,
}: {
  variant?: "primary" | "secondary" | "subtle"
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  style?: CSSProperties
}) {
  const base: CSSProperties = {
    height: "32px",
    borderRadius: "4px",
    fontSize: "14px",
    fontWeight: 600,
    padding: "0 16px",
    cursor: disabled ? "not-allowed" : "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    border: "1px solid transparent",
    transition: "opacity 0.1s, background 0.1s",
    whiteSpace: "nowrap",
  }
  const styles: Record<string, CSSProperties> = {
    primary: {
      background: disabled ? "var(--border)" : "var(--accent)",
      color: disabled ? "var(--secondary)" : "#fff",
      border: "1px solid transparent",
    },
    secondary: {
      background: "transparent",
      color: "var(--accent)",
      border: "1px solid var(--accent)",
    },
    subtle: {
      background: "transparent",
      color: "var(--text)",
      border: "1px solid var(--border)",
    },
  }
  return (
    <button onClick={onClick} disabled={disabled} style={{ ...base, ...styles[variant], ...s }}>
      {children}
    </button>
  )
}

export function TextLink({
  children,
  onClick,
  style: s,
}: {
  children: ReactNode
  onClick?: () => void
  style?: CSSProperties
}) {
  return (
    <button onClick={onClick} style={{
      background: "none",
      border: "none",
      color: "var(--accent)",
      fontSize: "13px",
      fontWeight: 600,
      cursor: "pointer",
      padding: 0,
      display: "inline-flex",
      alignItems: "center",
      gap: "3px",
      ...s,
    }}>
      {children}
    </button>
  )
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export function Panel({
  title,
  right,
  children,
  style: s,
  noPad,
}: {
  title?: ReactNode
  right?: ReactNode
  children: ReactNode
  style?: CSSProperties
  noPad?: boolean
}) {
  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "2px",
      ...s,
    }}>
      {title !== undefined && (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
          height: "44px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)", letterSpacing: "0.01em" }}>
            {title}
          </span>
          {right && <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>{right}</div>}
        </div>
      )}
      {children}
    </div>
  )
}

// ─── Tab Strip ───────────────────────────────────────────────────────────────

export function TabStrip({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: string; label: string; badge?: number }>
  active: string
  onChange: (id: string) => void
}) {
  return (
    <div style={{
      display: "flex",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      flexShrink: 0,
    }}>
      {tabs.map(tab => {
        const isActive = tab.id === active
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            style={{
              background: "none",
              border: "none",
              borderBottom: isActive ? "2px solid var(--accent)" : "2px solid transparent",
              color: isActive ? "var(--accent)" : "var(--secondary)",
              fontWeight: isActive ? 600 : 400,
              fontSize: "13px",
              padding: "0 16px",
              height: "40px",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              whiteSpace: "nowrap",
              marginBottom: "-1px",
            }}
          >
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span style={{
                background: "#a4262c",
                color: "#fff",
                borderRadius: "2px",
                fontSize: "10px",
                fontWeight: 700,
                padding: "1px 5px",
                minWidth: "16px",
                textAlign: "center",
                lineHeight: "14px",
              }}>
                {tab.badge}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ─── Metric strip (full-width, 1px rules) ────────────────────────────────────

export function MetricStrip({ tiles }: {
  tiles: Array<{ label: string; value: string | number; context?: string }>
}) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(${tiles.length}, 1fr)`,
      border: "1px solid var(--border)",
      borderRadius: "2px",
      background: "var(--surface)",
    }}>
      {tiles.map((t, i) => (
        <div key={i} style={{
          padding: "16px 20px",
          borderRight: i < tiles.length - 1 ? "1px solid var(--border)" : "none",
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
            color: "var(--text)",
            lineHeight: 1.1,
            marginBottom: t.context ? "4px" : 0,
          }}>
            {t.value}
          </div>
          {t.context && (
            <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
              {t.context}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ─── Data table ──────────────────────────────────────────────────────────────

export interface Col<T> {
  key: string
  header: string
  width?: string | number
  align?: "left" | "right" | "center"
  render: (row: T) => ReactNode
}

export function Table<T extends { id: string }>({
  cols,
  rows,
  emptyMessage = "No documents awaiting your review.\nAll submissions in this view have been processed.",
  rowHeight = 44,
}: {
  cols: Col<T>[]
  rows: T[]
  emptyMessage?: string
  rowHeight?: number
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {cols.map(c => (
              <th key={c.key} style={{
                padding: "0 12px",
                height: "36px",
                textAlign: c.align ?? "left",
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                color: "var(--secondary)",
                whiteSpace: "nowrap",
                width: c.width,
                background: "var(--surface)",
              }}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={cols.length} style={{ padding: "40px", textAlign: "center" }}>
                <div style={{ color: "var(--secondary)", fontSize: "14px", lineHeight: 1.6, whiteSpace: "pre-line" }}>
                  {emptyMessage}
                </div>
              </td>
            </tr>
          ) : (
            rows.map((row, ri) => (
              <tr key={row.id} style={{
                borderBottom: ri < rows.length - 1 ? "1px solid var(--border)" : "none",
              }}>
                {cols.map(c => (
                  <td key={c.key} style={{
                    padding: "0 12px",
                    height: `${rowHeight}px`,
                    textAlign: c.align ?? "left",
                    verticalAlign: "middle",
                    color: "var(--text)",
                  }}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}

// ─── Top bar ─────────────────────────────────────────────────────────────────

export function TopBar({
  period,
  onPeriodChange,
  userName = "Maj. Chen, S.",
  userRole = "AFSVC Portfolio Manager",
  userInitials = "SC",
  onHelp,
}: {
  period: string
  onPeriodChange?: (p: string) => void
  userName?: string
  userRole?: string
  userInitials?: string
  onHelp?: () => void
}) {
  return (
    <div style={{
      height: "48px",
      background: "var(--surface)",
      borderBottom: "1px solid var(--border)",
      display: "grid",
      gridTemplateColumns: "1fr auto 1fr",
      alignItems: "center",
      padding: "0 16px",
      flexShrink: 0,
    }}>
      {/* Left: mark + product name */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="2" fill="var(--accent)" />
          <text x="14" y="19.5" textAnchor="middle" fill="white" fontSize="12" fontWeight="700" fontFamily="Inter, sans-serif">MF</text>
        </svg>
        <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)", whiteSpace: "nowrap" }}>
          Mission Feeding Operations
        </span>
      </div>

      {/* Centre: period selector */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }}>
        <span style={{ fontSize: "12px", color: "var(--secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
          Period
        </span>
        <select
          value={period}
          onChange={e => onPeriodChange?.(e.target.value)}
          style={{
            background: "var(--bg)",
            color: "var(--text)",
            border: "1px solid var(--border)",
            borderRadius: "4px",
            fontSize: "13px",
            fontWeight: 600,
            padding: "4px 28px 4px 10px",
            height: "28px",
            cursor: "pointer",
            appearance: "none",
            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 16 16'%3E%3Cpolyline points='3.5,6 8,10 12.5,6' stroke='%23616161' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")`,
            backgroundRepeat: "no-repeat",
            backgroundPosition: "right 8px center",
            fontFamily: "inherit",
          }}
        >
          <option>August 2026</option>
          <option>July 2026</option>
          <option>June 2026</option>
          <option>September 2026</option>
        </select>
      </div>

      {/* Right: help + identity */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", justifyContent: "flex-end" }}>
        <button onClick={onHelp} style={{
          background: "none", border: "none", color: "var(--secondary)",
          cursor: "pointer", padding: "4px", display: "flex", alignItems: "center",
        }}>
          <Icons.Help size={16} />
        </button>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)", lineHeight: 1.3 }}>
            {userName}
          </div>
          <div style={{ fontSize: "11px", color: "var(--secondary)", lineHeight: 1.3 }}>
            {userRole}
          </div>
          <div style={{ fontSize: "11px", color: "var(--secondary)", lineHeight: 1.3 }}>
            CAC authenticated
          </div>
        </div>
        <div style={{
          width: "30px",
          height: "30px",
          borderRadius: "50%",
          background: "var(--accent)",
          color: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "11px",
          fontWeight: 700,
          flexShrink: 0,
          letterSpacing: "0.02em",
        }}>
          {userInitials}
        </div>
      </div>
    </div>
  )
}

// ─── Label ───────────────────────────────────────────────────────────────────

export function Label({ children, style: s }: { children: ReactNode; style?: CSSProperties }) {
  return (
    <div style={{
      fontSize: "11px",
      fontWeight: 600,
      textTransform: "uppercase",
      letterSpacing: "0.04em",
      color: "var(--secondary)",
      ...s,
    }}>
      {children}
    </div>
  )
}

// ─── Progress bar ─────────────────────────────────────────────────────────────

export function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div style={{
      height: "3px",
      background: "var(--border)",
      borderRadius: "1px",
      overflow: "hidden",
    }}>
      <div style={{
        height: "100%",
        width: `${pct}%`,
        background: "var(--accent)",
        borderRadius: "1px",
        transition: "width 0.3s ease",
      }} />
    </div>
  )
}

// ─── Dropdown ────────────────────────────────────────────────────────────────

export function Select({
  value,
  onChange,
  options,
  placeholder,
  style: s,
}: {
  value: string
  onChange: (v: string) => void
  options: Array<{ value: string; label: string }>
  placeholder?: string
  style?: CSSProperties
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        background: "var(--surface)",
        color: value === "" ? "var(--secondary)" : "var(--text)",
        border: "1px solid var(--border)",
        borderRadius: "4px",
        fontSize: "13px",
        padding: "0 28px 0 10px",
        height: "32px",
        cursor: "pointer",
        appearance: "none",
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 16 16'%3E%3Cpolyline points='3.5,6 8,10 12.5,6' stroke='%23616161' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")`,
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 8px center",
        fontFamily: "inherit",
        ...s,
      }}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

// ─── Environment banner ───────────────────────────────────────────────────────
// Rendered above the top bar only in non-production environments.
// Nothing renders in production (banner === null).

export type EnvBanner = "pilot" | "readonly" | null

export function EnvironmentBanner({ banner }: { banner: EnvBanner }) {
  if (!banner) return null
  const label = banner === "pilot" ? "PILOT ENVIRONMENT" : "READ ONLY — MAINTENANCE"
  return (
    <div style={{
      height: "28px",
      background: "#e8e4d8",
      color: "#242424",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "11px",
      fontWeight: 600,
      letterSpacing: "0.06em",
      textTransform: "uppercase",
      borderBottom: "1px solid #c8c4b8",
      flexShrink: 0,
      userSelect: "none",
    }}>
      {label}
    </div>
  )
}

// ─── CUI information banner ────────────────────────────────────────────────────
// Component library reference only. Do not place on any screen.
// Marking string is intentionally blank — no marking has been designated
// for Mission Feeding EOM tracking data. A decorative CUI banner is a policy error.
//
// Usage (component library frame only):
//   <CUIBanner marking="" />

export function CUIBanner({ marking }: { marking: string }) {
  if (!marking) return null
  return (
    <div style={{
      height: "24px",
      background: "#f5f5f5",
      borderBottom: "1px solid #d1d1d1",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: "11px",
      fontWeight: 700,
      letterSpacing: "0.08em",
      color: "#242424",
      userSelect: "none",
    }}>
      {marking}
    </div>
  )
}
