import { useState, useRef, useEffect } from "react";
import { Send, Loader2, FileText, Network, GitBranch, Zap, ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { streamQuery, type StreamMetadata, type Source } from "../lib/api";

interface AssistantMeta {
  retrieval_mode: string;
  graph_entities_used: string[];
  decision_trail_used: boolean;
  chunks_used: number;
  denied_chunk_count: number;
  retrieval_ms: number;
  sources: Source[];
  latency_ms?: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;  // true while tokens are still arriving
  meta?: AssistantMeta;
}

const SUGGESTIONS = [
  "Who works on Project Atlas?",
  "Why did we choose PostgreSQL over MySQL?",
  "What is our parental leave policy?",
  "Which teams collaborate on the payment system?",
  "What decisions were made about the Q3 architecture?",
  "What alternatives did leadership consider for the stack?",
];

const MODE_META: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  vector:   { label: "Vector",         color: "var(--ok)",       bg: "var(--ok-soft)",       icon: <FileText size={11} /> },
  graph:    { label: "Graph",          color: "var(--primary)",  bg: "var(--primary-soft)",  icon: <Network size={11} /> },
  hybrid:   { label: "Hybrid",         color: "var(--warn)",     bg: "var(--warn-soft)",     icon: <GitBranch size={11} /> },
  decision: { label: "Decision Trail", color: "var(--decision)", bg: "var(--decision-soft)", icon: <Zap size={11} /> },
};

function ModeBadge({ mode }: { mode: string }) {
  const m = MODE_META[mode] ?? { label: mode, color: "var(--text-3)", bg: "var(--surface-3)", icon: null };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 999,
      background: m.bg, color: m.color,
      fontSize: 11, fontWeight: 500,
    }}>
      {m.icon} {m.label}
    </span>
  );
}

function DecisionCard() {
  return (
    <div style={{
      marginTop: 12,
      borderRadius: 10,
      border: "1px solid var(--decision-soft)",
      background: "var(--decision-soft)",
      overflow: "hidden",
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "8px 14px",
        background: "var(--decision)",
        color: "white",
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
      }}>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
          <polygon points="5,0 10,5 5,10 0,5" />
        </svg>
        Decision Trail Active
      </div>
      <div style={{ padding: "10px 14px", fontSize: 12, color: "var(--text-2)", lineHeight: 1.5 }}>
        This answer was retrieved from the Decision Trail. The response incorporates
        structured decision records — including alternatives considered, decision makers,
        and superseded decisions. See source citations for evidence chunks.
      </div>
    </div>
  );
}

