"use client";

import { useState } from "react";

/* ─────────────────────────────────────────────────────────
 * APPROVAL CARD (human-in-the-loop)
 * ───────────────────────────────────────────────────────── */

export default function ApprovalCard({ questions = [], onComplete }) {
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState({});
  const [custom, setCustom] = useState({});
  const [sent, setSent] = useState(false);
  const [open, setOpen] = useState(true);
  
  if (!questions || questions.length === 0) return null;
  
  const question = questions[qi];
  const last = qi === questions.length - 1;
  const selected = answers[qi] ?? [];
  const hasAnswer = selected.length > 0 || Boolean(custom[qi]?.trim());

  const toggle = (index) => {
    setAnswers((current) => {
      const picked = current[qi] ?? [];
      const next = question.type === "radio"
        ? [index]
        : picked.includes(index)
          ? picked.filter((item) => item !== index)
          : [...picked, index];
      return { ...current, [qi]: next };
    });
    if (question.type === "radio") {
      setCustom((current) => ({ ...current, [qi]: "" }));
      // single-choice auto-advances
      window.setTimeout(() => {
        if (qi === questions.length - 1) {
          setSent(true);
          if (onComplete) onComplete({ answers, custom });
        }
        else setQi((current) => Math.min(questions.length - 1, current + 1));
      }, 480);
    }
  };

  const reset = () => {
    setQi(0);
    setAnswers({});
    setCustom({});
    setSent(false);
    setOpen(true);
  };

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="rounded-control bg-surface px-3 py-2 text-[12.5px] font-medium text-ink shadow-btn transition-colors duration-150 hover:bg-hover">
        Open approvals
      </button>
    );
  }

  return (
    <div className="flex min-h-[196px] w-full max-w-80 flex-col items-stretch">
      <div className="w-full self-start overflow-hidden rounded-card bg-surface shadow-card">
        {sent ? (
          <div className="flex h-37 flex-col items-center justify-center gap-2">
            <span
              className="flex size-6 items-center justify-center rounded-full bg-green text-white"
              style={{ animation: "pop-in 300ms cubic-bezier(0.23,1,0.32,1) both" }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
            </span>
            <span className="text-[13px] font-medium text-ink" style={{ animation: "fade-up 350ms cubic-bezier(0.23,1,0.32,1) 100ms both" }}>
              Decisions submitted
            </span>
            <button type="button" onClick={reset} className="text-[12px] font-medium text-accent-ink hover:underline">
              Start over
            </button>
          </div>
        ) : (
          <div key={qi} className="primitive-card-pad" style={{ animation: "fade-up 350ms cubic-bezier(0.23,1,0.32,1) both" }}>
            <div className="flex items-start justify-between gap-3">
              <span className="text-[13px] font-medium text-ink">{question.q}</span>
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setOpen(false)}
                className="primitive-icon-button shrink-0 text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            {question.summary && (
              <div className="mt-1.5 text-[12px] text-ink-2 leading-relaxed pr-6">
                {question.summary}
              </div>
            )}
            <div className="mt-3 flex flex-col gap-0.5">
              {question.options.map((option, i) => {
                const on = selected.includes(i);
                return (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggle(i)}
                    className="-mx-1.5 flex items-center gap-2 rounded-control px-1.5 py-1 text-left transition-colors duration-100 hover:bg-hover"
                  >
                    <span
                      className={`flex size-4 shrink-0 items-center justify-center transition-colors duration-200
                        ${question.type === "radio" ? "rounded-full" : "rounded-[5px]"}
                        ${on ? "bg-ink text-canvas" : "shadow-[inset_0_0_0_1.5px_var(--line-strong)] text-transparent"}`}
                    >
                      {question.type === "radio" ? (
                        <span className="size-1.5 rounded-full bg-canvas transition-transform duration-200" style={{ transform: on ? "scale(1)" : "scale(0)" }} />
                      ) : (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
                      )}
                    </span>
                    <span className={`text-[13px] transition-colors duration-200 ${on ? "text-ink" : "text-ink-2"}`}>
                      {option}
                    </span>
                  </button>
                );
              })}
              <label className="-mx-1.5 flex items-center gap-2 rounded-control px-1.5 py-1 transition-colors duration-100 focus-within:bg-hover hover:bg-hover">
                <span aria-hidden="true" className="size-4 shrink-0" />
                <input
                  value={custom[qi] ?? ""}
                  onChange={(event) => {
                    setCustom((current) => ({ ...current, [qi]: event.target.value }));
                    if (question.type === "radio") setAnswers((current) => ({ ...current, [qi]: [] }));
                  }}
                  placeholder="Type a reason..."
                  aria-label="Custom answer"
                  className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-3"
                />
              </label>
            </div>
          </div>
        )}

        {/* footer */}
        <div className="primitive-card-footer flex items-center justify-between">
          <span className="flex items-center gap-2">
            <button
              type="button"
              aria-label="Previous"
              disabled={qi === 0 || sent}
              onClick={() => setQi((current) => Math.max(0, current - 1))}
              className="flex size-6 items-center justify-center rounded-[5px] text-ink-3 transition-colors duration-100 enabled:hover:bg-hover enabled:hover:text-ink-2 disabled:opacity-35"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
            </button>
            <span className="flex items-center gap-1 mx-1.5">
              <span className="text-[11.5px] font-medium text-ink-2 tabular-nums">
                {qi + 1} of {questions.length} findings
              </span>
            </span>
            <button
              type="button"
              aria-label="Next"
              disabled={last || sent}
              onClick={() => setQi((current) => Math.min(questions.length - 1, current + 1))}
              className="flex size-6 items-center justify-center rounded-[5px] text-ink-3 transition-colors duration-100 enabled:hover:bg-hover enabled:hover:text-ink-2 disabled:opacity-35"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            </button>
          </span>
          {!sent && (
            <button
              type="button"
              aria-label={last ? "Send answers" : "Next question"}
              disabled={!hasAnswer}
              onClick={() => {
                if (last) {
                  setSent(true);
                  if (onComplete) onComplete({ answers, custom });
                } else {
                  setQi((current) => current + 1);
                }
              }}
              className="-mr-0.5 flex size-7 items-center justify-center rounded-[8px] transition-[background-color,color,transform] duration-200 enabled:active:scale-[0.96]"
              style={{
                background: hasAnswer ? "var(--ink)" : "var(--field)",
                color: hasAnswer ? "var(--surface)" : "var(--ink-3)",
                boxShadow: hasAnswer ? "inset 0 1px 0 rgba(255,255,255,0.14)" : "var(--shadow-btn)",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
