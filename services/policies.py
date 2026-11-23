"""
E-Commerce Business Policies & Rules.
These policies dictate what actions agents can take autonomously
vs what requires supervisor or human approval.
"""
from typing import Dict, Any

POLICIES: Dict[str, Any] = {
    "return_window_days": 30,
    "auto_refund_limit_usd": 50.00,
    "address_change_allowed_statuses": ["pending", "processing"],
    "cancellation_allowed_statuses": ["pending", "processing"],
    "damaged_goods_full_refund": True,
    "requires_return_for_items_above_usd": 100.00,
    "vip_instant_credit": True
}

POLICY_KNOWLEDGE_BASE = """
# Enterprise E-Commerce Store Policies

## 1. Return & Refund Policy
- Items can be returned or refunded within 30 days of confirmed delivery.
- Orders under $50.00 with damaged or defective items are eligible for an immediate full refund without requiring physical return.
- Any refund exceeding $50.00 requires supervisor authorization (Human-in-the-Loop review).
- Final sale or clearance items cannot be refunded unless damaged in transit.
- Refunds are credited to the original payment method within 3 to 5 business days.

## 2. Order Cancellation & Address Changes
- Customers can cancel an order or modify the shipping address ONLY if the order status is 'pending' or 'processing'.
- Once an order has transitioned to 'shipped' or 'delivered', address modifications and instant cancellations cannot be processed. Customers must initiate a return after arrival.

## 3. Customer Tiers & VIP Perks
- **VIP Customers**: Receive expedited shipping and instant store credit waivers on minor disputes.
- **Gold Customers**: Priority email support and extended 45-day return window.
- **Regular Customers**: Standard 30-day return policy.
"""

def get_policy_text() -> str:
    """Returns the full knowledge base text for RAG/Policy Agent retrieval."""
    return POLICY_KNOWLEDGE_BASE.strip()
