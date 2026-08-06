import React from "react";
import TicketStub, { Row } from "./TicketStub";

export default function EligibilityCard({ data }) {
  const tone = data.eligible ? "moss" : "berry";
  const title = data.eligible ? "Eligible" : "Not eligible";
  return (
    <TicketStub
      eyebrow={`${data.request_type === "exchange" ? "Exchange" : "Return"} eligibility`}
      id={data.order_id}
      tone={tone}
      title={title}
    >
      <Row label="Reason" value={humanizeReason(data.reason)} />
      <Row label="Days since delivery" value={data.days_since_delivery} />
      <div className="pt-1.5 mt-1 border-t border-rule/70 space-y-2">
        {(data.items || []).map((item) => (
          <div key={item.sku}>
            <div className="flex items-baseline justify-between text-[13px]">
              <span className="text-ink">{item.name}</span>
              <span className={item.eligible ? "text-moss" : "text-berry"}>
                {item.eligible ? "Eligible" : "Denied"}
              </span>
            </div>
            <p className="text-[12px] text-ink-soft leading-snug mt-0.5">{item.message}</p>
            {item.refund_estimate !== undefined && (
              <p className="text-[12px] font-mono text-ink mt-0.5">Refund est. ₹{item.refund_estimate}</p>
            )}
          </div>
        ))}
      </div>
    </TicketStub>
  );
}

function humanizeReason(r) {
  return { changed_mind: "Changed mind", wrong_size: "Wrong size", damaged: "Damaged",
           incorrect_item: "Incorrect item" }[r] || r;
}
