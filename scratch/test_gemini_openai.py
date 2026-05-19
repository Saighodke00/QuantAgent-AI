import os, time
from dotenv import load_dotenv; load_dotenv()
from langchain_openai import ChatOpenAI

print("Testing OpenAI-compatible Gemini endpoint...")

keys = []
for i in ["", "_2", "_3"]:
    k = os.environ.get(f"GEMINI_API_KEY{i}", "").strip()
    if k:
        keys.append(k)

print(f"Loaded {len(keys)} Gemini keys.")

for idx, key in enumerate(keys):
    t = time.perf_counter()
    try:
        model = ChatOpenAI(
            model="gemini-2.5-flash",
            api_key=key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            temperature=0.0,
            timeout=10,
        )
        res = model.invoke("Say hello")
        print(f"Key #{idx+1} SUCCESS in {time.perf_counter()-t:.2f}s: {res.content.strip()}")
    except Exception as e:
        print(f"Key #{idx+1} FAILED in {time.perf_counter()-t:.2f}s: {e}")
