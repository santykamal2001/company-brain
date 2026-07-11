import { useNavigate } from "react-router-dom";
import NeuralCanvas from "../components/NeuralCanvas";
import { useUser, useTheme } from "../App";
import { Shield, Network, Zap, GitBranch, Lock, BarChart3, ArrowRight, Check } from "lucide-react";

const features = [
  {
    icon: Network,
    title: "Hybrid Graph RAG",
    body: "Vector search + knowledge graph traversal in a single query, routed automatically by question type. Multi-hop relational answers no competitor can match.",
  },
  {
    icon: GitBranch,
    title: "Decision Trail",
    body: "Every decision — why, who, alternatives considered — captured as first-class graph nodes. Answer 'why did we choose X?' from documents indexed years ago.",
  },
  {
    icon: Shield,
    title: "Chunk-Level RBAC",
    body: "ACL enforcement at the individual chunk and graph-node level. The LLM never sees content the requestor isn't cleared for. EU AI Act Article 13 compliant.",
  },
  {
    icon: Zap,
    title: "MCP Knowledge Substrate",
    body: "Expose governed retrieval as an MCP server. Claude Code, Cursor, and your internal agents query Mnemo — with full RBAC on every call.",
  },
  {
    icon: Lock,
    title: "Self-Hosted",
    body: "Single-command Docker deployment. Your data, your compute, your LLM choice. No SaaS dependency. Run fully air-gapped with Ollama.",
  },
  {
    icon: BarChart3,
    title: "Knowledge Health Score",
    body: "Live dashboard: stale content, conflicting claims, coverage gaps, permission drift. The 73% of AI deployments that fail on data quality won't fail here.",
  },
];

const stats = [
  { value: "67%", label: "retrieval failure reduction" },
  { value: "< 0.14¢", label: "per document indexed" },
  { value: "2-layer", label: "RBAC defense depth" },
  { value: "1-cmd", label: "Docker deploy" },
];

