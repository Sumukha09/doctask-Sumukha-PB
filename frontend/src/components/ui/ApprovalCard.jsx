"use client";

import { useState } from "react";


export default function ApprovalCard({ finding, totalPending, onSubmit, isSubmitting }) {
  const [custom, setCustom] = useState("");
  
  if (!finding) return null;

  const handleToggle = (decision) => {
    if (isSubmitting) return;
    onSubmit(finding.id, decision, custom);
    setCustom("");
  };

  return (
    <div className="flex min-h-[196px] w-full max-w-80 flex-col items-stretch">
      <div className="w-full self-start overflow-hidden rounded-card bg-surface shadow-card">
        <div className="primitive-card-pad" style={{ animation: "fade-up 350ms cubic-bezier(0.23,1,0.32,1) both" }}>
          <div className="flex items-start justify-between gap-3">
            <span className="text-[13px] font-medium text-ink">{finding.title}</span>
          </div>
          {finding.summary && (
            <div className="mt-1.5 text-[12px] text-ink-2 leading-relaxed pr-6">
              {finding.summary}
            </div>
          )}
          
          <div className="mt-3 flex flex-col gap-2">
             <div className="flex gap-2">
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleToggle('approve')}
                  className="flex-1 flex items-center justify-center gap-2 rounded-control px-3 py-2 text-sm font-medium transition-colors bg-green/10 text-green hover:bg-green/20 disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => handleToggle('reject')}
                  className="flex-1 flex items-center justify-center gap-2 rounded-control px-3 py-2 text-sm font-medium transition-colors bg-red/10 text-red hover:bg-red/20 disabled:opacity-50"
                >
                  Reject
                </button>
             </div>
            <label className="flex items-center gap-2 rounded-control px-2 py-1.5 transition-colors duration-100 focus-within:bg-hover hover:bg-hover border border-line">
              <input
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
                disabled={isSubmitting}
                placeholder="Optional comment..."
                className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-ink-3"
              />
            </label>
          </div>
        </div>
        
        {/* footer */}
        <div className="primitive-card-footer flex items-center justify-between bg-inset border-t border-line">
           <span className="text-[11.5px] font-medium text-ink-2">
             {totalPending} pending findings remaining
           </span>
           {isSubmitting && (
             <span className="flex items-center gap-2 text-[11.5px] text-accent">
               <span className="animate-pulse">Submitting...</span>
             </span>
           )}
        </div>
      </div>
    </div>
  );
}
