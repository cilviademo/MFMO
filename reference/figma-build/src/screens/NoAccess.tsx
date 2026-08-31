import type { Screen } from "../components/ui"
import { Btn, Icons } from "../components/ui"

interface NoAccessProps {
  nav: (s: Screen) => void
  pending?: boolean
}

export default function NoAccess({ nav, pending = false }: NoAccessProps) {
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
          background: "var(--status-na-bg)",
          border: "1px solid var(--status-na-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--status-na-text)",
        }}>
          <Icons.Lock size={22} />
        </div>

        {/* Heading + body */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ fontSize: "22px", fontWeight: 300, color: "var(--text)", lineHeight: 1.2 }}>
            Your account isn't mapped to an installation yet.
          </div>
          <div style={{ fontSize: "14px", color: "var(--secondary)", lineHeight: 1.6 }}>
            Access to this application requires your account to be associated with a specific
            installation and portfolio. Contact your Portfolio Manager to request access or
            submit a request below.
          </div>
        </div>

        {/* Pending state notice */}
        {pending && (
          <div style={{
            background: "var(--status-review-bg)",
            border: "1px solid var(--status-review-border)",
            borderRadius: "2px",
            padding: "10px 14px",
            fontSize: "13px",
            color: "var(--status-review-text)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}>
            <Icons.Clock size={14} />
            Requested 2 Sep · awaiting review
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {!pending && (
            <Btn variant="primary" onClick={() => nav("request-access")}>
              Request access
            </Btn>
          )}
          <Btn variant="subtle">
            Contact your Portfolio Manager
          </Btn>
        </div>
      </div>
    </div>
  )
}
