"use client";

import { useState } from "react";

/* ─────────────────────────────────────────────────────────
 * RECOMMENDATION CARD
 * ───────────────────────────────────────────────────────── */

function Meter({ signal, tone }) {
  return (
    <span className="flex items-end gap-0.5">
      {[0, 1, 2].map((bar) => (
        <span
          key={bar}
          className="w-1 rounded-full transition-colors duration-300"
          style={{ height: 10, background: bar < signal ? tone : "var(--line-strong)" }}
        />
      ))}
    </span>
  );
}

export default function RecommendationCard({ title, options = [], onAccept }) {
  const [selected, setSelected] = useState(0);
  const [open, setOpen] = useState(false);

  if (!options || options.length === 0) return null;

  const active = options[selected];
  const others = options.map((o, i) => ({ o, i })).filter(({ i }) => i !== selected);

  return (
    <div className="w-full max-w-95 overflow-hidden rounded-card bg-surface shadow-card">
      <div className="primitive-card-pad">
        <span className="text-[13px] font-semibold text-ink">
          {title}
        </span>
        <div
          key={active.key}
          className="mt-1.5 min-h-12 text-[13px] leading-relaxed text-ink-2"
          style={{ animation: "fade-in 180ms ease-out both" }}
        >
          {active.body}
        </div>
      </div>

      <div
        className="grid transition-[grid-template-rows,opacity] duration-300"
        style={{
          gridTemplateRows: open ? "1fr" : "0fr",
          opacity: open ? 1 : 0,
          transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        <div className="overflow-hidden">
          <div className="border-t border-line bg-inset px-2 py-2">
            <p className="px-1.5 pb-1 text-[11px] font-medium text-ink-3">
              Other options
            </p>
            {others.map(({ o, i }) => (
              <button
                key={o.key}
                type="button"
                onClick={() => {
                  setSelected(i);
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between gap-3 rounded-control px-1.5 py-1.5 text-left transition-colors duration-100 hover:bg-hover-2"
              >
                <span className="flex items-center gap-2 truncate">
                  <Meter signal={o.signal} tone={o.tone} />
                  <span className="truncate text-[12.5px] font-medium text-ink-2">
                    {o.short}
                  </span>
                </span>
                <span className="shrink-0 text-[11px] font-medium" style={{ color: o.tone }}>
                  {o.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="primitive-card-footer flex items-center justify-between gap-2">
        {others.length > 0 ? (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className="flex h-7 items-center gap-1 rounded-[6px] px-2 text-[12px] font-medium text-ink-2 transition-colors duration-100 hover:bg-hover hover:text-ink"
          >
            Alternatives
            <svg
              width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
              className="transition-transform duration-300"
              style={{ transform: open ? "rotate(180deg)" : "rotate(0)" }}
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
        ) : <div />}
        <button
          type="button"
          onClick={() => onAccept && onAccept(active)}
          className={`h-7 rounded-[8px] px-3 text-[12px] font-medium shadow-btn transition-[transform,opacity] duration-200 active:scale-[0.96] ${active.ctaStyle}`}
        >
          {active.cta}
        </button>
      </div>
    </div>
  );
}
