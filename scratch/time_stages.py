import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv; load_dotenv()
from langchain_core.messages import HumanMessage, SystemMessage

print('=== TIMING EACH STAGE ===')
print()

# Stage 1: LLM init
t = time.perf_counter()
from agents.llm import get_llm, clean_response_content
llm = get_llm()
print(f'LLM init           : {time.perf_counter()-t:.2f}s')

# Stage 2: Intent Analyst LLM call
SYS = 'Return ONLY this JSON: {"ticker":"AAPL","strategy_name":"RSI","strategy_type":"mean_reversion","date_start":"2023-01-01","date_end":"2025-01-01","strategy_description":"RSI"}'
t = time.perf_counter()
r = llm.invoke([SystemMessage(content=SYS), HumanMessage(content='RSI on AAPL for 2 years')])
elapsed = time.perf_counter() - t
content = clean_response_content(r.content)
print(f'Intent Analyst LLM : {elapsed:.2f}s  ({len(content)} chars returned)')

# Stage 3: Small LLM roundtrip
t = time.perf_counter()
r2 = llm.invoke([HumanMessage(content='Say READY')])
print(f'Small LLM roundtrip: {time.perf_counter()-t:.2f}s')

# Stage 4: Subprocess cold start
t = time.perf_counter()
import subprocess
p = subprocess.run(
    [sys.executable, '-c', 'import yfinance, pandas, numpy, sklearn, json; print("warm")'],
    capture_output=True, text=True, timeout=30
)
print(f'Subprocess cold    : {time.perf_counter()-t:.2f}s  (out={p.stdout.strip()})')

# Stage 5: Subprocess warm
t = time.perf_counter()
p2 = subprocess.run(
    [sys.executable, '-c', 'import yfinance, pandas, numpy, json; print("warm2")'],
    capture_output=True, text=True, timeout=30
)
print(f'Subprocess warm    : {time.perf_counter()-t:.2f}s')

# Stage 6: yfinance download
t = time.perf_counter()
import yfinance as yf
hist = yf.Ticker('AAPL').history(period='2y')
print(f'yfinance download  : {time.perf_counter()-t:.2f}s  ({len(hist)} rows)')

print()
print('=========================')