function SourcesPanel({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div style={{ marginTop: 10 }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 5,
          fontSize: 11, color: "var(--text-3)", fontWeight: 500,
          background: "none", border: "none", cursor: "pointer", padding: 0,
        }}
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {sources.length} source{sources.length > 1 ? "s" : ""}
      </button>
      {open && (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          {sources.slice(0, 5).map((src, i) => (
            <div key={i} style={{
              padding: "9px 12px",
              borderRadius: 8,
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 280 }}>
                  {src.document_title}
                </span>
                <span style={{ fontSize: 10, color: "var(--ok)", fontWeight: 600, flexShrink: 0, marginLeft: 8 }}>
                  {(src.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="line-clamp-2" style={{ margin: 0, fontSize: 11, color: "var(--text-2)", lineHeight: 1.5 }}>
                {src.excerpt}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = (q: string) => {
    if (!q.trim() || loading) return;
    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: q };
    const assistantId = crypto.randomUUID();
    setMessages(m => [...m, userMsg, { id: assistantId, role: "assistant", content: "", streaming: true }]);
    setInput("");
    setLoading(true);

    const cancel = streamQuery(
      q,
      // onMetadata — retrieval done, sources available before LLM starts
      (meta: StreamMetadata) => {
        setMessages(m => m.map(msg =>
          msg.id === assistantId ? { ...msg, meta: { ...meta } } : msg
        ));
      },
      // onToken — append each token as it arrives
      (token: string) => {
        setMessages(m => m.map(msg =>
          msg.id === assistantId ? { ...msg, content: msg.content + token } : msg
        ));
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      },
      // onDone — finalize with total latency
      (latencyMs: number) => {
        setMessages(m => m.map(msg =>
          msg.id === assistantId
            ? { ...msg, streaming: false, meta: msg.meta ? { ...msg.meta, latency_ms: latencyMs } : undefined }
            : msg
        ));
        setLoading(false);
      },
      // onError
      (err: Error) => {
        setMessages(m => m.map(msg =>
          msg.id === assistantId
            ? { ...msg, content: `Error: ${err.message}`, streaming: false }
            : msg
        ));
        setLoading(false);
      },
    );
    cancelRef.current = cancel;
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); }
  };

  const isEmpty = messages.length === 0;

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Recent sidebar */}
      <div style={{
        width: 220,
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        background: "var(--surface)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}>
        <div style={{ padding: "14px 14px 8px", borderBottom: "1px solid var(--border)" }}>
          <p style={{ margin: 0, fontSize: 11, fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em" }}>
            Suggestions
          </p>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 6px" }}>
          {SUGGESTIONS.map((q, i) => (
            <button
              key={i}
              onClick={() => { setInput(q); inputRef.current?.focus(); }}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "7px 10px", borderRadius: 8, marginBottom: 2,
                fontSize: 12, color: "var(--text-2)", lineHeight: 1.4,
                background: "none", border: "none", cursor: "pointer",
              }}
              onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--surface-3)"}
              onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "none"}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Messages */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 24px 0" }}>
          {isEmpty && (
            <div style={{ textAlign: "center", marginTop: 80, animation: "fadeIn 0.3s ease" }}>
              <svg width="52" height="52" viewBox="0 0 28 28" fill="none" style={{ margin: "0 auto 16px", display: "block" }}>
                <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" fill="var(--primary)" opacity="0.12" />
                <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" stroke="var(--primary)" strokeWidth="1.5" fill="none" />
                <circle cx="14" cy="14" r="3.5" fill="var(--primary)" />
              </svg>
              <p style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 600, color: "var(--text)" }}>
                Ask your company anything
              </p>
              <p style={{ margin: "0 0 24px", fontSize: 13, color: "var(--text-2)" }}>
                Hybrid Graph RAG · Decision Trail · RBAC-enforced
              </p>
            </div>
          )}

          {messages.map(msg => (
            <div
              key={msg.id}
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                marginBottom: 20,
                animation: "fadeIn 0.2s ease",
              }}
            >
              <div style={{ maxWidth: "72%" }}>
                {/* Bubble */}
                <div style={{
                  padding: "11px 14px",
                  borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                  background: msg.role === "user" ? "var(--primary)" : "var(--surface)",
                  border: msg.role === "user" ? "none" : "1px solid var(--border)",
                  color: msg.role === "user" ? "var(--on-primary)" : "var(--text)",
                  fontSize: 14,
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                  boxShadow: msg.role === "assistant" ? "0 1px 4px var(--shadow)" : "none",
                }}>
                  {msg.content}
                </div>

                {/* Streaming cursor */}
                {msg.streaming && msg.content === "" && (
                  <span style={{ display: "inline-block", width: 8, height: 14, background: "var(--primary)", borderRadius: 2, animation: "pulse-dot 1s ease-in-out infinite", verticalAlign: "middle", marginLeft: 2 }} />
                )}

                {/* Metadata — appears as soon as retrieval is done (before streaming finishes) */}
                {msg.meta && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <ModeBadge mode={msg.meta.retrieval_mode} />
                      <span style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {msg.meta.chunks_used} chunks
                        {msg.meta.latency_ms != null ? ` · ${msg.meta.latency_ms}ms` : ` · ${msg.meta.retrieval_ms}ms retrieval`}
                      </span>
                      {msg.meta.graph_entities_used.length > 0 && (
                        <span style={{ fontSize: 11, color: "var(--primary)" }}>
                          {msg.meta.graph_entities_used.length} graph nodes
                        </span>
                      )}
                      {msg.meta.denied_chunk_count > 0 && (
                        <span style={{
                          display: "inline-flex", alignItems: "center", gap: 4,
                          fontSize: 11, color: "var(--warn)", fontWeight: 500,
                        }}>
                          <AlertTriangle size={10} />
                          {msg.meta.denied_chunk_count} restricted
                        </span>
                      )}
                    </div>

                    {msg.meta.decision_trail_used && <DecisionCard />}
                    <SourcesPanel sources={msg.meta.sources} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && messages[messages.length - 1]?.content === "" && (
            <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 20 }}>
              <div style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "11px 16px", borderRadius: "14px 14px 14px 4px",
                background: "var(--surface)", border: "1px solid var(--border)",
                boxShadow: "0 1px 4px var(--shadow)",
              }}>
                <div style={{ display: "flex", gap: 4 }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{
                      width: 5, height: 5, borderRadius: "50%",
                      background: "var(--primary)", opacity: 0.5,
                      animation: `pulse-dot 1.2s ${i * 0.2}s ease-in-out infinite`,
                    }} />
                  ))}
                </div>
                <span style={{ fontSize: 12, color: "var(--text-3)" }}>Thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} style={{ height: 24 }} />
        </div>

        {/* Input */}
        <div style={{
          padding: "12px 20px 20px",
          borderTop: "1px solid var(--border)",
          background: "var(--surface)",
        }}>
          <div style={{
            display: "flex",
            alignItems: "flex-end",
            gap: 10,
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: "10px 10px 10px 14px",
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
              }}
              onKeyDown={handleKey}
              placeholder="Ask your company anything…"
              disabled={loading}
              rows={1}
              style={{
                flex: 1,
                resize: "none",
                border: "none",
                outline: "none",
                background: "transparent",
                color: "var(--text)",
                fontSize: 14,
                lineHeight: 1.5,
                maxHeight: 140,
                overflowY: "auto",
              }}
            />
            <button
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center",
                width: 36, height: 36, borderRadius: 8, flexShrink: 0,
                background: input.trim() && !loading ? "var(--primary)" : "var(--surface-3)",
                color: input.trim() && !loading ? "var(--on-primary)" : "var(--text-3)",
                border: "none", cursor: !input.trim() || loading ? "not-allowed" : "pointer",
                transition: "background 0.15s",
              }}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
          <p style={{ margin: "6px 0 0", fontSize: 10, color: "var(--text-3)", textAlign: "center" }}>
            Answers are restricted to content you're authorized to see · Enter to send · Shift+Enter for newline
          </p>
        </div>
      </div>
    </div>
  );
}
