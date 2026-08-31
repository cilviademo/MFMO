import { useState } from "react"
import { TopBar, TabStrip, Btn, TextLink, Icons, Label, PM_TABS, IDENTITY } from "../components/ui"
import type { Screen, Role } from "../components/ui"

interface Person {
  id: string
  name: string
  installation: string
  role: "base" | "pm"
  granted: string | null
  expires: string | null
}

interface PendingRequest {
  id: string
  name: string
  rank: string
  homeInstall: string
  reqInstall: string
  reason: string
  neededUntil: string | null
}

const PEOPLE: Person[] = [
  { id: "1", name: "Kim, P.",    installation: "JBSA Lackland", role: "base", granted: null,       expires: null },
  { id: "2", name: "Torres, M.", installation: "JBSA Lackland", role: "pm",   granted: "4 Aug 26", expires: null },
  { id: "3", name: "Nguyen, D.", installation: "Creech AFB",    role: "base", granted: null,       expires: null },
]

// Current user — cannot revoke their own access
const CURRENT_USER_ID = "2"

const PENDING: PendingRequest[] = [
  { id: "p1", name: "Chen, R.",      rank: "SSgt", homeInstall: "JBSA Lackland", reqInstall: "Creech AFB", reason: "TDY to Creech for 30 days", neededUntil: "30 Sep 26" },
  { id: "p2", name: "Rodriguez, S.", rank: "A1C",  homeInstall: "JBSA Lackland", reqInstall: "Altus AFB",  reason: "Cross-training assignment",  neededUntil: null },
]

