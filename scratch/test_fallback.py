import os
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Initialize models
gemini = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0.0,
    google_api_key=os.environ.get("GEMINI_API_KEY", "")
)

groq = ChatGroq(
    model="mixtral-8x7b-32768",
    temperature=0.0,
    groq_api_key=os.environ.get("GROQ_API_KEY", "")
)

# Resilient model with fallback
resilient = gemini.with_fallbacks([groq])

print("Resilient model created successfully!")
try:
    response = resilient.invoke([HumanMessage(content="Hello! Respond with 'Python' if you hear me.")])
    print("Response content:", response.content)
except Exception as e:
    print("Invocation failed:", str(e))
