import { useState } from "react";
import { X, Network } from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  type: "decision" | "person" | "project" | "topic" | "team";
  x: number;
  y: number;
  meta: Record<string, string>;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

// Demo graph — matches the Mnemo design layout
const NODES: GraphNode[] = [
  { id: "d1", label: "Adopt PostgreSQL",   type: "decision", x: 240, y: 140, meta: { decided: "2025-03-15", by: "Alice Kim, Marcus Chen", alternatives: "MySQL, CockroachDB", summary: "Chose PostgreSQL for ACID compliance, AGE extension support for the knowledge graph, and team familiarity." } },
  { id: "d2", label: "Q3 Architecture",    type: "decision", x: 660, y: 200, meta: { decided: "2025-06-01", by: "Marcus Chen", alternatives: "Monolith refactor", summary: "Split into async ingestion pipeline with Celery + Redis to enable parallel document processing at scale." } },
  { id: "d3", label: "Mobile-First UI",    type: "decision", x: 440, y: 380, meta: { decided: "2025-07-20", by: "Sarah Lin", alternatives: "Desktop-only, PWA", summary: "Prioritize mobile-responsive design for field teams accessing knowledge base on the go." } },
  { id: "p1", label: "Alice Kim",          type: "person",   x: 100, y: 290, meta: { role: "Lead Engineer", dept: "Engineering", email: "alice@company.com" } },
  { id: "p2", label: "Marcus Chen",        type: "person",   x: 370, y: 170, meta: { role: "Principal Architect", dept: "Platform", email: "marcus@company.com" } },
  { id: "p3", label: "Sarah Lin",          type: "person",   x: 590, y: 370, meta: { role: "Product Lead", dept: "Product", email: "sarah@company.com" } },
  { id: "pr1", label: "Project Atlas",     type: "project",  x: 560, y: 100, meta: { status: "Active", owner: "Marcus Chen", started: "2025-01-10" } },
  { id: "pr2", label: "Payments v2",       type: "project",  x: 270, y: 420, meta: { status: "Planning", owner: "Alice Kim", started: "2025-07-01" } },
  { id: "t1", label: "PostgreSQL",         type: "topic",    x: 120, y: 460, meta: { category: "Technology", related: "Database, Backend" } },
  { id: "t2", label: "Architecture",       type: "topic",    x: 780, y: 320, meta: { category: "Engineering", related: "Infrastructure, Backend" } },
  { id: "tm1", label: "Engineering",       type: "team",     x: 680, y: 110, meta: { dept: "Engineering", size: "12 members", lead: "Marcus Chen" } },
  { id: "tm2", label: "Platform",          type: "team",     x: 340, y: 70,  meta: { dept: "Platform", size: "6 members", lead: "Alice Kim" } },
];

const EDGES: GraphEdge[] = [
  { source: "p1",  target: "d1",  label: "MADE_BY" },
  { source: "p2",  target: "d1",  label: "MADE_BY" },
  { source: "p2",  target: "d2",  label: "MADE_BY" },
  { source: "p3",  target: "d3",  label: "MADE_BY" },
  { source: "d1",  target: "pr1", label: "ABOUT" },
  { source: "d2",  target: "pr1", label: "ABOUT" },
  { source: "d3",  target: "pr2", label: "ABOUT" },
  { source: "p1",  target: "pr1", label: "WORKS_ON" },
  { source: "p2",  target: "pr1", label: "WORKS_ON" },
  { source: "p1",  target: "pr2", label: "WORKS_ON" },
  { source: "tm1", target: "p2",  label: "INCLUDES" },
  { source: "tm2", target: "p1",  label: "INCLUDES" },
  { source: "t1",  target: "d1",  label: "DISCUSSED_IN" },
  { source: "t2",  target: "d2",  label: "DISCUSSED_IN" },
  { source: "pr1", target: "tm1", label: "OWNED_BY" },
];

const NODE_COLORS: Record<GraphNode["type"], { fill: string; stroke: string; label: string }> = {
  decision: { fill: "var(--decision-soft)", stroke: "var(--decision)", label: "Decision" },
  person:   { fill: "var(--primary-soft)",  stroke: "var(--primary)",  label: "Person" },
  project:  { fill: "var(--ok-soft)",       stroke: "var(--ok)",       label: "Project" },
  topic:    { fill: "var(--warn-soft)",      stroke: "var(--warn)",     label: "Topic" },
  team:     { fill: "var(--surface-3)",     stroke: "var(--border-2)", label: "Team" },
};

