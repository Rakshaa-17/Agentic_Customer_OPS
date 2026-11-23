"""
Policy / Knowledge Specialist Agent.
Has scoped access ONLY to the policy knowledge base tool: lookup_policy.
Cannot access money-moving or order-mutating tools (Least Privilege Principle).
"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from libs.models import get_chat_model
from libs.tools import lookup_policy
from libs.state import AgentState

POLICY_TOOLS = [lookup_policy]

POLICY_PROMPT = """You are the Store Policy and Knowledge Specialist.
Your job is to answer customer questions accurately based solely on official store policies.
Rules:
- Call lookup_policy to verify return windows, warranty terms, and customer tier perks.
- Return window is strictly 30 days from confirmed delivery for regular customers, 45 days for Gold.
- Do NOT make up policies or promise exceptions.
"""

def policy_node(state: AgentState) -> Dict[str, Any]:
    """Executes the Policy specialist agent with read-only knowledge tools."""
    llm = get_chat_model("specialist")
    agent = create_react_agent(
        model=llm,
        tools=POLICY_TOOLS,
        prompt=POLICY_PROMPT
    )
    
    result = agent.invoke({"messages": state["messages"]})
    new_messages = result["messages"][len(state["messages"]):]
    
    actions = []
    for m in new_messages:
        if isinstance(m, ToolMessage):
            actions.append({"tool": m.name, "output": m.content})
            
    return {
        "messages": new_messages,
        "actions_taken": actions,
        "step_count": state.get("step_count", 0) + 1
    }
