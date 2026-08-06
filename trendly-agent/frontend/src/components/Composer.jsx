import React, { useRef } from "react";
import { ArrowUp } from "lucide-react";

export default function Composer({ value, onChange, onSend, disabled, suggestions = [] }) {
  const ref = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-rule px-3 pt-2.5 pb-3 bg-paper">
      {suggestions.length > 0 && (
        <div className="flex gap-1.5 mb-2 overflow-x-auto scrollbar-thin pb-0.5">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onChange(s)}
              className="shrink-0 text-[12px] font-sans text-ink-soft border border-ink/15 rounded-full px-3 py-1 hover:bg-ink/5 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2 bg-paper-raised border border-ink/12 rounded-2xl px-3 py-2 focus-within:border-ink/30 transition-colors">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Trendly Support…"
          className="flex-1 resize-none bg-transparent outline-none text-[14px] font-sans text-ink placeholder:text-ink-soft/60 max-h-28 py-1"
        />
        <button
          onClick={onSend}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
          className="shrink-0 h-8 w-8 rounded-full bg-ink text-paper flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:bg-ink-soft transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-berry"
        >
          <ArrowUp size={16} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  );
}
