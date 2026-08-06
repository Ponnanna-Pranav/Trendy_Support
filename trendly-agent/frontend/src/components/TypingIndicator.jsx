import React from "react";

export default function TypingIndicator() {
  return (
    <div className="flex justify-start animate-rise">
      <div className="bg-paper-raised border border-ink/8 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-ink/40 animate-pulseDot"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
