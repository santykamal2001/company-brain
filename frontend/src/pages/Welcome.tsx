import { useNavigate } from "react-router-dom";
import { MessageSquare, Network, FileText, ArrowRight } from "lucide-react";
import { useUser, useTheme } from "../App";
import NeuralCanvas from "../components/NeuralCanvas";

const cards = [
  {
    to: "/app/ask",
    icon: MessageSquare,
    title: "Ask Mnemo",
    body: "Query your entire knowledge base in natural language. Hybrid Graph RAG routes each question to the right retrieval strategy.",
    color: "var(--primary)",
    soft: "var(--primary-soft)",
  },
  {
    to: "/app/graph",
    icon: Network,
    title: "Knowledge Graph",
    body: "Explore the living network of people, projects, decisions, and topics extracted from your indexed content.",
    color: "var(--decision)",
    soft: "var(--decision-soft)",
  },
  {
    to: "/app/documents",
    icon: FileText,
    title: "Documents",
    body: "Upload and manage the knowledge sources Mnemo ingests — PDFs, DOCX, spreadsheets, and more.",
    color: "var(--ok)",
    soft: "var(--ok-soft)",
  },
];

export default function Welcome() {
  const navigate = useNavigate();
  const { user } = useUser();
  const { theme } = useTheme();

  const firstName = user?.username?.split(" ")[0] ?? user?.email?.split("@")[0] ?? "there";

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px 24px",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Ambient canvas */}
      <div style={{ position: "absolute", inset: 0, opacity: 0.18, pointerEvents: "none" }}>
        <NeuralCanvas primaryRgb={theme === "dark" ? "28,183,160" : "14,140,121"} />
      </div>

      {/* Logo */}
      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10, marginBottom: 40 }}>
        <svg width="36" height="36" viewBox="0 0 28 28" fill="none">
          <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" fill="var(--primary)" opacity="0.15" />
          <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" stroke="var(--primary)" strokeWidth="1.5" fill="none" />
          <circle cx="14" cy="14" r="3.5" fill="var(--primary)" />
          <line x1="14" y1="10.5" x2="14" y2="5"    stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
          <line x1="14" y1="17.5" x2="14" y2="23"   stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
          <line x1="10.5" y1="12" x2="5.5" y2="9"   stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
          <line x1="17.5" y1="16" x2="22.5" y2="19" stroke="var(--primary)" strokeWidth="1.2" opacity="0.7" />
        </svg>
        <span style={{ fontWeight: 600, fontSize: 18, letterSpacing: "-0.01em", color: "var(--text)" }}>Mnemo</span>
      </div>

      {/* Greeting */}
      <div style={{ position: "relative", textAlign: "center", marginBottom: 48 }}>
        <h1 style={{
          margin: "0 0 10px",
          fontSize: "clamp(28px, 4vw, 42px)",
          fontWeight: 700,
          letterSpacing: "-0.03em",
          color: "var(--text)",
        }}>
          Welcome, {firstName}
        </h1>
        <p style={{ margin: 0, fontSize: 15, color: "var(--text-2)" }}>
          Your workspace is ready. Where would you like to start?
        </p>
      </div>

      {/* Nav cards */}
      <div style={{
        position: "relative",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: 16,
        width: "100%",
        maxWidth: 820,
        marginBottom: 40,
      }}>
        {cards.map(({ to, icon: Icon, title, body, color, soft }) => (
          <button
            key={to}
            onClick={() => navigate(to)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              gap: 12,
              padding: "22px 20px",
              borderRadius: 14,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              cursor: "pointer",
              textAlign: "left",
              transition: "box-shadow 0.15s, border-color 0.15s",
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.borderColor = color;
              (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 20px ${color}22`;
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
              (e.currentTarget as HTMLElement).style.boxShadow = "none";
            }}
          >
            <div style={{ padding: 10, borderRadius: 10, background: soft, color }}>
              <Icon size={18} />
            </div>
            <div>
              <p style={{ margin: "0 0 6px", fontSize: 14, fontWeight: 600, color: "var(--text)" }}>{title}</p>
              <p style={{ margin: 0, fontSize: 12, color: "var(--text-2)", lineHeight: 1.5 }}>{body}</p>
            </div>
            <div style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: 4, fontSize: 12, color, fontWeight: 500 }}>
              Open <ArrowRight size={12} />
            </div>
          </button>
        ))}
      </div>

      {/* Enter workspace */}
      <button
        onClick={() => navigate("/app/ask")}
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "12px 28px",
          borderRadius: 10,
          background: "var(--primary)",
          color: "var(--on-primary)",
          fontSize: 14,
          fontWeight: 600,
          border: "none",
          cursor: "pointer",
        }}
      >
        Enter workspace <ArrowRight size={14} />
      </button>
    </div>
  );
}