// Hexagon path helper
function hexPoints(cx: number, cy: number, r: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const a = (i * 60 - 30) * Math.PI / 180;
    return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
  }).join(" ");
}

function NodeShape({ node, selected, onClick }: { node: GraphNode; selected: boolean; onClick: React.MouseEventHandler<SVGGElement> }) {
  const c = NODE_COLORS[node.type];
  const { x, y } = node;
  const strokeW = selected ? 2.5 : 1.5;
  const strokeColor = selected ? c.stroke : c.stroke;

  if (node.type === "decision") {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <polygon
          points={hexPoints(x, y, 30)}
          fill={c.fill}
          stroke={strokeColor}
          strokeWidth={strokeW}
          filter={selected ? "drop-shadow(0 0 6px var(--decision))" : undefined}
        />
        <text x={x} y={y - 8} textAnchor="middle" fill="var(--text)" fontSize="9" fontWeight="500">
          {node.label.length > 14 ? node.label.substring(0, 14) + "…" : node.label}
        </text>
        <text x={x} y={y + 5} textAnchor="middle" fill={c.stroke} fontSize="8">
          ◆ DECISION
        </text>
      </g>
    );
  }
  if (node.type === "person") {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <circle cx={x} cy={y} r={24} fill={c.fill} stroke={strokeColor} strokeWidth={strokeW}
          filter={selected ? "drop-shadow(0 0 5px var(--primary))" : undefined} />
        <text x={x} y={y - 5} textAnchor="middle" fill="var(--text)" fontSize="9" fontWeight="500">
          {node.label.split(" ")[0]}
        </text>
        <text x={x} y={y + 7} textAnchor="middle" fill="var(--text-3)" fontSize="8">
          {node.label.split(" ").slice(1).join(" ")}
        </text>
      </g>
    );
  }
  if (node.type === "project") {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <rect x={x - 38} y={y - 18} width={76} height={36} rx={8}
          fill={c.fill} stroke={strokeColor} strokeWidth={strokeW}
          filter={selected ? "drop-shadow(0 0 5px var(--ok))" : undefined} />
        <text x={x} y={y + 4} textAnchor="middle" fill="var(--text)" fontSize="9" fontWeight="500">
          {node.label}
        </text>
      </g>
    );
  }
  if (node.type === "topic") {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <rect x={x - 36} y={y - 12} width={72} height={24} rx={12}
          fill={c.fill} stroke={strokeColor} strokeWidth={strokeW} />
        <text x={x} y={y + 4} textAnchor="middle" fill="var(--text)" fontSize="9">
          # {node.label}
        </text>
      </g>
    );
  }
  // team — dashed border
  return (
    <g onClick={onClick} style={{ cursor: "pointer" }}>
      <rect x={x - 38} y={y - 16} width={76} height={32} rx={6}
        fill={c.fill} stroke={strokeColor} strokeWidth={1.5} strokeDasharray="4,3" />
      <text x={x} y={y + 4} textAnchor="middle" fill="var(--text)" fontSize="9">
        {node.label}
      </text>
    </g>
  );
}

function nodeById(id: string) { return NODES.find(n => n.id === id)!; }

