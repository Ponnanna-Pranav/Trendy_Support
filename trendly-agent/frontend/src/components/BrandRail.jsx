import React from "react";
import { Clock, ShieldCheck, Truck } from "lucide-react";

export default function BrandRail() {
  return (
    <div className="hidden lg:flex flex-col justify-between h-full px-10 py-12 max-w-md">
      <div>
        <p className="text-[11px] uppercase tracking-[0.18em] text-berry font-sans font-semibold mb-6">
          Trendly · Support
        </p>
        <h1 className="font-display text-[42px] leading-[1.08] text-ink mb-5">
          Ask about your order.
          <br />
          Get a straight answer.
        </h1>
        <p className="text-[15px] text-ink-soft leading-relaxed font-sans max-w-sm">
          Order status, returns, exchanges, and shipping questions — answered from Trendly's
          actual policy, not a guess. Anything outside that, we hand straight to a person.
        </p>
      </div>

      <div className="space-y-5 mt-10">
        <Feature icon={<Truck size={16} />} title="Real order lookup" text="Grounded in your actual order record, verified by email." />
        <Feature icon={<ShieldCheck size={16} />} title="Grounded in policy" text="Every returns answer traces back to Trendly's written policy." />
        <Feature icon={<Clock size={16} />} title="9 AM – 9 PM IST" text="Outside that, or beyond what I can do, a specialist follows up." />
      </div>

      <p className="text-[11px] text-ink-soft/60 font-mono mt-10">trendly.com/support</p>
    </div>
  );
}

function Feature({ icon, title, text }) {
  return (
    <div className="flex items-start gap-3">
      <div className="h-8 w-8 rounded-full bg-ink/5 flex items-center justify-center text-ink shrink-0 mt-0.5">
        {icon}
      </div>
      <div>
        <p className="font-sans text-[13.5px] font-medium text-ink">{title}</p>
        <p className="font-sans text-[12.5px] text-ink-soft leading-snug mt-0.5">{text}</p>
      </div>
    </div>
  );
}
