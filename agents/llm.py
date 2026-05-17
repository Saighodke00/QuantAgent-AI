import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

class ResilientChatModel:
    """
    A robust custom wrapper that intercepts ALL execution-time exceptions
    (like 429 RESOURCE_EXHAUSTED) from the primary LLM and seamlessly
    routes the invocation to the fallback LLM.
    """
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def invoke(self, messages, *args, **kwargs):
        if not self.primary:
            if self.fallback:
                return self.fallback.invoke(messages, *args, **kwargs)
            raise ValueError("No active LLM available.")
        
        try:
            return self.primary.invoke(messages, *args, **kwargs)
        except Exception as e:
            if self.fallback:
                # Log silently without emojis to prevent Windows charmap print crashes
                print(f"[SYSTEM] Primary LLM invocation failed ({type(e).__name__}). Resiliently falling back to Groq...")
                return self.fallback.invoke(messages, *args, **kwargs)
            raise e

def get_llm(temperature: float = 0.0):
    """
    Returns a custom resilient LLM wrapper instance.
    Uses Google Gemini (gemini-flash-latest) as the primary provider with a fast 10s timeout.
    Resiliently falls back to Groq (llama-3.3-70b-versatile) if Gemini is rate-limited,
    exhausted (429), or encounters any invocation/connection errors.
    """
    gemini_model = None
    if os.environ.get("GEMINI_API_KEY"):
        try:
            gemini_model = ChatGoogleGenerativeAI(
                model="gemini-flash-latest",
                temperature=temperature,
                google_api_key=os.environ["GEMINI_API_KEY"],
                timeout=10.0,
            )
        except Exception:
            pass

    groq_model = None
    if os.environ.get("GROQ_API_KEY"):
        try:
            groq_model = ChatGroq(
                model="llama-3.1-8b-instant",
                temperature=temperature,
                groq_api_key=os.environ["GROQ_API_KEY"],
                timeout=10.0,
            )
        except Exception:
            pass

    return ResilientChatModel(gemini_model, groq_model)

def clean_response_content(content) -> str:
    """
    Robustly converts LLM response content (which can be a string or a list of parts)
    into a clean, stripped string.
    """
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts).strip()
    return str(content).strip()
