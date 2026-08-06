# SOLUTION.md

## Architecture

FastAPI service exposing one core endpoint (`POST /chat`), backed by a ReAct-style orchestration
loop (`app/agent.py`) that calls Llama 3.3 70B via Groq's free API with a 4-tool schema:
`get_order_status`, `search_policy`, `check_return_eligibility`, `initiate_rma`,
`check_and_issue_delay_credit`, `escalate_to_human`. The model decides which tools to call and in
what order per turn; results feed back as tool messages until it produces a final answer or hits
a 6-call iteration cap.

Three design choices define most of the system:

- **Split reasoning from computation.** The model classifies intent and reason (its strength);
  deterministic Python computes dates, eligibility, refund amounts, and delay windows (a
  strength models don't reliably have — off-by-one errors on a 30-day window or a forgotten
  final-sale exception are exactly the failure mode this assignment is designed to catch).
- **Grounding is structural, not just instructional.** Policy answers require a `search_policy`
  tool call returning actual chunk text; the system prompt forbids answering from the model's own
  knowledge. This is enforceable in the sense that a reviewer can check the tool trace — if a
  policy claim in the reply has no preceding `search_policy` call, that's a visible failure, not
  a hidden one.
- **Actions re-derive their own preconditions.** `initiate_rma` re-checks eligibility internally
  rather than trusting a prior turn's result, so a multi-turn conversation can't talk the system
  into an inconsistent state (decide "ineligible" in one turn, get argued into "just do it anyway"
  three turns later).

## Key trade-offs

- **In-memory session state and in-memory RMA/ticket/credit stores**, not a real database. Correct
  for a single-process demo; wrong for production (state is lost on restart, doesn't scale
  horizontally). Chose this to keep the assignment's scope to orchestration and prompt
  engineering rather than infra.
- **Local sentence-transformer for policy retrieval instead of an embeddings API.** Free (no
  cost, per the assignment constraint), runs on CPU, and small enough (6 policy sections) that
  retrieval quality isn't really the bottleneck here — but it does mean an extra ~90MB model
  download on first run, and I added a keyword-overlap fallback for environments without
  internet access to huggingface.co, which trades some retrieval quality for the system never
  hard-failing.
- **48-hour damage-report window approximated as 2 calendar days.** The policy specifies hours;
  order data only has a delivery *date*, not a timestamp. A real implementation would need
  delivery timestamps to enforce this precisely — flagged as a discovery question below rather
  than silently rounding and hoping it's close enough.
- **Business-day math for the delay-credit rule (§1.5) is a rough weekend-skip, not a real
  calendar.** No holiday calendar was provided; see discovery questions.
- **Deterministic rules over an LLM-graded rubric for eligibility**, even though this makes the
  system less flexible to policy wording changes than an LLM-only approach would be. Chose
  correctness and auditability over flexibility, since wrong eligibility calls have direct
  financial/trust consequences.

## Known limitations

- `orders.json` in this repo is placeholder data (3 orders, invented schema) — see README
  "Swapping in real data." The real 10-order dataset wasn't accessible programmatically from the
  assignment's Drive link, and it needs to be dropped in before this is truly done.
- No stock/inventory data source exists, so exchange requests can't actually verify the requested
  size is available — the tool notes this rather than guessing, and flags the specific
  final-sale × unavailable-size policy conflict (§4.3 vs §2.4) for human escalation instead of
  picking a side.
- No authentication beyond order_id + email matching — fine for a screening assignment, not
  sufficient for production (no rate limiting, no session expiry, no real identity provider).
- The demo video shows one thing that doesn't work — see the video for specifics; broadly, the
  weakest area is the 48-hour vs. calendar-date approximation above, and anything requiring a
  business-day calendar with actual Indian public holidays.
- No load testing done. 2,000 chats/day (~1.4/minute average, but real traffic isn't uniform)
  is well within what a single small instance + Groq's free tier can plausibly handle for a demo,
  but free-tier rate limits haven't been stress-tested here.

## Five discovery questions for Trendly's ops team

1. **What's the actual data source for order status/tracking in production** — a WMS, a carrier
   API, Shopify/similar, something else — and does it expose delivery *timestamps* (not just
   dates), which the 48-hour damage-report window and the lost-parcel/delay-credit rules both
   need to be enforced precisely rather than approximated?
2. **When the policy is silent or self-contradictory** (e.g. final-sale item + unavailable
   exchange size — §4.3 vs §2.4), who actually makes that call today, and what's the resolution
   in practice? I chose to escalate rather than guess; want to confirm that's the right default
   rather than, say, always favoring the customer or always favoring "no refund on final sale."
3. **What does the human agent's tooling look like on the other side of an escalation** — do
   they need the full conversation transcript, or is a structured summary (what I'm generating
   now) enough? Should escalation push into an existing helpdesk (Zendesk/Freshdesk/etc.) via API
   rather than sit in an internal queue?
4. **What's the actual daily/peak traffic shape**, not just the 2,000/day average — support chat
   volume is rarely uniform, and knowing peak concurrency changes both the free-tier LLM choice
   (rate limits) and whether in-memory session state is viable even as a bridge to a real
   deployment, or whether Redis/similar is needed from day one.
5. **Is there a public holiday calendar or business-day definition** to use for the §1.5 delay
   threshold and any other business-day-based rule, and does it vary by shipping region (the
   policy distinguishes metro/non-metro/remote delivery estimates, so plausibly yes)?
