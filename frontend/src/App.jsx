import { useState, useRef, useEffect, useCallback } from "react";
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { jwtDecode } from "jwt-decode";
import CitationPanel from "./CitationPanel";
import FollowupSuggestions from "./FollowupSuggestions";

const API = "http://localhost:8000";

const MODELS = [
  { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
  { id: "llama-3.1-8b-instant",    label: "Llama 3.1 8B ⚡" },
  { id: "mixtral-8x7b-32768",      label: "Mixtral 32K" },
];


// ── Icons ────────────────────────────────────────────────────────
const I = {
  send: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>,
  mic:  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>,
  stop: <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2"/></svg>,
  play: <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  vol:  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>,
  plus: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  trash:<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>,
  edit: <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
  file: <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>,
  bot:  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><line x1="12" y1="7" x2="12" y2="11"/></svg>,
  link: <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>,
  chat: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>,
};

// ── Dots loader ──────────────────────────────────────────────────
const Dots = () => (
  <div style={{display:"flex",gap:4,padding:"4px 0"}}>
    {[0,1,2].map(i=>(
      <div key={i} style={{width:7,height:7,borderRadius:"50%",background:"var(--accent)",
        animation:`bounce 1.2s ${i*.2}s ease-in-out infinite`}}/>
    ))}
    <style>{`@keyframes bounce{0%,80%,100%{transform:scale(.6);opacity:.4}40%{transform:scale(1);opacity:1}}`}</style>
  </div>
);

// ── Waveform animation while recording ───────────────────────────
const Waveform = () => (
  <div style={{display:"flex",gap:3,alignItems:"center",height:20}}>
    {[1,3,2,4,2,3,1].map((h,i)=>(
      <div key={i} style={{width:3,height:h*4,borderRadius:2,background:"var(--danger)",
        animation:`wave 0.8s ${i*.1}s ease-in-out infinite`}}/>
    ))}
    <style>{`@keyframes wave{0%,100%{transform:scaleY(.5)}50%{transform:scaleY(1.5)}}`}</style>
  </div>
);

// ── Message component ─────────────────────────────────────────────
const Msg = ({ m, msgId, activeSpeechId, onSpeak, onStop }) => {
  const isUser = m.role === "user";
  const isSpeaking = activeSpeechId === msgId;

  const handleSpeak = () => {
    if (isSpeaking) { 
      onStop(); 
    } else {
      onSpeak(msgId, m.content);
    }
  };

  return (
    <div style={{display:"flex",justifyContent:isUser?"flex-end":"flex-start",marginBottom:18,animation:"fadeUp .2s ease"}}>
      {!isUser && (
        <div style={{width:30,height:30,borderRadius:"50%",background:"var(--accent-dim)",
          border:"1px solid var(--accent)",display:"flex",alignItems:"center",
          justifyContent:"center",marginRight:9,flexShrink:0,marginTop:2}}>
          {I.bot}
        </div>
      )}
      <div style={{maxWidth:"74%",display:"flex",flexDirection:"column",gap:5}}>
        {isUser ? (
          <div style={{
            padding:"10px 15px",
            borderRadius:"16px 16px 4px 16px",
            background:"var(--accent)",
            color:"#fff",fontSize:14,lineHeight:1.65,
            whiteSpace:"pre-wrap",wordBreak:"break-word",
            border:"none",
            boxShadow:"0 2px 14px rgba(99,102,241,.3)",
          }}>{m.content}</div>
        ) : (
          <CitationPanel answer={m.content} citations={m.citations || []} />
        )}

        <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
          {m.sources?.map(s=>(
            <span key={s} style={{fontSize:11,padding:"2px 8px",borderRadius:20,
              background:"var(--accent-dim)",color:"var(--accent)",
              border:"1px solid var(--accent-border)",display:"flex",alignItems:"center",gap:4}}>
              {I.file} {s}
            </span>
          ))}
          {!isUser && (
            <button onClick={handleSpeak} style={{background:"none",border:"1px solid var(--border)",
              borderRadius:6,padding:"3px 8px",cursor:"pointer",color:"var(--muted)",
              display:"flex",alignItems:"center",gap:4,fontSize:11}}>
              {isSpeaking ? I.stop : I.play}
              {isSpeaking ? "Stop" : "Speak"}
            </button>
          )}
          {m.chunks_used > 0 && (
            <span style={{fontSize:11,color:"var(--muted)"}}>
              {m.chunks_used} chunks · {(m.prompt_tokens||0)+(m.completion_tokens||0)} tokens
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Main App ──────────────────────────────────────────────────────
function MainApp({ user, onLogout }) {
  // Global fetch interceptor to inject email header
  useEffect(() => {
    const originalFetch = window.fetch;
    window.fetch = async (url, options = {}) => {
      if (typeof url === "string" && url.startsWith(API)) {
        options.headers = { ...options.headers, "X-User-Email": user?.email || "anonymous" };
      }
      return originalFetch(url, options);
    };
    return () => { window.fetch = originalFetch; };
  }, [user]);

  // sessions
  const [sessions, setSessions]     = useState([]);
  const [activeId, setActiveId]     = useState(null);
  const [messages, setMessages]     = useState([]);
  const [editingId, setEditingId]   = useState(null);
  const [editTitle, setEditTitle]   = useState("");

  // chat
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [model, setModel]           = useState(MODELS[0].id);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [voice, setVoice]           = useState("");
  const [systemVoices, setSystemVoices] = useState([]);
  const [activeSpeechId, setActiveSpeechId] = useState(null);

  // voice recording
  const [recording, setRecording]   = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);

  // drive ingest
  const [driveLink, setDriveLink]   = useState("");
  const [indexing, setIndexing]     = useState(false);
  const [indexMsg, setIndexMsg]     = useState(null);
  const [indexedFiles, setIndexedFiles] = useState([]);

  // tabs
  const [sideTab, setSideTab]       = useState("history"); // "history" | "files"

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:"smooth"}); }, [messages, loading]);
  useEffect(()=>{ loadSessions(); loadFiles(); }, []);
  
  useEffect(()=>{
    const loadSystemVoices = () => {
      const vs = window.speechSynthesis.getVoices();
      if (vs.length > 0) {
        const premiumNames = ["Samantha", "Daniel", "Karen", "Moira", "Rishi", "Tessa", "Alex", "Victoria", "Fiona", "Veena", "Google US English", "Google UK English Male", "Google UK English Female", "Microsoft David", "Microsoft Zira", "Microsoft Mark"];
        const filtered = vs.filter(v => premiumNames.some(p => v.name.includes(p)));
        const finalVoices = filtered.length > 0 ? filtered : vs.filter(v => v.lang.startsWith("en")).slice(0, 5);
        setSystemVoices(finalVoices);
        setVoice(prev => {
          if (!prev || prev === "nova") {
            const v = vs.find(v => v.name.includes("Samantha") || v.name.includes("Google") || v.lang.startsWith("en")) || vs[0];
            return v ? v.name : "";
          }
          return prev;
        });
      }
    };
    loadSystemVoices();
    window.speechSynthesis.onvoiceschanged = loadSystemVoices;
  }, []);

  // ── Session loaders ───────────────────────────────────────────
  const loadSessions = async () => {
    try {
      const r = await fetch(`${API}/sessions`);
      const d = await r.json();
      setSessions(d);
    } catch {}
  };

  const loadFiles = async () => {
    try {
      const r = await fetch(`${API}/files`);
      const d = await r.json();
      setIndexedFiles(d.files || []);
    } catch {}
  };

  const openSession = async (id) => {
    setActiveId(id);
    try {
      const r = await fetch(`${API}/sessions/${id}`);
      const d = await r.json();
      setMessages(d.messages || []);
    } catch {}
  };

  const newSession = async () => {
    const r = await fetch(`${API}/sessions`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ title:"New Chat", model }),
    });
    const s = await r.json();
    setSessions(prev => [s, ...prev]);
    setActiveId(s.id);
    setMessages([]);
  };

  const deleteSession = async (id, e) => {
    e.stopPropagation();
    await fetch(`${API}/sessions/${id}`, { method:"DELETE" });
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeId === id) { setActiveId(null); setMessages([]); }
  };

  const saveRename = async (id) => {
    await fetch(`${API}/sessions/${id}/rename`, {
      method:"PATCH", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ title: editTitle }),
    });
    setSessions(prev => prev.map(s => s.id===id ? {...s, title: editTitle} : s));
    setEditingId(null);
  };

  // ── Ingest ────────────────────────────────────────────────────
  const handleIngest = async () => {
    if (!driveLink.trim()) return;
    setIndexing(true); setIndexMsg(null);
    try {
      const r = await fetch(`${API}/ingest`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ drive_link: driveLink, use_vision: true }),
      });
      const d = await r.json();
      if (r.ok) {
        setIndexMsg({ ok:true, text:`✓ ${d.files_processed} file(s) · ${d.chunks_stored} chunks` });
        setIndexedFiles(d.files || []);
        setDriveLink("");
        
        if (activeId && d.files && d.files.length > 0) {
          const s = sessions.find(x => x.id === activeId);
          if (s && s.title === "New Chat") {
            const newTitle = `Drive: ${d.files[0]}`.slice(0, 60) + (d.files[0].length > 53 ? "..." : "");
            fetch(`${API}/sessions/${activeId}/rename`, {
              method:"PATCH", headers:{"Content-Type":"application/json"},
              body: JSON.stringify({ title: newTitle })
            });
            setSessions(prev => prev.map(x => x.id === activeId ? {...x, title: newTitle} : x));
          }
        }
      } else {
        setIndexMsg({ ok:false, text: d.detail || "Failed." });
      }
    } catch { setIndexMsg({ ok:false, text:"Network error." }); }
    finally { setIndexing(false); }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIndexing(true);
    setIndexMsg(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const r = await fetch(`${API}/upload`, {
        method: "POST",
        body: formData,
      });
      const d = await r.json();

      if (r.ok) {
        setIndexMsg({ ok:true, text:`✓ 1 file indexed · ${d.chunks_stored} chunks` });
        setIndexedFiles(d.files || []);
        
        if (activeId) {
          const s = sessions.find(x => x.id === activeId);
          if (s && s.title === "New Chat") {
            const newTitle = `Doc: ${file.name}`.slice(0, 60) + (file.name.length > 55 ? "..." : "");
            fetch(`${API}/sessions/${activeId}/rename`, {
              method:"PATCH", headers:{"Content-Type":"application/json"},
              body: JSON.stringify({ title: newTitle })
            });
            setSessions(prev => prev.map(x => x.id === activeId ? {...x, title: newTitle} : x));
          }
        }
      } else {
        setIndexMsg({ ok:false, text: d.detail || "Upload failed." });
      }
    } catch {
      setIndexMsg({ ok:false, text:"Network error." });
    } finally {
      setIndexing(false);
      e.target.value = null; // reset input
    }
  };

  // ── Chat ──────────────────────────────────────────────────────
  const sendMessage = async (text) => {
    if (!text.trim() || loading || !activeId) return;
    const isFirstMessage = messages.length === 0;
    const userMsg = { role:"user", content:text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    if (isFirstMessage) {
      const s = sessions.find(x => x.id === activeId);
      if (s && s.title === "New Chat") {
        const newTitle = text.slice(0, 60) + (text.length > 60 ? "..." : "");
        setSessions(prev => prev.map(x => x.id === activeId ? {...x, title: newTitle} : x));
      }
    }
    setLoading(true);

    try {
      const historyPayload = messages.map(m => ({ role: m.role, content: m.content })).slice(-10);
      const r = await fetch(`${API}/chat/cited`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ 
          question: text, 
          session_id: activeId, 
          history: historyPayload, 
          model,
          enable_followups: true,
          followup_model: "llama-3.1-8b-instant"
        }),
      });
      const d = await r.json();
      if (r.ok) {
        const newAssistantMsg = {
          role:"assistant", content: d.answer,
          citations: d.citations,
          sources: d.sources, chunks_used: d.chunks_used,
          prompt_tokens: d.usage?.prompt_tokens,
          completion_tokens: d.usage?.completion_tokens,
          followups: d.followups,
          id: d.message_id || Date.now(), // Fallback if no ID
        };
        setMessages(prev => [...prev, newAssistantMsg]);
        setSessions(prev => prev.map(s => s.id===activeId ? {...s, message_count: s.message_count+2} : s));
        
        if (ttsEnabled) {
          speakText(newAssistantMsg.id, d.answer);
        }
      } else {
        setMessages(prev => [...prev, { role:"assistant", content:`⚠ ${d.detail}` }]);
      }
    } catch {
      setMessages(prev => [...prev, { role:"assistant", content:"⚠ Network error." }]);
    } finally {
      setLoading(false);
      setTimeout(()=>inputRef.current?.focus(), 50);
    }
  };

  const handleKey = (e) => {
    if (e.key==="Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  // ── Voice recording ───────────────────────────────────────────
  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
    const mr = new MediaRecorder(stream, { mimeType });
    audioChunksRef.current = [];
    mr.ondataavailable = e => audioChunksRef.current.push(e.data);
    mr.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      setTranscribing(true);
      const blob = new Blob(audioChunksRef.current, { type: mimeType });
      const form = new FormData();
      form.append("audio", blob, mimeType === "audio/webm" ? "audio.webm" : "audio.mp4");
      try {
        const r = await fetch(`${API}/voice/transcribe`, { method:"POST", body: form });
        const d = await r.json();
        if (d.text) { setInput(d.text); inputRef.current?.focus(); }
      } catch {}
      setTranscribing(false);
    };
    mr.start();
    mediaRecorderRef.current = mr;
    setRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  // ── Speak text via Native Web Speech API ────────────────────────
  const speakText = (id, text) => {
    window.speechSynthesis.cancel();
    setActiveSpeechId(id);
    const u = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    const voiceObj = voices.find(v => v.name === voice) || voices.find(v => v.name.includes("Samantha") || v.name.includes("Google") || v.lang.startsWith("en"));
    if (voiceObj) u.voice = voiceObj;
    
    u.rate = 1.05;
    u.onend = () => setActiveSpeechId(null);
    u.onerror = () => setActiveSpeechId(null);
    window.speechSynthesis.speak(u);
  };

  const stopSpeech = () => {
    window.speechSynthesis.cancel();
    setActiveSpeechId(null);
  };

  // ─────────────────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        :root{
          --bg:#f8f9fa; --surface:#ffffff; --surface2:#f1f3f5; --surface3:#e9ecef;
          --border:#dee2e6; --accent:#6366f1; --accent-dim:#6366f115;
          --accent-border:#6366f140; --text:#212529; --muted:#6c757d;
          --danger:#ef4444; --success:#10b981; --warn:#f59e0b;
        }
        body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;}
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:var(--border);border-radius:10px}
        input,textarea,select{font-family:inherit}
        input:focus,textarea:focus,select:focus{outline:none}
        @keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes pulse{0%,100%{opacity:.6}50%{opacity:1}}
      `}</style>

      <div style={{display:"flex",height:"100vh",overflow:"hidden"}}>

        {/* ── LEFT SIDEBAR ───────────────────────────────────── */}
        <div style={{width:260,background:"var(--surface)",borderRight:"1px solid var(--border)",
          display:"flex",flexDirection:"column",flexShrink:0}}>

          {/* Logo */}
          <div style={{padding:"18px 16px 14px",borderBottom:"1px solid var(--border)",
            display:"flex",alignItems:"center",justifyContent:"space-between"}}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <img src="/logo.png" alt="DriveChat Logo" style={{ width: 38, height: 38, objectFit: "contain" }} />
              <div>
                <div style={{fontWeight:800,fontSize:16,letterSpacing:"-.02em"}}>DriveChat</div>
              </div>
            </div>
            <button onClick={newSession} style={{
              width:30,height:30,borderRadius:8,background:"var(--accent)",border:"none",
              color:"#fff",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"}}
              title="New chat">
              {I.plus}
            </button>
          </div>

          {/* Tabs */}
          <div style={{display:"flex",borderBottom:"1px solid var(--border)"}}>
            {[{k:"history",label:"Chats",icon:I.chat},{k:"files",label:"Files",icon:I.file}].map(t=>(
              <button key={t.k} onClick={()=>setSideTab(t.k)} style={{
                flex:1,padding:"10px 0",background:"none",border:"none",cursor:"pointer",
                color: sideTab===t.k ? "var(--accent)" : "var(--muted)",
                borderBottom: sideTab===t.k ? "2px solid var(--accent)" : "2px solid transparent",
                fontSize:12,fontWeight:600,display:"flex",alignItems:"center",
                justifyContent:"center",gap:5,fontFamily:"inherit",
              }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{flex:1,overflowY:"auto",padding:10}}>

            {sideTab==="history" && (
              sessions.length===0
              ? <div style={{color:"var(--muted)",fontSize:12,textAlign:"center",paddingTop:20}}>No chats yet</div>
              : sessions.map(s=>(
                <div key={s.id} onClick={()=>openSession(s.id)}
                  style={{
                    padding:"9px 10px",borderRadius:8,marginBottom:3,cursor:"pointer",
                    background: activeId===s.id ? "var(--accent-dim)" : "transparent",
                    border: activeId===s.id ? "1px solid var(--accent-border)" : "1px solid transparent",
                    display:"flex",alignItems:"center",gap:6,
                  }}>
                  <div style={{color:"var(--muted)",flexShrink:0}}>{I.chat}</div>
                  {editingId===s.id ? (
                    <input autoFocus value={editTitle}
                      onChange={e=>setEditTitle(e.target.value)}
                      onBlur={()=>saveRename(s.id)}
                      onKeyDown={e=>e.key==="Enter"&&saveRename(s.id)}
                      onClick={e=>e.stopPropagation()}
                      style={{flex:1,background:"var(--surface3)",border:"1px solid var(--accent)",
                        borderRadius:4,padding:"2px 6px",color:"var(--text)",fontSize:12}}/>
                  ) : (
                    <span style={{flex:1,fontSize:12,overflow:"hidden",textOverflow:"ellipsis",
                      whiteSpace:"nowrap",color:"var(--text)"}}>{s.title}</span>
                  )}
                  <div style={{display:"flex",gap:2,flexShrink:0}}>
                    <button onClick={e=>{e.stopPropagation();setEditingId(s.id);setEditTitle(s.title)}}
                      style={{background:"none",border:"none",cursor:"pointer",color:"var(--muted)",padding:2,display:"flex"}}>
                      {I.edit}
                    </button>
                    <button onClick={e=>deleteSession(s.id,e)}
                      style={{background:"none",border:"none",cursor:"pointer",color:"var(--muted)",padding:2,display:"flex"}}>
                      {I.trash}
                    </button>
                  </div>
                </div>
              ))
            )}

            {sideTab==="files" && (
              <div>
                {/* Drive ingest */}
                <div style={{marginBottom:12}}>
                  <div style={{fontSize:11,fontWeight:600,color:"var(--muted)",letterSpacing:".07em",
                    textTransform:"uppercase",marginBottom:8}}>Index Drive Link</div>
                  <input value={driveLink} onChange={e=>setDriveLink(e.target.value)}
                    onKeyDown={e=>e.key==="Enter"&&handleIngest()}
                    placeholder="Paste Drive URL..."
                    style={{width:"100%",padding:"8px 10px",background:"var(--surface2)",
                      border:"1px solid var(--border)",borderRadius:7,color:"var(--text)",fontSize:12,marginBottom:6}}/>
                  <button onClick={handleIngest} disabled={indexing||!driveLink.trim()} style={{
                    width:"100%",padding:"8px",borderRadius:7,border:"none",
                    background:indexing||!driveLink.trim()?"var(--border)":"var(--accent)",
                    color:"#fff",cursor:indexing?"not-allowed":"pointer",fontSize:12,fontWeight:600,
                    display:"flex",alignItems:"center",justifyContent:"center",gap:6,fontFamily:"inherit",
                  }}>
                    {indexing
                      ? <><div style={{width:12,height:12,border:"2px solid #fff4",borderTopColor:"#fff",
                          borderRadius:"50%",animation:"spin .8s linear infinite"}}/>Indexing...</>
                      : <>{I.link} Index Files</>}
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
                    {I.file} Upload Local File
                  </button>

                  {indexMsg && (
                    <div style={{marginTop:6,padding:"6px 9px",borderRadius:6,fontSize:11,
                      background:indexMsg.ok?"#5eead415":"#f0629215",
                      color:indexMsg.ok?"var(--success)":"var(--danger)",
                      border:`1px solid ${indexMsg.ok?"#5eead440":"#f0629240"}`}}>
                      {indexMsg.text}
                    </div>
                  )}
                </div>

                {/* File list */}
                <div style={{fontSize:11,fontWeight:600,color:"var(--muted)",letterSpacing:".07em",
                  textTransform:"uppercase",marginBottom:8}}>
                  Indexed ({indexedFiles.length})
                </div>
                {indexedFiles.map(f=>(
                  <div key={f} style={{display:"flex",alignItems:"center",gap:6,padding:"6px 8px",
                    borderRadius:6,marginBottom:3,background:"var(--surface2)",
                    border:"1px solid var(--border)"}}>
                    <div style={{color:"var(--accent)",flexShrink:0}}>{I.file}</div>
                    <span style={{flex:1,fontSize:11,overflow:"hidden",textOverflow:"ellipsis",
                      whiteSpace:"nowrap",color:"var(--text)"}}>{f}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Settings */}
          <div style={{padding:12,borderTop:"1px solid var(--border)",display:"flex",flexDirection:"column",gap:8}}>
            <div style={{display:"flex",gap:8,alignItems:"center"}}>
              <select value={model} onChange={e=>setModel(e.target.value)} style={{
                flex:1,padding:"7px 8px",background:"var(--surface2)",border:"1px solid var(--border)",
                borderRadius:7,color:"var(--text)",fontSize:11,cursor:"pointer",fontFamily:"inherit"}}>
                {MODELS.map(m=><option key={m.id} value={m.id}>{m.label}</option>)}
              </select>
            </div>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between"}}>
              <div style={{display:"flex",alignItems:"center",gap:6}}>
                <div style={{color:"var(--muted)"}}>{I.vol}</div>
                <span style={{fontSize:11,color:"var(--muted)"}}>Auto TTS</span>
              </div>
              <button onClick={()=>setTtsEnabled(p=>!p)} style={{
                width:36,height:20,borderRadius:10,border:"none",cursor:"pointer",
                background:ttsEnabled?"var(--accent)":"var(--surface3)",
                position:"relative",transition:"background .2s"}}>
                <div style={{
                  position:"absolute",top:3,left:ttsEnabled?18:3,width:14,height:14,
                  borderRadius:"50%",background:"#fff",transition:"left .2s"}}/>
              </button>
            </div>
            {ttsEnabled && (
              <select value={voice} onChange={e=>setVoice(e.target.value)} style={{
                padding:"6px 8px",background:"var(--surface2)",border:"1px solid var(--border)",
                borderRadius:7,color:"var(--text)",fontSize:11,cursor:"pointer",fontFamily:"inherit"}}>
                {systemVoices.map(v=><option key={v.name} value={v.name}>{v.name} ({v.lang})</option>)}
              </select>
            )}
            
            {/* User Profile / Logout */}
            <div style={{marginTop: 8, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"8px", background:"var(--surface3)", borderRadius:8}}>
               <div style={{display:"flex", alignItems:"center", gap:6, overflow:"hidden"}}>
                 {user?.picture && <img src={user.picture} style={{width:20, height:20, borderRadius:"50%"}} />}
                 <div style={{fontSize:11, color:"var(--text)", whiteSpace:"nowrap", textOverflow:"ellipsis", overflow:"hidden"}}>
                    {user?.name || user?.email}
                 </div>
               </div>
               <button onClick={onLogout} style={{background:"none", border:"none", color:"var(--danger)", cursor:"pointer", fontSize:11, fontWeight:600}}>
                 Logout
               </button>
            </div>
          </div>
        </div>

        {/* ── MAIN CHAT AREA ──────────────────────────────────── */}
        <div style={{flex:1,display:"flex",flexDirection:"column",overflow:"hidden"}}>

          {/* Header */}
          <div style={{padding:"14px 24px",borderBottom:"1px solid var(--border)",
            background:"var(--surface)",display:"flex",alignItems:"center",justifyContent:"space-between"}}>
            <div>
              <div style={{fontWeight:700,fontSize:15}}>
                {sessions.find(s=>s.id===activeId)?.title || "Drive Chatbot"}
              </div>
              <div style={{fontSize:11,color:"var(--muted)",fontFamily:"'DM Mono',monospace"}}>
                {activeId ? `${messages.length} messages` : "Select or create a chat"}
              </div>
            </div>
            {activeId && (
              <button onClick={async()=>{
                await fetch(`${API}/sessions/${activeId}/messages`,{method:"DELETE"});
                setMessages([]);
              }} style={{
                padding:"6px 12px",borderRadius:6,background:"#ef444415",
                border:"1px solid #ef444440",color:"var(--danger)",fontSize:12,fontWeight:600,
                cursor:"pointer",display:"flex",alignItems:"center",gap:6,
                fontFamily:"inherit",transition:"background .15s"
              }}
              onMouseEnter={e=>e.currentTarget.style.background="#ef444425"}
              onMouseLeave={e=>e.currentTarget.style.background="#ef444415"}
              title="Clear chat history">
                {I.trash} Clear
              </button>
            )}
          </div>

          {/* Messages */}
          <div style={{flex:1,overflowY:"auto",padding:"24px 28px"}}>
            {!activeId ? (
              <div style={{display:"flex",flexDirection:"column",alignItems:"center",
                justifyContent:"center",height:"100%",gap:14}}>
                <img src="/logo.png" alt="DriveChat Logo" style={{ width: 64, height: 64, objectFit: "contain" }} />
                <div style={{fontWeight:800,fontSize:20}}>Welcome to DriveChat</div>
                <div style={{color:"var(--muted)",fontSize:13,textAlign:"center",maxWidth:360}}>
                  Create a new chat, index your Google Drive files,<br/>then ask questions with voice or text.
                </div>
                <button onClick={newSession} style={{padding:"10px 22px",borderRadius:9,
                  background:"var(--accent)",border:"none",color:"#fff",cursor:"pointer",
                  fontWeight:700,fontSize:13,fontFamily:"inherit"}}>
                  + New Chat
                </button>
              </div>
            ) : messages.length===0 ? (
              <div style={{display:"flex",flexDirection:"column",alignItems:"center",
                justifyContent:"center",height:"100%",gap:12}}>
                <img src="/logo.png" alt="DriveChat Logo" style={{ width: 56, height: 56, objectFit: "contain" }} />
                <div style={{color:"var(--muted)",fontSize:13}}>Ask your first question below</div>
                <div style={{display:"flex",flexWrap:"wrap",gap:8,justifyContent:"center",maxWidth:460}}>
                  {["Summarize all documents","What are the key findings?",
                    "List all important dates","Explain the data in the spreadsheet"].map(s=>(
                    <button key={s} onClick={()=>sendMessage(s)} style={{
                      padding:"7px 14px",borderRadius:20,fontSize:12,
                      background:"var(--surface2)",border:"1px solid var(--border)",
                      color:"var(--text)",cursor:"pointer",fontFamily:"inherit",
                      transition:"border-color .15s"}}
                      onMouseEnter={e=>e.target.style.borderColor="var(--accent)"}
                      onMouseLeave={e=>e.target.style.borderColor="var(--border)"}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((m,i)=>(
                  <div key={i}>
                    <Msg m={m} msgId={m.id || i} activeSpeechId={activeSpeechId} onSpeak={speakText} onStop={stopSpeech} />
                    {!loading && m.role === "assistant" && i === messages.length - 1 && (
                      <FollowupSuggestions
                        suggestions={m.followups || []}
                        onSelect={sendMessage}
                        isLoading={false}
                      />
                    )}
                  </div>
                ))}
                {loading && (
                  <div style={{display:"flex",alignItems:"flex-start",marginBottom:16}}>
                    <div style={{width:30,height:30,borderRadius:"50%",background:"var(--accent-dim)",
                      border:"1px solid var(--accent)",display:"flex",alignItems:"center",
                      justifyContent:"center",marginRight:9}}>
                      {I.bot}
                    </div>
                    <div style={{padding:"10px 14px",borderRadius:"14px 14px 14px 4px",
                      background:"var(--surface2)",border:"1px solid var(--border)"}}>
                      <Dots/>
                    </div>
                  </div>
                )}
                {loading && (
                  <FollowupSuggestions
                    suggestions={[]}
                    isLoading={true}
                  />
                )}
                <div ref={bottomRef}/>
              </>
            )}
          </div>

          {/* Input bar */}
          {activeId && (
            <div style={{padding:"14px 22px",borderTop:"1px solid var(--border)",background:"var(--surface)"}}>
              <div style={{display:"flex",gap:8,alignItems:"flex-end",
                background:"var(--surface2)",borderRadius:14,
                border:"1px solid var(--border)",padding:"10px 12px"}}>

                {/* Voice record button */}
                <button
                  onMouseDown={startRecording}
                  onMouseUp={stopRecording}
                  onTouchStart={startRecording}
                  onTouchEnd={stopRecording}
                  disabled={transcribing}
                  style={{
                    width:34,height:34,borderRadius:9,border:"none",cursor:"pointer",
                    background: recording ? "var(--danger)" : "var(--surface3)",
                    color: recording ? "#fff" : "var(--muted)",
                    display:"flex",alignItems:"center",justifyContent:"center",
                    flexShrink:0,animation:recording?"pulse 1s infinite":"none",
                    transition:"all .15s",
                  }}
                  title="Hold to record">
                  {transcribing
                    ? <div style={{width:12,height:12,border:"2px solid #fff4",borderTopColor:"var(--accent)",borderRadius:"50%",animation:"spin .8s linear infinite"}}/>
                    : recording ? <Waveform/> : I.mic}
                </button>

                <textarea ref={inputRef} value={input}
                  onChange={e=>setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder={recording?"Recording... release to transcribe":"Ask about your documents..."}
                  disabled={loading||recording}
                  rows={1}
                  style={{flex:1,background:"transparent",border:"none",color:"var(--text)",
                    fontSize:14,lineHeight:1.6,resize:"none",maxHeight:120,overflow:"auto",
                    fontFamily:"inherit"}}
                  onInput={e=>{e.target.style.height="auto";e.target.style.height=Math.min(e.target.scrollHeight,120)+"px"}}
                />

                <button onClick={()=>sendMessage(input)}
                  disabled={loading||!input.trim()}
                  style={{
                    width:34,height:34,borderRadius:9,border:"none",flexShrink:0,
                    background:loading||!input.trim()?"var(--border)":"var(--accent)",
                    color:"#fff",cursor:loading||!input.trim()?"not-allowed":"pointer",
                    display:"flex",alignItems:"center",justifyContent:"center",
                    transition:"background .15s",
                  }}>
                  {I.send}
                </button>
              </div>
              <div style={{fontSize:11,color:"var(--muted)",textAlign:"center",marginTop:6}}>
                Hold 🎤 to speak · Enter to send · Shift+Enter for newline
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ── Authentication Gate ──────────────────────────────────────────
export default function AppWrapper() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("dc_user")); } catch { return null; }
  });

  const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  if (!CLIENT_ID) {
    return <MainApp user={{ email: "anonymous", name: "Local Dev" }} onLogout={() => {}} />;
  }

  if (!user) {
    return (
      <GoogleOAuthProvider clientId={CLIENT_ID}>
        <div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",background:"var(--bg)",color:"var(--text)",fontFamily:"'Inter',sans-serif"}}>
          <div style={{background:"var(--surface)",padding:40,borderRadius:16,border:"1px solid var(--border)",textAlign:"center",boxShadow:"0 10px 30px rgba(0,0,0,0.05)"}}>
            <img src="/logo.png" alt="Logo" style={{width:64,marginBottom:20}}/>
            <h2 style={{marginBottom:10,fontWeight:800,fontSize:22,color:"var(--text)"}}>Sign in to DriveChat</h2>
            <p style={{marginBottom:30,color:"var(--muted)",fontSize:14}}>Use your Google account to access your secure workspace.</p>
            <div style={{display:"flex",justifyContent:"center"}}>
              <GoogleLogin 
                onSuccess={cred => {
                  const decoded = jwtDecode(cred.credential);
                  const u = { email: decoded.email, name: decoded.name, picture: decoded.picture };
                  localStorage.setItem("dc_user", JSON.stringify(u));
                  setUser(u);
                }}
                onError={() => console.error("Login Failed")}
              />
            </div>
          </div>
        </div>
      </GoogleOAuthProvider>
    );
  }

  return <MainApp user={user} onLogout={() => { localStorage.removeItem("dc_user"); setUser(null); }} />;
}
