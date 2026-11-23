"""
Agent Tools: Strongly typed, Pydantic-validated tools for LangGraph agents.
Directly interfaces with our underlying mock e-commerce services layer.
"""
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from services.orders import get_order, get_customer_orders, update_shipping_address as svc_update_address, cancel_order as svc_cancel_order
from services.payments import process_refund as svc_process_refund, get_payment_for_order
from services.crm import get_customer_by_email as svc_get_customer, get_customer
from services.policies import get_policy_text

# ==================== Pydantic Input Schemas ====================

class OrderLookupSchema(BaseModel):
    order_id: str = Field(..., description="The unique order ID to inspect, e.g. 'ORD-1001'.")

class CustomerLookupSchema(BaseModel):
    email: str = Field(..., description="The customer's email address to find their account and past orders.")

class UpdateShippingAddressSchema(BaseModel):
    order_id: str = Field(..., description="The order ID for which to change the shipping address.")
    new_address: str = Field(..., description="The complete updated shipping address.")

class CancelOrderSchema(BaseModel):
    order_id: str = Field(..., description="The order ID to cancel.")
    reason: str = Field(..., description="The customer's reason for cancellation.")

class RefundRequestSchema(BaseModel):
    order_id: str = Field(..., description="The order ID for which to request a refund.")
    amount: float = Field(..., description="The dollar amount to refund (e.g. 24.99).")
    reason: str = Field(..., description="Detailed explanation/reason for the refund.")

class PolicyLookupSchema(BaseModel):
    topic: str = Field(..., description="The policy topic or question to query (e.g. 'return window', 'damaged goods', 'refund limits').")


# ==================== LangChain Tool Implementations ====================

@tool("lookup_order", args_schema=OrderLookupSchema)
def lookup_order(order_id: str) -> str:
    """Retrieve complete details for a specific order including status, items, tracking number, and shipping address."""
    order = get_order(order_id)
    if not order:
        return f"Order '{order_id}' was not found in the system."
    return (
        f"Order ID: {order['id']}\n"
        f"Status: {order['status']}\n"
        f"Customer ID: {order['customer_id']}\n"
        f"Total: ${order['total_amount']:.2f} {order['currency']}\n"
        f"Shipping Address: {order['shipping_address']}\n"
        f"Tracking: {order.get('tracking_number') or 'Not yet assigned'}\n"
        f"Items: {order['items']}\n"
        f"Order Date: {order['order_date']}"
    )

@tool("lookup_customer", args_schema=CustomerLookupSchema)
def lookup_customer(email: str) -> str:
    """Find a customer by email, their tier (VIP, Gold, Regular), and list their recent orders."""
    cust = svc_get_customer(email)
    if not cust:
        return f"No customer account found with email '{email}'."
    
    orders = get_customer_orders(cust["id"])
    orders_summary = "\n".join([
        f"- {o['id']}: Status={o['status']}, Total=${o['total_amount']:.2f}, Date={o['order_date']}"
        for o in orders
    ]) if orders else "No orders on file."
    
    return (
        f"Customer: {cust['name']} (ID: {cust['id']})\n"
        f"Tier: {cust['tier'].upper()}\n"
        f"Email: {cust['email']}\n"
        f"Past Orders:\n{orders_summary}"
    )

@tool("update_shipping_address", args_schema=UpdateShippingAddressSchema)
def update_shipping_address(order_id: str, new_address: str) -> str:
    """Update the shipping address for an order. Only allowed if order is 'pending' or 'processing'."""
    res = svc_update_address(order_id, new_address)
    if not res["success"]:
        return f"ACTION FAILED: {res['error']}"
    return f"SUCCESS: Shipping address for order '{order_id}' has been updated to: {new_address}."

@tool("cancel_order", args_schema=CancelOrderSchema)
def cancel_order(order_id: str, reason: str) -> str:
    """Cancel an unshipped order. Only allowed if status is 'pending' or 'processing'."""
    res = svc_cancel_order(order_id, reason)
    if not res["success"]:
        return f"ACTION FAILED: {res['error']}"
    return f"SUCCESS: Order '{order_id}' has been successfully cancelled. Reason recorded: '{reason}'."

@tool("issue_refund", args_schema=RefundRequestSchema)
def issue_refund(order_id: str, amount: float, reason: str) -> str:
    """
    Request a refund for an order. 
    Amounts <= $50 are auto-approved by policy.
    Amounts > $50 are flagged for human supervisor approval.
    """
    # Deterministic idempotency key based on order and amount to prevent double refunds
    idempotency_key = f"IDEMP-{order_id}-{amount:.2f}-{uuid.uuid5(uuid.NAMESPACE_DNS, reason).hex[:6]}"
    res = svc_process_refund(order_id, amount, reason, idempotency_key=idempotency_key)
    
    if not res["success"]:
        if res.get("requires_human_approval"):
            return (
                f"ACTION PAUSED (REQUIRES HUMAN APPROVAL): Refund request of ${amount:.2f} for order '{order_id}' "
                f"exceeds the autonomous limit of ${res['threshold']:.2f}. "
                f"Ticket has been escalated to the Human Supervisor queue. Status: {res['status']}."
            )
        return f"ACTION FAILED: {res['error']}"
    
    return (
        f"SUCCESS: Refund of ${res['amount']:.2f} has been APPROVED and processed. "
        f"Refund ID: {res['refund_id']}. Remaining refundable balance: ${res['remaining_balance']:.2f}."
    )

@tool("lookup_policy", args_schema=PolicyLookupSchema)
def lookup_policy(topic: str) -> str:
    """Look up store policies regarding return windows, refund limits, address modifications, and VIP perks."""
    full_text = get_policy_text()
    return f"STORE POLICY KNOWLEDGE BASE (Query context: '{topic}'):\n\n{full_text}"

ALL_TOOLS = [
    lookup_order,
    lookup_customer,
    update_shipping_address,
    cancel_order,
    issue_refund,
    lookup_policy
]
