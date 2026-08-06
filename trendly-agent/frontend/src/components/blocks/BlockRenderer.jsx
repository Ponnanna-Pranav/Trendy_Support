import React from "react";
import OrderStatusCard from "./OrderStatusCard";
import EligibilityCard from "./EligibilityCard";
import RmaCard from "./RmaCard";
import { DelayCreditCard, EscalationCard, PolicySourcesCard } from "./MiscCards";

const REGISTRY = {
  order_status: OrderStatusCard,
  eligibility: EligibilityCard,
  rma: RmaCard,
  delay_credit: DelayCreditCard,
  escalation: EscalationCard,
  policy_sources: PolicySourcesCard,
};

export default function BlockRenderer({ blocks }) {
  if (!blocks || blocks.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 my-1.5">
      {blocks.map((b, i) => {
        const Comp = REGISTRY[b.type];
        if (!Comp) return null;
        return <Comp key={i} data={b.data} />;
      })}
    </div>
  );
}
