import { useState, useRef, useEffect } from "react"
import type { Screen, EnvBanner, Role } from "./components/ui"
import { EnvironmentBanner } from "./components/ui"
import Launch from "./screens/Launch"
import BaseHome from "./screens/BaseHome"
import Submit from "./screens/Submit"
import MyPackage from "./screens/MyPackage"
import AFSVCOverview from "./screens/AFSVCOverview"
import ReviewQueue from "./screens/ReviewQueue"
import Review from "./screens/Review"
import InstallationWorkspace from "./screens/InstallationWorkspace"
import CalendarScreen from "./screens/Calendar"
import AdminHealth from "./screens/AdminHealth"
import AccessManagement from "./screens/AccessManagement"
import EmptyState from "./screens/EmptyState"
import NoAccess from "./screens/NoAccess"
import ScopeUnresolved from "./screens/ScopeUnresolved"
import ConfigRequired from "./screens/ConfigRequired"
import RequestAccess from "./screens/RequestAccess"

// ── Frame catalogue ───────────────────────────────────────────────────────────

type Frame = { id: Screen; label: string }

const FRAME_GROUPS_BASE: { label: string; frames: Frame[] }[] = [
  {
    label: "Base",
    frames: [
      { id: "base-home",       label: "Home" },
      { id: "base-correction", label: "Home (correction)" },
      { id: "submit",          label: "Submit" },
      { id: "my-package",      label: "My Package" },
    ],
  },
  {
    label: "System states",
    frames: [
      { id: "no-access",        label: "No access" },
      { id: "scope-unresolved", label: "Scope unresolved" },
      { id: "config-required",  label: "Config required" },
      { id: "request-access",   label: "Request access" },
      { id: "admin-banner",     label: "Env banner (pilot)" },
      { id: "empty-state",      label: "Empty state" },
    ],
  },
  {
    label: "Responsive",
    frames: [
      { id: "base-768", label: "Base 768px" },
    ],
  },
]

const FRAME_GROUPS_PM: { label: string; frames: Frame[] }[] = [
  {
    label: "Base (for comparison)",
    frames: [
      { id: "base-home",    label: "Home — base user" },
      { id: "base-home-pm", label: "Home — Portfolio Manager" },
    ],
  },
  {
    label: "AFSVC",
    frames: [
      { id: "afsvc-overview",    label: "Overview" },
      { id: "review-queue",      label: "Review queue" },
      { id: "review-correction", label: "Review (correction)" },
      { id: "installation",      label: "Installation" },
      { id: "calendar",          label: "Calendar" },
      { id: "calendar-add-date", label: "Add a date (dialog)" },
      { id: "admin",             label: "Admin health" },
      { id: "access-mgmt",       label: "Access management" },
    ],
  },
  {
    label: "System states",
    frames: [
      { id: "no-access",        label: "No access" },
      { id: "scope-unresolved", label: "Scope unresolved" },
      { id: "config-required",  label: "Config required" },
      { id: "request-access",   label: "Request access" },
      { id: "admin-banner",     label: "Env banner (pilot)" },
      { id: "empty-state",      label: "Empty state" },
    ],
  },
  {
    label: "Responsive",
    frames: [
      { id: "review-768", label: "Review 768px" },
    ],
  },
]

// ── Frames panel + role switcher (fixed bottom-right, outside app chrome) ─────

