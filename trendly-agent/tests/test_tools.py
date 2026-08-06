"""
Unit tests for the deterministic tools — no LLM/API key required.
Run with: pytest tests/test_tools.py -v
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.orders import get_order_status
from app.tools.returns import check_return_eligibility
from app.tools.actions import initiate_rma, check_and_issue_delay_credit
from app.tools.policy import search_policy


# ---- order lookup / data leakage ----

def test_order_lookup_success():
    r = get_order_status("TRD-1001", "priya.sharma@example.com")
    assert r["found"] is True
    assert r["status"] == "delivered"


def test_order_lookup_wrong_email_blocked():
    r = get_order_status("TRD-1001", "someone.else@example.com")
    assert r["found"] is False
    assert "priya" not in r["message"].lower()


def test_order_lookup_nonexistent():
    r = get_order_status("TRD-9999", "nobody@example.com")
    assert r["found"] is False


def test_possible_lost_parcel_flagged():
    # TRD-1002 is in_transit with 11 days of no tracking movement
    r = get_order_status("TRD-1002", "arjun.mehta@example.com")
    assert r["possible_lost_parcel"] is True


# ---- return eligibility (policy 2.1) ----

def test_return_eligible_within_30_day_window():
    r = check_return_eligibility("TRD-1001", request_type="return", reason="changed_mind",
                                  today=date(2026, 7, 25))
    assert r["eligible"] is True
    assert r["items"][0]["refund_estimate"] == 1899


def test_return_ineligible_outside_30_day_window():
    r = check_return_eligibility("TRD-1001", request_type="return", reason="changed_mind",
                                  today=date(2026, 9, 1))
    assert r["eligible"] is False
    assert r["items"][0]["reason_code"] == "window_expired"


def test_return_not_yet_delivered():
    r = check_return_eligibility("TRD-1002", request_type="return", reason="changed_mind")
    assert r["eligible"] is False
    assert r["reason_code"] == "not_yet_delivered"


# ---- final sale (policy 2.4) ----

def test_final_sale_return_denied():
    r = check_return_eligibility("TRD-1003", request_type="return", reason="changed_mind",
                                  today=date(2026, 6, 10))
    assert r["eligible"] is False
    assert r["items"][0]["reason_code"] == "final_sale_exchange_only"


def test_final_sale_exchange_allowed():
    r = check_return_eligibility("TRD-1003", request_type="exchange", reason="wrong_size",
                                  desired_exchange_size="9", today=date(2026, 6, 10))
    assert r["eligible"] is True
    assert r["items"][0]["reason_code"] == "exchange_eligible"


# ---- damage claims override category/final-sale/window (policy 6) ----

def test_damage_claim_within_48h_overrides_final_sale():
    r = check_return_eligibility("TRD-1003", request_type="return", reason="damaged",
                                  has_photos=True, today=date(2026, 6, 7))
    assert r["eligible"] is True
    assert r["items"][0]["reason_code"] == "damage_or_incorrect_confirmed"


def test_damage_claim_after_48h_denied():
    r = check_return_eligibility("TRD-1003", request_type="return", reason="damaged",
                                  has_photos=True, today=date(2026, 6, 20))
    assert r["eligible"] is False
    assert r["items"][0]["reason_code"] == "damage_report_window_expired"


# ---- footwear box deduction (policy 2.5) ----

def test_footwear_missing_box_deduction():
    # use exchange->return path won't hit footwear deduction since final_sale;
    # simulate a non-final-sale footwear item scenario via direct evaluation
    from app.tools.returns import _evaluate_item
    item = {"sku": "X", "name": "Test Boots", "price": 2000, "category": "footwear",
            "final_sale": False, "footwear": True, "exchange_count": 0}
    result = _evaluate_item(item, days_since_delivery=5, request_type="return",
                             reason="changed_mind", desired_exchange_size=None,
                             has_original_box=False, has_photos=None)
    assert result["eligible"] is True
    assert result["refund_estimate"] == 1700  # 2000 - 300 deduction


# ---- action tools ----

def test_initiate_rma_creates_when_eligible():
    r = initiate_rma("TRD-1001", "TRD-DRESS-001", request_type="return", reason="changed_mind")
    assert r["created"] is True
    assert r["rma_id"].startswith("RMA-")


def test_initiate_rma_blocked_when_ineligible():
    r = initiate_rma("TRD-1003", "TRD-SHOE-022", request_type="return", reason="changed_mind")
    assert r["created"] is False


def test_delay_credit_issued_when_late():
    # TRD-1002 expected 2026-07-24, check well past it
    r = check_and_issue_delay_credit("TRD-1002", today=date(2026, 8, 5))
    assert r["issued"] is True
    assert r["amount"] == 250


def test_delay_credit_not_issued_when_on_time():
    r = check_and_issue_delay_credit("TRD-1002", today=date(2026, 7, 24))
    assert r["issued"] is False


# ---- policy grounding ----

def test_policy_search_returns_relevant_section():
    r = search_policy("how many days do I have to return an item")
    titles = [x["title"].lower() for x in r["results"]]
    assert any("return" in t for t in titles)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
