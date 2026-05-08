/**
 * CitationPanel.jsx
 * 
 * Shows the AI answer with:
 * 1. Inline citation badges [1], [2] linked to quotes
 * 2. A document panel showing the exact chunk with the quote highlighted in yellow
 * 3. Animated scroll-to-highlight on click
 * 
 * Usage:
 *   <CitationPanel answer={answer} citations={citations} />
 */

import { useState, useRef, useEffect } from "react";

// ── Highlight text inside a chunk ──────────────────────────────
function HighlightedChunk({ text, charStart, charEnd, isActive }) {
  if (charStart === -1 || charEnd === -1 || charStart >= charEnd) {
    return <p style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text)", whiteSpace: "pre-wrap" }}>{text}</p>;
  }

  const before    = text.slice(0, charStart);
  const highlight = text.slice(charStart, charEnd);
  const after     = text.slice(charEnd);

  return (
    <p style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text)", whiteSpace: "pre-wrap" }}>
      {before}
      <mark style={{
        background: isActive ? "#fbbf24" : "#fbbf2466",
        color: "#1a1200",
        borderRadius: 3,
        padding: "1px 2px",
        fontWeight: 600,
        transition: "background 0.4s ease",
        boxShadow: isActive ? "0 0 0 2px #fbbf24" : "none",
      }}>
        {highlight}
      </mark>
      {after}
    </p>
  );
}

// ── Single citation badge ──────────────────────────────────────
function CitationBadge({ index, citation, isActive, onClick }) {
  return (
    <button
      onClick={() => onClick(index)}
      title={citation.relevance}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 20,
        height: 20,
        borderRadius: "50%",
        fontSize: 10,
        fontWeight: 700,
        cursor: "pointer",
        border: "none",
        marginLeft: 3,
        marginBottom: 1,
        verticalAlign: "middle",
        background: isActive ? "#fbbf24" : "var(--accent)",
        color: isActive ? "#1a1200" : "#fff",
        transition: "all 0.2s",
        transform: isActive ? "scale(1.2)" : "scale(1)",
        boxShadow: isActive ? "0 0 0 3px #fbbf2460" : "none",
      }}
    >
      {index + 1}
    </button>
  );
}