function Harness({
  screen, role, onRoleChange, nav, dark, setDark, banner, setBanner,
}: {
  screen: Screen
  role: Role
  onRoleChange: (r: Role) => void
  nav: (s: Screen) => void
  dark: boolean
  setDark: (v: boolean) => void
  banner: EnvBanner
  setBanner: (v: EnvBanner) => void
}) {
  const [open, setOpen] = useState(false)
  const [roleOpen, setRoleOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const roleRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open && !roleOpen) return
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
      if (roleRef.current && !roleRef.current.contains(e.target as Node)) setRoleOpen(false)
    }
    document.addEventListener("mousedown", handle)
    return () => document.removeEventListener("mousedown", handle)
  }, [open, roleOpen])

  const groups = role === "pm" ? FRAME_GROUPS_PM : FRAME_GROUPS_BASE

  const ctrlBtn: React.CSSProperties = {
    height: "22px",
    padding: "0 8px",
    borderRadius: "3px",
    fontSize: "10px",
    fontWeight: 600,
    cursor: "pointer",
    border: "1px solid #444",
    letterSpacing: "0.04em",
  }

  return (
    <div
      ref={ref}
      style={{ position: "fixed", bottom: "16px", right: "16px", zIndex: 9999, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}
    >
      {/* Role dropdown — opens upward */}
      {roleOpen && (
        <div ref={roleRef} style={{
          position: "absolute",
          bottom: "42px",
          right: 0,
          background: "#1c1c1c",
          border: "1px solid #3a3a3a",
          borderRadius: "6px",
          overflow: "hidden",
          minWidth: "180px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
        }}>
          <div style={{ padding: "6px 12px 4px", fontSize: "9px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#555" }}>
            Test harness — role
          </div>
          {(["base", "pm"] as Role[]).map(r => (
            <button
              key={r}
              onClick={() => { onRoleChange(r); setRoleOpen(false) }}
              style={{
                display: "block",
                width: "100%",
                padding: "9px 16px",
                background: role === r ? "#2d4a6b" : "transparent",
                border: "none",
                color: role === r ? "#8cc8f0" : "#999",
                fontSize: "13px",
                fontWeight: role === r ? 600 : 400,
                textAlign: "left",
                cursor: "pointer",
              }}
            >
              {r === "pm" ? "Portfolio Manager" : "Base user"}
            </button>
          ))}
        </div>
      )}
      {open && (
        <div style={{
          background: "#1c1c1c",
          border: "1px solid #3a3a3a",
          borderRadius: "6px",
          padding: "12px",
          minWidth: "200px",
          maxHeight: "70vh",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
        }}>
          {/* Controls */}
          <div style={{ display: "flex", gap: "6px", paddingBottom: "10px", borderBottom: "1px solid #333", flexWrap: "wrap" }}>
            <button onClick={() => { nav("launch"); setOpen(false) }} style={{ ...ctrlBtn, background: "#2a2a2a", color: "#aaa" }}>Launch</button>
            <button onClick={() => setDark(!dark)} style={{ ...ctrlBtn, background: dark ? "#4ea0d4" : "#2a2a2a", color: dark ? "#fff" : "#aaa" }}>{dark ? "Dark ✓" : "Dark"}</button>
            <button onClick={() => setBanner(banner === "pilot" ? null : "pilot")} style={{ ...ctrlBtn, background: banner === "pilot" ? "#555" : "#2a2a2a", color: "#aaa" }}>Pilot</button>
            <button onClick={() => setBanner(banner === "readonly" ? null : "readonly")} style={{ ...ctrlBtn, background: banner === "readonly" ? "#555" : "#2a2a2a", color: "#aaa" }}>RO</button>
          </div>

          {/* Frame groups filtered by role */}
          {groups.map(group => (
            <div key={group.label}>
              <div style={{ fontSize: "9px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#666", marginBottom: "6px" }}>
                {group.label}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
                {group.frames.map(f => (
                  <button
                    key={f.id}
                    onClick={() => { nav(f.id); setOpen(false) }}
                    style={{
                      background: screen === f.id ? "#2d4a6b" : "transparent",
                      border: "none",
                      borderRadius: "3px",
                      color: screen === f.id ? "#8cc8f0" : "#999",
                      fontSize: "12px",
                      fontWeight: screen === f.id ? 600 : 400,
                      padding: "5px 8px",
                      textAlign: "left",
                      cursor: "pointer",
                      width: "100%",
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: "6px" }}>
        {/* Role pill */}
        <button
          onClick={() => { setRoleOpen(o => !o); setOpen(false) }}
          style={{
            height: "32px",
            padding: "0 12px",
            borderRadius: "16px",
            background: "#2a2a2a",
            border: "1px solid #444",
            color: "#aaa",
            fontSize: "11px",
            fontWeight: 600,
            cursor: "pointer",
            letterSpacing: "0.03em",
            display: "flex",
            alignItems: "center",
            gap: "5px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}
        >
          <span style={{ color: "#555", fontSize: "10px" }}>Role</span>
          {role === "pm" ? "Portfolio Manager" : "Base user"}
          <span style={{ fontSize: "9px", opacity: 0.5 }}>▾</span>
        </button>
        {/* Frames pill */}
        <button
          onClick={() => { setOpen(o => !o); setRoleOpen(false) }}
          style={{
            height: "32px",
            padding: "0 14px",
            borderRadius: "16px",
            background: "#2a2a2a",
            border: "1px solid #444",
            color: "#888",
            fontSize: "11px",
            fontWeight: 600,
            cursor: "pointer",
            letterSpacing: "0.04em",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}
        >
          Frames
        </button>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen] = useState<Screen>("launch")
  const [role, setRole] = useState<Role>("base")
  const [dark, setDark] = useState(false)
  const [banner, setBanner] = useState<EnvBanner>(null)

  const nav = (s: Screen) => setScreen(s)

  const handleRoleChange = (r: Role) => {
    setRole(r)
    // Navigate to the appropriate home for the new role
    setScreen(r === "pm" ? "afsvc-overview" : "base-home")
  }

  const is768 = screen === "base-768" || screen === "review-768"
  const isLaunch = screen === "launch"

  return (
    <div className={dark ? "dark" : ""} style={{ height: "100%", display: "flex", flexDirection: "column" }}>

      {/* App frame */}
      <div style={{
        flex: 1,
        overflow: is768 ? "auto" : "hidden",
        display: "flex",
        justifyContent: is768 ? "center" : undefined,
        background: is768 ? "var(--bg)" : undefined,
      }}>
        <div style={{
          width: is768 ? "768px" : "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          flexShrink: is768 ? 0 : undefined,
          borderLeft: is768 ? "1px solid var(--border)" : "none",
          borderRight: is768 ? "1px solid var(--border)" : "none",
        }}>
          {!isLaunch && <EnvironmentBanner banner={banner} />}

          {screen === "launch"            && <Launch nav={nav} role={role} />}
          {screen === "base-home"         && <BaseHome nav={nav} />}
          {screen === "base-correction"   && <BaseHome nav={nav} hasCorrection />}
          {screen === "submit"            && <Submit nav={nav} />}
          {screen === "my-package"        && <MyPackage nav={nav} />}
          {screen === "afsvc-overview"    && <AFSVCOverview nav={nav} role={role} />}
          {screen === "base-home-pm"      && <AFSVCOverview nav={nav} role={role} />}
          {screen === "review-queue"      && <ReviewQueue nav={nav} role={role} />}
          {screen === "review-correction" && <Review nav={nav} role={role} returningForCorrection />}
          {screen === "installation"      && <InstallationWorkspace nav={nav} role={role} />}
          {screen === "calendar"          && <CalendarScreen nav={nav} role={role} />}
          {screen === "calendar-add-date" && <CalendarScreen nav={nav} role="pm" showAddDate />}
          {screen === "admin"             && <AdminHealth nav={nav} role={role} />}
          {screen === "access-mgmt"       && <AccessManagement nav={nav} role={role} />}
          {screen === "empty-state"       && <EmptyState nav={nav} />}
          {screen === "base-768"          && <BaseHome nav={nav} hasCorrection narrow />}
          {screen === "review-768"        && <Review nav={nav} role={role} returningForCorrection narrow />}
          {screen === "no-access"         && <NoAccess nav={nav} />}
          {screen === "scope-unresolved"  && <ScopeUnresolved nav={nav} />}
          {screen === "config-required"   && <ConfigRequired nav={nav} />}
          {screen === "request-access"    && <RequestAccess nav={nav} />}
          {screen === "admin-banner"      && <BaseHome nav={nav} />}
        </div>
      </div>

      {/* Frames panel + role switcher — fixed bottom-right, outside app chrome */}
      <Harness
        screen={screen}
        role={role}
        onRoleChange={handleRoleChange}
        nav={nav}
        dark={dark}
        setDark={setDark}
        banner={banner}
        setBanner={setBanner}
      />
    </div>
  )
}