export default function Landing() {
  const navigate = useNavigate();
  const { user } = useUser();
  const { theme, toggle } = useTheme();

  const handleLaunch = () => {
    navigate(user ? "/app/ask" : "/login");
  };

  const s: Record<string, React.CSSProperties> = {
    page: {
      minHeight: "100vh",
      background: "var(--bg)",
      color: "var(--text)",
    },
    nav: {
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      height: 56,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 40px",
      background: "var(--bg)",
      borderBottom: "1px solid var(--border)",
      zIndex: 100,
    },
    logo: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontWeight: 600,
      fontSize: 15,
      letterSpacing: "-0.01em",
    },
    navLinks: {
      display: "flex",
      alignItems: "center",
      gap: 24,
    },
    navLink: {
      fontSize: 13,
      color: "var(--text-2)",
      cursor: "pointer",
      background: "none",
      border: "none",
      padding: 0,
    },
    ctaBtn: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "7px 16px",
      borderRadius: 8,
      background: "var(--primary)",
      color: "var(--on-primary)",
      fontSize: 13,
      fontWeight: 500,
      cursor: "pointer",
      border: "none",
    },
    hero: {
      position: "relative",
      minHeight: "calc(100vh - 56px)",
      marginTop: 56,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      padding: "80px 40px 60px",
      overflow: "hidden",
    },
    canvasBg: {
      position: "absolute",
      inset: 0,
      opacity: 0.35,
    },
    badge: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: "4px 12px",
      borderRadius: 999,
      background: "var(--primary-soft)",
      color: "var(--primary)",
      fontSize: 12,
      fontWeight: 500,
      marginBottom: 24,
      position: "relative",
    },
    h1: {
      margin: "0 0 20px",
      fontSize: "clamp(36px, 5vw, 58px)",
      fontWeight: 700,
      lineHeight: 1.1,
      letterSpacing: "-0.03em",
      maxWidth: 760,
      position: "relative",
    },
    accent: { color: "var(--primary)" },
    sub: {
      margin: "0 0 40px",
      fontSize: 17,
      color: "var(--text-2)",
      maxWidth: 560,
      lineHeight: 1.6,
      position: "relative",
    },
    heroBtns: {
      display: "flex",
      gap: 12,
      position: "relative",
    },
    btnPrimary: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      padding: "11px 24px",
      borderRadius: 10,
      background: "var(--primary)",
      color: "var(--on-primary)",
      fontSize: 14,
      fontWeight: 600,
      cursor: "pointer",
      border: "none",
    },
    btnSecondary: {
      padding: "11px 24px",
      borderRadius: 10,
      background: "var(--surface)",
      border: "1px solid var(--border)",
      color: "var(--text)",
      fontSize: 14,
      fontWeight: 500,
      cursor: "pointer",
    },
    section: {
      padding: "80px 40px",
      maxWidth: 1100,
      margin: "0 auto",
    },
    sectionTitle: {
      fontSize: 13,
      fontWeight: 600,
      color: "var(--text-3)",
      textTransform: "uppercase",
      letterSpacing: "0.08em",
      marginBottom: 12,
    },
    sectionH2: {
      margin: "0 0 48px",
      fontSize: "clamp(26px, 3vw, 36px)",
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    grid: {
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
      gap: 16,
    },
    featureCard: {
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 14,
      padding: "22px 24px",
    },
    iconWrap: {
      display: "inline-flex",
      padding: 8,
      borderRadius: 8,
      background: "var(--primary-soft)",
      color: "var(--primary)",
      marginBottom: 14,
    },
    fTitle: {
      margin: "0 0 8px",
      fontSize: 14,
      fontWeight: 600,
    },
    fBody: {
      margin: 0,
      fontSize: 13,
      color: "var(--text-2)",
      lineHeight: 1.65,
    },
    statsRow: {
      borderTop: "1px solid var(--border)",
      borderBottom: "1px solid var(--border)",
      padding: "48px 40px",
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
      gap: 32,
      maxWidth: 1100,
      margin: "0 auto",
      textAlign: "center",
    },
    statVal: {
      fontSize: 36,
      fontWeight: 700,
      color: "var(--primary)",
      letterSpacing: "-0.02em",
    },
    statLabel: {
      fontSize: 13,
      color: "var(--text-2)",
      marginTop: 4,
    },
    footer: {
      padding: "60px 40px",
      textAlign: "center",
      borderTop: "1px solid var(--border)",
    },
    footerH: {
      fontSize: 28,
      fontWeight: 700,
      marginBottom: 12,
      letterSpacing: "-0.02em",
    },
    footerSub: {
      color: "var(--text-2)",
      fontSize: 14,
      marginBottom: 28,
    },
    checkList: {
      display: "flex",
      gap: 20,
      justifyContent: "center",
      flexWrap: "wrap",
      marginBottom: 32,
    },
    checkItem: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      fontSize: 13,
      color: "var(--text-2)",
    },
  };

  return (
    <div style={s.page}>
      {/* Nav */}
      <header style={s.nav}>
        <div style={s.logo}>
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
            <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" fill="var(--primary)" opacity="0.15" />
            <polygon points="14,2 25,8 25,20 14,26 3,20 3,8" stroke="var(--primary)" strokeWidth="1.5" fill="none" />
            <circle cx="14" cy="14" r="3.5" fill="var(--primary)" />
          </svg>
          Mnemo
        </div>
        <div style={s.navLinks}>
          <button style={s.navLink} onClick={toggle}>
            {theme === "dark" ? "☀ Light" : "◐ Dark"}
          </button>
          <button style={s.navLink} onClick={() => navigate("/login")}>Sign in</button>
          <button style={s.ctaBtn} onClick={handleLaunch}>
            Launch app <ArrowRight size={13} />
          </button>
        </div>
      </header>

      {/* Hero */}
      <section style={s.hero}>
        <div style={s.canvasBg}>
          <NeuralCanvas primaryRgb={theme === "dark" ? "28,183,160" : "14,140,121"} />
        </div>
        <div style={s.badge}>
          <Shield size={12} /> EU AI Act Article 13 Compliant
        </div>
        <h1 style={s.h1}>
          The governed knowledge<br />
          <span style={s.accent}>fabric</span> for the enterprise
        </h1>
        <p style={s.sub}>
          Mnemo ingests every document, decision, and conversation across your company —
          and lets every employee (and every AI agent) ask questions with answers
          restricted to exactly what they're cleared to see.
        </p>
        <div style={s.heroBtns}>
          <button style={s.btnPrimary} onClick={handleLaunch}>
            Get started <ArrowRight size={14} />
          </button>
          <button
            style={s.btnSecondary}
            onClick={() => navigate("/login")}
          >
            Sign in
          </button>
        </div>
      </section>

      {/* Stats */}
      <div style={s.statsRow}>
        {stats.map((st) => (
          <div key={st.value}>
            <div style={s.statVal}>{st.value}</div>
            <div style={s.statLabel}>{st.label}</div>
          </div>
        ))}
      </div>

      {/* Features */}
      <section style={s.section}>
        <div style={s.sectionTitle}>Why Mnemo</div>
        <h2 style={s.sectionH2}>Built for enterprises that can't afford data leaks</h2>
        <div style={s.grid}>
          {features.map((f) => (
            <div key={f.title} style={s.featureCard}>
              <div style={s.iconWrap}><f.icon size={16} /></div>
              <h3 style={s.fTitle}>{f.title}</h3>
              <p style={s.fBody}>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA footer */}
      <footer style={s.footer}>
        <h2 style={s.footerH}>Ready to give your company a memory?</h2>
        <p style={s.footerSub}>Self-hosted, single-command deploy. Your data never leaves your network.</p>
        <div style={s.checkList}>
          {["No SaaS dependency", "Ollama local LLM support", "Open-source friendly stack", "Docker Compose → K8s"].map((t) => (
            <span key={t} style={s.checkItem}>
              <Check size={13} color="var(--ok)" /> {t}
            </span>
          ))}
        </div>
        <button style={s.btnPrimary} onClick={handleLaunch}>
          Launch Mnemo <ArrowRight size={14} />
        </button>
      </footer>
    </div>
  );
}
