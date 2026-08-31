import { useState } from "react"
import type { Screen } from "../components/ui"
import { Btn, Icons, Label } from "../components/ui"

// Installation search options — authoritative names from QRG__Scrubbed_.csv only
const INSTALLATIONS = [
  "Altus AFB",
  "Andersen AB",
  "Arnold AFB",
  "Charleston, JB",
  "Creech AFB",
  "Fairchild AFB",
  "JBSA Lackland",
  "Minot AFB (2.0)",
  "Minot AFB (MAF)",
]

interface RequestAccessProps {
  nav: (s: Screen) => void
}

export default function RequestAccess({ nav }: RequestAccessProps) {
  const [installation, setInstallation] = useState("")
  const [query, setQuery] = useState("")
  const [reason, setReason] = useState("")
  const [neededUntil, setNeededUntil] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [open, setOpen] = useState(false)

  const filtered = INSTALLATIONS.filter(i =>
    i.toLowerCase().includes(query.toLowerCase())
  )

  if (submitted) {
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
          gap: "20px",
        }}>
          <div style={{
            width: "44px",
            height: "44px",
            borderRadius: "4px",
            background: "var(--status-review-bg)",
            border: "1px solid var(--status-review-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--status-review-text)",
          }}>
            <Icons.Clock size={22} />
          </div>
          <div style={{ fontSize: "22px", fontWeight: 300, color: "var(--text)", lineHeight: 1.2 }}>
            Request submitted.
          </div>
          <div style={{ fontSize: "14px", color: "var(--secondary)", lineHeight: 1.6 }}>
            Your Portfolio Manager will review this request. You'll receive a notification in
            Microsoft Teams when your access has been granted or declined.
          </div>
          <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
            Installation requested: <strong style={{ color: "var(--text)" }}>{installation}</strong>
          </div>
        </div>
      </div>
    )
  }

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
        gap: "24px",
      }}>
        {/* Header */}
        <div>
          <div style={{ fontSize: "22px", fontWeight: 300, color: "var(--text)", lineHeight: 1.2, marginBottom: "8px" }}>
            Request access
          </div>
          <div style={{ fontSize: "14px", color: "var(--secondary)", lineHeight: 1.6 }}>
            Your Portfolio Manager will review this request.
          </div>
        </div>

        {/* Installation search */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", position: "relative" }}>
          <Label>Installation</Label>
          <input
            type="text"
            placeholder="Search installations…"
            value={installation || query}
            onChange={e => {
              setQuery(e.target.value)
              setInstallation("")
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            style={{
              height: "32px",
              border: "1px solid var(--border)",
              borderRadius: "2px",
              padding: "0 10px",
              fontSize: "13px",
              background: "var(--surface)",
              color: "var(--text)",
              outline: "none",
              width: "100%",
            }}
          />
          {open && filtered.length > 0 && !installation && (
            <div style={{
              position: "absolute",
              top: "60px",
              left: 0,
              right: 0,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "2px",
              maxHeight: "180px",
              overflowY: "auto",
              zIndex: 10,
              boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            }}>
              {filtered.map(inst => (
                <div
                  key={inst}
                  onMouseDown={() => {
                    setInstallation(inst)
                    setQuery("")
                    setOpen(false)
                  }}
                  style={{
                    padding: "7px 12px",
                    fontSize: "13px",
                    cursor: "pointer",
                    color: "var(--text)",
                  }}
                >
                  {inst}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Reason */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <Label>Reason for access</Label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="Briefly describe why you need access to this installation."
            rows={3}
            style={{
              border: "1px solid var(--border)",
              borderRadius: "2px",
              padding: "8px 10px",
              fontSize: "13px",
              background: "var(--surface)",
              color: "var(--text)",
              outline: "none",
              resize: "vertical",
              fontFamily: "inherit",
              lineHeight: 1.5,
            }}
          />
        </div>

        {/* Needed until */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <Label>Needed until <span style={{ fontWeight: 400, color: "var(--secondary)" }}>(optional)</span></Label>
          <input
            type="date"
            value={neededUntil}
            onChange={e => setNeededUntil(e.target.value)}
            style={{
              height: "32px",
              border: "1px solid var(--border)",
              borderRadius: "2px",
              padding: "0 10px",
              fontSize: "13px",
              background: "var(--surface)",
              color: "var(--text)",
              outline: "none",
              width: "180px",
            }}
          />
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", paddingTop: "4px" }}>
          <Btn
            variant="primary"
            disabled={!installation || !reason.trim()}
            onClick={() => setSubmitted(true)}
          >
            Submit request
          </Btn>
          <Btn variant="subtle" onClick={() => nav("launch")}>
            Cancel
          </Btn>
        </div>
      </div>
    </div>
  )
}
