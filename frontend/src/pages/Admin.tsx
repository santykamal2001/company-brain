import { useEffect, useState } from "react";
import { Plus, Shield, RefreshCw, AlertTriangle } from "lucide-react";
import {
  createUser,
  getHealthEvents,
  getOverview,
  listUsers,
  updateUser,
  type AnalyticsOverview,
  type User,
} from "../lib/api";

export default function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [healthEvents, setHealthEvents] = useState<{ id: string; event_type: string; severity: string; title: string; description: string }[]>([]);
  const [tab, setTab] = useState<"users" | "health">("users");
  const [loading, setLoading] = useState(true);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUser, setNewUser] = useState({ email: "", username: "", password: "", role: "employee" });

  useEffect(() => {
    Promise.all([listUsers(), getOverview(), getHealthEvents()])
      .then(([u, o, h]) => { setUsers(u); setOverview(o); setHealthEvents(h); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    try {
      const user = await createUser(newUser);
      setUsers((u) => [user, ...u]);
      setShowCreateUser(false);
      setNewUser({ email: "", username: "", password: "", role: "employee" });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create user");
    }
  };

  const toggleActive = async (user: User) => {
    try {
      const updated = await updateUser(user.id, { is_active: !user.is_active } as any);
      setUsers((us) => us.map((u) => (u.id === user.id ? updated : u)));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update user");
    }
  };

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-800 mb-6">Admin</h1>

      {/* Stats */}
      {overview && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: "Documents", value: overview.document_count },
            { label: "Total Queries", value: overview.total_queries },
            { label: "Access Denials", value: overview.access_denials },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-2xl font-bold text-gray-800">{s.value}</p>
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {(["users", "health"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {t === "users" ? "User Management" : "Knowledge Health"}
          </button>
        ))}
      </div>

      {/* Users tab */}
      {tab === "users" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">{users.length} users</p>
            <button
              onClick={() => setShowCreateUser(true)}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
            >
              <Plus size={14} /> Add User
            </button>
          </div>

          {showCreateUser && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 space-y-3">
              <p className="font-medium text-sm text-blue-800">New User</p>
              {(["email", "username", "password"] as const).map((field) => (
                <input
                  key={field}
                  type={field === "password" ? "password" : "text"}
                  placeholder={field}
                  value={newUser[field]}
                  onChange={(e) => setNewUser((n) => ({ ...n, [field]: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"
                />
              ))}
              <select
                value={newUser.role}
                onChange={(e) => setNewUser((n) => ({ ...n, role: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm"
              >
                {["admin", "manager", "employee", "guest"].map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
              <div className="flex gap-2">
                <button onClick={handleCreate} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Create</button>
                <button onClick={() => setShowCreateUser(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">Cancel</button>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  {["Email", "Username", "Role", "Department", "Status", ""].map((h) => (
                    <th key={h} className="px-4 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-800">{user.email}</td>
                    <td className="px-4 py-3 text-gray-600">{user.username}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        user.role === "admin" ? "bg-red-100 text-red-700" :
                        user.role === "manager" ? "bg-purple-100 text-purple-700" :
                        "bg-gray-100 text-gray-600"
                      }`}>{user.role}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{user.department_id ? "—" : "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${user.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-400"}`}>
                        {user.is_active ? "active" : "inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleActive(user)}
                        className="text-xs text-gray-400 hover:text-gray-700"
                      >
                        {user.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Health tab */}
      {tab === "health" && (
        <div className="space-y-3">
          {healthEvents.length === 0 && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
              <Shield size={32} className="mx-auto text-green-500 mb-2" />
              <p className="text-green-700 font-medium">No active health issues</p>
              <p className="text-green-600 text-sm mt-1">Knowledge base looks healthy</p>
            </div>
          )}
          {healthEvents.map((event) => (
            <div
              key={event.id}
              className={`border rounded-xl p-4 ${
                event.severity === "high" ? "border-red-200 bg-red-50" :
                event.severity === "medium" ? "border-amber-200 bg-amber-50" :
                "border-gray-200 bg-gray-50"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle size={14} className={
                  event.severity === "high" ? "text-red-500" :
                  event.severity === "medium" ? "text-amber-500" : "text-gray-400"
                } />
                <span className="font-medium text-sm text-gray-800">{event.title}</span>
                <span className="text-xs text-gray-400 ml-auto">{event.event_type}</span>
              </div>
              <p className="text-sm text-gray-600">{event.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
