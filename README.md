# Trendly Support Agent

An agentic support assistant for D2C fashion retailers — order status, shipping questions,
policy Q&A, and return/exchange requests handled end to end by a real tool-calling agent, with
a polished embeddable chat widget and clean escalation to a human when it should hand off.

Originally built for the Yellow.ai FDE screening assignment; extended here into a deployable
product: persistent storage, an embeddable widget frontend, basic auth/rate-limiting, an admin
view, and Docker packaging.

## What's in the box

- **Agent backend** (`app/`) — FastAPI + a real ReAct tool-calling loop (Groq/Llama 3.3), 6
  tools, deterministic policy logic, SQLite persistence.
- **Widget frontend** (`frontend/`) — React + Tailwind. One build, two modes: a full-page demo
  ("try it" landing) and an embeddable floating-launcher widget for a storefront.
- **Embed loader** (`frontend/public/embed.js` → ships to `/embed.js`) — the one-line snippet a
  retailer drops on their site.
- **Admin visibility** — `/admin/tickets`, `/admin/rmas`, `/admin/credits`, key-protected.
- **Docker** — multi-stage build, `docker-compose.yml` for one-command self-hosting.

## Quick start (local, no Docker)

```bash
git clone <this-repo>
cd trendly-agent

# backend
pip install -r requirements.txt
cp .env.example .env        # add your GROQ_API_KEY — free: console.groq.com/keys

# frontend (only needed if you're changing the UI — a built copy already ships in /static)
cd frontend && npm install && npm run build && cd ..

# run
uvicorn app.main:app --reload
```

Open **http://localhost:8000** — full-page demo UI. Add `?embed=1&open=1` to preview widget mode
the way it'll look embedded on a storefront.

## Quick start (Docker — closer to how you'd actually ship this)

```bash
cp .env.example .env   # add GROQ_API_KEY at minimum
docker compose up --build
```

Same URL, same behavior, but built into a single container with a persistent volume for the
SQLite store (`trendly-data`), so escalated tickets/RMAs/credits survive container restarts.

## Embedding on a storefront

Once deployed, a retailer adds one line to their site:

```html
<script src="https://YOUR-DEPLOYED-URL/embed.js" data-base-url="https://YOUR-DEPLOYED-URL" async></script>
```

This injects a fixed-position iframe (bottom-right launcher bubble that expands into the chat
panel on click). It's iframe-based specifically so the host page and the widget never need
cross-origin DOM access — the same approach Intercom/Drift-style widgets use. Sizing is driven
by `postMessage` between the widget and the loader script (see `frontend/public/embed.js`).

## Architecture

```
app/
  main.py          FastAPI app: /chat, /reset, /health, /admin/*, rate limiting, CORS, auth
  agent.py          ReAct orchestration loop: model <-> tools, iteration cap, failure fallback
  prompts.py        System prompt — ground rules, escalation triggers, tool-chaining guidance
  db.py             SQLite persistence: sessions, tickets, RMAs, credits
  ui_blocks.py       Converts a turn's tool trace into structured cards for the frontend
  tools/
    orders.py         Order lookup + identity verification (order_id + email)
    policy.py          Policy grounding: chunk trendly_policy.md, semantic search (local
                        sentence-transformers; keyword fallback if offline or POLICY_SEARCH_MODE=keyword)
    returns.py          Deterministic return/exchange eligibility (policy sec 2, 4, 6)
    actions.py          Side-effecting tools: initiate_rma, check_and_issue_delay_credit (sec 1.5)
    escalate.py          Creates a human-actionable ticket
  data/
    trendly_policy.md   the real policy doc (provided)
    orders.json           PLACEHOLDER, see "Swapping in real data" below
frontend/
  src/App.jsx          switches between embed-widget mode and full-page demo mode (?embed=1)
  src/useChat.js         chat state / API calls
  src/components/        ChatPanel, Composer, MessageBubble, Launcher, BrandRail
  src/components/blocks/  structured "ticket stub" cards: order status, eligibility, RMA, etc.
  public/embed.js         the widget loader snippet (copied to /static/embed.js on build)
static/                built frontend output (committed, so `uvicorn app.main:app` alone serves
                        the full product without requiring a frontend build step first)
tests/
  test_tools.py             unit tests, deterministic logic, no API key needed
  test_agent_loop_mock.py    mocked-LLM tests of the ReAct loop plumbing, no API key needed
  test_conversations.py      scripted multi-turn conversations against a live server + real model
```

### Why tool-calling, not keyword matching

Each user turn goes through `app/agent.py::run_turn`, a real ReAct loop: the model sees a tool
schema, decides which tool(s) to call and with what arguments, we execute them, feed results back
as `tool` messages, and repeat until the model returns a final answer or hits a 6-iteration
safety cap (which auto-escalates rather than looping or returning nothing).

### Why some logic is deterministic Python, not model reasoning

Return eligibility depends on precise date math, category exclusions, final-sale rules, and a
footwear deduction — exactly what an LLM occasionally gets subtly wrong. `check_return_eligibility`
and `check_and_issue_delay_credit` are plain Python; the model's job is to gather the right inputs
and relay the result faithfully. The system prompt explicitly forbids it from computing eligibility
itself.

### Structured output, not raw JSON

