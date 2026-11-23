"""
Resolution Agent: Synthesizes specialist outputs into a polished,
empathetic customer-facing reply with action receipts and clear next steps.
"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from libs.models import get_chat_model
from libs.state import AgentState

RESOLUTION_SYSTEM_PROMPT = """You are the Senior Customer Resolution Agent.
Your job is to compose the final customer-facing reply based on the specialist actions and findings.
Guidelines:
- Tone: Empathetic, professional, concise.
- Clarity: Quote specific order IDs, tracking numbers, or refund confirmation IDs when available.
- If an action was blocked by policy (e.g. address change on an already shipped package), clearly and politely explain WHY, and provide the alternative next step (e.g. initiate return upon arrival).
- If a refund was submitted for human manager review (> $50), reassure the customer that their request is under priority review with a supervisor.
"""

def resolution_node(state: AgentState) -> Dict[str, Any]:
    """Formats the final customer resolution response."""
    llm = get_chat_model("specialist")
    
    conversation_summary = "\n".join([
        f"{m.type.upper()}: {m.content}" for m in state["messages"][-6:]
    ])
    
    prompt = [
        SystemMessage(content=RESOLUTION_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Customer Intent: {state.get('intent')}\n"
            f"Sentiment: {state.get('sentiment')}\n"
            f"Recent Conversation & Tool Actions:\n{conversation_summary}\n\n"
            "Please write the final polished, helpful customer response."
        ))
    ]
    
    response = llm.invoke(prompt)
    
    return {
        "messages": [AIMessage(content=response.content)],
        "step_count": state.get("step_count", 0) + 1
    }
