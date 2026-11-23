"""
LangGraph Multi-Agent Customer Operations Graph with Human-in-the-Loop Interrupt Gate.
Wires Supervisor, Triage, Order/Billing, Policy, Approval Gate, and Resolution nodes
with durable SqliteSaver checkpointing.
"""
import os
import sqlite3
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from libs.state import AgentState
from libs.agents.triage import triage_node
from libs.agents.order_billing import order_billing_node
from libs.agents.policy import policy_node
from libs.agents.approval_gate import human_approval_gate_node
from libs.agents.resolution import resolution_node
from langchain_core.messages import HumanMessage, AIMessage

CHECKPOINT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checkpoints.db")

def route_from_triage(state: AgentState) -> str:
    """Routes to the appropriate specialist based on triage intent."""
    intent = state.get("intent")
    
    if intent == "policy_question":
        return "policy"
    elif intent in ["order_status", "return_refund", "address_change", "billing_dispute"]:
        return "order_billing"
    else:
        return "resolution"

def route_from_order_billing(state: AgentState) -> str:
    """If a sensitive action requires human approval, routes to the approval gate."""
    if state.get("requires_human_approval") and state.get("approval_status") is None:
        return "human_approval_gate"
    return "resolution"

def build_customer_ops_graph(checkpointer: Optional[SqliteSaver] = None):
    """
    Constructs and compiles the full multi-agent StateGraph with Human-in-the-Loop interrupt gate.
    Flow:
      START -> triage -> (policy | order_billing | resolution)
      order_billing -> (human_approval_gate [interrupt] | resolution)
      human_approval_gate -> resolution -> END
      policy -> resolution -> END
    """
    builder = StateGraph(AgentState)
    
    # 1. Add Nodes
    builder.add_node("triage", triage_node)
    builder.add_node("order_billing", order_billing_node)
    builder.add_node("policy", policy_node)
    builder.add_node("human_approval_gate", human_approval_gate_node)
    builder.add_node("resolution", resolution_node)
    
    # 2. Add Edges
    builder.add_edge(START, "triage")
    
    builder.add_conditional_edges(
        "triage",
        route_from_triage,
        {
            "order_billing": "order_billing",
            "policy": "policy",
            "resolution": "resolution"
        }
    )
    
    builder.add_conditional_edges(
        "order_billing",
        route_from_order_billing,
        {
            "human_approval_gate": "human_approval_gate",
            "resolution": "resolution"
        }
    )
    
    builder.add_edge("human_approval_gate", "resolution")
    builder.add_edge("policy", "resolution")
    builder.add_edge("resolution", END)
    
    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()

def get_compiled_graph():
    """Returns a compiled graph bound to the persistent SQLite checkpointer."""
    conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return build_customer_ops_graph(checkpointer=checkpointer)

def run_ticket_turn(thread_id: str, user_message: str) -> Dict[str, Any]:
    """
    Executes a single customer turn on a stateful, checkpointed ticket thread.
    If an action triggers interrupt(), execution pauses and returns status='awaiting_human_approval'.
    """
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    input_state = {
        "messages": [HumanMessage(content=user_message)],
        "actions_taken": [],
        "requires_human_approval": False,
        "step_count": 0
    }
    
    final_state = graph.invoke(input_state, config=config)
    
    # Check if graph halted on interrupt
    state_snapshot = graph.get_state(config)
    is_paused = len(state_snapshot.next) > 0 and "human_approval_gate" in state_snapshot.next
    
    pending_interrupt = None
    if is_paused:
        for task in state_snapshot.tasks:
            if task.interrupts:
                pending_interrupt = task.interrupts[0].value
                break

    final_ai_msg = next((m.content for m in reversed(final_state["messages"]) if m.type == "ai"), "")
    
    return {
        "thread_id": thread_id,
        "is_paused": is_paused,
        "pending_interrupt": pending_interrupt,
        "intent": final_state.get("intent"),
        "sentiment": final_state.get("sentiment"),
        "actions_taken": final_state.get("actions_taken", []),
        "requires_human_approval": final_state.get("requires_human_approval", False),
        "response": final_ai_msg,
        "step_count": final_state.get("step_count", 0)
    }

def resume_ticket(thread_id: str, approved: bool, reviewer: str = "Supervisor", reason: str = "") -> Dict[str, Any]:
    """
    Resumes an interrupted graph from its checkpoint using Command(resume=...).
    """
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    resume_command = Command(resume={
        "approved": approved,
        "reviewer": reviewer,
        "reason": reason
    })
    
    final_state = graph.invoke(resume_command, config=config)
    final_ai_msg = next((m.content for m in reversed(final_state["messages"]) if m.type == "ai"), "")
    
    return {
        "thread_id": thread_id,
        "is_paused": False,
        "approval_status": final_state.get("approval_status"),
        "response": final_ai_msg,
        "step_count": final_state.get("step_count", 0)
    }