`app/ui_blocks.py` turns the tool trace into typed blocks (`order_status`, `eligibility`, `rma`,
`delay_credit`, `escalation`, `policy_sources`) that the frontend renders as real UI — styled like
a garment tag / receipt stub, which is the frontend's one deliberate signature visual choice (see
"Design" below) rather than a chat bubble full of JSON.

### Persistence

Sessions, tickets, RMAs, and store credits are all in SQLite (`app/db.py`), so state survives a
process restart or redeploy — the thing an in-memory dict can't do. Good for a single-instance
deployment; graduate to Postgres (schema is trivial to port — see the table definitions in
`db.py`) once you need to run more than one backend instance behind a load balancer.

### Security posture (what's here vs. what production needs)

- **Identity verification on order lookup** — `get_order_status` requires `order_id` + the email
  on file; a mismatch returns a generic "couldn't verify" message rather than confirming which
  part was wrong, so the bot can't be used to enumerate valid IDs.
- **No bank details collected in chat** — enforced in the system prompt per policy 3.3.
- **Optional widget API key** — set `WIDGET_API_KEY`; `/chat` then requires `x-api-key`. Off by
  default so local dev / grading is frictionless.
- **Optional admin key** — `/admin/*` endpoints require `x-admin-key` matching `ADMIN_KEY`, always
  (no "off by default" here — unset `ADMIN_KEY` just means admin endpoints are unreachable).
- **Rate limiting** — simple per-IP fixed-window limiter (`RATE_LIMIT_PER_MINUTE`, default 30/min).
  Fine for one instance; move to a Redis-backed limiter (e.g. `slowapi` + Redis) once scaled out.
- **CORS** — defaults to `*` for convenience; set `ALLOWED_ORIGINS` to your actual storefront
  domain(s) before real production use.
- **What's genuinely missing for a commercial deployment:** real authentication/session tokens
  (currently anyone with a session_id can continue that session — fine for a support widget where
  the session_id itself isn't guessable and carries no more privilege than "continue this specific
  conversation", but worth knowing), multi-tenancy (this is single-retailer; see below), audit
  logging, and a real helpdesk integration instead of the in-app ticket table.

### Multi-tenancy note

This build is single-tenant (one policy doc, one order dataset, one brand). To actually sell this
to multiple retailers, the natural extension is: a `tenant_id` on every table in `db.py`, a
per-tenant `policy.md` + `orders` data source (swap the flat-file loaders in `orders.py`/`policy.py`
for a lookup keyed by tenant), and the embed script passing `data-tenant-id` so `/chat` knows which
tenant's policy/tools to load. Deliberately not built here — right-sized scope for "make the demo
credible," not "build the SaaS platform" — but the seams are exactly where you'd expect them.

### Design

Frontend design brief: this is a fashion retailer's support tool, so it should feel like an
editorial fashion brand, not generic SaaS blue. Ink black (`#15151A`) + paper white (`#F3F2EE`) +
a berry-magenta accent (`#C81E5C`); Fraunces (display serif) paired with Inter (UI) and IBM Plex
Mono for order/ticket IDs. The one deliberate signature element: structured data renders as a
perforated "ticket stub" (`frontend/src/components/blocks/TicketStub.jsx`) — a garment-tag/receipt
treatment that ties the UI to the actual subject matter (fashion retail returns) instead of a
templated chat-card look.

## Swapping in real data

`app/data/orders.json` currently contains **3 placeholder orders**, not the real 10-order fixed
dataset from the assignment Drive folder. To finish setup:

1. Download the real `orders.json`.
2. Drop it into `app/data/orders.json`, matching this schema (adjust `app/tools/orders.py`'s
   loader if field names differ):
   ```
   order_id, customer_email, customer_name, order_date, status, cancelled,
   delivered_date, expected_delivery_date, tracking_number,
   days_since_last_tracking_update, items: [{sku, name, size, qty, price,
   category, final_sale, footwear, exchange_count}]
   ```
3. Re-run `pytest tests/test_tools.py` — update the fixtures' expected dates/results to match.

`app/data/trendly_policy.md` is already the real policy document.

## Testing

```bash
# Deterministic logic, no API key needed (17 tests)
pytest tests/test_tools.py -v

# ReAct loop plumbing with a mocked LLM, no API key needed
python tests/test_agent_loop_mock.py

# Real scripted conversations against the real model (uses API quota)
uvicorn app.main:app &
python tests/test_conversations.py
```

## Deploying

**Render (simplest, matches the original assignment's ask):** `render.yaml` is pre-configured —
New -> Blueprint -> point at the repo -> add `GROQ_API_KEY` in the dashboard.

**Docker (anywhere — Fly.io, a VPS, Railway, ECS, etc.):**
```bash
docker build -t trendly-agent .
docker run -p 8000:8000 --env-file .env -v trendly-data:/app/data trendly-agent
```
Mount `/app/data` to a persistent volume so the SQLite store survives redeploys.

## AI usage note

Built with Claude (Anthropic) as a pair-programming collaborator: architecture, scaffolding,
the ReAct loop, tool implementations, the frontend, and prompt drafting were generated with
Claude and reviewed/adjusted by me. I made the policy-to-rule interpretation calls (e.g. how to
handle the final-sale x unavailable-exchange-size policy conflict — see `SOLUTION.md`) and
validated logic against the real policy doc and the test suite before treating it as done.

## Known limitations

See `SOLUTION.md` for architecture trade-offs and discovery questions, and `PROMPTS.md` for
prompt design notes and what still needs a live-model iteration pass.
