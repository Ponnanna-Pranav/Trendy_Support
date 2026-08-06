"""
Agent orchestration.

Real tool-calling ReAct loop (not keyword matching): we hand the model a
tool schema, let it decide which tool(s) to call and in what order, execute
them, feed results back, and repeat until it produces a final answer or we
hit a safety cap on iterations (failure recovery: cap prevents infinite
tool-call loops; if hit, we force an escalation instead of silently failing).
"""
from __future__ import annotations
import json
import os
import logging
from typing import Any

# pyrefly: ignore [missing-import]
from groq import Groq

from app.prompts import SYSTEM_PROMPT
from app.tools.orders import get_order_status
from app.tools.policy import search_policy
from app.tools.returns import check_return_eligibility
from app.tools.actions import initiate_rma, check_and_issue_delay_credit
from app.tools.escalate import escalate_to_human

logger = logging.getLogger("trendly_agent")

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TOOL_ITERATIONS = 6

api_key = os.environ.get("GROQ_API_KEY")
if not api_key or api_key == "your_groq_api_key_here":
    client = Groq(api_key="dummy_key_please_configure_in_dot_env")
    IS_CONFIGURED = False
else:
    client = Groq(api_key=api_key)
    IS_CONFIGURED = True

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up an order's status, items, and tracking info. Requires "
                            "identity verification via order_id + the email on the order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "e.g. TRD-1001"},
                    "email": {"type": "string", "description": "Email on file for the order"},
                },
                "required": ["order_id", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search Trendly's shipping & returns policy document for relevant "
                            "sections. Always call this before answering any policy question — "
                            "never answer from general knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "description": "Number of sections to return", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_eligibility",
            "description": "Deterministically checks whether an order (or one item on it) is "
                            "eligible for a return or exchange under policy sections 2, 4, and "
                            "6. Always call this instead of reasoning about dates, categories, "
                            "or final-sale rules yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "request_type": {"type": "string", "enum": ["return", "exchange"]},
                    "reason": {
                        "type": "string",
                        "enum": ["changed_mind", "wrong_size", "damaged", "incorrect_item"],
                    },
                    "sku": {"type": "string", "description": "Optional: specific item SKU"},
                    "desired_exchange_size": {"type": "string", "description": "Only for exchanges"},
                    "has_original_box": {"type": "boolean", "description": "Footwear only (policy 2.5)"},
                    "has_photos": {"type": "boolean", "description": "Required for damaged/incorrect claims (policy 6.1)"},
                },
                "required": ["order_id", "request_type", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_rma",
            "description": "Creates an actual return/exchange request (RMA) once eligibility "
                            "is confirmed and you have the info needed (sku, and for damage "
                            "claims, photos confirmed). Re-checks eligibility itself, so only "
                            "call this after telling the customer the outcome, as the action "
                            "step of an already-decided return/exchange.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "sku": {"type": "string"},
                    "request_type": {"type": "string", "enum": ["return", "exchange"]},
                    "reason": {"type": "string", "enum": ["changed_mind", "wrong_size", "damaged", "incorrect_item"]},
                    "desired_exchange_size": {"type": "string"},
                    "has_original_box": {"type": "boolean"},
                    "has_photos": {"type": "boolean"},
                },
                "required": ["order_id", "sku", "request_type", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_and_issue_delay_credit",
            "description": "Policy 1.5: if an order is more than 3 business days past its "
                            "expected delivery date, issues a ₹250 store credit automatically "
                            "on request. Use when a customer asks about a late/delayed order.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Hand off the conversation to a human support agent with an "
                            "actionable summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "What the human needs to know to pick this up"},
                    "category": {
                        "type": "string",
                        "enum": ["policy_gap", "eligibility_dispute", "fraud_suspicion",
                                 "angry_customer", "lost_parcel", "cod_refund_bank_details",
                                 "technical_issue", "other"],
                    },
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"], "default": "normal"},
                    "order_id": {"type": "string"},
                },
                "required": ["summary", "category"],
            },
        },
    },
]

TOOL_IMPL = {
    "get_order_status": get_order_status,
    "search_policy": search_policy,
    "check_return_eligibility": check_return_eligibility,
    "initiate_rma": initiate_rma,
    "check_and_issue_delay_credit": check_and_issue_delay_credit,
    "escalate_to_human": escalate_to_human,
}


def _execute_tool(name: str, args: dict) -> dict:
    if name not in TOOL_IMPL:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return TOOL_IMPL[name](**args)
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001 - surface any tool failure back to the model
        logger.exception("Tool %s failed", name)
        return {"error": f"Tool {name} failed: {e}"}


def run_turn(history: list[dict], user_message: str) -> tuple[str, list[dict], list[dict]]:
    """Runs one user turn through the ReAct loop.

    Returns (assistant_text, updated_history, trace) where trace is a list of
    {tool, args, result} dicts for observability/debugging/demo purposes.
    """
    if not IS_CONFIGURED:
        new_history = history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": "GROQ_API_KEY not configured"}
        ]
        return (
            "Hello! The Trendly Support Agent is loaded, but the GROQ_API_KEY environment variable "
            "is not configured. Please add your Groq API key to the '.env' file in the project root directory "
            "and restart the server to enable chat functionality.",
            new_history,
            []
        )

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [
        {"role": "user", "content": user_message}
    ]
    trace: list[dict] = []

    for iteration in range(MAX_TOOL_ITERATIONS):
        # pyrefly: ignore [no-matching-overload]
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
        choice = resp.choices[0].message

        if not choice.tool_calls:
            final_text = choice.content or ""
            new_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": final_text},
            ]
            return final_text, new_history, trace

        # Model wants to call tool(s) — execute each and feed results back
        # pyrefly: ignore [bad-assignment]
        messages.append({
            "role": "assistant",
            "content": choice.content,
            "tool_calls": [tc.model_dump() for tc in choice.tool_calls],
        })
        for tc in choice.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            result = _execute_tool(tc.function.name, args)
            trace.append({"tool": tc.function.name, "args": args, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    # Hit the iteration cap without a final answer — fail safe by escalating
    # rather than looping forever or returning nothing.
    fallback_result = escalate_to_human(
        summary=f"Agent could not resolve after {MAX_TOOL_ITERATIONS} tool calls. "
                f"Last user message: {user_message}",
        category="technical_issue",
        priority="high",
    )
    trace.append({"tool": "escalate_to_human (auto, iteration cap)", "args": {}, "result": fallback_result})
    final_text = (
        "I'm having trouble resolving this on my own, so I've escalated it to our support "
        f"team — ticket {fallback_result['ticket_id']}. They'll follow up shortly."
    )
    new_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_text},
    ]
    return final_text, new_history, trace
