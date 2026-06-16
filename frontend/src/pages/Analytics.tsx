import { useEffect, useState } from "react";
import { getOverview, getQueryHistory } from "../lib/api";

interface QueryHistoryItem {
  question: string;
  retrieval_mode: string;
  latency_ms: number;
  timestamp: string;
}

const MODE_COLORS: Record<string, string> = {
  vector: "bg-blue-100 text-blue-700",
  graph: "bg-purple-100 text-purple-700",
  hybrid: "bg-green-100 text-green-700",
  decision: "bg-amber-100 text-amber-700",
};

export default function Analytics() {
  const [overview, setOverview] = useState<{ document_count: number; total_queries: number; access_denials: number } | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getOverview(), getQueryHistory()])
      .then(([o, h]) => { setOverview(o); setHistory(h as QueryHistoryItem[]); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold text-gray-800 mb-6">Analytics</h1>

      {overview && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: "Indexed Documents", value: overview.document_count, color: "text-blue-600" },
            { label: "Total Queries", value: overview.total_queries, color: "text-green-600" },
            { label: "Access Denials", value: overview.access_denials, color: "text-red-500" },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-sm text-gray-500 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <h2 className="text-sm font-medium text-gray-600 mb-3">Recent Queries</h2>
      {history.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No queries yet</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                {["Question", "Mode", "Latency", "Time"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {history.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-800 max-w-sm truncate">{item.question}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${MODE_COLORS[item.retrieval_mode] || "bg-gray-100 text-gray-600"}`}>
                      {item.retrieval_mode}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{item.latency_ms}ms</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
