import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { login, getMe } from "../lib/api";
import { useUser, useTheme } from "../App";
import NeuralCanvas from "../components/NeuralCanvas";

export default function Login() {
  const navigate = useNavigate();
  const { setUser } = useUser();
  const { theme } = useTheme();

  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [remember, setRemember] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError("Email and password required."); return; }
    setError(""); setLoading(true);
    try {
      await login(email, password);
      const me = await getMe();
      setUser(me);
      navigate("/welcome", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      {/* Left panel — branding */}
      <div style={{
        flex: "0 0 400px",
        position: "relative",
        background: theme === "dark" ? "#0A0C12" : "#0B6F61",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        padding: "40px 36px",
      }}>
        <div style={{ position: "absolute", inset: 0, opacity: 0.28 }}>
          <NeuralCanvas primaryRgb="255,255,255" />
        </div>

        {/* Brand mark */}
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10, marginBottom: "auto" }}>
          <svg width="32" height="32" viewBox="0 0 28 28" fill="none">
            <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" fill="rgba(255,255,255,0.2)" />
            <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" stroke="rgba(255,255,255,0.8)" strokeWidth="1.5" fill="none" />
            <circle cx="14" cy="14" r="3.5" fill="white" />
          </svg>
          <span style={{ fontWeight: 600, fontSize: 16, color: "white", letterSpacing: "-0.01em" }}>Mnemo</span>
        </div>

        {/* Bottom copy */}
        <div style={{ position: "relative" }}>
          <h2 style={{ margin: "0 0 12px", fontSize: 26, fontWeight: 700, color: "white", letterSpacing: "-0.02em", lineHeight: 1.2 }}>
            Institutional memory,<br />governed.
          </h2>
          <p style={{ margin: 0, fontSize: 13, color: "rgba(255,255,255,0.65)", lineHeight: 1.6 }}>
            Hybrid Graph RAG · Chunk-level RBAC · Decision Trail · EU AI Act compliant.
          </p>
          <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 10 }}>
            {["Hybrid Graph + Vector retrieval","Chunk-level RBAC enforcement","EU AI Act Article 13 audit trail"].map(t => (
              <div key={t} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 4, height: 4, borderRadius: "50%", background: "rgba(255,255,255,0.75)", flexShrink: 0 }} />
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)" }}>{t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 40 }}>
        <div style={{ width: "100%", maxWidth: 380 }}>
          <h1 style={{ margin: "0 0 6px", fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>
            Welcome back
          </h1>
          <p style={{ margin: "0 0 28px", fontSize: 13, color: "var(--text-2)" }}>
            Sign in to your Mnemo workspace
          </p>

          {/* SSO buttons */}
          {[
            { label: "Continue with SAML SSO", icon: "⊞" },
            { label: "Continue with OIDC", icon: "◯" },
          ].map(({ label, icon }) => (
            <button
              key={label}
              onClick={() => setError("SSO configuration required — contact your admin.")}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                width: "100%", padding: "10px 0", borderRadius: 8,
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--text)", fontSize: 13, fontWeight: 500,
                cursor: "pointer", marginBottom: 10,
              }}
            >
              <span style={{ fontSize: 16 }}>{icon}</span> {label}
            </button>
          ))}

          {/* Divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "20px 0" }}>
            <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>or sign in with email</span>
            <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 5 }}>
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
                style={{
                  display: "block", width: "100%", padding: "9px 12px",
                  borderRadius: 8, border: "1px solid var(--border)",
                  background: "var(--surface)", color: "var(--text)", fontSize: 13,
                  outline: "none", boxSizing: "border-box",
                }}
                onFocus={e => (e.target.style.borderColor = "var(--primary)")}
                onBlur={e  => (e.target.style.borderColor = "var(--border)")}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 5 }}>
                Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  style={{
                    display: "block", width: "100%", padding: "9px 38px 9px 12px",
                    borderRadius: 8, border: "1px solid var(--border)",
                    background: "var(--surface)", color: "var(--text)", fontSize: 13,
                    outline: "none", boxSizing: "border-box",
                  }}
                  onFocus={e => (e.target.style.borderColor = "var(--primary)")}
                  onBlur={e  => (e.target.style.borderColor = "var(--border)")}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  style={{ position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-3)" }}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-2)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={remember}
                onChange={e => setRemember(e.target.checked)}
                style={{ accentColor: "var(--primary)" }}
              />
              Trust this device for 30 days
            </label>

            {error && (
              <div style={{ padding: "9px 12px", borderRadius: 8, background: "var(--danger-soft)", color: "var(--danger)", fontSize: 12 }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                padding: "11px", borderRadius: 8,
                background: "var(--primary)", color: "var(--on-primary)",
                fontSize: 14, fontWeight: 600, border: "none",
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading
                ? <><Loader2 size={15} className="animate-spin" /> Signing in…</>
                : "Sign in"}
            </button>
          </form>

          <p style={{ marginTop: 24, fontSize: 11, color: "var(--text-3)", textAlign: "center", lineHeight: 1.5 }}>
            Contact your admin if you don't have access.
          </p>
        </div>
      </div>
    </div>
  );
}
