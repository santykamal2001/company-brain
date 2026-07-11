import { useEffect, useState } from "react";
import { getAuditLog, getOverview, type AuditEntry, type AnalyticsOverview } from "../lib/api";
import { ClipboardList, Loader2, ShieldCheck, Search } from "lucide-react";

const MODE_COLORS: Record<string, { color: string; bg: string }> = {
  vector:   { color: "var(--ok)",       bg: "var(--ok-soft)" },
  graph:    { color: "var(--primary)",  bg: "var(--primary-soft)" },
  hybrid:   { color: "var(--warn)",     bg: "var(--warn-soft)" },
  decision: { color: "var(--decision)", bg: "var(--decision-soft)" },
};

function StatCard({ value, label, color }: { value: number | string; label: string; color: string }) {
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 12, padding: "16px 18px",
    }}>
      <p style={{ margin: "0 0 4px", fontSize: 24, fontWeight: 700, color, letterSpacing: "-0.02em" }}>{value}</p>
      <p style={{ margin: 0, fontSize: 12, color: "var(--text-2)" }}>{label}</p>
    </div>
  );
}

export default function AuditLog() {
  const [entries, setEntries]   = useState<AuditEntry[]>([]);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState("");

  useEffect(() => {
    Promise.all([getAuditLog(), getOverview()])
      .then(([e, o]) => { setEntries(e); setOverview(o); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const avgLatency = entries.length
    ? Math.round(entries.reduce((s, e) => s + (e.latency_ms ?? 0), 0) / entries.length)
    : 0;

  const totalDenied = entries.reduce((s, e) => s + (e.chunks_denied ?? 0), 0);

  const filtered = entries.filter(e =>
    !search ||
    e.retrieval_mode?.toLowerCase().includes(search.toLowerCase()) ||
    e.event_type?.toLowerCase().includes(search.toLowerCase()) ||
    e.caller_type?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-3)" }}>
        <Loader2 size={24} className="animate-spin" />
      </div>
    );
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "24px 28px" }}>
      <div style={{ maxWidth: 1000 }}>
        <h1 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>
          Audit Log
        </h1>
        <p style={{ margin: "0 0 24px", fontSize: 13, color: "var(--text-2)" }}>
          Immutable record of every retrieval event — chunk-level evidence for RBAC enforcement.
        </p>

        {/* EU AI Act banner */}
        <div style={{
          display: "flex", alignItems: "flex-start", gap: 12,
          padding: "14px 16px", borderRadius: 10,
          background: "var(--primary-soft)",
          border: "1px solid var(--primary)22",
          marginBottom: 24,
        }}>
          <ShieldCheck size={16} style={{ color: "var(--primary)", flexShrink: 0, marginTop: 1 }} />
          <div>
            <p style={{ margin: "0 0 2px", fontSize: 12, fontWeight: 600, color: "var(--primary)" }}>
              EU AI Act — Article 13 Compliance
            </p>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-2)", lineHeight: 1.5 }}>
              Every retrieval event is logged with returned and denied chunk counts, latency, access control version, and caller identity.
              This log satisfies Article 13 technical documentation and traceability obligations for high-risk AI systems (Annex III).
            </p>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
          <StatCard value={entries.length}                  label="Total events"    color="var(--text)" />
          <StatCard value={overview?.total_queries ?? 0}    label="Queries"         color="var(--primary)" />
          <StatCard value={totalDenied}                     label="Chunks denied"   color="var(--danger)" />
          <StatCard value={`${avgLatency}ms`}               label="Avg latency"     color="var(--ok)" />
        </div>

        {/* Search */}
        <div style={{ position: "relative", marginBottom: 16 }}>
          <Search size={14} style={{
            position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)",
            color: "var(--text-3)", pointerEvents: "none",
          }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Filter by mode, event type, caller…"
            style={{
              width: "100%", padding: "9px 12px 9px 34px", borderRadius: 8,
              border: "1px solid var(--border)", background: "var(--surface)",
              color: "var(--text)", fontSize: 13, outline: "none", boxSizing: "border-box",
            }}
            onFocus={e => (e.target.style.borderColor = "var(--primary)")}
            onBlur={e  => (e.target.style.borderColor = "var(--border)")}
          />
        </div>

        {/* Table */}
        {filtered.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-3)" }}>
            <ClipboardList size={40} style={{ margin: "0 auto 12px", display: "block", opacity: 0.3 }} />
            <p style={{ margin: 0, fontSize: 14 }}>
              {entries.length === 0 ? "No audit events yet — events appear after queries are made." : "No results match your filter."}
            </p>
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--border)" }}>
                    {["Timestamp", "Event", "Mode", "Caller", "Returned", "Denied", "Latency"].map(h => (
                      <th key={h} style={{
                        padding: "9px 14px", textAlign: "left",
                        fontSize: 10, fontWeight: 600, color: "var(--text-3)",
                        textTransform: "uppercase", letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((entry, i) => {
                    const mc = MODE_COLORS[entry.retrieval_mode] ?? { color: "var(--text-2)", bg: "var(--surface-3)" };
                    const ts = entry.timestamp ? new Date(entry.timestamp) : null;
                    return (
                      <tr
                        key={i}
                        style={{ borderBottom: "1px solid var(--border)" }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--surface-2)"}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
                      >
                        <td style={{ padding: "10px 14px", color: "var(--text-3)", whiteSpace: "nowrap" }} className="mono">
                          {ts ? ts.toLocaleString() : "—"}
                        </td>
                        <td style={{ padding: "10px 14px", color: "var(--text-2)" }}>{entry.event_type || "query"}</td>
                        <td style={{ padding: "10px 14px" }}>
                          <span style={{
                            padding: "2px 8px", borderRadius: 999, fontSize: 10, fontWeight: 500,
                            background: mc.bg, color: mc.color,
                          }}>
                            {entry.retrieval_mode || "—"}
                          </span>
                        </td>
                        <td style={{ padding: "10px 14px", color: "var(--text-2)" }}>{entry.caller_type || "user"}</td>
                        <td style={{ padding: "10px 14px" }}>
                          <span style={{ color: "var(--ok)", fontWeight: 600 }}>{entry.chunks_returned ?? 0}</span>
                        </td>
                        <td style={{ padding: "10px 14px" }}>
                          <span style={{ color: entry.chunks_denied > 0 ? "var(--danger)" : "var(--text-3)", fontWeight: entry.chunks_denied > 0 ? 600 : 400 }}>
                            {entry.chunks_denied ?? 0}
                          </span>
                        </td>
                        <td style={{ padding: "10px 14px", color: "var(--text-2)" }} className="mono">
                          {entry.latency_ms != null ? `${entry.latency_ms}ms` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div style={{
              padding: "10px 14px",
              borderTop: "1px solid var(--border)",
              fontSize: 11, color: "var(--text-3)",
              display: "flex", justifyContent: "space-between",
            }}>
              <span>Showing {filtered.length} of {entries.length} events</span>
              <span>Retained per your data retention policy</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
