import type { Screen } from "../components/ui"
import { Btn, Icons } from "../components/ui"

interface ScopeUnresolvedProps {
  nav: (s: Screen) => void
}

export default function ScopeUnresolved({ nav }: ScopeUnresolvedProps) {
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
        maxWidth: "480px",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: "24px",
      }}>
        {/* Icon */}
        <div style={{
          width: "44px",
          height: "44px",
          borderRadius: "4px",
          background: "var(--status-late-bg)",
          border: "1px solid var(--status-late-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--status-late-text)",
        }}>
          <Icons.Warning size={22} />
        </div>

        {/* Heading + body */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "22px", fontWeight: 300, color: "var(--text)", lineHeight: 1.2 }}>
            We couldn't verify which installation you work at.
          </div>
          <div style={{ fontSize: "14px", color: "var(--secondary)", lineHeight: 1.6 }}>
            Your account was authenticated but we weren't able to determine your installation
            assignment. This may be a configuration issue. If the problem persists, contact
            your Portfolio Manager with the reference below.
          </div>
        </div>

        {/* Error reference — selectable */}
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          padding: "10px 14px",
          fontSize: "13px",
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          width: "100%",
        }}>
          <span style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--secondary)" }}>
            Reference
          </span>
          <span
            style={{
              fontVariantNumeric: "tabular-nums",
              userSelect: "text",
              color: "var(--text)",
              fontWeight: 600,
              fontSize: "14px",
              letterSpacing: "0.03em",
            }}
          >
            MF-20260831-A7F4
          </span>
          <span style={{ fontSize: "11px", color: "var(--secondary)" }}>
            Include this reference when contacting your Portfolio Manager or submitting a help request.
          </span>
        </div>

        {/* Action */}
        <div style={{ display: "flex", gap: "8px" }}>
          <Btn variant="primary" onClick={() => nav("request-access")}>
            Request access
          </Btn>
        </div>
      </div>
    </div>
  )
}
