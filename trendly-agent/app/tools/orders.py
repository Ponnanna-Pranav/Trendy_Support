"""
Order lookup tool.

Design note on data leakage: a support bot that lets anyone type any
order_id and get full order + customer details is a data leakage bug
waiting to happen. We require the caller to also supply the email on
file for the order. If it doesn't match, we return a generic "verification
failed" result instead of any order details (and don't reveal *why* —
e.g. we don't say "wrong email" vs "order not found", so the tool can't be
used to enumerate valid order IDs or emails).
"""
from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache

ORDERS_PATH = Path(__file__).parent.parent / "data" / "orders.json"


@lru_cache(maxsize=1)
def _load_orders() -> dict:
    data = json.loads(ORDERS_PATH.read_text(encoding="utf-8"))

    # Build customer lookup: customer_id -> customer dict
    customers = {c["customer_id"]: c for c in data.get("customers", [])}

    orders = {}
    for o in data["orders"]:
        # Normalize to internal schema the rest of the code expects
        cid = o.get("customer_id")
        customer = customers.get(cid, {})

        # Derive footwear flag from category on items
        items = []
        for item in o.get("items", []):
            normalized_item = {
                "sku": item.get("sku"),
                "name": item.get("name"),
                "size": item.get("size"),
                "qty": item.get("qty", 1),
                "price": item.get("price", 0),
                "category": item.get("category", "apparel"),
                "final_sale": item.get("final_sale", False),
                "footwear": item.get("category", "").lower() == "footwear",
                "exchange_count": item.get("exchange_count", 0),
            }
            items.append(normalized_item)

        # Normalize dates: real schema uses placed_at / delivered_at (ISO timestamps)
        def _date_only(val):
            if not val:
                return None
            return str(val)[:10]  # take YYYY-MM-DD prefix from ISO timestamp

        normalized = {
            "order_id": o["order_id"],
            "customer_email": customer.get("email", ""),
            "customer_name": customer.get("name", ""),
            "order_date": _date_only(o.get("placed_at")),
            "status": o.get("status", "unknown"),
            # Real schema uses "cancelled" status rather than a boolean flag
            "cancelled": o.get("status") == "cancelled",
            "delivered_date": _date_only(o.get("delivered_at")),
            "expected_delivery_date": _date_only(o.get("expected_delivery")),
            "tracking_number": o.get("tracking_number"),
            "days_since_last_tracking_update": o.get("days_since_last_tracking_update", 0),
            "shipping_fee_paid": o.get("shipping_fee", 0),
            "payment_method": o.get("payment_method"),
            "items": items,
        }
        orders[o["order_id"].upper()] = normalized

    return orders


def get_order_status(order_id: str, email: str) -> dict:
    """Tool entrypoint. Requires order_id + the email on file to prevent
    unauthorized lookups of other customers' orders."""
    orders = _load_orders()
    order = orders.get(order_id.strip().upper())

    if not order or order["customer_email"].lower() != email.strip().lower():
        return {
            "found": False,
            "message": (
                "Could not verify an order with that order ID and email combination. "
                "Ask the customer to double check both, or offer to escalate if they're "
                "confident the details are correct."
            ),
        }

    tracking_stale_days = order.get("days_since_last_tracking_update") or 0
    possible_lost_parcel = (
        order["status"] not in ("delivered", "cancelled")
        and (order["status"] == "lost_in_transit" or tracking_stale_days >= 10)
    )

    return {
        "found": True,
        "order_id": order["order_id"],
        "status": order["status"],
        "cancelled": order.get("cancelled", False),
        "possible_lost_parcel": possible_lost_parcel,
        "note": (
            "No tracking movement for 10+ days — per policy 1.6 this is a lost-parcel "
            "claim, not a return. Escalate to a human; don't try to resolve it yourself."
            if possible_lost_parcel else None
        ),
        "order_date": order["order_date"],
        "delivered_date": order.get("delivered_date"),
        "expected_delivery_date": order.get("expected_delivery_date"),
        "tracking_number": order.get("tracking_number"),
        "days_since_last_tracking_update": order.get("days_since_last_tracking_update"),
        "shipping_fee_paid": order.get("shipping_fee_paid"),
        "payment_method": order.get("payment_method"),
        "items": order["items"],
    }


def _get_order_raw(order_id: str) -> dict | None:
    """Internal helper (not an LLM tool) used by the returns-eligibility tool,
    which already operates within a verified session."""
    return _load_orders().get(order_id.strip().upper())


