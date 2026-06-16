import { useEffect, useRef, useState } from "react";
import { Upload, RefreshCw, Trash2, AlertCircle, CheckCircle, Clock } from "lucide-react";
import {
  deleteDocument,
  listDocuments,
  reindexDocument,
  uploadDocument,
  type Document,
} from "../lib/api";

const STATUS_ICON: Record<string, React.ReactNode> = {
  done: <CheckCircle size={14} className="text-green-500" />,
  indexing: <Clock size={14} className="text-blue-400 animate-pulse" />,
  pending: <Clock size={14} className="text-gray-400" />,
  error: <AlertCircle size={14} className="text-red-400" />,
};

export default function Documents() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reload = () =>
    listDocuments()
      .then(setDocs)
      .catch(console.error)
      .finally(() => setLoading(false));

  useEffect(() => { reload(); }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setUploading(true);
    try {
      await Promise.all(Array.from(files).map((f) => uploadDocument(f)));
      await reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleReindex = async (id: string) => {
    await reindexDocument(id).catch(console.error);
    await reload();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    await deleteDocument(id).catch(console.error);
    setDocs((d) => d.filter((doc) => doc.id !== id));
  };

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-xl font-semibold text-gray-800">Documents</h1>
        <div className="flex gap-2">
          <button
            onClick={reload}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            <Upload size={14} /> {uploading ? "Uploading…" : "Upload"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      </div>

      {docs.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Upload size={40} className="mx-auto mb-4 opacity-40" />
          <p>No documents yet. Upload your first document to get started.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                {["Title", "Status", "Chunks", "Classification", "Size", "Created", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {docs.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-800 truncate max-w-xs">{doc.title}</div>
                    {doc.error_message && (
                      <div className="text-xs text-red-500 truncate">{doc.error_message}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {STATUS_ICON[doc.status] ?? null}
                      <span className="text-gray-600">{doc.status}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{doc.chunk_count}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      doc.classification === "confidential" || doc.classification === "restricted"
                        ? "bg-red-100 text-red-700"
                        : doc.classification === "internal"
                        ? "bg-gray-100 text-gray-600"
                        : "bg-green-100 text-green-700"
                    }`}>{doc.classification}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(0)} KB` : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleReindex(doc.id)}
                        className="text-gray-400 hover:text-blue-500 transition-colors"
                        title="Reindex"
                      >
                        <RefreshCw size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
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
