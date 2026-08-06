import React, { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel";
import Launcher from "./components/Launcher";
import BrandRail from "./components/BrandRail";

const params = new URLSearchParams(window.location.search);
const EMBED_MODE = params.get("embed") === "1";

function WidgetApp() {
  const [open, setOpen] = useState(params.get("open") === "1");

  const toggle = () => {
    const next = !open;
    setOpen(next);
    window.parent?.postMessage({ source: "trendly-widget", type: "toggle", open: next }, "*");
  };

  useEffect(() => {
    window.parent?.postMessage({ source: "trendly-widget", type: "ready" }, "*");
  }, []);

  return (
    <div className="h-screen w-screen flex items-end justify-end p-4">
      {open && (
        <div className="mb-3 w-[380px] h-[600px] max-h-[85vh]">
          <ChatPanel onClose={toggle} />
        </div>
      )}
      <div className="absolute bottom-4 right-4">
        <Launcher open={open} onToggle={toggle} />
      </div>
    </div>
  );
}

function FullPageApp() {
  return (
    <div className="min-h-screen bg-paper flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-5xl grid lg:grid-cols-[1fr_420px] gap-8 items-stretch">
        <BrandRail />
        <div className="h-[680px] max-h-[85vh] w-full mx-auto">
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return EMBED_MODE ? <WidgetApp /> : <FullPageApp />;
}
