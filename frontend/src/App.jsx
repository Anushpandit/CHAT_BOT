import { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:8000";

const MODELS = [
  { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
  { id: "llama-3.1-8b-instant",    label: "Llama 3.1 8B (Fast)" },
  { id: "mixtral-8x7b-32768",      label: "Mixtral 8x7B (32K)" },
];

// ── Icons ────────────────────────────────────────────────
const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const DriveIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 20H2l4-8h16l-4 8z"/><path d="M6.5 12L12 2l5.5 10"/>
  </svg>
);
const FileIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
  </svg>
);
const TrashIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
  </svg>
);
const BotIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><line x1="12" y1="7" x2="12" y2="11"/><line x1="8" y1="15" x2="8" y2="15"/><line x1="16" y1="15" x2="16" y2="15"/>
  </svg>
);
const SparkleIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
  </svg>
);

// ── Typing indicator ─────────────────────────────────────
const TypingDots = () => (
  <div style={{ display:"flex", gap:4, alignItems:"center", padding:"4px 0" }}>
    {[0,1,2].map(i => (
      <div key={i} style={{
        width:7, height:7, borderRadius:"50%",
        background:"var(--accent)",
        animation:`bounce 1.2s ease-in-out ${i*0.2}s infinite`,
      }}/>
    ))}
    <style>{`@keyframes bounce{0%,80%,100%{transform:scale(0.6);opacity:0.4}40%{transform:scale(1);opacity:1}}`}</style>
  </div>
);

