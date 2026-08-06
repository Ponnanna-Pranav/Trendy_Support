import React from "react";
import TicketStub, { Row } from "./TicketStub";

export function DelayCreditCard({ data }) {
  if (!data.issued) {
    return (
      <TicketStub eyebrow="Delay credit" tone="ink" title="Not applicable yet">
        <p className="text-[13px] text-ink-soft leading-snug">{data.message}</p>
      </TicketStub>
    );
  }
  return (
    <TicketStub eyebrow="Delay credit" id={data.credit_id} tone="moss" title={`₹${data.amount} store credit issued`}>
      <p className="text-[13px] text-ink-soft leading-snug">{data.message}</p>
    </TicketStub>
  );
}

export function EscalationCard({ data }) {
  return (
    <TicketStub eyebrow="Escalated to a human" id={data.ticket_id} tone="amber" title="A specialist will follow up">
      <p className="text-[13px] text-ink-soft leading-snug">{data.message}</p>
    </TicketStub>
  );
}

export function PolicySourcesCard({ data }) {
  return (
    <div className="animate-rise flex flex-wrap gap-1.5 max-w-[380px]">
      <span className="text-[11px] uppercase tracking-[0.1em] text-ink-soft/70 font-sans mr-1 mt-1">
        Grounded in
      </span>
      {(data.sources || []).map((s) => (
        <span
          key={s.section_id}
          className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-ink/5 text-ink-soft border border-ink/10"
        >
          {s.title}
        </span>
      ))}
    </div>
  );
}
