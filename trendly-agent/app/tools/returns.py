"""
Return/exchange eligibility + resolution tool, implementing trendly_policy.md
sections 2 (Returns), 3 (Refunds), 4 (Exchanges), and 6 (Damaged/wrong items).

Why this is deterministic code and not left to the LLM: date-window math,
category exclusions, final-sale exchange-only logic, footwear deductions,
and shipping-fee-refund conditions are exactly the kind of multi-condition
rules an LLM will occasionally get subtly wrong — and getting them wrong
here means either wrongly denying a customer or promising something Trendly
policy doesn't allow (an "unauthorized discount" failure mode). So the model's
job is to gather the inputs this function needs and relay its output
faithfully, not to compute eligibility itself.

Known policy ambiguity (flagged rather than silently resolved — see
SOLUTION.md discovery questions): section 4.3 says an exchange with an
unavailable size auto-converts to a refund, but section 2.4 says final-sale
items get no refund ever. We don't guess; we escalate that specific
combination to a human.
"""
from __future__ import annotations
from datetime import date, datetime

from app.tools.orders import _get_order_raw

# Policy 2.3 — non-returnable categories (standard return/exchange only;
# damage/incorrect-item claims under section 6 override this exclusion).
NON_RETURNABLE_CATEGORIES = {"innerwear", "socks", "jewellery", "beauty", "fragrance", "face_masks", "gift_cards"}

STANDARD_RETURN_WINDOW_DAYS = 30          # 2.1
DAMAGE_REPORT_WINDOW_HOURS = 48           # 6.1 (approximated as 2 calendar days — see README)
FOOTWEAR_NO_BOX_DEDUCTION = 300           # 2.5
EXCHANGE_LIMIT_PER_ITEM = 1               # 4.4


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _evaluate_item(
    item: dict,
    days_since_delivery: int,
    request_type: str,
    reason: str,
    desired_exchange_size: str | None,
    has_original_box: bool | None,
    has_photos: bool | None,
) -> dict:
    name, sku = item["name"], item["sku"]
    is_damage_claim = reason in ("damaged", "incorrect_item")

    # --- Damage / incorrect item path (policy section 6) ---
    if is_damage_claim:
        damage_window_days = 2  # 48h approximation, see module docstring
        if days_since_delivery > damage_window_days:
            return _deny(sku, name, "damage_report_window_expired",
                         f"Damaged/incorrect item reports must be made within 48 hours of "
                         f"delivery; this was delivered {days_since_delivery} day(s) ago.")
        result = _approve(sku, name, "damage_or_incorrect_confirmed",
                           "Eligible for a free replacement or a full refund including "
                           "shipping, customer's choice (policy 6.2). Non-returnable "
                           "categories are covered under this claim type.")
        if not has_photos:
            result["action_required"] = "Ask the customer for photos before processing (policy 6.1)."
        return result

    # --- Standard return/exchange path (policy sections 2 & 4) ---
    if item.get("category") in NON_RETURNABLE_CATEGORIES:
        return _deny(sku, name, "non_returnable_category",
                     f"{name} is in a non-returnable category ({item.get('category')}) per "
                     "policy 2.3 and can't be returned or exchanged for a standard reason.")

    if days_since_delivery > STANDARD_RETURN_WINDOW_DAYS:
        return _deny(sku, name, "window_expired",
                     f"Delivered {days_since_delivery} day(s) ago; the 30-day return window "
                     "(policy 2.1) has passed. No exceptions apply.")

    is_final_sale = bool(item.get("final_sale"))

    if request_type == "return":
        if is_final_sale:
            return _deny(sku, name, "final_sale_exchange_only",
                         f"{name} is final sale — eligible for a size exchange only, "
                         "not a refund or store credit (policy 2.4).")
        deduction = 0
        note = None
        if item.get("footwear"):
            if has_original_box is False:
                deduction = FOOTWEAR_NO_BOX_DEDUCTION
                note = f"₹{FOOTWEAR_NO_BOX_DEDUCTION} deducted for missing original shoe box (policy 2.5)."
            elif has_original_box is None:
                note = "Ask whether the original shoe box is available — affects refund amount (policy 2.5)."
        refund_amount = max(item["price"] - deduction, 0)
        result = _approve(sku, name, "return_eligible",
                           f"Eligible for return. Refund estimate: ₹{refund_amount} to original "
                           "payment method 3–7 business days after inspection (policy 3.1). "
                           "Original shipping fee is not refunded for change-of-mind returns (policy 3.2).")
        result["refund_estimate"] = refund_amount
        if note:
            result["note"] = note
        return result

    if request_type == "exchange":
        if item.get("exchange_count", 0) >= EXCHANGE_LIMIT_PER_ITEM:
            return _deny(sku, name, "exchange_limit_reached",
                         f"{name} has already used its one allowed exchange (policy 4.4). "
                         "A second exchange needs human approval — escalate.")
        result = _approve(sku, name, "exchange_eligible",
                           f"Eligible for a size exchange (policy 4.2). Requested size: "
                           f"{desired_exchange_size or 'not yet specified'}.")
        if is_final_sale:
            result["note"] = ("Final sale item: if the requested size is unavailable, policy "
                               "conflicts (4.3 says auto-refund, 2.4 says final-sale items get "
                               "no refund) — escalate to a human rather than deciding either way.")
        else:
            result["note"] = "If requested size is unavailable, this auto-converts to a refund (policy 4.3)."
        return result

    return _deny(sku, name, "invalid_request_type", "request_type must be 'return' or 'exchange'.")


