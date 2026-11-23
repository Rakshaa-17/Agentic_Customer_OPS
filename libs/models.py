"""
Model Factory: Provides configured LLM instances based on environment configuration.
Supports Groq (default), Gemini, and OpenAI with clean provider abstraction.
"""
import os
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

def get_chat_model(role: str = "specialist") -> BaseChatModel:
    """
    Returns an initialized chat model based on the configured MODEL_PROVIDER and role.
    Roles:
      - 'triage': fast intent classification (default: openai/gpt-oss-120b)
      - 'specialist': robust function calling & reasoning (default: openai/gpt-oss-120b)
      - 'supervisor': deep reasoning & edge-case management (default: openai/gpt-oss-120b)
    """
    provider = os.getenv("MODEL_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set in your .env file. "
                "Please add GROQ_API_KEY=gsk_... to your .env file."
            )

        if role == "triage":
            model_name = os.getenv("GROQ_TRIAGE_MODEL", "openai/gpt-oss-120b")
            temperature = 0.0
        elif role == "supervisor":
            model_name = os.getenv("GROQ_SUPERVISOR_MODEL", "openai/gpt-oss-120b")
            temperature = 0.0
        else: # specialist
            model_name = os.getenv("GROQ_SPECIALIST_MODEL", "openai/gpt-oss-120b")
            temperature = 0.1

        return ChatGroq(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            max_retries=2
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in your .env file.")
        model_name = "gemini-2.0-flash" if role in ["triage", "specialist"] else "gemini-1.5-pro"
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.1
        )

    else:
        raise ValueError(f"Unsupported MODEL_PROVIDER: '{provider}'. Supported providers: 'groq', 'gemini'")
