const BASE = import.meta.env.VITE_API_BASE || "";
const API_KEY = import.meta.env.VITE_WIDGET_API_KEY || null;

export async function sendMessage(message, sessionId) {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(API_KEY ? { "x-api-key": API_KEY } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function resetSession(sessionId) {
  if (!sessionId) return;
  await fetch(`${BASE}/reset?session_id=${encodeURIComponent(sessionId)}`, { method: "POST" });
}
