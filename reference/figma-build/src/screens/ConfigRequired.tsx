import type { Screen } from "../components/ui"
import { Icons } from "../components/ui"

// Only visible to tenant admins. No application data is shown.
const UNSET_ITEMS = [
  { label: "SharePoint site URL", description: "Root site for document libraries — not set" },
  { label: "Portfolio mapping list", description: "Installation-to-portfolio mapping list — not found" },
  { label: "Reviewer group", description: "AFSVC reviewer security group — not configured" },
  { label: "Cycle configuration", description: "Current reporting cycle dates — not defined" },
]

interface ConfigRequiredProps {
  nav: (s: Screen) => void
}

export default function ConfigRequired({ nav }: ConfigRequiredProps) {
  return (
    <div style={{
      minHeight: "100%",
      background: "var(--bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px",
    }}>
      <div style={{
        maxWidth: "520px",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: "28px",
      }}>
        {/* Icon */}
        <div style={{
          width: "44px",
          height: "44px",
          borderRadius: "4px",
          background: "var(--status-overdue-bg)",
          border: "1px solid var(--status-overdue-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--status-overdue-text)",
        }}>
          <Icons.Warning size={22} />
        </div>

        {/* Heading + body */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "22px", fontWeight: 300, color: "var(--text)", lineHeight: 1.2 }}>
            This environment hasn't been configured yet.
          </div>
          <div style={{ fontSize: "14px", color: "var(--secondary)", lineHeight: 1.6 }}>
            The following settings must be completed before any user can access the application.
            No application data is visible until configuration is complete.
          </div>
        </div>

        {/* Checklist */}
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          width: "100%",
          overflow: "hidden",
        }}>
          <div style={{
            padding: "10px 16px",
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--secondary)",
            borderBottom: "1px solid var(--border)",
          }}>
            Required settings — not yet configured
          </div>
          {UNSET_ITEMS.map((item, i) => (
            <div
              key={i}
              style={{
                padding: "12px 16px",
                borderBottom: i < UNSET_ITEMS.length - 1 ? "1px solid var(--border)" : "none",
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
              }}
            >
              <div style={{
                width: "16px",
                height: "16px",
                borderRadius: "2px",
                border: "1.5px solid var(--status-overdue-border)",
                background: "var(--status-overdue-bg)",
                flexShrink: 0,
                marginTop: "1px",
              }} />
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                  {item.label}
                </span>
                <span style={{ fontSize: "12px", color: "var(--secondary)" }}>
                  {item.description}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ fontSize: "12px", color: "var(--secondary)", lineHeight: 1.6 }}>
          Complete these settings in the Power Platform admin center, then return to this application.
        </div>
      </div>
    </div>
  )
}
