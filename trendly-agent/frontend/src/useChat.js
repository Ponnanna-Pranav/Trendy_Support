import { useState, useCallback } from "react";
import { sendMessage, resetSession } from "./api";

const WELCOME = {
  role: "assistant",
  text: "Hi, I'm Trendly Support. I can check an order, answer a shipping or returns question, or start a return/exchange. What do you need?",
  blocks: [],
};

export function useChat() {
  const [messages, setMessages] = useState([WELCOME]);
  const [sessionId, setSessionId] = useState(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const send = useCallback(
    async (text) => {
      if (!text.trim() || sending) return;
      setError(null);
      setMessages((m) => [...m, { role: "user", text, blocks: [] }]);
      setSending(true);
      try {
        const data = await sendMessage(text, sessionId);
        setSessionId(data.session_id);
        setMessages((m) => [...m, { role: "assistant", text: data.reply, blocks: data.blocks || [] }]);
      } catch (e) {
        setError(e.message || "Something went wrong.");
        setMessages((m) => [
          ...m,
          { role: "assistant", text: "Sorry, I hit an error reaching support. Please try again in a moment.", blocks: [] },
        ]);
      } finally {
        setSending(false);
      }
    },
    [sessionId, sending]
  );

  const reset = useCallback(async () => {
    await resetSession(sessionId);
    setSessionId(null);
    setMessages([WELCOME]);
    setError(null);
  }, [sessionId]);

  return { messages, send, sending, error, reset };
}
