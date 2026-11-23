"""
Unit tests for Tool Layer and Pydantic Schemas.
"""
import pytest
from services.seed_data import seed_database
from libs.tools import (
    lookup_order,
    lookup_customer,
    update_shipping_address,
    cancel_order,
    issue_refund,
    lookup_policy
)

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()

def test_tool_lookup_order_found():
    res = lookup_order.invoke({"order_id": "ORD-1001"})
    assert "ORD-1001" in res
    assert "Organic Coffee Beans" in res
    assert "pending" in res

def test_tool_lookup_order_not_found():
    res = lookup_order.invoke({"order_id": "ORD-NONEXISTENT"})
    assert "was not found" in res

def test_tool_lookup_customer():
    res = lookup_customer.invoke({"email": "alice@example.com"})
    assert "Alice Vance" in res
    assert "VIP" in res
    assert "ORD-1001" in res

def test_tool_update_address_success():
    res = update_shipping_address.invoke({
        "order_id": "ORD-1001",
        "new_address": "42 Galaxy Way, Suite 100"
    })
    assert "SUCCESS" in res
    assert "42 Galaxy Way, Suite 100" in res

def test_tool_update_address_rejected_shipped():
    # ORD-1004 is shipped
    res = update_shipping_address.invoke({
        "order_id": "ORD-1004",
        "new_address": "42 Galaxy Way, Suite 100"
    })
    assert "ACTION FAILED" in res
    assert "Cannot change shipping address" in res

def test_tool_refund_under_threshold():
    # ORD-1002 is $24.99 -> under $50 limit -> auto-approved
    res = issue_refund.invoke({
        "order_id": "ORD-1002",
        "amount": 24.99,
        "reason": "Item arrived broken in box"
    })
    assert "SUCCESS" in res
    assert "APPROVED" in res

def test_tool_refund_exceeding_threshold_pauses_for_approval():
    # ORD-1003 is $180.00 -> > $50 limit -> requires human approval
    res = issue_refund.invoke({
        "order_id": "ORD-1003",
        "amount": 180.00,
        "reason": "Headphones defective"
    })
    assert "ACTION PAUSED (REQUIRES HUMAN APPROVAL)" in res
    assert "exceeds the autonomous limit of $50.00" in res

def test_tool_lookup_policy():
    res = lookup_policy.invoke({"topic": "return window"})
    assert "30 days" in res
    assert "$50.00" in res
