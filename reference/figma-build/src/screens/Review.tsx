import { useState } from "react"
import { TopBar, TabStrip, Panel, StatusChip, Btn, TextLink, Icons, PM_TABS, IDENTITY } from "../components/ui"
import type { Screen, Role } from "../components/ui"

interface VersionRow {
  v: string
  filename: string
  date: string
  by: string
  qc: "pending" | "accepted" | "rejected"
  current: boolean
}

const VERSIONS: VersionRow[] = [
  { v: "v2", filename: "Lackland_1119_AUG2026_v2.pdf", date: "4 Sep 09:14", by: "SrA Kim, P.", qc: "pending", current: true },
  { v: "v1", filename: "Lackland_1119_AUG2026.pdf", date: "1 Sep 14:07", by: "SrA Kim, P.", qc: "rejected", current: false },
]

const QC_COLOR = {
  pending: "var(--status-review-text)",
  accepted: "var(--status-accepted-text)",
  rejected: "var(--status-overdue-text)",
}
const QC_LABEL = { pending: "Pending", accepted: "Accepted", rejected: "Rejected" }

interface ReviewProps {
  nav: (s: Screen) => void
  role?: Role
  returningForCorrection?: boolean
  narrow?: boolean
}

const DECISIONS = [
  { id: "accept", label: "Accept", detail: "Document meets all requirements.", needsReason: false },
  { id: "correction", label: "Return for correction", detail: "Return to installation with comments.", needsReason: true },
  { id: "wrong", label: "Wrong document", detail: "File does not match the requirement.", needsReason: true },
  { id: "na", label: "Not applicable", detail: "Requirement does not apply this period.", needsReason: true },
]

const REASON_OPTIONS = [
  { value: "", label: "Select reason…" },
  { value: "period", label: "Wrong reporting period" },
  { value: "incomplete", label: "Incomplete — missing sections" },
  { value: "signature", label: "Missing signature or endorsement" },
  { value: "format", label: "Wrong format or template" },
  { value: "other", label: "Other — see comment" },
]