export default function Graph() {
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const handleClick = (n: GraphNode) => {
    setSelected(prev => prev?.id === n.id ? null : n);
  };

  const connectedEdges = selected
    ? EDGES.filter(e => e.source === selected.id || e.target === selected.id)
    : [];

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden", background: "var(--bg)" }}>
      {/* SVG canvas */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {/* Legend */}
        <div style={{
          position: "absolute", top: 16, left: 16, zIndex: 10,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 10, padding: "10px 14px",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          <p style={{ margin: 0, fontSize: 10, fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 4 }}>
            Node types
          </p>
          {(Object.entries(NODE_COLORS) as [GraphNode["type"], typeof NODE_COLORS[GraphNode["type"]]][]).map(([type, c]) => (
            <div key={type} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 12, height: 12, borderRadius: type === "person" ? "50%" : type === "topic" ? "50%" : 3, background: c.fill, border: `1.5px solid ${c.stroke}` }} />
              <span style={{ fontSize: 11, color: "var(--text-2)" }}>{c.label}</span>
            </div>
          ))}
        </div>

        <svg
          width="100%" height="100%"
          viewBox="0 0 900 530"
          style={{ display: "block" }}
          onClick={() => setSelected(null)}
        >
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6 Z" fill="var(--border-2)" />
            </marker>
          </defs>

          {/* Edges */}
          {EDGES.map((edge, i) => {
            const src = nodeById(edge.source);
            const tgt = nodeById(edge.target);
            const isHighlit = selected && (edge.source === selected.id || edge.target === selected.id);
            const mx = (src.x + tgt.x) / 2;
            const my = (src.y + tgt.y) / 2;
            return (
              <g key={i}>
                <line
                  x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                  stroke={isHighlit ? "var(--primary)" : "var(--border-2)"}
                  strokeWidth={isHighlit ? 1.8 : 1.2}
                  strokeOpacity={isHighlit ? 0.9 : 0.5}
                  markerEnd="url(#arrow)"
                />
                <text x={mx} y={my - 4} textAnchor="middle" fill="var(--text-3)" fontSize="8" opacity={isHighlit ? 1 : 0.5}>
                  {edge.label}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map(node => (
            <NodeShape
              key={node.id}
              node={node}
              selected={selected?.id === node.id}
              onClick={e => { e.stopPropagation(); handleClick(node); }}
            />
          ))}
        </svg>

        {/* Empty state overlay */}
        {NODES.length === 0 && (
          <div style={{
            position: "absolute", inset: 0, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 12, color: "var(--text-3)",
          }}>
            <Network size={48} style={{ opacity: 0.3 }} />
            <p style={{ margin: 0, fontSize: 14 }}>No graph data yet — upload documents to build the knowledge graph</p>
          </div>
        )}
      </div>

      {/* Detail panel */}
      {selected && (
        <div style={{
          width: 280,
          flexShrink: 0,
          borderLeft: "1px solid var(--border)",
          background: "var(--surface)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          animation: "slide-in 0.2s ease",
        }}>
          {/* Header */}
          <div style={{
            padding: "14px 16px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 10,
          }}>
            <div>
              <div style={{
                display: "inline-block", padding: "2px 8px", borderRadius: 999, marginBottom: 6,
                background: NODE_COLORS[selected.type].fill,
                border: `1px solid ${NODE_COLORS[selected.type].stroke}`,
                fontSize: 10, fontWeight: 600, color: NODE_COLORS[selected.type].stroke,
                textTransform: "uppercase", letterSpacing: "0.05em",
              }}>
                {NODE_COLORS[selected.type].label}
              </div>
              <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text)", lineHeight: 1.3 }}>
                {selected.label}
              </p>
            </div>
            <button onClick={() => setSelected(null)} style={{ color: "var(--text-3)", flexShrink: 0, marginTop: 2 }}>
              <X size={15} />
            </button>
          </div>

          {/* Meta */}
          <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px" }}>
            {Object.entries(selected.meta).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 12 }}>
                <p style={{ margin: "0 0 2px", fontSize: 10, fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                  {k}
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--text)", lineHeight: 1.5 }}>{v}</p>
              </div>
            ))}

            {/* Connected edges */}
            {connectedEdges.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <p style={{ margin: "0 0 8px", fontSize: 10, fontWeight: 600, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                  Connections ({connectedEdges.length})
                </p>
                {connectedEdges.map((e, i) => {
                  const other = e.source === selected.id ? nodeById(e.target) : nodeById(e.source);
                  const dir   = e.source === selected.id ? "→" : "←";
                  return (
                    <div
                      key={i}
                      style={{
                        display: "flex", alignItems: "center", gap: 8,
                        padding: "6px 8px", borderRadius: 6, marginBottom: 4,
                        background: "var(--surface-2)", cursor: "pointer",
                        fontSize: 11,
                      }}
                      onClick={() => setSelected(other)}
                    >
                      <span style={{ color: "var(--text-3)", flexShrink: 0 }}>{dir} {e.label}</span>
                      <span style={{ color: "var(--text)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {other.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
