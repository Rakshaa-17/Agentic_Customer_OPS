"""
Human-in-the-Loop Approval Gate Node.
Uses LangGraph 1.x interrupt() to pause graph execution and await supervisor decision.
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage
from langgraph.types import interrupt
from libs.state import AgentState
from services.payments import approve_pending_refund, reject_pending_refund

def human_approval_gate_node(state: AgentState) -> Dict[str, Any]:
    """
    Halts graph execution using LangGraph's interrupt() function.
    Freezes state into persistent checkpointer until resumed via Reviewer Console.
    Resumes with: Command(resume={'approved': bool, 'reviewer': str, 'reason': str})
    """
    pending = state.get("pending_action") or {}
    order_id = pending.get("order_id", state.get("order_id"))
    amount = pending.get("amount", 0.0)
    reason = pending.get("reason", "Customer requested refund")

    # ==================== SUSPEND GRAPH HERE ====================
    decision = interrupt({
        "ticket_thread": state.get("order_id") or "UNKNOWN",
        "action": "issue_refund",
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "summary": f"Refund of ${amount:.2f} for order '{order_id}' exceeds the autonomous limit and requires supervisor authorization."
    })
    # ============================================================

    approved = decision.get("approved", False)
    reviewer = decision.get("reviewer", "HUMAN_SUPERVISOR")
    rejection_reason = decision.get("reason", "Supervisor denied refund request per policy.")

    if approved:
        # Execute the approved refund via approve_pending_refund
        res = approve_pending_refund(order_id=order_id, reviewer=reviewer)
        status_msg = (
            f"HUMAN APPROVAL GRANTED by {reviewer}.\n"
            f"Refund of ${amount:.2f} for order '{order_id}' was successfully processed in database. "
            f"Refund ID: {res.get('refund_id')}."
        )
        return {
            "approval_status": "approved",
            "requires_human_approval": False,
            "pending_action": None,
            "actions_taken": [{"tool": "human_approved_refund", "output": status_msg}],
            "messages": [AIMessage(content=status_msg)],
            "step_count": state.get("step_count", 0) + 1
        }
    else:
        # Record rejection via reject_pending_refund
        res = reject_pending_refund(order_id=order_id, reviewer=reviewer, reason=rejection_reason)
        status_msg = (
            f"HUMAN SUPERVISOR REVIEW: Refund request for ${amount:.2f} was REJECTED by {reviewer}.\n"
            f"Reason: {rejection_reason}"
        )
        return {
            "approval_status": "rejected",
            "requires_human_approval": False,
            "pending_action": None,
            "actions_taken": [{"tool": "human_rejected_refund", "output": status_msg}],
            "messages": [AIMessage(content=status_msg)],
            "step_count": state.get("step_count", 0) + 1
        }
