import { useEffect, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes, Navigate } from "react-router-dom";
import {
  MessageSquare, FileText, BarChart2, Settings, Network, LogOut,
} from "lucide-react";
import { getMe, logout, type Me } from "./lib/api";
import Chat from "./pages/Chat";
import Documents from "./pages/Documents";
import Analytics from "./pages/Analytics";
import Admin from "./pages/Admin";
import Login from "./pages/Login";

const NAV = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/analytics", label: "Analytics", icon: BarChart2 },
];

function Layout({ user, onLogout }: { user: Me; onLogout: () => void }) {
  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-100 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Network size={20} className="text-blue-600" />
            <span className="font-semibold text-gray-800">Company Brain</span>
          </div>
        </div>

        <nav className="flex-1 p-2 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-50"
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
          {user.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-50"
                }`
              }
            >
              <Settings size={16} />
              Admin
            </NavLink>
          )}
        </nav>

        <div className="p-3 border-t border-gray-100">
          <div className="px-2 py-1 mb-1">
            <p className="text-xs font-medium text-gray-700 truncate">{user.email}</p>
            <p className="text-xs text-gray-400">{user.role}</p>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <Routes>
          <Route path="/chat" element={<Chat />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = async () => {
    await logout().catch(() => {});
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Network size={32} className="text-blue-500 animate-pulse" />
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={() => getMe().then(setUser)} />;
  }

  return (
    <BrowserRouter>
      <Layout user={user} onLogout={handleLogout} />
    </BrowserRouter>
  );
}
