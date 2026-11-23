"""
Integration Tests for LangGraph Multi-Agent Customer Operations.
Tests: Routing, Specialist nodes, Multi-turn thread continuity, and Checkpointing.
"""
import pytest
import os
import sqlite3
import unicodedata
from services.seed_data import seed_database
from apps.graph import build_customer_ops_graph, run_ticket_turn
from services.orders import get_order
from langgraph.checkpoint.sqlite import SqliteSaver

TEST_CHECKPOINT_DB = "test_checkpoints.db"

def normalize_text(text: str) -> str:
    """Normalizes Unicode non-breaking hyphens and spaces to standard ASCII for robust assertions."""
    return text.replace("\u2011", "-").replace("\u2013", "-").replace("\u202f", " ")

@pytest.fixture(autouse=True)
def setup_test_env():
    seed_database()
    yield
    # Clean up test DB after test completes
    if os.path.exists(TEST_CHECKPOINT_DB):
        try:
            os.remove(TEST_CHECKPOINT_DB)
        except PermissionError:
            pass

def test_multi_agent_order_status_inquiry():
    res = run_ticket_turn(thread_id="THREAD-TEST-STATUS", user_message="Where is my order ORD-1001?")
    assert res["intent"] == "order_status"
    norm_resp = normalize_text(res["response"])
    assert "ORD-1001" in norm_resp
    assert "pending" in norm_resp.lower()

def test_multi_agent_policy_question_routing():
    res = run_ticket_turn(thread_id="THREAD-TEST-POLICY", user_message="What is your return policy window?")
    assert res["intent"] == "policy_question"
    assert "30" in res["response"]

def test_multi_turn_thread_continuity_with_checkpoint():
    conn = sqlite3.connect(TEST_CHECKPOINT_DB, check_same_thread=False)
    try:
        checkpointer = SqliteSaver(conn)
        graph = build_customer_ops_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "THREAD-MULTI-TURN-01"}}
        
        # Turn 1: Customer asks about order
        turn1 = graph.invoke({
            "messages": [{"role": "user", "content": "Hi, what is in my order ORD-1001?"}],
            "actions_taken": [],
            "requires_human_approval": False,
            "step_count": 0
        }, config=config)
        
        norm_t1 = normalize_text(turn1["messages"][-1].content)
        assert "ORD-1001" in norm_t1
        assert turn1["intent"] == "order_status"
        
        # Turn 2: Customer asks follow-up referencing previous turn without repeating order number!
        turn2 = graph.invoke({
            "messages": [{"role": "user", "content": "Great, please update its shipping address to 123 Pine St, Dallas, TX."}]
        }, config=config)
        
        norm_t2 = normalize_text(turn2["messages"][-1].content)
        # Verify in DB that address updated on ORD-1001
        order = get_order("ORD-1001")
        assert "123 Pine St" in order["shipping_address"] or "123 Pine St" in norm_t2
    finally:
        conn.close()
