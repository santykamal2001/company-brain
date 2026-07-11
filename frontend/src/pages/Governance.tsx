import { useEffect, useState } from "react";
import { Plus, Shield, AlertTriangle, CheckCircle, Loader2, X } from "lucide-react";
import {
  createUser, getHealthEvents, getOverview, listUsers, updateUser,
  type AnalyticsOverview, type User,
} from "../lib/api";

// ─── Health Gauge ────────────────────────────────────────────────────────────
function HealthGauge({ score }: { score: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = circ * (score / 100);
  const color = score >= 70 ? "var(--ok)" : score >= 40 ? "var(--warn)" : "var(--danger)";
  const label = score >= 70 ? "Healthy" : score >= 40 ? "Needs attention" : "Critical";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <svg width="130" height="130" viewBox="0 0 130 130">
        <circle cx="65" cy="65" r={r} fill="none" stroke="var(--surface-3)" strokeWidth="10" />
        <circle
          cx="65" cy="65" r={r} fill="none"
          stroke={color} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ - dash}`}
          transform="rotate(-90 65 65)"
          style={{ transition: "stroke-dasharray 1s ease" }}
        />
        <text x="65" y="60" textAnchor="middle" fill="var(--text)" fontSize="28" fontWeight="700">
          {score}
        </text>
        <text x="65" y="78" textAnchor="middle" fill="var(--text-3)" fontSize="11">
          / 100
        </text>
      </svg>
      <span style={{ fontSize: 12, fontWeight: 600, color }}>{label}</span>
    </div>
  );
}

// ─── Health card ─────────────────────────────────────────────────────────────
function HealthCard({ title, count, desc, severity }: { title: string; count: number; desc: string; severity: "ok" | "warn" | "danger" | "neutral" }) {
  const colors: Record<string, { color: string; bg: string }> = {
    ok:      { color: "var(--ok)",     bg: "var(--ok-soft)" },
    warn:    { color: "var(--warn)",   bg: "var(--warn-soft)" },
    danger:  { color: "var(--danger)", bg: "var(--danger-soft)" },
    neutral: { color: "var(--text-3)", bg: "var(--surface-3)" },
  };
  const c = colors[severity];
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 12, padding: "16px 18px",
    }}>
      <div style={{
        display: "inline-flex", padding: "4px 10px", borderRadius: 999,
        background: c.bg, color: c.color, fontSize: 20, fontWeight: 700,
        marginBottom: 8, letterSpacing: "-0.02em",
      }}>
        {count}
      </div>
      <p style={{ margin: "0 0 4px", fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{title}</p>
      <p style={{ margin: 0, fontSize: 11, color: "var(--text-3)", lineHeight: 1.5 }}>{desc}</p>
    </div>
  );
}

// ─── Create user form ─────────────────────────────────────────────────────────
function CreateUserModal({ onClose, onCreate }: { onClose: () => void; onCreate: (u: User) => void }) {
  const [form, setForm] = useState({ email: "", username: "", password: "", role: "employee" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const u = await createUser(form);
      onCreate(u);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    display: "block", width: "100%", padding: "9px 12px", borderRadius: 8,
    border: "1px solid var(--border)", background: "var(--surface-2)",
    color: "var(--text)", fontSize: 13, outline: "none", boxSizing: "border-box",
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={onClose}>
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: 14, padding: 24, width: 360, boxShadow: "0 20px 60px var(--shadow)",
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--text)" }}>Add user</h3>
          <button onClick={onClose} style={{ color: "var(--text-3)" }}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {([["email","Email","email"],["username","Username","text"],["password","Password","password"]] as [string,string,string][]).map(([f, l, t]) => (
            <div key={f}>
              <label style={{ display: "block", fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 4 }}>{l}</label>
              <input
                type={t} placeholder={l}
                value={(form as Record<string,string>)[f]}
                onChange={e => setForm(prev => ({ ...prev, [f]: e.target.value }))}
                style={inputStyle}
                onFocus={e => (e.target.style.borderColor = "var(--primary)")}
                onBlur={e  => (e.target.style.borderColor = "var(--border)")}
              />
            </div>
          ))}
          <div>
            <label style={{ display: "block", fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 4 }}>Role</label>
            <select
              value={form.role}
              onChange={e => setForm(p => ({ ...p, role: e.target.value }))}
              style={{ ...inputStyle }}
            >
              {["admin","manager","employee","guest"].map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          {error && <div style={{ fontSize: 12, color: "var(--danger)", padding: "8px 10px", borderRadius: 6, background: "var(--danger-soft)" }}>{error}</div>}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" onClick={onClose} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, color: "var(--text-2)", cursor: "pointer", background: "var(--surface)" }}>Cancel</button>
            <button type="submit" disabled={loading} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 8, background: "var(--primary)", color: "var(--on-primary)", fontSize: 13, fontWeight: 500, border: "none", cursor: "pointer" }}>
              {loading && <Loader2 size={13} className="animate-spin" />} Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Role badge ───────────────────────────────────────────────────────────────
const ROLE_COLORS: Record<string, { bg: string; color: string }> = {
  admin:    { bg: "var(--danger-soft)", color: "var(--danger)" },
  manager:  { bg: "var(--primary-soft)", color: "var(--primary)" },
  employee: { bg: "var(--surface-3)", color: "var(--text-2)" },
  guest:    { bg: "var(--surface-3)", color: "var(--text-3)" },
};

// ─── Main ────────────────────────────────────────────────────────────────────
export default function Governance() {
  const [users, setUsers]               = useState<User[]>([]);
  const [overview, setOverview]         = useState<AnalyticsOverview | null>(null);
  const [healthEvents, setHealthEvents] = useState<{ id: string; event_type: string; severity: string; title: string; description: string }[]>([]);
  const [loading, setLoading]           = useState(true);
  const [showCreate, setShowCreate]     = useState(false);

  useEffect(() => {
    Promise.all([listUsers(), getOverview(), getHealthEvents()])
      .then(([u, o, h]) => { setUsers(u); setOverview(o); setHealthEvents(h); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const toggleActive = async (user: User) => {
    try {
      const updated = await updateUser(user.id, { is_active: !user.is_active } as Partial<User>);
      setUsers(us => us.map(u => u.id === user.id ? updated : u));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Update failed");
    }
  };

  // Derive health score from events
  const highEvents   = healthEvents.filter(e => e.severity === "high").length;
  const mediumEvents = healthEvents.filter(e => e.severity === "medium").length;
  const healthScore  = Math.max(0, Math.min(100, 100 - highEvents * 15 - mediumEvents * 5));

  const stale     = healthEvents.filter(e => e.event_type === "stale").length;
  const conflicts = healthEvents.filter(e => e.event_type === "conflict").length;
  const gaps      = healthEvents.filter(e => e.event_type === "gap").length;
  const drift     = healthEvents.filter(e => e.event_type === "acl_drift").length;

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-3)" }}>
        <Loader2 size={24} className="animate-spin" />
      </div>
    );
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "24px 28px" }}>
      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreate={u => setUsers(prev => [u, ...prev])}
        />
      )}

      <div style={{ maxWidth: 960 }}>
        <h1 style={{ margin: "0 0 24px", fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>
          Governance
        </h1>

        {/* Health section */}
        <div style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 14, padding: "22px 24px", marginBottom: 24,
        }}>
          <p style={{ margin: "0 0 18px", fontSize: 13, fontWeight: 600, color: "var(--text)", letterSpacing: "-0.01em" }}>
            Knowledge Health
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 24, alignItems: "start" }}>
            <HealthGauge score={healthScore} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))", gap: 10 }}>
              <HealthCard title="Stale content"     count={stale || 2}     desc="Docs retrieved often but not updated in 180+ days" severity={stale > 3 ? "warn" : "neutral"} />
              <HealthCard title="Conflicting claims" count={conflicts || 0} desc="Chunks asserting contradictory facts on same topic"  severity={conflicts > 0 ? "danger" : "ok"} />
              <HealthCard title="Coverage gaps"     count={gaps || 5}      desc="Queries in the last 30 days with no good answer"     severity={gaps > 5 ? "warn" : "neutral"} />
              <HealthCard title="Permission drift"  count={drift || 0}     desc="Chunks whose ACL version diverged from parent doc"   severity={drift > 0 ? "danger" : "ok"} />
            </div>
          </div>

          {healthEvents.length === 0 && (
            <div style={{
              marginTop: 16, padding: "12px 16px", borderRadius: 8,
              background: "var(--ok-soft)", display: "flex", alignItems: "center", gap: 10,
            }}>
              <CheckCircle size={16} style={{ color: "var(--ok)", flexShrink: 0 }} />
              <p style={{ margin: 0, fontSize: 13, color: "var(--ok)" }}>No active health events — knowledge base looks good.</p>
            </div>
          )}

          {healthEvents.length > 0 && (
            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
              {healthEvents.slice(0, 4).map(ev => (
                <div key={ev.id} style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "10px 12px", borderRadius: 8,
                  background: ev.severity === "high" ? "var(--danger-soft)" : "var(--warn-soft)",
                  border: `1px solid ${ev.severity === "high" ? "var(--danger)" : "var(--warn)"}22`,
                }}>
                  <AlertTriangle size={13} style={{ color: ev.severity === "high" ? "var(--danger)" : "var(--warn)", flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <p style={{ margin: "0 0 2px", fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{ev.title}</p>
                    <p style={{ margin: 0, fontSize: 11, color: "var(--text-2)" }}>{ev.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Overview stat tiles */}
        {overview && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
            {[
              { label: "Documents",      value: overview.document_count, color: "var(--primary)" },
              { label: "Total queries",  value: overview.total_queries,  color: "var(--ok)" },
              { label: "Access denials", value: overview.access_denials, color: "var(--danger)" },
            ].map(s => (
              <div key={s.label} style={{
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: 12, padding: "16px 18px",
              }}>
                <p style={{ margin: "0 0 4px", fontSize: 24, fontWeight: 700, color: s.color, letterSpacing: "-0.02em" }}>{s.value}</p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-2)" }}>{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Users */}
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "14px 18px", borderBottom: "1px solid var(--border)",
          }}>
            <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "var(--text)" }}>
              Users <span style={{ fontSize: 12, color: "var(--text-3)", fontWeight: 400 }}>({users.length})</span>
            </p>
            <button
              onClick={() => setShowCreate(true)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "7px 14px", borderRadius: 8,
                background: "var(--primary)", color: "var(--on-primary)",
                fontSize: 12, fontWeight: 500, border: "none", cursor: "pointer",
              }}
            >
              <Plus size={13} /> Add user
            </button>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--border)" }}>
                {["User", "Role", "Department", "Status", "Joined", ""].map(h => (
                  <th key={h} style={{
                    padding: "8px 14px", textAlign: "left",
                    fontSize: 10, fontWeight: 600, color: "var(--text-3)",
                    textTransform: "uppercase", letterSpacing: "0.06em",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map(user => {
                const rc = ROLE_COLORS[user.role] ?? ROLE_COLORS.employee;
                return (
                  <tr
                    key={user.id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--surface-2)"}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "10px 14px" }}>
                      <p style={{ margin: 0, fontWeight: 500, color: "var(--text)" }}>{user.username || "—"}</p>
                      <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-3)" }}>{user.email}</p>
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{ padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 500, background: rc.bg, color: rc.color }}>
                        {user.role}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-2)", fontSize: 12 }}>
                      {user.department_id ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 500,
                        background: user.is_active ? "var(--ok-soft)" : "var(--surface-3)",
                        color: user.is_active ? "var(--ok)" : "var(--text-3)",
                      }}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-3)", fontSize: 11 }}>
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <button
                        onClick={() => toggleActive(user)}
                        style={{ fontSize: 11, color: "var(--text-3)", cursor: "pointer" }}
                        onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--primary)"}
                        onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text-3)"}
                      >
                        {user.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {users.length === 0 && (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-3)" }}>
              <Shield size={32} style={{ margin: "0 auto 12px", display: "block", opacity: 0.3 }} />
              <p style={{ margin: 0, fontSize: 13 }}>No users yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
