import { createContext, useContext, useEffect, useState } from "react";
import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  MessageSquare, Network, FileText, Shield, ClipboardList,
  LogOut, Sun, Moon,
} from "lucide-react";
import { getMe, logout, type Me } from "./lib/api";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Welcome from "./pages/Welcome";
import Chat from "./pages/Chat";
import Graph from "./pages/Graph";
import Documents from "./pages/Documents";
import Governance from "./pages/Governance";
import AuditLog from "./pages/AuditLog";

// ─── Contexts ──────────────────────────────────────────────────────────────
export const ThemeCtx = createContext<{ theme: string; toggle: () => void }>({
  theme: "light",
  toggle: () => {},
});
export const UserCtx = createContext<{
  user: Me | null;
  setUser: (u: Me | null) => void;
}>({ user: null, setUser: () => {} });

export function useTheme() { return useContext(ThemeCtx); }
export function useUser()  { return useContext(UserCtx); }

// ─── Protected route ────────────────────────────────────────────────────────
function Protected({ children }: { children: React.ReactNode }) {
  const { user } = useUser();
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

// ─── Sidebar logo ───────────────────────────────────────────────────────────
function MnemoLogo() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <polygon
          points="14,2 25,8 25,20 14,26 3,20 3,8"
          fill="var(--primary)"
          opacity="0.15"
        />
        <polygon
          points="14,2 25,8 25,20 14,26 3,20 3,8"
          stroke="var(--primary)"
          strokeWidth="1.5"
          fill="none"
        />
        <circle cx="14" cy="14" r="3.5" fill="var(--primary)" />
        <line x1="14" y1="10.5" x2="14" y2="5"   stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
        <line x1="14" y1="17.5" x2="14" y2="23"  stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
        <line x1="10.5" y1="12" x2="5.5" y2="9"  stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
        <line x1="17.5" y1="16" x2="22.5" y2="19" stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
      </svg>
      <span style={{ fontWeight: 600, fontSize: 15, letterSpacing: "-0.01em", color: "var(--text)" }}>
        Mnemo
      </span>
    </div>
  );
}

// ─── Sidebar ────────────────────────────────────────────────────────────────
const NAV = [
  { to: "/app/ask",        label: "Ask",             icon: MessageSquare },
  { to: "/app/graph",      label: "Knowledge Graph", icon: Network },
  { to: "/app/documents",  label: "Documents",       icon: FileText },
  { to: "/app/audit",      label: "Audit Log",       icon: ClipboardList },
];

const navLinkStyle = (isActive: boolean): React.CSSProperties => ({
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: "7px 10px",
  borderRadius: 8,
  fontSize: 13,
  fontWeight: isActive ? 500 : 400,
  color: isActive ? "var(--primary)" : "var(--text-2)",
  background: isActive ? "var(--primary-soft)" : "transparent",
  transition: "background 0.15s, color 0.15s",
  textDecoration: "none",
  cursor: "pointer",
});

function Sidebar({ user, onLogout }: { user: Me; onLogout: () => void }) {
  const { theme, toggle } = useTheme();

  const nav = user.role === "admin"
    ? [...NAV, { to: "/app/governance", label: "Governance", icon: Shield }]
    : NAV;

  return (
    <aside style={{
      width: 212,
      background: "var(--surface)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ padding: "16px 14px 14px", borderBottom: "1px solid var(--border)" }}>
        <MnemoLogo />
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "8px 6px", display: "flex", flexDirection: "column", gap: 2 }}>
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => navLinkStyle(isActive)}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: "10px 10px 14px", borderTop: "1px solid var(--border)" }}>
        {/* Theme toggle */}
        <button
          onClick={toggle}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: "6px 10px",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--text-3)",
            marginBottom: 6,
          }}
        >
          {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>

        {/* User info */}
        <div style={{ padding: "6px 10px", marginBottom: 4 }}>
          <p style={{ margin: 0, fontSize: 12, fontWeight: 500, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {user.username || user.email}
          </p>
          <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--text-3)" }}>
            {user.role}{user.department ? ` · ${user.department}` : ""}
          </p>
        </div>

        {/* Sign out */}
        <button
          onClick={onLogout}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: "6px 10px",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--text-3)",
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.color = "var(--danger)";
            (e.currentTarget as HTMLElement).style.background = "var(--danger-soft)";
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.color = "var(--text-3)";
            (e.currentTarget as HTMLElement).style.background = "transparent";
          }}
        >
          <LogOut size={13} /> Sign out
        </button>
      </div>
    </aside>
  );
}

// ─── App layout (sidebar + content) ─────────────────────────────────────────
function AppLayout() {
  const { user, setUser } = useUser();
  if (!user) return <Navigate to="/login" replace />;

  const handleLogout = async () => {
    await logout().catch(() => {});
    setUser(null);
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar user={user} onLogout={handleLogout} />
      <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", background: "var(--bg)" }}>
        <Routes>
          <Route path="ask"        element={<Chat />} />
          <Route path="graph"      element={<Graph />} />
          <Route path="documents"  element={<Documents />} />
          <Route path="governance" element={<Governance />} />
          <Route path="audit"      element={<AuditLog />} />
          <Route path="*"          element={<Navigate to="ask" replace />} />
        </Routes>
      </main>
    </div>
  );
}

// ─── Loading screen ──────────────────────────────────────────────────────────
function LoadingScreen() {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      height: "100vh", background: "var(--bg)",
    }}>
      <svg width="32" height="32" viewBox="0 0 28 28" className="animate-spin" fill="none">
        <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" stroke="var(--primary)" strokeWidth="1.5" />
        <circle cx="14" cy="14" r="3" fill="var(--primary)" />
      </svg>
    </div>
  );
}

// ─── Root ────────────────────────────────────────────────────────────────────
export default function App() {
  const [theme, setTheme] = useState<string>(() => {
    return localStorage.getItem("mnemo-theme") || "light";
  });
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const toggle = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("mnemo-theme", next);
  };

  if (loading) return (
    <ThemeCtx.Provider value={{ theme, toggle }}>
      <LoadingScreen />
    </ThemeCtx.Provider>
  );

  return (
    <ThemeCtx.Provider value={{ theme, toggle }}>
      <UserCtx.Provider value={{ user, setUser }}>
        <BrowserRouter>
          <Routes>
            <Route path="/"       element={<Landing />} />
            <Route path="/login"  element={<Login />} />
            <Route path="/welcome" element={<Protected><Welcome /></Protected>} />
            <Route path="/app/*"  element={<Protected><AppLayout /></Protected>} />
            <Route path="*"       element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </UserCtx.Provider>
    </ThemeCtx.Provider>
  );
}
