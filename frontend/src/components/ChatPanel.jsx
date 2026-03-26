import { useState, useRef, useEffect } from "react";
import axios from "axios";

const SUGGESTED_QUERIES = [
  "Which products are associated with the highest number of billing documents?",
  "Trace the full flow of billing document 90504298",
  "Identify sales orders delivered but not billed",
  "Which customers have the highest total order amounts?",
  "Show sales orders with billing but no journal entry",
  "What is the total billed amount per customer?",
];

export default function ChatPanel({ apiBase, onHighlight }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! I can help you analyze the **Order to Cash** process.\n\nAsk me about sales orders, deliveries, billing documents, payments, customers, or products.",
      isWelcome: true,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (queryText) => {
    const q = (queryText || input).trim();
    if (!q || loading) return;

    setInput("");
    setShowSuggestions(false);
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);

    try {
      const res = await axios.post(`${apiBase}/chat`, { query: q });
      const { answer, sql, data, blocked } = res.data;

      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: answer,
          sql,
          rowCount: data?.rows?.length,
          blocked,
          tableData: data?.rows?.length > 0 && data?.columns ? data : null,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "❌ Connection error. Please make sure the backend is running.", isError: true },
      ]);
    }
    setLoading(false);
  };

  const formatText = (text) => {
    // Simple markdown-like formatting
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br/>");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "14px 20px", borderBottom: "1px solid #e5e7eb" }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: "#111" }}>Chat with Graph</div>
        <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 2 }}>Order to Cash</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
          <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e" }} />
          <span style={{ fontSize: 11, color: "#6b7280" }}>AI Agent ready</span>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: "auto", padding: "16px",
        display: "flex", flexDirection: "column", gap: 12
      }}>
        {messages.map((msg, i) => (
          <div key={i}>
            {/* Role label */}
            <div style={{
              fontSize: 11, color: "#9ca3af", marginBottom: 4,
              textAlign: msg.role === "user" ? "right" : "left"
            }}>
              {msg.role === "user" ? "You" : "🤖 Graph Agent"}
            </div>

            {/* Message bubble */}
            <div style={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start"
            }}>
              <div style={{
                background: msg.role === "user" ? "#1f2937" : msg.blocked ? "#fef3c7" : "#f0f4ff",
                color: msg.role === "user" ? "white" : "#1f2937",
                padding: "10px 14px", borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                maxWidth: "90%", fontSize: 13, lineHeight: 1.6,
                border: msg.blocked ? "1px solid #fcd34d" : "none"
              }}>
                <span dangerouslySetInnerHTML={{ __html: formatText(msg.text) }} />

                {/* Table preview */}
                {msg.tableData && msg.tableData.rows.length > 0 && (
                  <div style={{ marginTop: 10, overflowX: "auto" }}>
                    <table style={{ fontSize: 11, borderCollapse: "collapse", width: "100%" }}>
                      <thead>
                        <tr>
                          {msg.tableData.columns.slice(0, 4).map((col) => (
                            <th key={col} style={{
                              padding: "4px 8px", background: "#e0e7ff",
                              color: "#3730a3", fontWeight: 600, textAlign: "left",
                              borderRadius: 4
                            }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {msg.tableData.rows.slice(0, 5).map((row, ri) => (
                          <tr key={ri} style={{ background: ri % 2 === 0 ? "white" : "#f8fafc" }}>
                            {row.slice(0, 4).map((cell, ci) => (
                              <td key={ci} style={{ padding: "4px 8px", color: "#374151" }}>
                                {String(cell || "").slice(0, 20)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {msg.tableData.rows.length > 5 && (
                      <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4, textAlign: "right" }}>
                        + {msg.tableData.rows.length - 5} more rows
                      </div>
                    )}
                  </div>
                )}

                {/* SQL toggle */}
                {msg.sql && !msg.blocked && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{
                      cursor: "pointer", fontSize: 11, color: "#6366f1",
                      userSelect: "none"
                    }}>
                      View SQL ({msg.rowCount ?? 0} rows)
                    </summary>
                    <pre style={{
                      background: "#1e1e2e", color: "#cdd6f4",
                      padding: 10, borderRadius: 6, marginTop: 6,
                      fontSize: 10, overflowX: "auto", whiteSpace: "pre-wrap",
                      maxHeight: 200
                    }}>{msg.sql}</pre>
                  </details>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div style={{ display: "flex", gap: 4, padding: "8px 0" }}>
            {[0, 1, 2].map((i) => (
              <div key={i} style={{
                width: 8, height: 8, borderRadius: "50%",
                background: "#6366f1",
                animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`
              }} />
            ))}
            <style>{`
              @keyframes bounce {
                0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
                40% { transform: translateY(-6px); opacity: 1; }
              }
            `}</style>
          </div>
        )}

        {/* Suggested queries */}
        {showSuggestions && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 8 }}>Try asking:</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {SUGGESTED_QUERIES.map((q, i) => (
                <button key={i} onClick={() => send(q)} style={{
                  background: "white", border: "1px solid #e5e7eb",
                  borderRadius: 8, padding: "8px 12px", cursor: "pointer",
                  fontSize: 12, color: "#4b5563", textAlign: "left",
                  transition: "all 0.15s"
                }}
                  onMouseEnter={(e) => e.target.style.background = "#f0f4ff"}
                  onMouseLeave={(e) => e.target.style.background = "white"}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: "12px 16px", borderTop: "1px solid #e5e7eb",
        display: "flex", gap: 8, alignItems: "flex-end"
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Ask about orders, deliveries, billing..."
          rows={2}
          style={{
            flex: 1, border: "1px solid #e5e7eb", borderRadius: 10,
            padding: "10px 12px", fontSize: 13, outline: "none",
            resize: "none", fontFamily: "inherit", lineHeight: 1.5,
            color: "#1f2937"
          }}
          onFocus={(e) => e.target.style.borderColor = "#6366f1"}
          onBlur={(e) => e.target.style.borderColor = "#e5e7eb"}
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim() ? "#e5e7eb" : "#1f2937",
            color: loading || !input.trim() ? "#9ca3af" : "white",
            border: "none", borderRadius: 10,
            padding: "10px 16px", cursor: loading ? "not-allowed" : "pointer",
            fontSize: 13, fontWeight: 600, transition: "all 0.15s",
            whiteSpace: "nowrap"
          }}
        >
          Send ↵
        </button>
      </div>
    </div>
  );
}
