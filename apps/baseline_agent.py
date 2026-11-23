"""
Single-Agent Baseline (ReAct pattern).
This serves as our initial benchmark against which we will measure
the lift provided by our multi-agent supervisor architecture.
"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from libs.models import get_chat_model
from libs.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an e-commerce customer support operations agent.
You have access to tools to lookup orders, lookup customers, update shipping addresses, cancel orders, and issue refunds.
You must always verify policies and follow company rules:
- Only cancel orders or update addresses if the order is 'pending' or 'processing'.
- Refunds exceeding $50.00 require human supervisor approval.
- Be polite, accurate, and concise. Always tell the customer what action was taken and quote any relevant IDs (order ID, refund ID, etc.).
"""

def get_baseline_agent():
    """Compiles and returns a single ReAct agent with all available tools."""
    llm = get_chat_model("specialist")
    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT
    )
    return agent

def run_baseline_turn(agent, message_history: List[Dict[str, str]]) -> str:
    """
    Executes a single turn of the baseline agent given a list of messages:
    [{'role': 'user'|'assistant', 'content': '...'}]
    """
    messages = []
    for msg in message_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    
    result = agent.invoke({"messages": messages})
    # The final message is the agent's response
    final_message = result["messages"][-1]
    return final_message.content

if __name__ == "__main__":
    agent = get_baseline_agent()
    response = run_baseline_turn(agent, [{"role": "user", "content": "Hi, what is the status of my order ORD-1001?"}])
    print("Baseline Agent Response:\n", response)
