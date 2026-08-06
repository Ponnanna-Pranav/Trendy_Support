"""
Escalation tool.

Writes a ticket a human agent could actually act on: what the customer
wants, what's already been established (order/eligibility facts), and
why the bot couldn't resolve it. Persisted to SQLite (app/db.py) so tickets
survive a restart; in a larger production setup this would instead POST to
a real helpdesk (Zendesk/Freshdesk/etc.) — see README productization notes.
"""
from __future__ import annotations
import itertools
from datetime import datetime, timezone

from app import db

_start_ticket = db.get_max_id_suffix("tickets", "ticket_id", len("TCK-"))
_start_ticket = max(1000, _start_ticket) + 1 if _start_ticket is not None else 1001
_ticket_counter = itertools.count(_start_ticket)


def escalate_to_human(
    summary: str,
    category: str,
    priority: str = "normal",
    order_id: str | None = None,
) -> dict:
    """Tool entrypoint. category one of: policy_gap, eligibility_dispute,
    fraud_suspicion, angry_customer, lost_parcel, cod_refund_bank_details,
    technical_issue, other. priority one of: low, normal, high, urgent."""
    ticket_id = f"TCK-{next(_ticket_counter)}"
    ticket = {
        "ticket_id": ticket_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "category": category,
        "priority": priority,
        "order_id": order_id,
        "status": "open",
    }
    db.save_record("tickets", ticket_id, ticket)
    return {
        "ticket_id": ticket_id,
        "message": (
            f"Escalated to a human agent as ticket {ticket_id}. Tell the customer "
            "a support specialist will follow up, and share the ticket ID."
        ),
    }


def get_ticket(ticket_id: str) -> dict | None:
    return db.get_record("tickets", ticket_id)
