import React from "react";
import TicketStub, { Row } from "./TicketStub";

export default function RmaCard({ data }) {
  if (!data.created) {
    return (
      <TicketStub eyebrow="Return request" tone="berry" title="Couldn't be created">
        <p className="text-[13px] text-ink-soft leading-snug">{data.message}</p>
      </TicketStub>
    );
  }
  const r = data.record || {};
  return (
    <TicketStub eyebrow={r.request_type === "exchange" ? "Exchange request" : "Return request"} id={data.rma_id} tone="moss" title="Confirmed">
      <Row label="Item" value={r.sku} mono />
      <Row label="Status" value="Pickup scheduling" />
      {r.refund_estimate !== undefined && <Row label="Refund est." value={`₹${r.refund_estimate}`} mono />}
      {r.desired_exchange_size && <Row label="Requested size" value={r.desired_exchange_size} />}
      <p className="text-[12px] text-ink-soft leading-snug pt-1.5 mt-1 border-t border-rule/70">
        Free reverse pickup — the carrier will attempt up to 2 times.
      </p>
    </TicketStub>
  );
}
