import React from "react";
import { MessageCircle, X } from "lucide-react";

export default function Launcher({ open, onToggle }) {
  return (
    <button
      onClick={onToggle}
      aria-label={open ? "Close support chat" : "Open support chat"}
      className="h-14 w-14 rounded-full bg-ink text-paper shadow-launcher flex items-center justify-center hover:scale-105 active:scale-95 transition-transform focus-visible:outline focus-visible:outline-2 focus-visible:outline-berry focus-visible:outline-offset-2"
    >
      {open ? <X size={22} /> : <MessageCircle size={22} />}
    </button>
  );
}
