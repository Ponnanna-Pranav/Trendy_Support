# PROMPTS.md

This documents the system prompt (`app/prompts.py`), the tool-schema design choices that affect
model behavior as much as the prompt does, and how/why each was iterated. Built collaboratively
with Claude; the policy-to-rule interpretation calls and the iteration decisions below are mine.

## Full current system prompt

See `app/prompts.py::SYSTEM_PROMPT` — reproduced here isn't useful since it'll drift out of sync;
read it there.

## Design principles behind it

1. **Numbered, non-negotiable "ground rules" up top.** Models weight instructions unevenly
   across a long prompt; the five failure modes that matter most (invented policy, self-computed
   eligibility, unauthorized discounts, data leakage, fabricated IDs) are listed first, each as
   its own numbered rule, rather than buried in prose. Each rule names the *specific tool* that
   makes it enforceable (e.g. "never decide eligibility yourself → always call
   check_return_eligibility"), so the rule and the mechanism to follow it sit together.

2. **Escalation is a single consolidated list of triggers, not scattered mentions.** Early drafts
   mentioned escalation in three different places (data leakage section, refusal section, general
   guidance) and reading through resulting transcripts, this produced inconsistent escalation
   *categories* — the model would pick `other` for things that clearly matched `policy_gap` or
   `eligibility_dispute` because the mapping wasn't spelled out in one place. Consolidating into
   one list, each trigger paired with the category to use, fixed this.

3. **Tool descriptions carry real prompt-engineering weight.** For tool-calling models, the
   function `description` field is functionally part of the prompt — it's what the model reads
   when deciding *whether* to call a tool at all. E.g. `check_return_eligibility`'s description
   explicitly says "Always call this instead of reasoning about dates, categories, or final-sale
   rules yourself" — that instruction lives on the tool, not just in the system prompt, because
   the decision of *which* tool to reach for happens at the tool-selection step, not after.

4. **Known policy ambiguity is named, not silently resolved.** Policy §4.3 (unavailable exchange
   size auto-converts to refund) conflicts with §2.4 (final-sale items never get a refund) for the
   specific case of a final-sale item whose requested exchange size is out of stock. Rather than
   picking a side in code or in the prompt, `check_return_eligibility` flags the conflict in its
   output and the system prompt tells the model to escalate that specific combination rather than
   decide it. This was a deliberate "handle uncertainty" choice per the assignment brief, and it's
   the kind of thing worth raising with Trendly's ops team directly (see SOLUTION.md).

## Tool schema iteration

- **`reason` as a closed enum, not free text.** First draft let the model pass a free-text reason
  string into `check_return_eligibility`. That pushes categorization work onto the eligibility
  function (string-matching on "damaged", "broke", "arrived broken", etc. — fragile) and hides a
  decision the *model* is well-suited to make (which policy bucket does this fall into) inside a
  brittle string parser. Switched to an enum (`changed_mind | wrong_size | damaged |
  incorrect_item`) so the model does the classification (its strength) and the tool does the date
  math and rule application (its strength).
- **`initiate_rma` re-checks eligibility internally** rather than accepting a `confirmed_eligible`
  boolean from the model. Trusting the model's prior turn to be honest about eligibility is exactly
  the kind of gap a multi-turn conversation could drift through (e.g. the model checks eligibility,
  then several turns later the customer asks it to "just process it anyway" and if `initiate_rma`
  trusted the caller, a sufficiently leading prompt could talk it into creating an RMA for
  something ineligible). Re-deriving eligibility inside the action tool closes that gap
  structurally instead of relying on the prompt to hold the line.
- **`get_order_status` requires `email`, not just `order_id`.** Sequential order IDs
  (`TRD-1001`, `TRD-1002`, ...) are trivially enumerable; requiring a second factor and returning
  a generic "couldn't verify" message (not "wrong email" vs "order not found") prevents using the
  bot to enumerate valid IDs or emails.

## What still needs a live-model iteration pass

I designed and unit-tested every deterministic path (17 passing tests in `tests/test_tools.py`,
plus offline mocked-LLM tests of the orchestration loop in `tests/test_agent_loop_mock.py`), but
I did not have a live Groq API key in the environment I built this in, so the prompt above has
**not yet been iterated against real model outputs**. Before submitting:

1. Run `python tests/test_conversations.py` against the running server with a real `GROQ_API_KEY`.
2. Read every transcript, not just pass/fail — specifically watch for:
   - Does the model ask for `email` before calling `get_order_status`, or does it guess/skip?
   - Does it pick the right `escalate_to_human` category, or default to `other` too often?
   - Does it call `initiate_rma` after explaining eligibility, or just describe what it *would*
     do without acting? (The prompt says "don't just describe it, do it" — verify this lands.)
   - Any case where it answers a policy question without calling `search_policy` first? (Check
     the trace — if there's a text answer with no preceding `search_policy` call, that's a
     grounding failure.)
3. Log any observed failure here with the fix you made, e.g.:
   ```
   Observed: model answered "yes, footwear needs the box" without calling search_policy first
             when the customer had already asked about footwear returns two turns earlier.
   Fix: reworded rule 1 to "always call search_policy first" (not "before answering policy
        questions", which the model apparently read as "only the first time in a session").
   ```