// ── Message bubble ───────────────────────────────────────
const Message = ({ msg, onSourceClick, activeFilter }) => {
  const isUser = msg.role === "user";
  return (
    <div style={{
      display:"flex", justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom:16, animation:"fadeUp 0.25s ease",
    }}>
      {!isUser && (
        <div style={{
          width:32, height:32, borderRadius:"50%", background:"var(--accent-bg)",
          display:"flex", alignItems:"center", justifyContent:"center",
          marginRight:10, flexShrink:0, marginTop:2,
          border:"1px solid var(--accent)",
        }}>
          <BotIcon />
        </div>
      )}
      <div style={{ maxWidth:"72%", display:"flex", flexDirection:"column", gap:4 }}>
        <div style={{
          padding: isUser ? "10px 16px" : "12px 16px",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          background: isUser ? "var(--accent)" : "var(--msg-bg)",
          color: isUser ? "#fff" : "var(--text)",
          fontSize:14, lineHeight:1.6,
          boxShadow: isUser ? "0 2px 12px rgba(99,102,241,0.3)" : "0 1px 4px rgba(0,0,0,0.08)",
          whiteSpace:"pre-wrap", wordBreak:"break-word",
          border: isUser ? "none" : "1px solid var(--border)",
        }}>
          {msg.content}
        </div>
        {msg.sources?.length > 0 && (
          <div style={{ display:"flex", gap:6, flexWrap:"wrap", paddingLeft:2 }}>
            {msg.sources.map(s => (
              <span 
                key={s} 
                onClick={() => onSourceClick && onSourceClick(s)}
                style={{
                  fontSize:11, padding:"2px 8px", borderRadius:20,
                  background: activeFilter === s ? "var(--accent)" : "var(--tag-bg)",
                  color: activeFilter === s ? "#fff" : "var(--accent)",
                  border:"1px solid var(--accent-light)",
                  display:"flex", alignItems:"center", gap:4,
                  cursor: onSourceClick ? "pointer" : "default",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={e => {
                  if (onSourceClick && activeFilter !== s) {
                    e.target.style.background = "var(--accent-light)";
                  }
                }}
                onMouseLeave={e => {
                  if (onSourceClick && activeFilter !== s) {
                    e.target.style.background = "var(--tag-bg)";
                  }
                }}
              >
                <FileIcon/> {s}
              </span>
            ))}
          </div>
        )}
        {msg.usage && (
          <div style={{ fontSize:11, color:"var(--muted)", paddingLeft:2 }}>
            {msg.usage.total_tokens} tokens · {msg.chunks_used} chunks
          </div>
        )}
      </div>
    </div>
  );
};

// ── Main App ─────────────────────────────────────────────
export default function App() {
  const [driveLink, setDriveLink]   = useState("");
  const [indexing, setIndexing]     = useState(false);
  const [indexStatus, setIndexStatus] = useState(null); // {ok, message}
  const [indexedFiles, setIndexedFiles] = useState([]);

  const [messages, setMessages]     = useState([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [model, setModel]           = useState(MODELS[0].id);
  const [filterFile, setFilterFile] = useState("");

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [messages, loading]);

  // Load existing files on mount
  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/files`);
      const data = await res.json();
      setIndexedFiles(data.files || []);
    } catch {}
  };

  const handleIngest = async () => {
    if (!driveLink.trim()) return;
    setIndexing(true);
    setIndexStatus(null);

    try {
      const res = await fetch(`${API_BASE}/ingest`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ drive_link: driveLink, use_vision: true }),
      });
      const data = await res.json();

      if (res.ok) {
        setIndexStatus({ ok:true, message:`✓ ${data.files_processed} file(s) indexed · ${data.chunks_stored} chunks stored` });
        setIndexedFiles(data.files || []);
        setDriveLink("");
      } else {
        setIndexStatus({ ok:false, message: data.detail || "Ingestion failed." });
      }
    } catch (e) {
      setIndexStatus({ ok:false, message:"Network error — is the backend running?" });
    } finally {
      setIndexing(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIndexing(true);
    setIndexStatus(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (res.ok) {
        setIndexStatus({ ok:true, message:`✓ 1 file indexed · ${data.chunks_stored} chunks stored` });
        setIndexedFiles(data.files || []);
      } else {
        setIndexStatus({ ok:false, message: data.detail || "Upload failed." });
      }
    } catch (e) {
      setIndexStatus({ ok:false, message:"Network error — is the backend running?" });
    } finally {
      setIndexing(false);
      e.target.value = null; // reset input
    }
  };

  const handleDeleteFile = async (fileName) => {
    try {
      await fetch(`${API_BASE}/files/${encodeURIComponent(fileName)}`, { method:"DELETE" });
      setIndexedFiles(prev => prev.filter(f => f !== fileName));
      if (filterFile === fileName) setFilterFile("");
    } catch {}
  };

  const handleSend = async () => {
    let q = input.trim();
    if (!q && filterFile) {
      q = `Can you summarize ${filterFile}?`;
    }
    if (!q || loading) return;

    const userMsg = { role:"user", content:q };
    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    try {
      const history = newHistory
        .slice(-8)
        .map(m => ({ role: m.role, content: m.content }));

      const res = await fetch(`${API_BASE}/chat`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          question: q,
          history: history.slice(0, -1),
          model,
          top_k: 5,
          filter_file: filterFile || null,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessages(prev => [...prev, {
          role:"assistant",
          content: data.answer,
          sources: data.sources,
          chunks_used: data.chunks_used,
          usage: data.usage,
        }]);
      } else {
        setMessages(prev => [...prev, {
          role:"assistant",
          content:`⚠ Error: ${data.detail || "Something went wrong."}`,
        }]);
      }
    } catch {
      setMessages(prev => [...prev, {
        role:"assistant",
        content:"⚠ Network error — is the backend running on port 8000?",
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <>
      <style>{`
        *, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
        :root {
          --bg: #f8fafc;
          --surface: #ffffff;
          --surface2: #f1f5f9;
          --border: #e2e8f0;
          --accent: #111827;
          --accent-light: #11182733;
          --accent-bg: #11182710;
          --text: #0f172a;
          --muted: #64748b;
          --msg-bg: #f1f5f9;
          --tag-bg: #1118270a;
          --danger: #ef4444;
          --success: #10b981;
        }
        body { background:var(--bg); color:var(--text); font-family:'DM Sans',system-ui,sans-serif; }
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Space+Grotesk:wght@600;700&display=swap');
        ::-webkit-scrollbar { width:5px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:var(--border); border-radius:10px; }
        @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
        @keyframes spin { to{transform:rotate(360deg)} }
        textarea:focus, input:focus, select:focus { outline:none; }
      `}</style>

      <div style={{ display:"flex", height:"100vh", overflow:"hidden" }}>

        {/* ── Sidebar ────────────────────────────────────── */}
        <div style={{
          width:280, background:"var(--surface)", borderRight:"1px solid var(--border)",
          display:"flex", flexDirection:"column", flexShrink:0,
        }}>
          {/* Logo */}
          <div style={{ padding:"20px 20px 16px", borderBottom:"1px solid var(--border)" }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <img src="/logo.png" alt="DriveChat Logo" style={{ width: 38, height: 38, objectFit: "contain" }} />
              <div>
                <div style={{ fontFamily:"'Space Grotesk',sans-serif", fontWeight:700, fontSize:15 }}>
                  DriveChat
                </div>
                <div style={{ fontSize:11, color:"var(--muted)" }}>Powered by Groq</div>
              </div>
            </div>
          </div>

          {/* Ingest section */}
          <div style={{ padding:16, borderBottom:"1px solid var(--border)" }}>
            <div style={{ fontSize:11, fontWeight:600, color:"var(--muted)", letterSpacing:"0.08em", textTransform:"uppercase", marginBottom:10 }}>
              Add Documents
            </div>
            <div style={{ position:"relative", marginBottom:8 }}>
              <div style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"var(--muted)" }}>
                <DriveIcon/>
              </div>
              <input
                value={driveLink}
                onChange={e => setDriveLink(e.target.value)}
                onKeyDown={e => e.key==="Enter" && handleIngest()}
                placeholder="Paste Drive URL..."
                style={{
                  width:"100%", padding:"9px 10px 9px 36px",
                  background:"var(--surface2)", border:"1px solid var(--border)",
                  borderRadius:8, color:"var(--text)", fontSize:12,
                }}
              />
            </div>
            <button
              onClick={handleIngest}
              disabled={indexing || !driveLink.trim()}
              style={{
                width:"100%", padding:"9px", borderRadius:8,
                background: indexing ? "var(--border)" : "var(--accent)",
                color:"#fff", border:"none", cursor: indexing ? "not-allowed" : "pointer",
                fontSize:13, fontWeight:600, display:"flex", alignItems:"center", justifyContent:"center", gap:8,
                transition:"opacity 0.15s",
              }}
            >
              {indexing ? (
                <>
                  <div style={{ width:14, height:14, border:"2px solid #ffffff44", borderTopColor:"#fff", borderRadius:"50%", animation:"spin 0.8s linear infinite" }}/>
                  Indexing...
                </>
              ) : "Index Files"}
            </button>

            <div style={{ display:"flex", alignItems:"center", margin:"12px 0", color:"var(--muted)", fontSize:11 }}>
              <div style={{ flex:1, height:1, background:"var(--border)" }}/>
              <div style={{ padding:"0 8px" }}>OR</div>
              <div style={{ flex:1, height:1, background:"var(--border)" }}/>
            </div>

            <input 
              type="file" 
              id="file-upload" 
              style={{ display:"none" }} 
              onChange={handleFileUpload}
            />
            <button
              onClick={() => document.getElementById("file-upload").click()}
              disabled={indexing}
              style={{
                width:"100%", padding:"9px", borderRadius:8,
                background: "transparent",
                color:"var(--text)", border:"1px solid var(--border)", cursor: indexing ? "not-allowed" : "pointer",
                fontSize:13, fontWeight:600, display:"flex", alignItems:"center", justifyContent:"center", gap:8,
                transition:"opacity 0.15s",
              }}
            >
              <FileIcon /> Upload Local File
            </button>
            {indexStatus && (
              <div style={{
                marginTop:8, padding:"7px 10px", borderRadius:6, fontSize:12,
                background: indexStatus.ok ? "#34d39915" : "#f8717115",
                color: indexStatus.ok ? "var(--success)" : "var(--danger)",
                border: `1px solid ${indexStatus.ok ? "#34d39940" : "#f8717140"}`,
              }}>
                {indexStatus.message}
              </div>
            )}
          </div>

          {/* Indexed files */}
          <div style={{ flex:1, overflowY:"auto", padding:16 }}>
            <div style={{ fontSize:11, fontWeight:600, color:"var(--muted)", letterSpacing:"0.08em", textTransform:"uppercase", marginBottom:10 }}>
              Indexed Files ({indexedFiles.length})
            </div>
            {indexedFiles.length === 0 ? (
              <div style={{ fontSize:12, color:"var(--muted)", textAlign:"center", paddingTop:20 }}>
                No files indexed yet
              </div>
            ) : (
              indexedFiles.map(f => (
                <div
                  key={f}
                  onClick={() => setFilterFile(filterFile === f ? "" : f)}
                  style={{
                    display:"flex", alignItems:"center", justifyContent:"space-between",
                    padding:"7px 9px", borderRadius:7, marginBottom:4, cursor:"pointer",
                    background: filterFile===f ? "var(--accent-bg)" : "transparent",
                    border: filterFile===f ? "1px solid var(--accent-light)" : "1px solid transparent",
                    transition:"all 0.15s",
                  }}
                >
                  <div style={{ display:"flex", alignItems:"center", gap:7, overflow:"hidden" }}>
                    <div style={{ color:"var(--accent)", flexShrink:0 }}><FileIcon/></div>
                    <span style={{ fontSize:12, color:"var(--text)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{f}</span>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); handleDeleteFile(f); }}
                    style={{ background:"none", border:"none", cursor:"pointer", color:"var(--muted)", padding:2, flexShrink:0, display:"flex" }}
                  >
                    <TrashIcon/>
                  </button>
                </div>
              ))
            )}
          </div>

          {/* Model selector */}
          <div style={{ padding:16, borderTop:"1px solid var(--border)" }}>
            <div style={{ fontSize:11, fontWeight:600, color:"var(--muted)", letterSpacing:"0.08em", textTransform:"uppercase", marginBottom:8 }}>
              Model
            </div>
            <select
              value={model}
              onChange={e => setModel(e.target.value)}
              style={{
                width:"100%", padding:"8px 10px",
                background:"var(--surface2)", border:"1px solid var(--border)",
                borderRadius:8, color:"var(--text)", fontSize:12, cursor:"pointer",
              }}
            >
              {MODELS.map(m => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
            {filterFile && (
              <div style={{ marginTop:8, fontSize:11, color:"var(--accent)", display:"flex", alignItems:"center", gap:4 }}>
                <FileIcon/> Filtering: {filterFile}
              </div>
            )}
          </div>
        </div>

        {/* ── Chat Area ──────────────────────────────────── */}
        <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

          {/* Header */}
          <div style={{
            padding:"16px 24px", borderBottom:"1px solid var(--border)",
            display:"flex", alignItems:"center", justifyContent:"space-between",
            background:"var(--surface)",
          }}>
            <div>
              <div style={{ fontFamily:"'Space Grotesk',sans-serif", fontWeight:700, fontSize:16 }}>
                Document Chat
              </div>
              <div style={{ fontSize:12, color:"var(--muted)" }}>
                {indexedFiles.length > 0
                  ? `${indexedFiles.length} file(s) ready · Ask anything`
                  : "Index a Drive link to get started"}
              </div>
            </div>
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                style={{
                  padding:"6px 14px", borderRadius:7,
                  background:"var(--surface2)", border:"1px solid var(--border)",
                  color:"var(--muted)", fontSize:12, cursor:"pointer",
                }}
              >
                Clear chat
              </button>
            )}
          </div>

          {/* Messages */}
          <div style={{ flex:1, overflowY:"auto", padding:"24px 28px" }}>
            {messages.length === 0 ? (
              <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"100%", gap:12 }}>
                <img src="/logo.png" alt="DriveChat Logo" style={{ width: 72, height: 72, objectFit: "contain", marginBottom: 8 }} />
                <div style={{ fontFamily:"'Space Grotesk',sans-serif", fontWeight:700, fontSize:18 }}>
                  What would you like to know?
                </div>
                <div style={{ fontSize:14, color:"var(--muted)", textAlign:"center", maxWidth:380 }}>
                  Index a Google Drive link from the sidebar,<br/>then ask questions about your documents.
                </div>
                {indexedFiles.length > 0 && (
                  <div style={{ display:"flex", flexWrap:"wrap", gap:8, marginTop:8, justifyContent:"center", maxWidth:500 }}>
                    {[
                      "Summarize all documents",
                      "What are the key points?",
                      "List all important dates",
                      "What data is in the spreadsheet?",
                    ].map(suggestion => (
                      <button
                        key={suggestion}
                        onClick={() => { setInput(suggestion); inputRef.current?.focus(); }}
                        style={{
                          padding:"7px 14px", borderRadius:20, fontSize:13,
                          background:"var(--surface2)", border:"1px solid var(--border)",
                          color:"var(--text)", cursor:"pointer",
                          transition:"border-color 0.15s",
                        }}
                        onMouseEnter={e => e.target.style.borderColor="var(--accent)"}
                        onMouseLeave={e => e.target.style.borderColor="var(--border)"}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <Message 
                    key={i} 
                    msg={msg} 
                    onSourceClick={(s) => setFilterFile(filterFile === s ? "" : s)}
                    activeFilter={filterFile}
                  />
                ))}
                {loading && (
                  <div style={{ display:"flex", alignItems:"flex-start", marginBottom:16 }}>
                    <div style={{
                      width:32, height:32, borderRadius:"50%", background:"var(--accent-bg)",
                      display:"flex", alignItems:"center", justifyContent:"center",
                      marginRight:10, border:"1px solid var(--accent)",
                    }}>
                      <BotIcon/>
                    </div>
                    <div style={{
                      padding:"10px 16px", borderRadius:"18px 18px 18px 4px",
                      background:"var(--msg-bg)", border:"1px solid var(--border)",
                    }}>
                      <TypingDots/>
                    </div>
                  </div>
                )}
                <div ref={bottomRef}/>
              </>
            )}
          </div>

          {/* Input area */}
          <div style={{ padding:"16px 24px", borderTop:"1px solid var(--border)", background:"var(--surface)" }}>
            <div style={{
              display:"flex", gap:10, alignItems:"flex-end",
              background:"var(--surface2)", borderRadius:14,
              border:"1px solid var(--border)", padding:"10px 14px",
              transition:"border-color 0.15s",
            }}
              onFocus={() => {}}
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={filterFile ? `Ask a question about ${filterFile} (or press Send to summarize)...` : indexedFiles.length > 0 ? "Ask a question about your documents..." : "Index a Drive link first..."}
                disabled={loading || indexedFiles.length === 0}
                rows={1}
                style={{
                  flex:1, background:"transparent", border:"none",
                  color:"var(--text)", fontSize:14, lineHeight:1.6,
                  resize:"none", maxHeight:120, overflow:"auto",
                  fontFamily:"inherit",
                }}
                onInput={e => {
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
                }}
              />
              <button
                onClick={handleSend}
                disabled={loading || (!input.trim() && !filterFile) || indexedFiles.length === 0}
                style={{
                  width:36, height:36, borderRadius:9, border:"none",
                  background: (loading || (!input.trim() && !filterFile) || indexedFiles.length===0) ? "var(--border)" : "var(--accent)",
                  color: "#fff", cursor: (loading || (!input.trim() && !filterFile)) ? "not-allowed" : "pointer",
                  display:"flex", alignItems:"center", justifyContent:"center",
                  flexShrink:0, transition:"background 0.15s",
                }}
              >
                <SendIcon/>
              </button>
            </div>
            <div style={{ fontSize:11, color:"var(--muted)", textAlign:"center", marginTop:8 }}>
              Enter to send · Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
