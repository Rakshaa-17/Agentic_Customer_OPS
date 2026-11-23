"""
Integration test for LangGraph Human-in-the-Loop Interrupt Gate & Resumption.
Validates:
1. High-value refund (> $50) triggers interrupt().
2. Database state confirms money was NOT moved while paused.
3. Supervisor approval via Command(resume=...) executes the transaction.
4. Customer receives confirmed resolution from the resumed graph.
"""
import pytest
import os
import uuid
import sqlite3
from services.seed_data import seed_database
from services.db import get_connection
from apps.graph import run_ticket_turn, resume_ticket

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()
    yield

def test_hitl_approval_lifecycle():
    thread_id = f"HITL-TEST-APP-{uuid.uuid4().hex[:8]}"
    
    # Step 1: Customer requests $180 refund on ORD-1003 (exceeds $50 auto-refund threshold)
    turn1 = run_ticket_turn(
        thread_id=thread_id,
        user_message="My headphones in order ORD-1003 are broken. I need a full refund of $180.00."
    )
    
    # Step 2: Assert graph is paused at human_approval_gate
    assert turn1["is_paused"] is True
    assert turn1["pending_interrupt"] is not None
    assert turn1["pending_interrupt"]["amount"] == 180.00
    assert turn1["pending_interrupt"]["order_id"] == "ORD-1003"
    
    # Step 3: Assert database payment was NOT refunded while waiting for approval
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE order_id = 'ORD-1003'")
        payment = cursor.fetchone()
        assert payment["status"] != "refunded"
        assert payment["refunded_amount"] == 0.0
    finally:
        conn.close()
    
    # Step 4: Human supervisor reviews and approves the refund via Reviewer Console
    resume_res = resume_ticket(
        thread_id=thread_id,
        approved=True,
        reviewer="Supervisor_Alice"
    )
    
    # Step 5: Assert graph resumed and completed
    assert resume_res["is_paused"] is False
    assert resume_res["approval_status"] == "approved"
    
    # Step 6: Assert database payment is now REFUNDED
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE order_id = 'ORD-1003'")
        payment_after = cursor.fetchone()
        assert payment_after["refunded_amount"] == 180.00
        assert payment_after["status"] == "refunded"
        
        # Step 7: Assert refund audit record was updated to approved with supervisor identity
        cursor.execute("SELECT * FROM refund_transactions WHERE order_id = 'ORD-1003' ORDER BY created_at DESC")
        refund_record = cursor.fetchone()
        assert refund_record["status"] == "approved"
        assert "Supervisor_Alice" in refund_record["reason"] or refund_record["approved_by"] == "HUMAN_SUPERVISOR"
    finally:
        conn.close()

def test_hitl_rejection_lifecycle():
    thread_id = f"HITL-TEST-REJ-{uuid.uuid4().hex[:8]}"
    
    # Customer requests high-value refund
    turn1 = run_ticket_turn(
        thread_id=thread_id,
        user_message="I want a $180.00 refund for ORD-1003 because I don't like the color."
    )
    assert turn1["is_paused"] is True
    
    # Supervisor rejects the refund
    resume_res = resume_ticket(
        thread_id=thread_id,
        approved=False,
        reviewer="Supervisor_Bob",
        reason="Color preference after delivery is not eligible for refund under store policy."
    )
    
    assert resume_res["is_paused"] is False
    assert resume_res["approval_status"] == "rejected"
    
    # Database payment must remain untouched (0.0 refunded)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE order_id = 'ORD-1003'")
        payment = cursor.fetchone()
        assert payment["refunded_amount"] == 0.0
        
        # Verify refund record is marked rejected
        cursor.execute("SELECT * FROM refund_transactions WHERE order_id = 'ORD-1003' ORDER BY created_at DESC")
        refund_record = cursor.fetchone()
        assert refund_record["status"] == "rejected"
    finally:
        conn.close()
