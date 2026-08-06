"""
Turns a turn's tool-call trace into structured "blocks" the frontend can
render as real UI (order status card, eligibility card, RMA stub, etc.)
instead of dumping raw tool JSON at the customer. Kept separate from
agent.py so the orchestration loop doesn't know or care how its output is
displayed — this is a pure presentation-layer concern.
"""
from __future__ import annotations


def trace_to_blocks(trace: list[dict]) -> list[dict]:
    blocks = []
    for t in trace:
        tool, result = t["tool"], t["result"]

        if tool == "get_order_status" and result.get("found"):
            blocks.append({"type": "order_status", "data": result})

        elif tool == "check_return_eligibility" and "reason_code" not in result:
            blocks.append({"type": "eligibility", "data": result})

        elif tool == "initiate_rma":
            blocks.append({"type": "rma", "data": result})

        elif tool == "check_and_issue_delay_credit":
            blocks.append({"type": "delay_credit", "data": result})

        elif tool.startswith("escalate_to_human"):
            blocks.append({"type": "escalation", "data": result})

        elif tool == "search_policy":
            sources = [
                {"title": r["title"], "section_id": r["section_id"]}
                for r in result.get("results", [])
            ]
            if sources:
                blocks.append({"type": "policy_sources", "data": {"sources": sources}})

    return blocks