function AdminSubNav({ active, nav }: { active: "health" | "access"; nav: (s: Screen) => void }) {
  return (
    <div style={{
      display: "flex",
      gap: "0",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      padding: "0 40px",
    }}>
      {[
        { id: "health" as const, label: "System health", screen: "admin" as Screen },
        { id: "access" as const, label: "Access management", screen: "access-mgmt" as Screen },
      ].map(item => (
        <button
          key={item.id}
          onClick={() => nav(item.screen)}
          style={{
            background: "none",
            border: "none",
            borderBottom: active === item.id ? "2px solid var(--accent)" : "2px solid transparent",
            color: active === item.id ? "var(--accent)" : "var(--secondary)",
            fontSize: "13px",
            fontWeight: active === item.id ? 600 : 400,
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

interface DialogProps {
  mode: "grant" | "revoke"
  person: Person
  onClose: () => void
}

function Dialog({ mode, person, onClose }: DialogProps) {
  const [duration, setDuration] = useState<"permanent" | "until">("permanent")
  const [date, setDate] = useState("")
  const [reason, setReason] = useState("")

  const isGrant = mode === "grant"
  const canSubmit = reason.trim().length > 0 && (duration === "permanent" || date !== "")

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.4)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 500,
    }}>
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "4px",
        padding: "28px",
        width: "440px",
        maxWidth: "90vw",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}>
        {/* Header */}
        <div>
          <div style={{
            fontSize: "11px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.07em",
            color: isGrant ? "var(--status-review-text)" : "var(--status-overdue-text)",
            marginBottom: "6px",
          }}>
            {isGrant ? "Grant Portfolio Manager" : "Revoke Portfolio Manager"}
          </div>
          <div style={{ fontSize: "14px", color: "var(--secondary)" }}>
            {person.name} · {person.installation}
          </div>
        </div>

        {isGrant ? (
          <>
            {/* Scope */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <Label>Scope</Label>
              <select
                style={{
                  height: "32px",
                  border: "1px solid var(--border)",
                  borderRadius: "2px",
                  padding: "0 10px",
                  fontSize: "13px",
                  background: "var(--surface)",
                  color: "var(--text)",
                }}
              >
                <option>Portfolio 2</option>
              </select>
            </div>

            {/* Duration */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <Label>Duration</Label>
              {(["permanent", "until"] as const).map(opt => (
                <label key={opt} style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "13px", color: "var(--text)" }}>
                  <input
                    type="radio"
                    name="duration"
                    value={opt}
                    checked={duration === opt}
                    onChange={() => setDuration(opt)}
                    style={{ accentColor: "var(--accent)" }}
                  />
                  {opt === "permanent" ? "Permanent" : (
                    <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      Until
                      {duration === "until" && (
                        <input
                          type="date"
                          value={date}
                          onChange={e => setDate(e.target.value)}
                          style={{
                            height: "28px",
                            border: "1px solid var(--border)",
                            borderRadius: "2px",
                            padding: "0 8px",
                            fontSize: "12px",
                            background: "var(--surface)",
                            color: "var(--text)",
                          }}
                        />
                      )}
                    </span>
                  )}
                </label>
              ))}
            </div>
          </>
        ) : (
          /* Revoke — what the person loses */
          <div style={{
            background: "var(--status-overdue-bg)",
            border: "1px solid var(--status-overdue-border)",
            borderRadius: "2px",
            padding: "12px 14px",
            fontSize: "13px",
            color: "var(--status-overdue-text)",
            lineHeight: 1.6,
          }}>
            {person.name} will lose the ability to review submissions, manage the facility
            registry, and grant access to others.
          </div>
        )}

        {/* Reason */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <Label>Reason <span style={{ fontWeight: 400, color: "var(--secondary)" }}>(required)</span></Label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={2}
            style={{
              border: "1px solid var(--border)",
              borderRadius: "2px",
              padding: "8px 10px",
              fontSize: "13px",
              background: "var(--surface)",
              color: "var(--text)",
              resize: "vertical",
              fontFamily: "inherit",
              lineHeight: 1.5,
              outline: "none",
            }}
          />
        </div>

        {/* Warning */}
        {isGrant && (
          <div style={{ fontSize: "12px", color: "var(--secondary)", lineHeight: 1.6 }}>
            This person will be able to review submissions, manage the registry, and grant
            this role to others.
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
          <Btn variant="subtle" onClick={onClose}>Cancel</Btn>
          <Btn
            variant="primary"
            disabled={!canSubmit}
            onClick={onClose}
          >
            {isGrant ? "Grant" : "Revoke"}
          </Btn>
        </div>
      </div>
    </div>
  )
}

interface AccessManagementProps {
  nav: (s: Screen) => void
  role: Role
}

export default function AccessManagement({ nav, role }: AccessManagementProps) {
  const [view, setView] = useState<"table" | "pending">("table")
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState("all")
  const [dialogMode, setDialogMode] = useState<"grant" | "revoke" | null>(null)
  const [dialogPerson, setDialogPerson] = useState<Person | null>(null)

  const ident = IDENTITY.pm

  const filtered = PEOPLE.filter(p => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.installation.toLowerCase().includes(search.toLowerCase())) return false
    if (roleFilter !== "all" && p.role !== roleFilter) return false
    return true
  })

  const openDialog = (mode: "grant" | "revoke", person: Person) => {
    setDialogMode(mode)
    setDialogPerson(person)
  }

  const colStyle = (w?: string): React.CSSProperties => ({
    width: w,
    padding: "0 16px",
    fontSize: "13px",
    color: "var(--text)",
    whiteSpace: "nowrap" as const,
    overflow: "hidden",
    textOverflow: "ellipsis",
  })

  const thStyle = (w?: string): React.CSSProperties => ({
    ...colStyle(w),
    fontSize: "11px",
    fontWeight: 700,
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    color: "var(--secondary)",
  })

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" userName={ident.userName} userRole={ident.userRole} userInitials={ident.userInitials} />
      <TabStrip
        tabs={PM_TABS}
        active="admin"
        onChange={id => {
          if (id === "overview") nav("afsvc-overview")
          if (id === "review") nav("review-queue")
          if (id === "installations") nav("installation")
          if (id === "calendar") nav("calendar")
        }}
      />
      <AdminSubNav active="access" nav={nav} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "24px" }}>

        {/* Heading */}
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px" }}>
              Access management
            </h1>
            <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
              Portfolio 2 · {PEOPLE.length} people
            </div>
          </div>
        </div>

        {/* Pending requests banner */}
        {PENDING.length > 0 && view === "table" && (
          <div style={{
            background: "var(--status-review-bg)",
            border: "1px solid var(--status-review-border)",
            borderRadius: "2px",
            padding: "10px 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
          }}>
            <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--status-review-text)" }}>
              {PENDING.length} access {PENDING.length === 1 ? "request" : "requests"} pending
            </span>
            <TextLink onClick={() => setView("pending")} style={{ fontSize: "13px" }}>
              Review requests <Icons.ChevronRight size={12} />
            </TextLink>
          </div>
        )}

        {view === "pending" ? (
          /* ── Pending requests ── */
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <TextLink onClick={() => setView("table")} style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "4px" }}>
                <Icons.ChevronLeft size={12} /> Back
              </TextLink>
              <span style={{ fontSize: "16px", fontWeight: 600, color: "var(--text)" }}>
                Pending access requests
              </span>
            </div>

            {PENDING.map(req => (
              <div key={req.id} style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "2px",
                padding: "20px 24px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px" }}>
                  <div>
                    <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--text)", marginBottom: "3px" }}>
                      {req.rank} {req.name}
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--secondary)" }}>
                      {req.homeInstall} → <strong style={{ color: "var(--text)" }}>{req.reqInstall}</strong>
                      {req.neededUntil && ` · Until ${req.neededUntil}`}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                    <Btn variant="primary" onClick={() => setView("table")}>Approve</Btn>
                    <Btn variant="subtle" onClick={() => setView("table")}>Deny</Btn>
                  </div>
                </div>
                <div style={{
                  fontSize: "13px",
                  color: "var(--secondary)",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "2px",
                  padding: "10px 14px",
                  lineHeight: 1.6,
                }}>
                  <span style={{ fontWeight: 600, color: "var(--text)" }}>Reason: </span>
                  {req.reason}
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* ── Table view ── */
          <>
            {/* Filter toolbar */}
            <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ position: "relative", flex: "1", minWidth: "160px", maxWidth: "280px" }}>
                <span style={{ position: "absolute", left: "9px", top: "50%", transform: "translateY(-50%)", color: "var(--secondary)", pointerEvents: "none", display: "flex" }}>
                  <Icons.Search size={13} />
                </span>
                <input
                  type="text"
                  placeholder="Search people…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{
                    height: "32px",
                    width: "100%",
                    border: "1px solid var(--border)",
                    borderRadius: "2px",
                    padding: "0 10px 0 30px",
                    fontSize: "13px",
                    background: "var(--surface)",
                    color: "var(--text)",
                    outline: "none",
                  }}
                />
              </div>
              <select
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
                style={{
                  height: "32px",
                  border: "1px solid var(--border)",
                  borderRadius: "2px",
                  padding: "0 10px",
                  fontSize: "13px",
                  background: "var(--surface)",
                  color: "var(--text)",
                }}
              >
                <option value="all">All roles</option>
                <option value="base">Base user</option>
                <option value="pm">Portfolio Manager</option>
              </select>
              {(search || roleFilter !== "all") && (
                <TextLink onClick={() => { setSearch(""); setRoleFilter("all") }} style={{ fontSize: "12px" }}>
                  Reset
                </TextLink>
              )}
            </div>

            {/* Table */}
            <div style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "2px",
              overflow: "hidden",
            }}>
              {/* Header */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "1fr 160px 160px 100px 120px 120px",
                height: "36px",
                borderBottom: "1px solid var(--border)",
                alignItems: "center",
                background: "var(--bg)",
              }}>
                {["Name", "Installation", "Role", "Granted", "Expires", ""].map((h, i) => (
                  <div key={i} style={thStyle()}>{h}</div>
                ))}
              </div>

              {filtered.map((person, i) => (
                <div
                  key={person.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 160px 160px 100px 120px 120px",
                    height: "52px",
                    borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none",
                    alignItems: "center",
                  }}
                >
                  <div style={colStyle()}>
                    <span style={{ fontWeight: 600 }}>{person.name}</span>
                  </div>
                  <div style={{ ...colStyle("160px"), color: "var(--secondary)" }}>
                    {person.installation}
                  </div>
                  <div style={colStyle("160px")}>
                    <span style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: "2px",
                      background: person.role === "pm" ? "var(--status-review-bg)" : "var(--bg)",
                      color: person.role === "pm" ? "var(--status-review-text)" : "var(--secondary)",
                      border: `1px solid ${person.role === "pm" ? "var(--status-review-border)" : "var(--border)"}`,
                    }}>
                      {person.role === "pm" ? "Portfolio Manager" : "Base user"}
                    </span>
                  </div>
                  <div style={{ ...colStyle("100px"), fontSize: "12px", color: "var(--secondary)" }}>
                    {person.granted ?? "—"}
                  </div>
                  <div style={{ padding: "0 16px", fontSize: "12px" }}>
                    {person.expires ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
                        <span style={{ color: "var(--status-late-text)", fontWeight: 600 }}>{person.expires}</span>
                        <span style={{ fontSize: "10px", color: "var(--secondary)" }}>temporary</span>
                      </div>
                    ) : (
                      <span style={{ color: "var(--secondary)" }}>—</span>
                    )}
                  </div>
                  <div style={{ padding: "0 16px", display: "flex", justifyContent: "flex-end" }}>
                    {person.id === CURRENT_USER_ID ? (
                      <span style={{ fontSize: "12px", color: "var(--secondary)" }}>—</span>
                    ) : (
                      <TextLink
                        onClick={() => openDialog(person.role === "base" ? "grant" : "revoke", person)}
                        style={{ fontSize: "12px", whiteSpace: "nowrap" }}
                      >
                        {person.role === "base" ? "Grant Portfolio Manager" : "Revoke"} <Icons.ChevronRight size={11} />
                      </TextLink>
                    )}
                  </div>
                </div>
              ))}

              {filtered.length === 0 && (
                <div style={{ padding: "32px", textAlign: "center", fontSize: "13px", color: "var(--secondary)" }}>
                  No results match your filters.
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Grant / Revoke dialog */}
      {dialogMode && dialogPerson && (
        <Dialog
          mode={dialogMode}
          person={dialogPerson}
          onClose={() => { setDialogMode(null); setDialogPerson(null) }}
        />
      )}
    </div>
  )
}
