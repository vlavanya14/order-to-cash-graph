import { useRef, useCallback, useState, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";

const TYPE_COLORS = {
  SalesOrder:      "#4A90D9",
  SalesOrderItem:  "#74B3E8",
  Delivery:        "#50C878",
  DeliveryItem:    "#82D9A0",
  BillingDocument: "#FF6B6B",
  JournalEntry:    "#FFD700",
  Payment:         "#FF9F40",
  Customer:        "#9B59B6",
  Product:         "#E67E22",
  Plant:           "#1ABC9C",
};

const TYPE_ICONS = {
  SalesOrder: "📋", SalesOrderItem: "📝", Delivery: "🚚",
  BillingDocument: "🧾", JournalEntry: "📒", Payment: "💰",
  Customer: "👤", Product: "📦", Plant: "🏭",
};

export default function GraphView({ graphData, highlightNodes, onNodeSelect, selectedNode }) {
  const fgRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const containerRef = useRef();

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const nodeColor = useCallback(
    (node) => {
      if (highlightNodes.has(node.id)) return "#ef4444";
      if (selectedNode && selectedNode.id === node.id) return "#f59e0b";
      return node.color || TYPE_COLORS[node.type] || "#9ca3af";
    },
    [highlightNodes, selectedNode]
  );

  const nodeCanvasObject = useCallback(
    (node, ctx, globalScale) => {
      const isHighlighted = highlightNodes.has(node.id);
      const isSelected = selectedNode && selectedNode.id === node.id;
      const size = isHighlighted || isSelected ? 7 : 5;
      const color = isHighlighted ? "#ef4444" : isSelected ? "#f59e0b" : (node.color || "#9ca3af");

      // Draw node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      if (isHighlighted || isSelected) {
        ctx.strokeStyle = "white";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Draw label only when zoomed in enough
      if (globalScale >= 1.5 || isHighlighted || isSelected) {
        const label = node.label?.length > 16 ? node.label.slice(0, 16) + "…" : (node.label || node.id);
        ctx.font = `${10 / globalScale}px sans-serif`;
        ctx.fillStyle = "#374151";
        ctx.textAlign = "center";
        ctx.fillText(label, node.x, node.y + size + 8 / globalScale);
      }
    },
    [highlightNodes, selectedNode]
  );

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%", position: "relative" }}>
      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeCanvasObject={nodeCanvasObject}
        nodeCanvasObjectMode={() => "replace"}
        linkColor={(link) =>
          link.source?.id && highlightNodes.has(link.source?.id || link.source)
            ? "#ef4444"
            : "#cbd5e1"
        }
        linkWidth={(link) =>
          highlightNodes.has(link.source?.id || link.source) ? 2 : 0.8
        }
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        onNodeClick={(node) => onNodeSelect(node === selectedNode ? null : node)}
        onBackgroundClick={() => onNodeSelect(null)}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />

      {/* Node Detail Panel */}
      {selectedNode && (
        <div style={{
          position: "absolute", top: 16, left: 16,
          background: "white", borderRadius: 12,
          boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
          maxWidth: 300, maxHeight: "70vh", overflowY: "auto",
          padding: 16, fontSize: 12, zIndex: 10,
          border: "1px solid #e5e7eb"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 10, color: "#9ca3af", marginBottom: 2 }}>
                {TYPE_ICONS[selectedNode.type] || "●"} {selectedNode.type}
              </div>
              <div style={{ fontWeight: 700, fontSize: 13, color: "#111" }}>
                {selectedNode.label}
              </div>
            </div>
            <button
              onClick={() => onNodeSelect(null)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#9ca3af", fontSize: 18 }}
            >×</button>
          </div>

          <div style={{ borderTop: "1px solid #f3f4f6", paddingTop: 10 }}>
            {Object.entries(selectedNode.data || {})
              .filter(([, v]) => v && v !== "None" && v !== "null")
              .slice(0, 15)
              .map(([k, v]) => (
                <div key={k} style={{ marginBottom: 6, display: "flex", gap: 6 }}>
                  <span style={{ color: "#6b7280", fontWeight: 600, minWidth: 90, flexShrink: 0 }}>{k}:</span>
                  <span style={{ color: "#374151", wordBreak: "break-all" }}>
                    {String(v).length > 40 ? String(v).slice(0, 40) + "…" : String(v)}
                  </span>
                </div>
              ))}
            {Object.keys(selectedNode.data || {}).length > 15 && (
              <div style={{ color: "#9ca3af", fontStyle: "italic", fontSize: 11, marginTop: 4 }}>
                + {Object.keys(selectedNode.data).length - 15} more fields hidden
              </div>
            )}
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#9ca3af", borderTop: "1px solid #f3f4f6", paddingTop: 8 }}>
            ID: {selectedNode.id}
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{
        position: "absolute", bottom: 16, left: 16,
        background: "white", borderRadius: 10,
        boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
        padding: "10px 14px", fontSize: 11,
        border: "1px solid #e5e7eb"
      }}>
        <div style={{ fontWeight: 600, marginBottom: 6, color: "#374151" }}>Node Types</div>
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
            <span style={{ color: "#6b7280" }}>{TYPE_ICONS[type]} {type}</span>
          </div>
        ))}
      </div>

      {/* Controls hint */}
      <div style={{
        position: "absolute", bottom: 16, right: 16,
        background: "rgba(255,255,255,0.9)", borderRadius: 8,
        padding: "8px 12px", fontSize: 11, color: "#9ca3af",
        border: "1px solid #e5e7eb"
      }}>
        🖱 Scroll to zoom · Drag to pan · Click node to inspect
      </div>
    </div>
  );
}
