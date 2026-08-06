from __future__ import annotations
import os
import time
import uuid
import logging
from collections import defaultdict, deque

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import db
from app.agent import run_turn
from app.ui_blocks import trace_to_blocks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trendly.main")

app = FastAPI(title="Trendly Support Agent")

# CORS: comma-separated origin list in prod (e.g. "https://trendly.com,https://www.trendly.com").
# Defaults to "*" for local dev / the assignment demo — tighten this before real production use.
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allowed_origins == "*" else [o.strip() for o in _allowed_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- optional widget API key (off by default so local dev / grading is frictionless) ----
WIDGET_API_KEY = os.environ.get("WIDGET_API_KEY")  # set this in production to require it
if WIDGET_API_KEY:
    WIDGET_API_KEY = WIDGET_API_KEY.strip()
    if not WIDGET_API_KEY or WIDGET_API_KEY.startswith("#"):
        WIDGET_API_KEY = None

ADMIN_KEY = os.environ.get("ADMIN_KEY")  # required for /admin endpoints regardless
if ADMIN_KEY:
    ADMIN_KEY = ADMIN_KEY.strip()
    if not ADMIN_KEY or ADMIN_KEY.startswith("#"):
        ADMIN_KEY = None

# ---- minimal in-memory rate limiter (fixed window per IP) ----
# Fine for a single-process deploy; swap for Redis-backed limiting (e.g. slowapi
# with a redis backend) once running more than one instance.
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "30"))
_hits: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(key: str):
    now = time.time()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down.")
    q.append(now)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    trace: list[dict]
    blocks: list[dict]


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, x_api_key: str | None = Header(default=None)):
    if WIDGET_API_KEY and x_api_key != WIDGET_API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")

    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty.")
    if len(req.message) > 4000:
        raise HTTPException(status_code=400, detail="message too long (max 4000 chars).")

    session_id = req.session_id or str(uuid.uuid4())
    history = db.get_session(session_id)

    try:
        reply, new_history, trace = run_turn(history, req.message)
    except Exception:
        logger.exception("Agent turn failed for session %s", session_id)
        raise HTTPException(status_code=500, detail="Something went wrong on our end. Please try again.")

    db.save_session(session_id, new_history)
    blocks = trace_to_blocks(trace)
    return ChatResponse(session_id=session_id, reply=reply, trace=trace, blocks=blocks)


@app.post("/reset")
def reset(session_id: str):
    db.delete_session(session_id)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---- minimal admin visibility into escalations/RMAs/credits ----

def _require_admin(x_admin_key: str | None):
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid admin key.")


@app.get("/admin/tickets")
def admin_tickets(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    return db.list_records("tickets")


@app.get("/admin/rmas")
def admin_rmas(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    return db.list_records("rmas")


@app.get("/admin/credits")
def admin_credits(x_admin_key: str | None = Header(default=None)):
    _require_admin(x_admin_key)
    return db.list_records("credits")


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# ---- static frontend (built React app lands in /static — see frontend/README) ----
if os.path.isdir("static") and os.path.exists("static/index.html"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    @app.get("/")
    def index():
        return JSONResponse({"message": "Frontend not built yet. Run `npm run build` in /frontend, "
                                         "or use the API directly at POST /chat."})
