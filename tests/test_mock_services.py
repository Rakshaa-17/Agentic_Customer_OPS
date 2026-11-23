"""
Unit tests for Mock Services & E-Commerce Business Logic.
"""
import pytest
import os
from services.seed_data import seed_database
from services.orders import get_order, update_shipping_address, cancel_order
from services.payments import process_refund, get_payment_for_order
from services.crm import get_customer

TEST_DB = "test_customer_ops.db"

@pytest.fixture(autouse=True)
def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    seed_database(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_get_customer():
    cust = get_customer("CUST-101", db_path=TEST_DB)
    assert cust is not None
    assert cust["name"] == "Alice Vance"
    assert cust["tier"] == "vip"

def test_order_address_change_pending():
    # ORD-1001 is pending -> address update allowed
    res = update_shipping_address("ORD-1001", "100 New Road, Portland, OR", db_path=TEST_DB)
    assert res["success"] is True
    order = get_order("ORD-1001", db_path=TEST_DB)
    assert order["shipping_address"] == "100 New Road, Portland, OR"

def test_order_address_change_shipped_rejected():
    # ORD-1004 is shipped -> address update blocked by policy
    res = update_shipping_address("ORD-1004", "100 New Road, Portland, OR", db_path=TEST_DB)
    assert res["success"] is False
    assert "Cannot change shipping address" in res["error"]

def test_order_cancellation():
    res = cancel_order("ORD-1001", reason="Customer changed mind", db_path=TEST_DB)
    assert res["success"] is True
    order = get_order("ORD-1001", db_path=TEST_DB)
    assert order["status"] == "cancelled"

def test_refund_auto_approved_under_threshold():
    # ORD-1002 is $24.99 (under $50 auto-refund threshold)
    res = process_refund(
        order_id="ORD-1002",
        amount=24.99,
        reason="Mug arrived cracked",
        idempotency_key="TEST-KEY-001",
        db_path=TEST_DB
    )
    assert res["success"] is True
    assert res["status"] == "approved"
    assert res["approved_by"] == "AUTO_AGENT"

def test_refund_exceeding_threshold_requires_approval():
    # ORD-1003 is $180.00 (exceeds $50 auto-refund threshold)
    res = process_refund(
        order_id="ORD-1003",
        amount=180.00,
        reason="Headphones defective",
        idempotency_key="TEST-KEY-002",
        db_path=TEST_DB
    )
    assert res["success"] is False
    assert res["requires_human_approval"] is True
    assert res["status"] == "pending_approval"

def test_refund_override_by_human():
    # When human supervisor approves
    res = process_refund(
        order_id="ORD-1003",
        amount=180.00,
        reason="Headphones defective",
        idempotency_key="TEST-KEY-003",
        override_approval=True,
        db_path=TEST_DB
    )
    assert res["success"] is True
    assert res["status"] == "approved"
    assert res["approved_by"] == "HUMAN_SUPERVISOR"

def test_refund_idempotency_protection():
    # Execute first refund
    res1 = process_refund(
        order_id="ORD-1002",
        amount=10.00,
        reason="Partial discount",
        idempotency_key="IDEMP-SAME-KEY",
        db_path=TEST_DB
    )
    assert res1["success"] is True
    assert res1.get("idempotent_replay") is None or res1.get("idempotent_replay") is False

    # Execute duplicate request with SAME idempotency key
    res2 = process_refund(
        order_id="ORD-1002",
        amount=10.00,
        reason="Partial discount",
        idempotency_key="IDEMP-SAME-KEY",
        db_path=TEST_DB
    )
    assert res2["success"] is True
    assert res2.get("idempotent_replay") is True
