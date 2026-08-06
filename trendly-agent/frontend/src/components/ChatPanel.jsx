import React, { useEffect, useRef, useState } from "react";
import { X, RotateCcw, Minus } from "lucide-react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import Composer from "./Composer";
import { useChat } from "../useChat";

const SUGGESTIONS = ["Where's my order?", "Start a return", "Return window?", "Talk to a human"];

export default function ChatPanel({ onClose, embedded = false }) {
  const { messages, send, sending, reset } = useChat();
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = () => {
    const text = draft;
    setDraft("");
    send(text);
  };

  return (
    <div
      className={
        embedded
          ? "flex flex-col h-full w-full bg-paper"
          : "flex flex-col h-full w-full bg-paper rounded-card shadow-panel border border-ink/10 overflow-hidden animate-panelIn"
      }
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-rule bg-paper-raised">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-full bg-ink flex items-center justify-center">
            <span className="font-display text-paper text-[15px]">T</span>
          </div>
          <div>
            <p className="font-display text-[15px] text-ink leading-none">Trendly Support</p>
            <p className="text-[11px] text-moss mt-0.5 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-moss inline-block" /> Online now
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={reset}
            aria-label="Reset conversation"
            className="h-8 w-8 rounded-full flex items-center justify-center text-ink-soft hover:bg-ink/5 transition-colors"
            title="Start over"
          >
            <RotateCcw size={15} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close chat"
              className="h-8 w-8 rounded-full flex items-center justify-center text-ink-soft hover:bg-ink/5 transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin px-3.5 py-4 flex flex-col gap-3">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} text={m.text} blocks={m.blocks} />
        ))}
        {sending && <TypingIndicator />}
      </div>

      <Composer value={draft} onChange={setDraft} onSend={handleSend} disabled={sending} suggestions={messages.length <= 1 ? SUGGESTIONS : []} />
    </div>
  );
}
