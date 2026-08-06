import React from "react";
import BlockRenderer from "./blocks/BlockRenderer";

export default function MessageBubble({ role, text, blocks }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-rise`}>
      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[86%]`}>
        {text && (
          <div
            className={
              isUser
                ? "bg-ink text-paper rounded-2xl rounded-br-sm px-4 py-2.5 text-[14px] leading-relaxed font-sans"
                : "bg-paper-raised text-ink rounded-2xl rounded-bl-sm px-4 py-2.5 text-[14px] leading-relaxed font-sans border border-ink/8"
            }
          >
            {text}
          </div>
        )}
        {!isUser && <BlockRenderer blocks={blocks} />}
      </div>
    </div>
  );
}
