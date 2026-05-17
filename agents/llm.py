import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

def get_llm(temperature: float = 0.0):
    """
    Returns a LangChain LLM instance.
    Uses Google Gemini (gemini-flash-latest) as the primary provider.
    Falls back to Groq (mixtral-8x7b-32768) if Gemini is unavailable or fails.
    """
    # 1. Try Gemini
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-flash-latest",
                temperature=temperature,
                google_api_key=os.environ["GEMINI_API_KEY"],
            )
        except Exception:
            # Fall back to Groq if Gemini creation fails
            pass

    # 2. Try Groq
    if os.environ.get("GROQ_API_KEY"):
        return ChatGroq(
            model="mixtral-8x7b-32768",
            temperature=temperature,
            groq_api_key=os.environ["GROQ_API_KEY"],
        )

    raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY is set in the environment.")

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
