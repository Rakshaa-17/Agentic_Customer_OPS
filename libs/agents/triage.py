"""
Triage Agent: Rapid intent classification, sentiment analysis, and entity extraction.
Uses the lightweight fast model (openai/gpt-oss-20b on Groq) with Pydantic structured output.
"""
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from libs.models import get_chat_model
from libs.state import AgentState

class TriageOutput(BaseModel):
    intent: Literal["order_status", "return_refund", "address_change", "billing_dispute", "policy_question", "complaint", "general"] = Field(
        ..., description="The primary intent of the customer's request."
    )
    sentiment: Literal["positive", "neutral", "frustrated", "angry"] = Field(
        ..., description="The detected customer emotional tone."
    )
    customer_email: Optional[str] = Field(None, description="Extracted customer email address, if provided.")
    order_id: Optional[str] = Field(None, description="Extracted order ID (e.g. 'ORD-1001'), if mentioned.")
    summary: str = Field(..., description="A 1-sentence concise summary of what the customer is asking.")

TRIAGE_SYSTEM_PROMPT = """You are a Tier-1 Customer Operations Triage Specialist.
Analyze the customer's message and categorize their intent, sentiment, and extract relevant entities (order ID, email).
Intents:
- order_status: checking delivery, tracking, or order progress.
- return_refund: asking for return, money back, replacement, or reporting damaged goods.
- address_change: modifying delivery address.
- billing_dispute: charged wrong amount or unexpected fee.
- policy_question: asking about return windows, warranties, VIP perks, or store rules.
- complaint: expressing dissatisfaction or service delay without requesting a specific order action.
- general: greeting, vague request, or chit-chat.
"""

def triage_node(state: AgentState) -> Dict[str, Any]:
    """Triage node: runs structured intent and entity extraction."""
    llm = get_chat_model("triage")
    structured_llm = llm.with_structured_output(TriageOutput)
    
    last_user_message = next((m.content for m in reversed(state["messages"]) if m.type == "human"), "")
    
    messages = [
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        HumanMessage(content=f"Customer Inquiry: {last_user_message}")
    ]
    
    result: TriageOutput = structured_llm.invoke(messages)
    
    return {
        "intent": result.intent,
        "sentiment": result.sentiment,
        "order_id": result.order_id or state.get("order_id"),
        "step_count": state.get("step_count", 0) + 1
    }
