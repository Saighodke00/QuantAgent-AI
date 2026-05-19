import os, time
from dotenv import load_dotenv; load_dotenv()
from langchain_openai import ChatOpenAI

print("Testing Cerebras Qwen-3-235b...")

keys = []
for i in ["", "_2"]:
    k = os.environ.get(f"CEREBRAS_API_KEY{i}", "").strip()
    if k:
        keys.append(k)

print(f"Loaded {len(keys)} Cerebras keys.")

for idx, key in enumerate(keys):
    t = time.perf_counter()
    try:
        model = ChatOpenAI(
            model="qwen-3-235b-a22b-instruct-2507",
            api_key=key,
            base_url="https://api.cerebras.ai/v1",
            temperature=0.0,
            timeout=10,
        )
        res = model.invoke("Say hello")
        print(f"Key #{idx+1} SUCCESS in {time.perf_counter()-t:.2f}s: {res.content.strip()}")
    except Exception as e:
        print(f"Key #{idx+1} FAILED in {time.perf_counter()-t:.2f}s: {e}")