export default function Review({ nav, role = "pm", returningForCorrection = false, narrow = false }: ReviewProps) {
  const ident = IDENTITY.pm
  const [decision, setDecision] = useState(returningForCorrection ? "correction" : "accept")
  const [reason, setReason] = useState(returningForCorrection ? "period" : "")
  const [comment, setComment] = useState(returningForCorrection ? "The uploaded SAIIT reflects July. Submit the August review." : "")
  const [dueDate, setDueDate] = useState("")

  const selectedDecision = DECISIONS.find(d => d.id === decision)!
  const showDetails = selectedDecision.needsReason

  const layout = narrow ? "column" : "row"

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip tabs={PM_TABS} active="review" onChange={id => {
        if (id === "overview") nav("afsvc-overview")
        if (id === "installations") nav("installation")
        if (id === "calendar") nav("calendar")
        if (id === "admin") nav("admin")
      }} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "16px" }}>

        {/* Breadcrumb */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--secondary)" }}>
          <TextLink onClick={() => nav("afsvc-overview")} style={{ fontSize: "12px" }}>Overview</TextLink>
          <Icons.ChevronRight size={11} />
          <TextLink onClick={() => nav("review-queue")} style={{ fontSize: "12px" }}>Review queue</TextLink>
          <Icons.ChevronRight size={11} />
          <span>1119 · JBSA Lackland</span>
        </div>

        {/* Title row */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px", lineHeight: 1.2 }}>
              Review
            </h1>
            <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
              1119 — AF Form 1119 Feeding Summary &nbsp;·&nbsp; JBSA Lackland · Live Oak &nbsp;·&nbsp; August 2026
            </div>
          </div>
        </div>

        {/* Two-column layout */}
        <div style={{
          display: "flex",
          flexDirection: narrow ? "column" : "row",
          gap: "24px",
          alignItems: "flex-start",
          flex: 1,
        }}>

          {/* Left 65% — document workspace */}
          <div style={{ flex: narrow ? undefined : "0 0 65%", display: "flex", flexDirection: "column", gap: "16px", minWidth: 0, width: narrow ? "100%" : undefined }}>

            {/* Utility row */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "10px 0",
              borderBottom: "1px solid var(--border)",
              flexWrap: "wrap",
            }}>
              <div style={{ flex: 1, display: "flex", flexWrap: "wrap", gap: "16px", fontSize: "12px", color: "var(--secondary)" }}>
                <span><strong style={{ color: "var(--text)" }}>Requirement</strong> 1119</span>
                <span><strong style={{ color: "var(--text)" }}>Installation</strong> JBSA Lackland</span>
                <span><strong style={{ color: "var(--text)" }}>Period</strong> August 2026</span>
                <span><strong style={{ color: "var(--text)" }}>Version</strong> v2</span>
                <span><strong style={{ color: "var(--text)" }}>Submitted</strong> 4 Sep 09:14</span>
              </div>
              <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                <Btn variant="subtle" style={{ height: "28px", fontSize: "12px", padding: "0 10px" }}>
                  <Icons.ExternalLink size={13} />
                  Open in Teams
                </Btn>
                <Btn variant="subtle" style={{ height: "28px", fontSize: "12px", padding: "0 10px" }}>
                  <Icons.Download size={13} />
                  Download
                </Btn>
              </div>
            </div>

            {/* File placeholder */}
            <div style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "2px",
              padding: "24px",
              display: "flex",
              alignItems: "center",
              gap: "16px",
            }}>
              <div style={{ color: "var(--secondary)" }}>
                <Icons.Document size={32} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  color: "var(--text)",
                  fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                  marginBottom: "4px",
                }}>
                  Lackland_1119_AUG2026_v2.pdf
                </div>
                <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
                  PDF · 1.8 MB · Submitted 4 Sep 2026 09:14 by SrA Kim, P.
                </div>
                <div style={{ fontSize: "12px", color: "var(--secondary)", marginTop: "4px" }}>
                  Open document to review
                </div>
              </div>
              <Btn variant="subtle">
                <Icons.ExternalLink size={14} />
                Open document
              </Btn>
            </div>

            {/* Version history */}
            <Panel title="Version history">
              <div>
                {VERSIONS.map((v, i) => (
                  <div key={v.v} style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "10px 20px",
                    borderBottom: i < VERSIONS.length - 1 ? "1px solid var(--border)" : "none",
                    background: v.current ? "var(--status-open-bg)" : "transparent",
                  }}>
                    <span style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                      color: "var(--secondary)",
                      width: "22px",
                      flexShrink: 0,
                    }}>
                      {v.v}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: "12px",
                        color: "var(--text)",
                        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}>
                        {v.filename}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--secondary)", marginTop: "2px" }}>
                        {v.by} · {v.date}
                      </div>
                    </div>
                    <span style={{ fontSize: "11px", fontWeight: 600, color: QC_COLOR[v.qc] }}>
                      {QC_LABEL[v.qc]}
                    </span>
                    {v.current && (
                      <StatusChip status="open" />
                    )}
                  </div>
                ))}
              </div>
            </Panel>

            {/* Previous reviewer comment — only shown when returning */}
            {returningForCorrection && (
              <div style={{
                borderLeft: "3px solid var(--status-late-border)",
                background: "var(--status-late-bg)",
                padding: "14px 16px",
                borderRadius: "0 2px 2px 0",
              }}>
                <div style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: "var(--status-late-text)",
                  marginBottom: "6px",
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                }}>
                  <Icons.History size={12} />
                  Previous reviewer comment — v1 rejection (1 Sep 2026)
                </div>
                <div style={{ fontSize: "13px", color: "var(--text)", lineHeight: 1.6, fontStyle: "italic" }}>
                  "The uploaded SAIIT reflects July figures. The header date reads 31 Jul 2026. Resubmit with the August reporting period."
                </div>
                <div style={{ fontSize: "11px", color: "var(--secondary)", marginTop: "6px" }}>
                  Maj. Chen, S. — AFSVC Portfolio Manager
                </div>
              </div>
            )}
          </div>

          {/* Right 35% — decision panel */}
          <div style={{
            flex: narrow ? undefined : "0 0 35%",
            width: narrow ? "100%" : undefined,
            position: narrow ? undefined : "sticky",
            top: 0,
          }}>
            <Panel title="Decision">
              <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>

                {DECISIONS.map(d => {
                  const isSel = decision === d.id
                  return (
                    <button
                      key={d.id}
                      onClick={() => setDecision(d.id)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        background: isSel ? "var(--status-open-bg)" : "var(--surface)",
                        border: isSel ? "1.5px solid var(--accent)" : "1px solid var(--border)",
                        borderRadius: "2px",
                        padding: "10px 12px",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        gap: "3px",
                        transition: "border-color 0.1s",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <div style={{
                          width: "13px",
                          height: "13px",
                          borderRadius: "50%",
                          border: `1.5px solid ${isSel ? "var(--accent)" : "var(--border)"}`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}>
                          {isSel && (
                            <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: "var(--accent)" }} />
                          )}
                        </div>
                        <span style={{ fontSize: "13px", fontWeight: 600, color: isSel ? "var(--accent)" : "var(--text)" }}>
                          {d.label}
                        </span>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--secondary)", paddingLeft: "21px" }}>
                        {d.detail}
                      </div>
                    </button>
                  )
                })}

                {/* Progressive disclosure */}
                {showDetails && (
                  <>
                    <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "4px" }}>
                      <label style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        color: "var(--secondary)",
                      }}>
                        Reason
                      </label>
                      <select
                        value={reason}
                        onChange={e => setReason(e.target.value)}
                        style={{
                          height: "32px",
                          background: "var(--surface)",
                          color: reason === "" ? "var(--secondary)" : "var(--text)",
                          border: "1px solid var(--border)",
                          borderRadius: "4px",
                          fontSize: "13px",
                          padding: "0 10px",
                          fontFamily: "inherit",
                          cursor: "pointer",
                          appearance: "none",
                          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 16 16'%3E%3Cpolyline points='3.5,6 8,10 12.5,6' stroke='%23616161' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")`,
                          backgroundRepeat: "no-repeat",
                          backgroundPosition: "right 8px center",
                        }}
                      >
                        {REASON_OPTIONS.map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                      <label style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        color: "var(--secondary)",
                      }}>
                        Comment
                      </label>
                      <textarea
                        value={comment}
                        onChange={e => setComment(e.target.value)}
                        placeholder="Explain what needs to be corrected…"
                        rows={3}
                        style={{
                          background: "var(--surface)",
                          color: "var(--text)",
                          border: "1px solid var(--border)",
                          borderRadius: "4px",
                          fontSize: "13px",
                          padding: "8px 10px",
                          fontFamily: "inherit",
                          resize: "vertical",
                          width: "100%",
                        }}
                      />
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                      <label style={{
                        fontSize: "11px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        color: "var(--secondary)",
                      }}>
                        Correction due
                      </label>
                      <input
                        type="date"
                        value={dueDate}
                        onChange={e => setDueDate(e.target.value)}
                        style={{
                          height: "32px",
                          background: "var(--surface)",
                          color: "var(--text)",
                          border: "1px solid var(--border)",
                          borderRadius: "4px",
                          fontSize: "13px",
                          padding: "0 10px",
                          fontFamily: "inherit",
                          width: "100%",
                        }}
                      />
                    </div>
                  </>
                )}

                <Btn
                  variant="primary"
                  style={{ marginTop: "4px", justifyContent: "center" }}
                  disabled={showDetails && (reason === "" || comment === "")}
                >
                  Save decision
                </Btn>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  )
}
