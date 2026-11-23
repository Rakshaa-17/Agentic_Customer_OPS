"""
Payments & Refund domain service with Idempotency Support.
Supports state transition from pending_approval -> approved / rejected.
"""
from typing import Optional, Dict, Any
import uuid
from services.db import get_connection
from services.policies import POLICIES

def get_payment_for_order(order_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def approve_pending_refund(order_id: str, reviewer: str = "HUMAN_SUPERVISOR", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Transitions the pending refund for an order to APPROVED and updates payment balance."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM refund_transactions WHERE order_id = ? AND status = 'pending_approval' ORDER BY created_at DESC LIMIT 1",
        (order_id,)
    )
    pending = cursor.fetchone()
    if not pending:
        conn.close()
        return {"success": False, "error": f"No pending refund found for order {order_id}."}
        
    amount = pending["amount"]
    
    # Update payment
    cursor.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
    payment = cursor.fetchone()
    total_paid = payment["amount"]
    already_refunded = payment["refunded_amount"]
    new_refunded = round(already_refunded + amount, 2)
    new_status = "refunded" if new_refunded >= total_paid else "partially_refunded"
    
    with conn:
        conn.execute(
            "UPDATE refund_transactions SET status = 'approved', approved_by = ?, reason = reason || ' [APPROVED BY ' || ? || ']' WHERE id = ?",
            (reviewer, reviewer, pending["id"])
        )
        conn.execute(
            "UPDATE payments SET refunded_amount = ?, status = ? WHERE order_id = ?",
            (new_refunded, new_status, order_id)
        )
    conn.close()
    
    return {
        "success": True,
        "refund_id": pending["id"],
        "order_id": order_id,
        "amount": amount,
        "status": "approved",
        "approved_by": reviewer,
        "remaining_balance": round(total_paid - new_refunded, 2)
    }

def reject_pending_refund(order_id: str, reviewer: str = "HUMAN_SUPERVISOR", reason: str = "", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Transitions the pending refund for an order to REJECTED without modifying payment balance."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM refund_transactions WHERE order_id = ? AND status = 'pending_approval' ORDER BY created_at DESC LIMIT 1",
        (order_id,)
    )
    pending = cursor.fetchone()
    if not pending:
        conn.close()
        return {"success": False, "error": f"No pending refund found for order {order_id}."}
        
    with conn:
        conn.execute(
            "UPDATE refund_transactions SET status = 'rejected', approved_by = ?, reason = reason || ' [REJECTED BY ' || ? || ': ' || ? || ']' WHERE id = ?",
            (reviewer, reviewer, reason, pending["id"])
        )
    conn.close()
    
    return {
        "success": True,
        "refund_id": pending["id"],
        "order_id": order_id,
        "amount": pending["amount"],
        "status": "rejected",
        "approved_by": reviewer,
        "reason": reason
    }

def process_refund(
    order_id: str, 
    amount: float, 
    reason: str, 
    idempotency_key: str,
    override_approval: bool = False,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processes a refund.
    - Enforces idempotency via idempotency_key.
    - If amount > auto_refund_limit ($50) and not override_approval, flags for HITL approval.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Fetch payment record
    cursor.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,))
    payment = cursor.fetchone()
    if not payment:
        conn.close()
        return {"success": False, "error": f"No payment record found for order {order_id}."}
    
    total_paid = payment["amount"]
    already_refunded = payment["refunded_amount"]
    max_refundable = round(total_paid - already_refunded, 2)

    # 1. Idempotency Check
    cursor.execute("SELECT * FROM refund_transactions WHERE idempotency_key = ?", (idempotency_key,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return {
            "success": True,
            "idempotent_replay": True,
            "refund_id": existing["id"],
            "status": existing["status"],
            "amount": existing["amount"],
            "message": "Refund already processed with this idempotency key."
        }
    
    if amount <= 0:
        conn.close()
        return {"success": False, "error": "Refund amount must be greater than $0.00."}
        
    if amount > max_refundable:
        conn.close()
        return {
            "success": False,
            "error": f"Requested refund amount ${amount:.2f} exceeds remaining refundable balance ${max_refundable:.2f}."
        }
    
    refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
    
    # 2. Check Policy Threshold ($50 Auto-Refund Limit)
    auto_limit = POLICIES["auto_refund_limit_usd"]
    if amount > auto_limit and not override_approval:
        # High value refund: record as pending approval for Human-in-the-Loop
        with conn:
            conn.execute(
                """
                INSERT INTO refund_transactions 
                (id, order_id, amount, reason, idempotency_key, status, approved_by)
                VALUES (?, ?, ?, ?, ?, 'pending_approval', NULL)
                """,
                (refund_id, order_id, amount, reason, idempotency_key)
            )
        conn.close()
        return {
            "success": False,
            "requires_human_approval": True,
            "refund_id": refund_id,
            "amount": amount,
            "threshold": auto_limit,
            "reason": reason,
            "status": "pending_approval",
            "message": f"Refund of ${amount:.2f} exceeds auto-approval threshold (${auto_limit:.2f}). Paused for human approval."
        }
    
    # 3. Execute Immediate Refund
    new_refunded = round(already_refunded + amount, 2)
    new_payment_status = "refunded" if new_refunded >= total_paid else "partially_refunded"
    
    with conn:
        conn.execute(
            """
            INSERT INTO refund_transactions 
            (id, order_id, amount, reason, idempotency_key, status, approved_by)
            VALUES (?, ?, ?, ?, ?, 'approved', ?)
            """,
            (refund_id, order_id, amount, reason, idempotency_key, "HUMAN_SUPERVISOR" if override_approval else "AUTO_AGENT")
        )
        conn.execute(
            "UPDATE payments SET refunded_amount = ?, status = ? WHERE order_id = ?",
            (new_refunded, new_payment_status, order_id)
        )
    conn.close()
    
    return {
        "success": True,
        "refund_id": refund_id,
        "order_id": order_id,
        "amount": amount,
        "remaining_balance": round(total_paid - new_refunded, 2),
        "status": "approved",
        "approved_by": "HUMAN_SUPERVISOR" if override_approval else "AUTO_AGENT"
    }
