import { useState, useRef, useEffect } from "react";
import { Send, Loader2, GitBranch, FileText, Network, Zap } from "lucide-react";
import { query, type QueryResponse } from "../lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
  timestamp: Date;
}

const MODE_COLORS: Record<string, string> = {
  vector: "bg-blue-100 text-blue-700",
  graph: "bg-purple-100 text-purple-700",
  hybrid: "bg-green-100 text-green-700",
  decision: "bg-amber-100 text-amber-700",
};

const MODE_ICONS: Record<string, React.ReactNode> = {
  vector: <FileText size={12} />,
  graph: <Network size={12} />,
  hybrid: <GitBranch size={12} />,
  decision: <Zap size={12} />,
};

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const resp = await query(question);
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: resp.answer,
        response: resp,
        timestamp: new Date(),
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20">
            <Network size={48} className="mx-auto mb-4 opacity-40" />
            <p className="text-lg font-medium">Ask your company anything</p>
            <p className="text-sm mt-2">Powered by Hybrid Graph RAG + Decision Trail</p>
            <div className="mt-6 grid grid-cols-1 gap-2 max-w-sm mx-auto text-left">
              {[
                "Who works on Project Atlas?",
                "Why did we choose PostgreSQL over MySQL?",
                "What is our parental leave policy?",
                "Which teams collaborate on the payment system?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  className="text-sm px-3 py-2 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 text-left transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className={`max-w-3xl ${msg.role === "user" ? "order-2" : "order-1"}`}>
              <div
                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
                }`}
              >
                {msg.content}
              </div>

              {/* Assistant metadata */}
              {msg.response && (
                <div className="mt-2 space-y-2">
                  {/* Retrieval mode badge */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                        MODE_COLORS[msg.response.retrieval_mode] || "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {MODE_ICONS[msg.response.retrieval_mode]}
                      {msg.response.retrieval_mode}
                    </span>
                    {msg.response.decision_trail_used && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                        <Zap size={10} /> Decision Trail
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {msg.response.chunks_used} chunks · {msg.response.latency_ms}ms
                    </span>
                    {msg.response.denied_chunk_count > 0 && (
                      <span className="text-xs text-orange-500">
                        {msg.response.denied_chunk_count} chunks restricted
                      </span>
                    )}
                  </div>

                  {/* Sources */}
                  {msg.response.sources.length > 0 && (
                    <div className="space-y-1">
                      {msg.response.sources.slice(0, 4).map((src, i) => (
                        <div
                          key={i}
                          className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2 text-xs"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-gray-700 truncate">
                              {src.document_title}
                            </span>
                            <span className="text-gray-400 ml-2 shrink-0">
                              {(src.score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="text-gray-500 line-clamp-2">{src.excerpt}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <Loader2 size={16} className="animate-spin text-blue-500" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 p-4 bg-white">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage(input)}
            placeholder="Ask your company anything..."
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
