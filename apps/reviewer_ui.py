"""
Streamlit Reviewer Console & Operations Dashboard.
Provides real-time customer chat, agent routing visibility, and Human-in-the-Loop approval queue.
"""
import streamlit as st
import sqlite3
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.graph import get_compiled_graph, run_ticket_turn, resume_ticket
from services.orders import get_order
from services.payments import get_payment_for_order
from services.seed_data import seed_database
from services.db import get_connection

st.set_page_config(
    page_title="Agentic Customer Operations Console",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Agentic Customer Operations — Reviewer Console")
st.caption("LangGraph 1.x Multi-Agent Supervised Ticket Resolution with Human-in-the-Loop Interrupts")

# Sidebar: Environment & Reset Controls
with st.sidebar:
    st.header("⚙️ Controls & Database")
    if st.button("🔄 Reset Seed Database", use_container_width=True):
        seed_database()
        st.success("Database re-seeded successfully!")
    
    st.divider()
    st.subheader("Active Ticket Threads")
    thread_id = st.text_input("Active Thread ID", value="TICKET-1003")

# Main Layout: 2 Columns (Left: Chat & Live Agent Trace, Right: Supervisor Approval Queue)
col_chat, col_approvals = st.columns([3, 2], gap="large")

with col_approvals:
    st.subheader("🚨 Supervisor Human-in-the-Loop Queue")
    
    # Check if current thread has an active interrupt in the checkpointer
    graph = get_compiled_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = graph.get_state(config)
    
    pending_interrupt = None
    if state_snapshot and state_snapshot.next and "human_approval_gate" in state_snapshot.next:
        for t in state_snapshot.tasks:
            if t.interrupts:
                pending_interrupt = t.interrupts[0].value
                break
                
    if pending_interrupt:
        st.warning("⚠️ **ACTION PAUSED: High-Risk Operation Awaiting Approval**")
        st.markdown(f"**Target Order:** `{pending_interrupt.get('order_id')}`")
        st.markdown(f"**Requested Refund:** `${pending_interrupt.get('amount', 0):.2f}`")
        st.markdown(f"**Reason:** *{pending_interrupt.get('reason')}*")
        st.info(pending_interrupt.get("summary"))
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ Approve Refund", use_container_width=True, type="primary"):
                with st.spinner("Executing approved transaction and resuming graph..."):
                    res = resume_ticket(thread_id, approved=True, reviewer="Supervisor_Jane")
                    st.success("Refund Approved & Graph Resumed!")
                    st.rerun()
        with col_btn2:
            if st.button("❌ Reject Request", use_container_width=True):
                with st.spinner("Recording rejection and resuming customer reply..."):
                    res = resume_ticket(thread_id, approved=False, reviewer="Supervisor_Jane", reason="Outside authorized policy limit.")
                    st.error("Request Rejected.")
                    st.rerun()
    else:
        st.success("✅ No pending supervisor approvals for this thread.")
        
    st.divider()
    st.subheader("📦 Order Quick Inspection")
    inspect_order_id = st.text_input("Inspect Order ID", value="ORD-1003")
    if inspect_order_id:
        ord_data = get_order(inspect_order_id)
        if ord_data:
            st.json({
                "Status": ord_data["status"],
                "Total Amount": f"${ord_data['total_amount']:.2f}",
                "Shipping Address": ord_data["shipping_address"],
                "Items": ord_data["items"]
            })
        else:
            st.caption("Order not found.")

with col_chat:
    st.subheader("💬 Customer Dialogue & Agent Resolution")
    
    # Initialize message log in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
    # Render messages from graph state if available
    if state_snapshot and state_snapshot.values and "messages" in state_snapshot.values:
        for m in state_snapshot.values["messages"]:
            role = "assistant" if m.type == "ai" else "user"
            with st.chat_message(role):
                st.write(m.content)
    
    # Input box for customer message
    user_input = st.chat_input("Type customer message here... (e.g. 'I want a $180 refund for order ORD-1003')")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.spinner("Multi-Agent Graph routing and evaluating..."):
            result = run_ticket_turn(thread_id, user_input)
            
            with st.chat_message("assistant"):
                st.write(result["response"])
                
            if result.get("is_paused"):
                st.warning("⚡ Graph halted at `human_approval_gate`. Check the Supervisor Approval Queue!")
            st.rerun()
