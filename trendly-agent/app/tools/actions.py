"""
Tools that actually DO something (as opposed to just deciding/explaining),
per the assignment's "then act on it" requirement. In-memory stores here
stand in for what would be real backend writes (RMA system, wallet/ledger
service) in production — see SOLUTION.md.

Deliberately separate from returns.check_return_eligibility: eligibility
is a pure decision function; initiate_rma is the side-effecting action,
and it re-derives eligibility itself rather than trusting the caller, so
the model can't talk it into creating an RMA for something ineligible by
skipping a step.
"""
from __future__ import annotations
import itertools
from datetime import date, datetime, timezone
from app import db
from app.tools.orders import _get_order_raw
from app.tools.returns import check_return_eligibility

_start_rma = db.get_max_id_suffix("rmas", "rma_id", len("RMA-"))
_start_rma = max(5000, _start_rma) + 1 if _start_rma is not None else 5001
_rma_counter = itertools.count(_start_rma)

_start_credit = db.get_max_id_suffix("credits", "credit_id", len("CR-"))
_start_credit = max(9000, _start_credit) + 1 if _start_credit is not None else 9001
_credit_counter = itertools.count(_start_credit)

DELAY_THRESHOLD_DAYS = 3       # policy 1.5
DELAY_CREDIT_AMOUNT = 250      # policy 1.5


def initiate_rma(
    order_id: str,
    sku: str,
    request_type: str = "return",
    reason: str = "changed_mind",
    desired_exchange_size: str | None = None,
    has_original_box: bool | None = None,
    has_photos: bool | None = None,
) -> dict:
    """Creates a return/exchange request (RMA), but only if the item is
    actually eligible — re-checks eligibility internally rather than
    trusting a prior tool call, so eligibility and action can't drift apart
    across a multi-turn conversation."""
    elig = check_return_eligibility(
        order_id=order_id, sku=sku, request_type=request_type, reason=reason,
        desired_exchange_size=desired_exchange_size,
        has_original_box=has_original_box, has_photos=has_photos,
    )
    if not elig.get("eligible"):
        return {
            "created": False,
            "message": "Cannot create an RMA — this item isn't eligible. Explain why using "
                        "the eligibility result, and escalate if the customer wants to contest it.",
            "eligibility": elig,
        }

    item_result = next((i for i in elig["items"] if i["sku"] == sku), elig["items"][0])
    rma_id = f"RMA-{next(_rma_counter)}"
    record = {
        "rma_id": rma_id,
        "order_id": order_id,
        "sku": sku,
        "request_type": request_type,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pickup_scheduled" if request_type in ("return", "exchange") else "processing",
        "refund_estimate": item_result.get("refund_estimate"),
        "desired_exchange_size": desired_exchange_size,
    }
    db.save_record("rmas", rma_id, record)
    return {
        "created": True,
        "rma_id": rma_id,
        "message": (
            f"Created {request_type} request {rma_id}. Free reverse pickup will be scheduled "
            "(policy 5.1) — tell the customer to expect a pickup window, and that the carrier "
            "will attempt pickup up to 2 times."
        ),
        "record": record,
    }


def check_and_issue_delay_credit(order_id: str, today: date | None = None) -> dict:
    """Policy 1.5: orders more than 3 business days past their expected
    delivery date qualify for a ₹250 store credit on request, no
    cancellation needed. Approximates business days as calendar days minus
    weekends (see README limitations re: holiday calendars)."""
    order = _get_order_raw(order_id)
    if order is None:
        return {"issued": False, "reason_code": "order_not_found", "message": "No order found with that ID."}

    if order["status"] in ("delivered", "cancelled"):
        return {"issued": False, "reason_code": "not_applicable",
                 "message": f"Order is already {order['status']}; delay credit doesn't apply."}

    expected = order.get("expected_delivery_date")
    if not expected:
        return {"issued": False, "reason_code": "no_expected_date",
                 "message": "No expected delivery date on file to evaluate delay against."}

    expected_date = datetime.strptime(expected, "%Y-%m-%d").date()
    ref_today = today or date.today()
    calendar_days_late = (ref_today - expected_date).days
    business_days_late = sum(
        1 for d in range(calendar_days_late)
        if (expected_date.toordinal() + d + 1) % 7 not in (5, 6)  # rough weekend skip
    ) if calendar_days_late > 0 else 0

    if business_days_late <= DELAY_THRESHOLD_DAYS:
        return {
            "issued": False, "reason_code": "not_delayed_enough",
            "message": f"Order is ~{business_days_late} business day(s) past its expected "
                       f"delivery date; delay credit requires more than {DELAY_THRESHOLD_DAYS} (policy 1.5).",
        }

    credit_id = f"CR-{next(_credit_counter)}"
    credit_record = {
        "credit_id": credit_id, "order_id": order_id, "amount": DELAY_CREDIT_AMOUNT,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    db.save_record("credits", credit_id, credit_record)
    return {
        "issued": True, "credit_id": credit_id, "amount": DELAY_CREDIT_AMOUNT,
        "message": f"Issued ₹{DELAY_CREDIT_AMOUNT} store credit ({credit_id}) for the delayed order (policy 1.5).",
    }
