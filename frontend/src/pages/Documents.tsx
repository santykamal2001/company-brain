import { useEffect, useRef, useState } from "react";
import { Upload, RefreshCw, Trash2, AlertCircle, CheckCircle, Clock, FileText, Layers, Loader2 } from "lucide-react";
import { deleteDocument, listDocuments, reindexDocument, uploadDocument, type Document } from "../lib/api";

const CLASS_STYLE: Record<string, { bg: string; color: string }> = {
  public:       { bg: "var(--ok-soft)",       color: "var(--ok)" },
  internal:     { bg: "var(--surface-3)",     color: "var(--text-2)" },
  confidential: { bg: "var(--warn-soft)",     color: "var(--warn)" },
  restricted:   { bg: "var(--danger-soft)",   color: "var(--danger)" },
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  done:     <CheckCircle size={12} style={{ color: "var(--ok)" }} />,
  indexing: <Loader2 size={12} className="animate-spin" style={{ color: "var(--primary)" }} />,
  pending:  <Clock size={12} style={{ color: "var(--text-3)" }} />,
  error:    <AlertCircle size={12} style={{ color: "var(--danger)" }} />,
};

function StatTile({ value, label, icon: Icon, color }: { value: number | string; label: string; icon: React.ElementType; color: string }) {
  return (
    <div style={{
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 12, padding: "16px 18px",
      display: "flex", alignItems: "center", gap: 14,
    }}>
      <div style={{ padding: 10, borderRadius: 10, background: `${color}18`, color }}>
        <Icon size={18} />
      </div>
      <div>
        <p style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text)", letterSpacing: "-0.02em" }}>{value}</p>
        <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-2)" }}>{label}</p>
      </div>
    </div>
  );
}

export default function Documents() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reload = () =>
    listDocuments()
      .then(setDocs)
      .catch(console.error)
      .finally(() => setLoading(false));

  useEffect(() => { reload(); }, []);

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      await Promise.all(Array.from(files).map(f => uploadDocument(f)));
      await reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleReindex = async (id: string) => {
    await reindexDocument(id).catch(console.error);
    await reload();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    await deleteDocument(id).catch(console.error);
    setDocs(d => d.filter(doc => doc.id !== id));
  };

  const stats = {
    indexed:    docs.filter(d => d.status === "done").length,
    chunks:     docs.reduce((s, d) => s + (d.chunk_count || 0), 0),
    processing: docs.filter(d => d.status === "indexing" || d.status === "pending").length,
    restricted: docs.filter(d => d.classification === "restricted" || d.classification === "confidential").length,
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-3)" }}>
        <Loader2 size={24} className="animate-spin" />
      </div>
    );
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "24px 28px" }}>
      <div style={{ maxWidth: 900 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>Documents</h1>
          <button
            onClick={reload}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "7px 14px", borderRadius: 8,
              border: "1px solid var(--border)", background: "var(--surface)",
              color: "var(--text-2)", fontSize: 12, cursor: "pointer",
            }}
          >
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {/* Stat tiles */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
          <StatTile value={stats.indexed}    label="Indexed"    icon={CheckCircle} color="var(--ok)"       />
          <StatTile value={stats.chunks}     label="Chunks"     icon={Layers}      color="var(--primary)"  />
          <StatTile value={stats.processing} label="Processing" icon={Clock}       color="var(--warn)"     />
          <StatTile value={stats.restricted} label="Restricted" icon={AlertCircle} color="var(--danger)"   />
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? "var(--primary)" : "var(--border)"}`,
            borderRadius: 12,
            padding: "28px 20px",
            textAlign: "center",
            cursor: "pointer",
            background: dragging ? "var(--primary-soft)" : "var(--surface-2)",
            transition: "border-color 0.15s, background 0.15s",
            marginBottom: 20,
          }}
        >
          {uploading
            ? <><Loader2 size={24} className="animate-spin" style={{ margin: "0 auto 8px", color: "var(--primary)", display: "block" }} /><p style={{ margin: 0, fontSize: 13, color: "var(--text-2)" }}>Uploading…</p></>
            : (
              <>
                <Upload size={24} style={{ margin: "0 auto 10px", color: dragging ? "var(--primary)" : "var(--text-3)", display: "block" }} />
                <p style={{ margin: "0 0 4px", fontSize: 13, fontWeight: 500, color: "var(--text)" }}>
                  {dragging ? "Drop to upload" : "Drag & drop files or click to browse"}
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text-3)" }}>PDF, DOCX, XLSX, PPTX, TXT, MD, CSV</p>
              </>
            )
          }
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv"
            style={{ display: "none" }}
            onChange={e => handleFiles(e.target.files)}
          />
        </div>

        {/* Table */}
        {docs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-3)" }}>
            <FileText size={40} style={{ margin: "0 auto 12px", display: "block", opacity: 0.3 }} />
            <p style={{ margin: 0, fontSize: 14 }}>No documents yet. Upload your first file to get started.</p>
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--surface-2)", borderBottom: "1px solid var(--border)" }}>
                  {["Document", "Classification", "Status", "Chunks", "Size", "Created", ""].map(h => (
                    <th key={h} style={{
                      padding: "9px 14px", textAlign: "left",
                      fontSize: 11, fontWeight: 600, color: "var(--text-3)",
                      textTransform: "uppercase", letterSpacing: "0.06em",
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {docs.map(doc => (
                  <tr
                    key={doc.id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--surface-2)"}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
                  >
                    <td style={{ padding: "10px 14px", maxWidth: 280 }}>
                      <p style={{ margin: 0, fontWeight: 500, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {doc.title}
                      </p>
                      {doc.error_message && (
                        <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--danger)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {doc.error_message}
                        </p>
                      )}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{
                        padding: "2px 8px", borderRadius: 999, fontSize: 11, fontWeight: 500,
                        background: (CLASS_STYLE[doc.classification] ?? CLASS_STYLE.internal).bg,
                        color: (CLASS_STYLE[doc.classification] ?? CLASS_STYLE.internal).color,
                      }}>
                        {doc.classification}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        {STATUS_ICON[doc.status] ?? null}
                        <span style={{ fontSize: 12, color: "var(--text-2)" }}>{doc.status}</span>
                      </div>
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-2)", fontSize: 12 }}>{doc.chunk_count}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-3)", fontSize: 11 }}>
                      {doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(0)} KB` : "—"}
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-3)", fontSize: 11, whiteSpace: "nowrap" }}>
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ display: "flex", gap: 10 }}>
                        <button
                          onClick={() => handleReindex(doc.id)}
                          title="Reindex"
                          style={{ color: "var(--text-3)" }}
                          onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--primary)"}
                          onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text-3)"}
                        >
                          <RefreshCw size={13} />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          title="Delete"
                          style={{ color: "var(--text-3)" }}
                          onMouseEnter={e => (e.currentTarget as HTMLElement).style.color = "var(--danger)"}
                          onMouseLeave={e => (e.currentTarget as HTMLElement).style.color = "var(--text-3)"}
                        >
                          <Trash2 size={13} />
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
    </div>
  );
}
