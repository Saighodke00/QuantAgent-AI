import os
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

class ResilientChatModel:
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
                print(f"⚠️ [SYSTEM] Primary LLM failed: {e}. Resiliently falling back to Groq...")
                return self.fallback.invoke(messages, *args, **kwargs)
            raise e

# Initialize Gemini with invalid key
gemini = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0.0,
    google_api_key="INVALID_KEY_TO_FORCE_ERROR",
    timeout=5.0
)

# Initialize Groq with valid key
groq = ChatGroq(
    model="mixtral-8x7b-32768",
    temperature=0.0,
    groq_api_key=os.environ.get("GROQ_API_KEY", ""),
    timeout=10.0
)

resilient = ResilientChatModel(gemini, groq)

print("Resilient model initialized. Running invocation test...")
try:
    response = resilient.invoke([HumanMessage(content="Hello! Respond with 'SUCCESS' if you hear me.")])
    print("Test result: SUCCESS!")
    print("Response content:", response.content)
except Exception as e:
    print("Test result: FAILED!")
    print("Exception raised:", type(e).__name__, str(e))
