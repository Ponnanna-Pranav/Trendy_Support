import React from "react";
import TicketStub, { Row } from "./TicketStub";

const STATUS_LABEL = {
  delivered: "Delivered",
  in_transit: "In transit",
  processing: "Processing",
  cancelled: "Cancelled",
};

export default function OrderStatusCard({ data }) {
  const tone = data.possible_lost_parcel ? "amber" : data.status === "delivered" ? "moss" : "ink";
  return (
    <TicketStub eyebrow="Order status" id={data.order_id} tone={tone} title={STATUS_LABEL[data.status] || data.status}>
      <Row label="Order date" value={data.order_date} />
      {data.status === "delivered" ? (
        <Row label="Delivered" value={data.delivered_date} />
      ) : (
        <Row label="Expected by" value={data.expected_delivery_date} />
      )}
      <Row label="Tracking no." value={data.tracking_number} mono />
      {data.possible_lost_parcel && (
        <div className="mt-2 rounded-md bg-amber-soft px-3 py-2 text-[12px] text-ink">
          No movement for {data.days_since_last_tracking_update}+ days — flagged as a possible
          lost parcel. A support specialist will look into this.
        </div>
      )}
      <div className="pt-2 mt-1 border-t border-rule/70">
        {(data.items || []).map((item) => (
          <div key={item.sku} className="flex items-baseline justify-between text-[13px] py-0.5">
            <span className="text-ink">{item.name}{item.size ? ` · ${item.size}` : ""}</span>
            <span className="text-ink-soft font-mono text-[11px]">{item.sku}</span>
          </div>
        ))}
      </div>
    </TicketStub>
  );
}
