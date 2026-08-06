import React from "react";

/**
 * The signature visual element: structured agent output (order status,
 * eligibility, RMA confirmation) rendered like a garment tag / receipt
 * stub rather than a generic chat card — ties the UI to the actual
 * subject matter (fashion retail returns) instead of a templated look.
 */
export default function TicketStub({ eyebrow, title, tone = "ink", id, children }) {
  const toneClasses = {
    ink: "border-ink/15",
    moss: "border-moss/40",
    berry: "border-berry/40",
    amber: "border-amber/40",
  };
  const dotClasses = {
    ink: "bg-ink",
    moss: "bg-moss",
    berry: "bg-berry",
    amber: "bg-amber",
  };

  return (
    <div
      className={`animate-rise w-full max-w-[380px] rounded-card bg-paper-raised border ${toneClasses[tone]} shadow-sm overflow-hidden`}
    >
      <div className="flex items-center justify-between px-4 pt-3 pb-2">
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 rounded-full ${dotClasses[tone]}`} />
          <span className="text-[11px] uppercase tracking-[0.12em] text-ink-soft font-sans font-medium">
            {eyebrow}
          </span>
        </div>
        {id && <span className="text-[11px] font-mono text-ink-soft">{id}</span>}
      </div>

      {title && (
        <div className="px-4 pb-2">
          <h4 className="font-display text-[17px] leading-snug text-ink">{title}</h4>
        </div>
      )}

      <div className="ticket-perf" />

      <div className="px-4 py-3 space-y-1.5">{children}</div>
    </div>
  );
}

export function Row({ label, value, mono = false }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div className="flex items-baseline justify-between gap-4 text-[13px]">
      <span className="text-ink-soft font-sans">{label}</span>
      <span className={`text-ink text-right ${mono ? "font-mono text-[12px]" : "font-sans"}`}>{value}</span>
    </div>
  );
}
