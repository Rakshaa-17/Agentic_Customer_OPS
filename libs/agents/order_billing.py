"""
Order & Billing Specialist Agent.
Has scoped tool access to: lookup_order, lookup_customer, update_shipping_address, cancel_order, issue_refund.
Detects when a refund exceeds $50 and flags pending_action for the Human-in-the-Loop gate.
"""
from typing import Dict, Any
import re
import uuid
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from libs.models import get_chat_model
from libs.tools import (
    lookup_order,
    lookup_customer,
    update_shipping_address,
    cancel_order,
    issue_refund
)
from libs.state import AgentState

ORDER_BILLING_TOOLS = [
    lookup_order,
    lookup_customer,
    update_shipping_address,
    cancel_order,
    issue_refund
]

ORDER_BILLING_PROMPT = """You are an Order and Billing Specialist Agent.
Your responsibility is to handle customer orders, status lookups, shipping address updates, cancellations, and refunds.
Rules:
- Call lookup_order to check status before attempting address changes or cancellations.
- Address updates and cancellations are ONLY valid when status is 'pending' or 'processing'.
- Refunds:
  - For damaged or defective goods under $50.00, issue the refund with the reason.
  - If a refund exceeds $50.00, call the issue_refund tool; it will safely return an action paused notice.
- Always report the tool execution result clearly.
"""

def order_billing_node(state: AgentState) -> Dict[str, Any]:
    """Executes the Order & Billing specialist logic using scoped tools."""
    llm = get_chat_model("specialist")
    agent = create_react_agent(
        model=llm,
        tools=ORDER_BILLING_TOOLS,
        prompt=ORDER_BILLING_PROMPT
    )
    
    result = agent.invoke({"messages": state["messages"]})
    new_messages = result["messages"][len(state["messages"]):]
    
    requires_approval = False
    pending_action = None
    actions = []
    
    for m in new_messages:
        if isinstance(m, ToolMessage):
            actions.append({"tool": m.name, "output": m.content})
            if "REQUIRES HUMAN APPROVAL" in m.content:
                requires_approval = True
                
                # Extract order ID and amount from tool message
                amount_match = re.search(r"\$([0-9]+(?:\.[0-9]{2})?)", m.content)
                order_match = re.search(r"order\s+'([^']+)'", m.content)
                
                amount = float(amount_match.group(1)) if amount_match else 0.0
                order_id = order_match.group(1) if order_match else state.get("order_id")
                
                pending_action = {
                    "action": "issue_refund",
                    "order_id": order_id,
                    "amount": amount,
                    "reason": "Customer reported issue exceeding auto-refund limit",
                    "idempotency_key": f"IDEMP-HITL-{order_id}-{amount:.2f}-{uuid.uuid4().hex[:6]}"
                }
    
    return {
        "messages": new_messages,
        "actions_taken": actions,
        "requires_human_approval": requires_approval,
        "pending_action": pending_action,
        "step_count": state.get("step_count", 0) + 1
    }
