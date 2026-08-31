import { TopBar, TabStrip, Icons } from "../components/ui"
import type { Screen } from "../components/ui"

const TABS_AFSVC = [
  { id: "overview", label: "Overview" },
  { id: "review", label: "Review", badge: 0 },
  { id: "installations", label: "Installations" },
  { id: "exceptions", label: "Exceptions", badge: 0 },
  { id: "activity", label: "Activity" },
]

export default function EmptyState({ nav }: { nav: (s: Screen) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg)" }}>
      <TopBar period="August 2026" />
      <TabStrip tabs={TABS_AFSVC} active="review" onChange={id => {
        if (id === "overview") nav("afsvc-overview")
      }} />

      <div style={{ flex: 1, overflow: "auto", padding: "40px", display: "flex", flexDirection: "column", gap: "24px" }}>
        <div>
          <h1 style={{ fontSize: "32px", fontWeight: 300, color: "var(--text)", margin: "0 0 4px" }}>
            Review queue
          </h1>
          <div style={{ fontSize: "13px", color: "var(--secondary)" }}>
            August 2026 · 0 submissions awaiting review
          </div>
        </div>

        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "2px",
          padding: "60px 40px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "12px",
          textAlign: "center",
        }}>
          <div style={{ color: "var(--border)" }}>
            <Icons.Document size={32} />
          </div>
          <div style={{
            fontSize: "15px",
            fontWeight: 600,
            color: "var(--text)",
          }}>
            No documents awaiting your review.
          </div>
          <div style={{
            fontSize: "13px",
            color: "var(--secondary)",
            maxWidth: "380px",
            lineHeight: 1.6,
          }}>
            All submissions in this view have been processed. New submissions will appear here as installations complete their packages.
          </div>
        </div>
      </div>
    </div>
  )
}
