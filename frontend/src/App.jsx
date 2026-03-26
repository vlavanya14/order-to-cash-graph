import { useState, useEffect } from "react";
import GraphView from "./components/GraphView";
import ChatPanel from "./components/ChatPanel";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/graph`),
      axios.get(`${API}/graph/stats`)
    ])
      .then(([graphRes, statsRes]) => {
        const raw = graphRes.data;
        setGraphData({
          nodes: raw.nodes,
          links: raw.edges.map((e) => ({
            source: e.source,
            target: e.target,
            relation: e.relation,
          })),
        });
        setStats(statsRes.data);
        setLoading(false);
      })
      .catch((err) => {
        setError("Failed to connect to backend. Make sure the server is running on port 8000.");
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      {/* Top Bar */}
      <div style={{
        height: 48, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 20px", borderBottom: "1px solid #e5e7eb",
        background: "white", zIndex: 100
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "#9ca3af" }}>Mapping /</span>
          <span style={{ fontWeight: 700, fontSize: 15, color: "#111" }}>Order to Cash</span>
        </div>
        {stats && (
          <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#6b7280" }}>
            <span>🔵 {stats.total_nodes} nodes</span>
            <span>🔗 {stats.total_edges} edges</span>
            {Object.entries(stats.by_type || {}).slice(0, 4).map(([t, c]) => (
              <span key={t}>{t}: {c}</span>
            ))}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Graph Area */}
        <div style={{ flex: 1, position: "relative", background: "#f9fafb" }}>
          {loading && (
            <div style={{
              position: "absolute", inset: 0, display: "flex",
              alignItems: "center", justifyContent: "center",
              flexDirection: "column", gap: 12
            }}>
              <div style={{ fontSize: 32 }}>⟳</div>
              <div style={{ fontSize: 14, color: "#6b7280" }}>Loading graph data...</div>
            </div>
          )}
          {error && (
            <div style={{
              position: "absolute", inset: 0, display: "flex",
              alignItems: "center", justifyContent: "center"
            }}>
              <div style={{
                background: "#fef2f2", border: "1px solid #fca5a5",
                borderRadius: 12, padding: 24, maxWidth: 400, textAlign: "center"
              }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
                <div style={{ color: "#dc2626", fontSize: 14 }}>{error}</div>
              </div>
            </div>
          )}
          {!loading && !error && (
            <GraphView
              graphData={graphData}
              highlightNodes={highlightNodes}
              onNodeSelect={setSelectedNode}
              selectedNode={selectedNode}
            />
          )}
        </div>

        {/* Chat Panel */}
        <div style={{
          width: 400, borderLeft: "1px solid #e5e7eb",
          background: "white", display: "flex", flexDirection: "column",
          flexShrink: 0
        }}>
          <ChatPanel
            apiBase={API}
            onHighlight={setHighlightNodes}
          />
        </div>
      </div>
    </div>
  );
}
