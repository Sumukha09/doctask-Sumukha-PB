"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";

/* ─────────────────────────────────────────────────────────
 * THINKING — expandable agent trace
 * ───────────────────────────────────────────────────────── */

const STAGES = [800, 600, 1800, 2600, 1600];

function useSequence(steps) {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (stage >= steps.length - 1) return;
    const t = setTimeout(() => setStage((s) => s + 1), steps[stage]);
    return () => clearTimeout(t);
  }, [stage, steps]);
  return stage;
}

const VARIANTS = {
  Steps: {
    active: "Thinking",
    done: "Completed task",
    rows: [
      { primary: "Reading document text" },
      { primary: "Extracting claims" },
      { primary: "Cross-referencing evidence", secondary: "sources" },
      { primary: "Detecting conflicts" },
    ],
  },
  Reasoning: {
    active: "Analyzing",
    done: "Analysis complete",
    rows: [
      { primary: "Found conflicting evidence across source documents." },
      { primary: "Flagging for human review before proceeding." },
    ],
  },
};

export default function ThinkingState({ variant = "Steps", rowsOverride = null, activeOverride = null, doneOverride = null, forceState = null }) {
  // If forceState is provided (e.g. "running" or "completed"), we don't animate the internal sequence
  const internalStage = useSequence(STAGES);
  const stage = forceState === "running" ? 1 : forceState === "completed" ? 5 : internalStage;
  
  const [manualExpanded, setManualExpanded] = useState(null);
  
  const v = VARIANTS[variant] ?? VARIANTS.Steps;
  const rows = rowsOverride || v.rows;
  const activeLabel = activeOverride || v.active;
  const doneLabel = doneOverride || v.done;
  
  const autoExpanded = stage >= 1 && stage < 4;
  const expanded = manualExpanded ?? autoExpanded;
  const working = stage < 3;
  const visible = stage < 2 ? 0 : stage === 2 ? Math.min(2, rows.length) : rows.length;
  const traceRef = useRef(null);
  const [lineHeight, setLineHeight] = useState(0);
  
  useLayoutEffect(() => {
    if (traceRef.current) setLineHeight(traceRef.current.offsetHeight);
  }, [visible, expanded, variant, stage]);

  return (
    <div className="flex min-h-[48px] w-full max-w-95 flex-col">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setManualExpanded((current) => !(current ?? autoExpanded))}
        className="-mx-1.5 flex w-fit items-center gap-2 rounded-control px-1.5 py-1
          transition-colors duration-100 hover:bg-hover-2"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill={working ? "var(--ink-2)" : "var(--ink-3)"}>
          <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />
        </svg>
        {working ? (
          <span
            className="bg-clip-text text-[13px] font-medium whitespace-nowrap text-transparent"
            style={{
              backgroundImage:
                "linear-gradient(90deg, var(--ink-3) 35%, var(--ink) 50%, var(--ink-3) 65%)",
              backgroundSize: "200% 100%",
              animation: "shimmer-text 1.4s linear infinite",
            }}
          >
            {activeLabel}
          </span>
        ) : (
          <span
            className="text-[13px] font-medium whitespace-nowrap text-ink-2"
            style={{ animation: "fade-in 350ms ease-out both" }}
          >
            {doneLabel}
          </span>
        )}
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ink-3)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
          className="transition-transform duration-300"
          style={{ transform: expanded ? "rotate(180deg)" : "rotate(0)" }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      <div
        className="grid transition-[grid-template-rows,opacity] duration-400"
        style={{
          gridTemplateRows: expanded ? "1fr" : "0fr",
          opacity: expanded ? 1 : 0,
          transitionTimingFunction: "cubic-bezier(0.23, 1, 0.32, 1)",
        }}
      >
        <div className="overflow-hidden">
          <div className="relative mt-1 ml-[5px] pl-4">
            <span
              aria-hidden
              className="absolute left-[3px] w-px bg-line"
              style={{ top: -8, height: lineHeight ? lineHeight - 2 : 0, transition: "height 500ms cubic-bezier(0.23,1,0.32,1)" }}
            />
            <div ref={traceRef} className="flex flex-col gap-1 py-1">
            {rows.slice(0, visible).map((row, i) => {
              const content = (
                <>
                {i < visible - 1 || !working ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ink-3)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                ) : (
                  <span className="size-3 shrink-0 rounded-full border-[1.5px] border-line-strong border-t-ink-2" style={{ animation: "spin 700ms linear infinite" }} />
                )}
                <span className={`min-w-0 truncate text-[12.5px] ${variant === "Reasoning" ? "whitespace-normal leading-relaxed text-ink-2" : "font-medium text-ink"}`}>
                  {row.primary}
                </span>
                {row.secondary && (
                  <span className={`shrink-0 text-[11.5px] text-ink-3`}>
                    {row.secondary}
                  </span>
                )}
                </>
              );
              const rowClass = "flex min-h-7 w-full items-center gap-2 rounded-[6px] px-1.5 py-0.5 text-left";
              const animation = { animation: `fade-up 320ms cubic-bezier(0.23,1,0.32,1) ${i * 120}ms both` };

              return (
                <div key={row.primary} className={rowClass} style={animation}>
                  {content}
                </div>
              );
            })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