def _approve(sku, name, code, message) -> dict:
    return {"sku": sku, "name": name, "eligible": True, "reason_code": code, "message": message}


def _deny(sku, name, code, message) -> dict:
    return {"sku": sku, "name": name, "eligible": False, "reason_code": code, "message": message}


def check_return_eligibility(
    order_id: str,
    request_type: str = "return",
    reason: str = "changed_mind",
    sku: str | None = None,
    desired_exchange_size: str | None = None,
    has_original_box: bool | None = None,
    has_photos: bool | None = None,
    today: date | None = None,
) -> dict:
    """Tool entrypoint.

    request_type: 'return' or 'exchange'
    reason: 'changed_mind' | 'wrong_size' | 'damaged' | 'incorrect_item'
    sku: optional, limit evaluation to one item on the order
    desired_exchange_size, has_original_box, has_photos: gather these from
      the customer when relevant; pass None if not yet known.
    """
    order = _get_order_raw(order_id)
    if order is None:
        return {"eligible": False, "reason_code": "order_not_found",
                "message": "No order found with that ID."}

    if order.get("cancelled"):
        return {"eligible": False, "reason_code": "order_cancelled",
                "message": "This order was cancelled; no return can be raised against it (policy 2.6)."}

    if order["status"] != "delivered" or not order.get("delivered_date"):
        return {"eligible": False, "reason_code": "not_yet_delivered",
                "message": f"Order status is '{order['status']}' — items can only be returned "
                           "after delivery."}

    items = order["items"]
    if sku:
        items = [i for i in items if i["sku"] == sku]
        if not items:
            return {"eligible": False, "reason_code": "item_not_found",
                     "message": "That item wasn't found on this order."}

    delivered = _parse_date(order["delivered_date"])
    ref_today = today or date.today()
    days_since_delivery = (ref_today - delivered).days

    item_results = [
        _evaluate_item(item, days_since_delivery, request_type, reason,
                        desired_exchange_size, has_original_box, has_photos)
        for item in items
    ]

    return {
        "order_id": order_id,
        "request_type": request_type,
        "reason": reason,
        "days_since_delivery": days_since_delivery,
        "items": item_results,
        "eligible": any(r["eligible"] for r in item_results),
    }