// ── Main CitationPanel ─────────────────────────────────────────
export default function CitationPanel({ answer, citations = [], isLoading = false }) {
  const [activeCitation, setActiveCitation] = useState(null);
  const [docPanelOpen, setDocPanelOpen]     = useState(false);
  const highlightRef = useRef(null);

  // Auto-open doc panel when citations arrive
  useEffect(() => {
    if (citations.length > 0) setDocPanelOpen(true);
  }, [citations]);

  // Scroll to highlighted chunk when active citation changes
  useEffect(() => {
    if (activeCitation !== null && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [activeCitation]);

  const handleBadgeClick = (idx) => {
    setActiveCitation(prev => prev === idx ? null : idx);
    setDocPanelOpen(true);
  };

  if (isLoading) {
    return (
      <div style={{ padding: "12px 16px", borderRadius: 12, background: "var(--surface2)", border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{
              width: 7, height: 7, borderRadius: "50%", background: "var(--accent)",
              animation: `bounce 1.2s ${i * 0.2}s ease-in-out infinite`,
            }} />
          ))}
        </div>
        <style>{`@keyframes bounce{0%,80%,100%{transform:scale(.6);opacity:.4}40%{transform:scale(1);opacity:1}}`}</style>
      </div>
    );
  }

  if (!answer) return null;

  const activeCit = activeCitation !== null ? citations[activeCitation] : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>

      {/* ── Answer bubble with inline citation badges ── */}
      <div style={{
        padding: "12px 16px",
        borderRadius: "16px 16px 16px 4px",
        background: "var(--surface2)",
        border: "1px solid var(--border)",
        fontSize: 14,
        lineHeight: 1.7,
        color: "var(--text)",
      }}>
        {/* Split answer into sentences and insert citation badges */}
        <AnswerWithBadges
          answer={answer}
          citations={citations}
          activeCitation={activeCitation}
          onBadgeClick={handleBadgeClick}
        />
      </div>

      {/* ── Citation chips row ── */}
      {citations.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", paddingLeft: 2 }}>
          {citations.map((c, i) => (
            <button
              key={i}
              onClick={() => handleBadgeClick(i)}
              style={{
                padding: "4px 10px",
                borderRadius: 20,
                fontSize: 11,
                cursor: "pointer",
                border: `1px solid ${activeCitation === i ? "#fbbf24" : "var(--accent-border)"}`,
                background: activeCitation === i ? "#fbbf2420" : "var(--accent-dim)",
                color: activeCitation === i ? "#fbbf24" : "var(--accent)",
                display: "flex",
                alignItems: "center",
                gap: 5,
                transition: "all 0.2s",
                fontFamily: "inherit",
              }}
            >
              <span style={{
                width: 16, height: 16, borderRadius: "50%",
                background: activeCitation === i ? "#fbbf24" : "var(--accent)",
                color: activeCitation === i ? "#1a1200" : "#fff",
                fontSize: 9, fontWeight: 700,
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0,
              }}>{i + 1}</span>
              <span style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {c.file}
              </span>
              {c.found && <span style={{ fontSize: 9, opacity: 0.7 }}>✓ located</span>}
            </button>
          ))}

          <button
            onClick={() => setDocPanelOpen(p => !p)}
            style={{
              padding: "4px 10px", borderRadius: 20, fontSize: 11, cursor: "pointer",
              border: "1px solid var(--border)", background: "transparent",
              color: "var(--muted)", fontFamily: "inherit",
            }}
          >
            {docPanelOpen ? "Hide evidence ↑" : "Show evidence ↓"}
          </button>
        </div>
      )}

      {/* ── Document evidence panel ── */}
      {docPanelOpen && citations.length > 0 && (
        <div style={{
          borderRadius: 12,
          border: "1px solid var(--border)",
          background: "var(--surface)",
          overflow: "hidden",
          animation: "fadeUp 0.2s ease",
        }}>
          {/* Panel header */}
          <div style={{
            padding: "10px 16px",
            borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            background: "var(--surface2)",
          }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", display: "flex", alignItems: "center", gap: 7 }}>
              <span>📄</span>
              Source Evidence
              <span style={{
                padding: "1px 7px", borderRadius: 20, fontSize: 10,
                background: "var(--accent-dim)", color: "var(--accent)",
                border: "1px solid var(--accent-border)",
              }}>
                {citations.length} quote{citations.length !== 1 ? "s" : ""}
              </span>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              {citations.map((_, i) => (
                <button
                  key={i}
                  onClick={() => handleBadgeClick(i)}
                  style={{
                    width: 24, height: 24, borderRadius: "50%", border: "none",
                    cursor: "pointer", fontSize: 11, fontWeight: 700,
                    background: activeCitation === i ? "#fbbf24" : "var(--surface3)",
                    color: activeCitation === i ? "#1a1200" : "var(--muted)",
                    transition: "all 0.2s", fontFamily: "inherit",
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Citation cards */}
          <div style={{ maxHeight: 360, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
            {citations.map((c, i) => {
              const isActive = activeCitation === i;
              return (
                <div
                  key={i}
                  ref={isActive ? highlightRef : null}
                  onClick={() => handleBadgeClick(i)}
                  style={{
                    borderRadius: 10,
                    border: `1px solid ${isActive ? "#fbbf2460" : "var(--border)"}`,
                    background: isActive ? "#fbbf2408" : "var(--surface2)",
                    padding: "10px 13px",
                    cursor: "pointer",
                    transition: "all 0.25s",
                    animation: isActive ? "pulse-border 1s ease" : "none",
                  }}
                >
                  {/* Citation header */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                      <span style={{
                        width: 20, height: 20, borderRadius: "50%", fontSize: 10, fontWeight: 700,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: isActive ? "#fbbf24" : "var(--accent)",
                        color: isActive ? "#1a1200" : "#fff",
                        flexShrink: 0,
                      }}>{i + 1}</span>
                      <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{c.file}</span>
                    </div>
                    {c.found
                      ? <span style={{ fontSize: 10, color: "var(--success)", background: "#5eead415", padding: "2px 7px", borderRadius: 10, border: "1px solid #5eead440" }}>✓ Verified</span>
                      : <span style={{ fontSize: 10, color: "var(--warn)", background: "#fbbf2415", padding: "2px 7px", borderRadius: 10, border: "1px solid #fbbf2440" }}>⚠ Approx</span>
                    }
                  </div>

                  {/* Chunk text with highlight */}
                  <div style={{
                    background: "var(--surface)", borderRadius: 7, padding: "10px 12px",
                    border: `1px solid ${isActive ? "#fbbf2440" : "var(--border)"}`,
                    marginBottom: 8, maxHeight: 180, overflowY: "auto",
                    fontSize: 13,
                  }}>
                    {c.chunk_text
                      ? <HighlightedChunk
                          text={c.chunk_text}
                          charStart={c.char_start}
                          charEnd={c.char_end}
                          isActive={isActive}
                        />
                      : <p style={{ fontStyle: "italic", color: "var(--muted)", fontSize: 12 }}>
                          "{c.quote}"
                        </p>
                    }
                  </div>

                  {/* Relevance note */}
                  {c.relevance && (
                    <div style={{ fontSize: 11, color: "var(--muted)", display: "flex", gap: 5, alignItems: "flex-start" }}>
                      <span>💡</span>
                      <span>{c.relevance}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeUp { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }
        @keyframes pulse-border { 0%{box-shadow:0 0 0 0 #fbbf2460} 70%{box-shadow:0 0 0 6px transparent} 100%{box-shadow:none} }
      `}</style>
    </div>
  );
}


// ── AnswerWithBadges: inserts citation badges at sentence boundaries ──
function AnswerWithBadges({ answer, citations, activeCitation, onBadgeClick }) {
  if (!citations.length) {
    return <span style={{ whiteSpace: "pre-wrap" }}>{answer}</span>;
  }

  // Split answer into sentences
  const sentences = answer.match(/[^.!?]+[.!?]+["']?\s*|[^.!?]+$/g) || [answer];

  // Assign citations to sentences by finding which sentence contains keywords from the quote
  const assigned = new Array(sentences.length).fill(null).map(() => []);
  citations.forEach((c, ci) => {
    if (!c.quote) return;
    const quoteWords = c.quote.toLowerCase().split(/\s+/).slice(0, 5).join(" ");
    let bestIdx = -1, bestScore = 0;
    sentences.forEach((s, si) => {
      const score = quoteWords.split(" ").filter(w => s.toLowerCase().includes(w)).length;
      if (score > bestScore) { bestScore = score; bestIdx = si; }
    });
    if (bestIdx >= 0 && bestScore >= 2) assigned[bestIdx].push(ci);
    else assigned[Math.min(ci, sentences.length - 1)].push(ci); // fallback
  });

  return (
    <span style={{ whiteSpace: "pre-wrap" }}>
      {sentences.map((sentence, si) => (
        <span key={si}>
          {sentence}
          {assigned[si].map(ci => (
            <CitationBadge
              key={ci}
              index={ci}
              citation={citations[ci]}
              isActive={activeCitation === ci}
              onClick={onBadgeClick}
            />
          ))}
        </span>
      ))}
    </span>
  );
}
