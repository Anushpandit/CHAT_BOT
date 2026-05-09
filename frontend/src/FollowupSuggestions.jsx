/**
 * FollowupSuggestions.jsx
 *
 * Animated follow-up question chips that appear below each AI answer.
 * Clicking a chip instantly sends the question as the next message.
 *
 * Props:
 *   suggestions  : string[]         - list of follow-up question strings
 *   onSelect     : (q: string) => void  - called when user clicks a chip
 *   isLoading    : boolean           - show skeleton while suggestions load
 */

import { useEffect, useState } from "react";

// ── Sparkle icon ─────────────────────────────────────────────────
const SparkleIcon = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 2l2.09 6.43H21l-5.47 3.97 2.09 6.43L12 14.9l-5.62 3.93 2.09-6.43L3 8.43h6.91z"/>
  </svg>
);

// ── Arrow icon ────────────────────────────────────────────────────
const ArrowIcon = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <line x1="5" y1="12" x2="19" y2="12"/>
    <polyline points="12 5 19 12 12 19"/>
  </svg>
);

// ── Skeleton chip ─────────────────────────────────────────────────
const SkeletonChip = ({ width, delay }) => (
  <div style={{
    height: 34,
    width,
    borderRadius: 20,
    background: "var(--skeleton-bg, #e5e7eb)",
    animation: `shimmer 1.4s ${delay}s ease-in-out infinite`,
    flexShrink: 0,
  }}/>
);

// ── Single chip ────────────────────────────────────────────────────
const Chip = ({ text, index, onSelect }) => {
  const [hovered, setHovered] = useState(false);
  const [clicked, setClicked] = useState(false);

  const handleClick = () => {
    setClicked(true);
    setTimeout(() => onSelect(text), 200);
  };

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        padding: "7px 14px",
        borderRadius: 20,
        fontSize: 13,
        cursor: "pointer",
        border: `1px solid ${hovered ? "var(--accent)" : "var(--border)"}`,
        background: clicked
          ? "var(--accent)"
          : hovered
          ? "var(--accent-dim)"
          : "var(--surface2)",
        color: clicked ? "#fff" : hovered ? "var(--accent)" : "var(--text)",
        transition: "all 0.18s cubic-bezier(.4,0,.2,1)",
        transform: clicked ? "scale(0.96)" : hovered ? "translateY(-1px)" : "none",
        whiteSpace: "nowrap",
        fontFamily: "inherit",
        animation: `chipIn 0.3s ${index * 0.08}s both cubic-bezier(.34,1.56,.64,1)`,
        flexShrink: 0,
        maxWidth: 240,
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      <span style={{
        color: clicked ? "#ffffffbb" : hovered ? "var(--accent)" : "var(--muted)",
        transition: "color .18s",
        flexShrink: 0,
      }}>
        <SparkleIcon/>
      </span>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{text}</span>
      <span style={{
        opacity: hovered && !clicked ? 1 : 0,
        transition: "opacity .18s",
        flexShrink: 0,
        color: "var(--accent)",
      }}>
        <ArrowIcon/>
      </span>
    </button>
  );
};

// ── Main component ─────────────────────────────────────────────────
export default function FollowupSuggestions({ suggestions = [], onSelect, isLoading = false }) {

  const [visible, setVisible] = useState(false);

  // Trigger entrance animation when suggestions arrive
  useEffect(() => {
    if (suggestions.length > 0) {
      const t = setTimeout(() => setVisible(true), 80);
      return () => clearTimeout(t);
    } else {
      setVisible(false);
    }
  }, [suggestions]);

  // Don't render if no suggestions and not loading
  if (!isLoading && suggestions.length === 0) return null;

  return (
    <div style={{
      marginTop: 10,
      opacity: visible || isLoading ? 1 : 0,
      transform: visible || isLoading ? "none" : "translateY(4px)",
      transition: "opacity 0.25s ease, transform 0.25s ease",
    }}>
      {/* Label */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        marginBottom: 8,
      }}>
        <div style={{
          width: 1,
          height: 14,
          background: "var(--border)",
          borderRadius: 1,
        }}/>
        <span style={{
          fontSize: 11,
          color: "var(--muted)",
          fontWeight: 500,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}>
          Ask next
        </span>
      </div>

      {/* Chips row */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
      }}>
        {isLoading && suggestions.length === 0 ? (
          // Skeleton loading state
          <>
            <SkeletonChip width={140} delay={0}/>
            <SkeletonChip width={180} delay={0.1}/>
            <SkeletonChip width={160} delay={0.2}/>
          </>
        ) : (
          suggestions.map((s, i) => (
            <Chip
              key={`${s}-${i}`}
              text={s}
              index={i}
              onSelect={onSelect}
            />
          ))
        )}
      </div>

      <style>{`
        @keyframes chipIn {
          from { opacity: 0; transform: scale(0.85) translateY(4px); }
          to   { opacity: 1; transform: scale(1) translateY(0); }
        }
        @keyframes shimmer {
          0%, 100% { opacity: 0.4; }
          50%       { opacity: 0.9; }
        }
      `}</style>
    </div>
  );
}
