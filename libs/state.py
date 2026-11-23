"""
Typed Graph State with LangGraph Reducers.
Defines the shared memory schema passed between all specialist agents.
"""
from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def merge_actions(existing: List[Dict[str, Any]], new_action: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer to accumulate actions taken across specialist agents."""
    if existing is None:
        existing = []
    if new_action is None:
        return existing
    return existing + new_action

class AgentState(TypedDict):
    """
    Core state for the Customer Operations Multi-Agent Graph.
    - messages: conversational history managed by LangGraph's add_messages reducer.
    - intent: classified primary intent.
    - sentiment: customer emotional state.
    - customer_id: identified customer ID.
    - order_id: target order ID.
    - actions_taken: list of audit records for tool executions.
    - requires_human_approval: flagged if an action exceeds autonomous thresholds.
    - pending_action: payload of the action awaiting human decision (e.g. refund amount, reason).
    - approval_status: 'pending', 'approved', or 'rejected'.
    - next_agent: next specialist node determined by the supervisor.
    - step_count: counter to enforce step budgets and prevent infinite loops.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    intent: Optional[Literal["order_status", "return_refund", "address_change", "billing_dispute", "policy_question", "complaint", "general"]]
    sentiment: Optional[Literal["positive", "neutral", "frustrated", "angry"]]
    customer_id: Optional[str]
    order_id: Optional[str]
    actions_taken: Annotated[List[Dict[str, Any]], merge_actions]
    requires_human_approval: bool
    pending_action: Optional[Dict[str, Any]]
    approval_status: Optional[Literal["pending", "approved", "rejected"]]
    next_agent: Optional[str]
    step_count: int
