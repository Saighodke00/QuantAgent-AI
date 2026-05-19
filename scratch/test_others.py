import os, time
from dotenv import load_dotenv; load_dotenv()

print("Testing other providers...")

# Test Groq
from langchain_groq import ChatGroq
try:
    t = time.perf_counter()
    g_key = os.environ.get("GROQ_API_KEY", "").strip()
    model = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=g_key, timeout=10)
    res = model.invoke("Say READY")
    print(f"Groq SUCCESS in {time.perf_counter()-t:.2f}s: {res.content.strip()}")
except Exception as e:
    print(f"Groq FAILED: {e}")

# Test OpenRouter
from langchain_openai import ChatOpenAI
try:
    t = time.perf_counter()
    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = ChatOpenAI(
        model="meta-llama/llama-3.3-70b-instruct:free",
        api_key=or_key,
        base_url="https://openrouter.ai/api/v1",
        timeout=10
    )
    res = model.invoke("Say READY")
    print(f"OpenRouter SUCCESS in {time.perf_counter()-t:.2f}s: {res.content.strip()}")
except Exception as e:
    print(f"OpenRouter FAILED: {e}")

# Test Mistral
from langchain_mistralai import ChatMistralAI
try:
    t = time.perf_counter()
    m_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    model = ChatMistralAI(model="mistral-small-latest", api_key=m_key, timeout=10)
    res = model.invoke("Say READY")
    print(f"Mistral SUCCESS in {time.perf_counter()-t:.2f}s: {res.content.strip()}")
except Exception as e:
    print(f"Mistral FAILED: {e}")
