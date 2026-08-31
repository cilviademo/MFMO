import { useState } from "react"
import { TopBar, TabStrip, Btn, Icons, Label, Select } from "../components/ui"
import type { Screen } from "../components/ui"

const REQ_OPTIONS = [
  { value: "", label: "Select requirement…" },
  { value: "1119", label: "1119 — AF Form 1119 Feeding Summary" },
  { value: "SF1080", label: "SF 1080 — Voucher for Transfers" },
  { value: "SAIIT", label: "SAIIT — Sales, Adjustments, Invoices, Inventory and Transfers" },
  { value: "GPC", label: "GPC — GPC Bank Statement" },
]

const TABS_BASE = [
  { id: "home", label: "Home" },
  { id: "package", label: "My Package", badge: 2 },
  { id: "calendar", label: "Calendar" },
]

export default function Submit({ nav }: { nav: (s: Screen) => void }) {
  const [req, setReq] = useState("")
  const [notes, setNotes] = useState("")
  const [dragOver, setDragOver] = useState(false)
  const [fileName, setFileName] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const canSubmit = req !== "" && fileName !== null

  if (submitted) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
        <TopBar period="August 2026" userName="SrA Kim, P." userRole="Base Accountant, JBSA Lackland" userInitials="PK" />
        <TabStrip tabs={TABS_BASE} active="package" onChange={() => {}} />
        <div style={{ flex: 1, padding: "40px", display: "flex", flexDirection: "column", gap: "0" }}>
          <div style={{ maxWidth: "520px" }}>
            <div style={{ marginBottom: "32px" }}>
              <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px", lineHeight: 1.2 }}>
                JBSA Lackland
              </h1>
              <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
                Legacy / APF · Portfolio 2 · August 2026 EOM
              </div>
            </div>

            {/* Confirmation */}
            <div style={{
              background: "var(--status-accepted-bg)",
              border: "1px solid var(--status-accepted-border)",
              borderLeft: "3px solid var(--status-accepted-border)",
              borderRadius: "0 2px 2px 0",
              padding: "20px",
              marginBottom: "24px",
            }}>
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: "var(--status-accepted-text)",
                fontSize: "13px",
                fontWeight: 700,
                letterSpacing: "0.02em",
                marginBottom: "6px",
              }}>
                <Icons.Check size={14} />
                Submitted
              </div>
              <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text)", marginBottom: "4px" }}>
                {req} &nbsp;·&nbsp; 4 Sep 2026 09:14
              </div>
              <div style={{
                fontSize: "13px",
                color: "var(--secondary)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                marginTop: "4px",
              }}>
                <Icons.Clock size={12} />
                Awaiting AFSVC review
              </div>
            </div>

            <Btn variant="subtle" onClick={() => nav("my-package")}>
              <Icons.ChevronRight size={14} />
              View package
            </Btn>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName="SrA Kim, P." userRole="Base Accountant, JBSA Lackland" userInitials="PK" />
      <TabStrip tabs={TABS_BASE} active="package" onChange={() => {}} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px" }}>
        <div style={{ maxWidth: "560px" }}>

          {/* Breadcrumb */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "24px", fontSize: "13px" }}>
            <button onClick={() => nav("base-home")} style={{
              background: "none", border: "none", color: "var(--accent)", fontSize: "13px",
              cursor: "pointer", padding: 0, textDecoration: "underline", textUnderlineOffset: "2px",
            }}>
              Home
            </button>
            <Icons.ChevronRight size={12} />
            <span style={{ color: "var(--secondary)" }}>Submit document</span>
          </div>

          <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 32px", lineHeight: 1.2 }}>
            Submit document
          </h1>

          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

            {/* Installation — pre-filled */}
            <div>
              <Label style={{ marginBottom: "6px" }}>Installation</Label>
              <div style={{
                height: "36px",
                padding: "0 12px",
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "4px",
                display: "flex",
                alignItems: "center",
                fontSize: "13px",
                color: "var(--secondary)",
              }}>
                JBSA Lackland
                <span style={{ marginLeft: "8px", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  · pre-filled from your access
                </span>
              </div>
            </div>

            {/* Reporting period — pre-filled */}
            <div>
              <Label style={{ marginBottom: "6px" }}>Reporting period</Label>
              <div style={{
                height: "36px",
                padding: "0 12px",
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "4px",
                display: "flex",
                alignItems: "center",
                fontSize: "13px",
                color: "var(--secondary)",
              }}>
                August 2026
                <span style={{ marginLeft: "8px", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  · pre-filled
                </span>
              </div>
            </div>

            {/* Requirement */}
            <div>
              <Label style={{ marginBottom: "6px" }}>Requirement</Label>
              <Select
                value={req}
                onChange={setReq}
                options={REQ_OPTIONS.slice(1)}
                placeholder="Select requirement…"
                style={{ width: "100%" }}
              />
            </div>

            {/* File drop target */}
            <div>
              <Label style={{ marginBottom: "6px" }}>File</Label>
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => {
                  e.preventDefault()
                  setDragOver(false)
                  const f = e.dataTransfer.files[0]
                  if (f) setFileName(f.name)
                }}
                style={{
                  border: `1.5px dashed ${dragOver ? "var(--accent)" : "var(--border)"}`,
                  borderRadius: "4px",
                  padding: "28px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "8px",
                  background: dragOver ? "var(--status-open-bg)" : "var(--bg)",
                  cursor: "pointer",
                  transition: "border-color 0.1s, background 0.1s",
                  textAlign: "center",
                }}
                onClick={() => {
                  // Simulate a file pick
                  if (!fileName) setFileName("Lackland_SAIIT_AUG2026.xlsx")
                }}
              >
                <div style={{ color: fileName ? "var(--status-accepted-text)" : "var(--secondary)" }}>
                  {fileName ? <Icons.Check size={24} /> : <Icons.Upload size={24} />}
                </div>
                {fileName ? (
                  <>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                      {fileName}
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); setFileName(null) }}
                      style={{ background: "none", border: "none", color: "var(--accent)", fontSize: "12px", cursor: "pointer" }}
                    >
                      Remove
                    </button>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
                      Drop a file here, or click to browse
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
                      PDF, XLSX, DOCX · Max 50 MB
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Notes — optional */}
            <div>
              <Label style={{ marginBottom: "6px" }}>Notes <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional)</span></Label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Any notes for the reviewer…"
                rows={3}
                style={{
                  width: "100%",
                  background: "var(--surface)",
                  color: "var(--text)",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  fontSize: "13px",
                  padding: "10px 12px",
                  fontFamily: "inherit",
                  resize: "vertical",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: "8px", paddingTop: "4px" }}>
              <Btn
                variant="primary"
                disabled={!canSubmit}
                onClick={() => setSubmitted(true)}
              >
                Submit
              </Btn>
              <Btn variant="subtle" onClick={() => nav("base-home")}>
                Cancel
              </Btn>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
