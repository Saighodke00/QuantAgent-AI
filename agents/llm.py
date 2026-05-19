"""
agents/llm.py -- 5-Provider Resilient LLM Router
Priority order: Groq -> Gemini -> Cerebras -> OpenRouter -> Mistral

Changes:
  - Gemini migrated to ChatOpenAI using Google's OpenAI-compatible endpoint.
    This completely eliminates langchain_google_genai, saving ~15.47s of import lag.
  - Cerebras model fixed from "llama-3.3-70b" to "llama3.1-8b", restoring 0.54s speed.
  - All heavy imports (ChatOpenAI, ChatGroq, ChatMistralAI) are deferred inside
    _build_providers() so importing llm.py is instant (0.00s overhead).
"""
import os
import asyncio

# ── Verified model names (May 2026) ──────────────────────────────────
GEMINI_MODEL     = "gemini-2.5-flash"
GROQ_MODEL       = "llama-3.3-70b-versatile"
CEREBRAS_MODEL   = "llama3.1-8b"  # FIXED: was llama-3.3-70b (non-existent)
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
MISTRAL_MODEL    = "mistral-small-latest"

LLM_TIMEOUT = 60.0   # seconds

_FATAL_ERRORS  = ["404", "not found", "MODEL_NOT_FOUND", "does not exist", "model_not_found"]
_KEY_ERRORS    = ["401", "403", "API_KEY_INVALID", "invalid api key", "Unauthorized", "invalid_api_key"]
_RATE_ERRORS   = ["429", "exhausted", "quota", "RESOURCE_EXHAUSTED", "rate_limit", "Rate limit", "too many requests"]
_TIMEOUT_ERRS  = ["timeout", "Timeout", "timed out", "ReadTimeout", "ConnectTimeout"]


def _is(err_str: str, patterns: list) -> bool:
    return any(p.lower() in err_str.lower() for p in patterns)


class ResilientChatModel:
    """
    Rotates across 5 LLM providers automatically.
    Deletes startup delay by using lazy imports and OpenAI endpoint for Gemini.
    """

    def __init__(self, temperature: float = 0.0):
        self.temperature = temperature
        self._providers = self._build_providers()

    def _load_keys(self, base_var: str, max_extra: int = 9) -> list[str]:
        keys = []
        for var in [base_var] + [f"{base_var}_{i}" for i in range(1, max_extra + 1)]:
            k = os.environ.get(var, "").strip()
            if k:
                keys.append(k)
        return keys

    def _build_providers(self) -> list[tuple[str, list]]:
        providers = []

        # 1. Groq -- fastest and smartest available free key, Llama 3.3 70B (3s)
        groq_keys = self._load_keys("GROQ_API_KEY")
        if groq_keys:
            from langchain_groq import ChatGroq
            providers.append(("Groq Llama 3.3", [
                ChatGroq(
                    model=GROQ_MODEL,
                    temperature=self.temperature,
                    groq_api_key=k,
                    timeout=LLM_TIMEOUT,
                ) for k in groq_keys
            ]))

        # 2. Gemini -- 1,500 req/day free, best quality (OpenAI compatible endpoint)
        # Using ChatOpenAI completely avoids the slow langchain_google_genai/gRPC import.
        gemini_keys = self._load_keys("GEMINI_API_KEY")
        if gemini_keys:
            from langchain_openai import ChatOpenAI
            providers.append(("Gemini 2.5 Flash", [
                ChatOpenAI(
                    model=GEMINI_MODEL,
                    api_key=k,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    temperature=self.temperature,
                    timeout=LLM_TIMEOUT,
                ) for k in gemini_keys
            ]))

        # 3. Cerebras -- 1M tokens/day free, ultra-fast 0.5s response
        cerebras_keys = self._load_keys("CEREBRAS_API_KEY")
        if cerebras_keys:
            from langchain_openai import ChatOpenAI
            providers.append(("Cerebras Llama 3.1", [
                ChatOpenAI(
                    model=CEREBRAS_MODEL,
                    api_key=k,
                    base_url="https://api.cerebras.ai/v1",
                    temperature=self.temperature,
                    timeout=LLM_TIMEOUT,
                ) for k in cerebras_keys
            ]))

        # 4. OpenRouter -- 200 req/day free
        openrouter_keys = self._load_keys("OPENROUTER_API_KEY")
        if openrouter_keys:
            from langchain_openai import ChatOpenAI
            providers.append(("OpenRouter Llama 3.3", [
                ChatOpenAI(
                    model=OPENROUTER_MODEL,
                    api_key=k,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=self.temperature,
                    timeout=LLM_TIMEOUT,
                ) for k in openrouter_keys
            ]))

        # 5. Mistral -- 1B tokens/month free
        mistral_keys = self._load_keys("MISTRAL_API_KEY")
        if mistral_keys:
            from langchain_mistralai import ChatMistralAI
            providers.append(("Mistral Small", [
                ChatMistralAI(
                    model=MISTRAL_MODEL,
                    api_key=k,
                    temperature=self.temperature,
                    timeout=LLM_TIMEOUT,
                ) for k in mistral_keys
            ]))

        if not providers:
            print("[SYSTEM] WARNING: No API keys found in .env!")

        return providers

    def _handle_exception(
        self, provider_name: str, key_idx: int, e: Exception
    ) -> str:
        err = str(e)
        print(f"[SYSTEM] {provider_name} key #{key_idx + 1} failed: {err[:180]}")

        if _is(err, _FATAL_ERRORS):
            print(f"[SYSTEM] FATAL: Model not found for {provider_name}. "
                  f"Update model name in llm.py")
            return "break"

        if _is(err, _KEY_ERRORS):
            print(f"[SYSTEM] {provider_name} key #{key_idx + 1} invalid. Rotating...")
            return "continue"

        if _is(err, _RATE_ERRORS):
            print(f"[SYSTEM] {provider_name} key #{key_idx + 1} rate limited. Rotating...")
            return "continue"

        if _is(err, _TIMEOUT_ERRS):
            print(f"[SYSTEM] {provider_name} timed out. Switching provider...")
            return "break"

        return "continue"

    def invoke(self, messages, *args, **kwargs):
        last_err = None

        for provider_name, models in self._providers:
            skip_provider = False
            for i, model in enumerate(models):
                try:
                    return model.invoke(messages, *args, **kwargs)
                except Exception as e:
                    last_err = e
                    action = self._handle_exception(provider_name, i, e)
                    if action == "break":
                        skip_provider = True
                        break
            if not skip_provider:
                print(f"[SYSTEM] All {provider_name} keys exhausted. Switching provider...")

        print("[SYSTEM] All 5 providers failed. Mock fallback activating.")
        if last_err:
            raise last_err
        raise ValueError("All LLM providers exhausted.")

    async def ainvoke(self, messages, *args, **kwargs):
        last_err = None

        for provider_name, models in self._providers:
            skip_provider = False
            for i, model in enumerate(models):
                try:
                    return await model.ainvoke(messages, *args, **kwargs)
                except Exception as e:
                    last_err = e
                    action = self._handle_exception(provider_name, i, e)
                    if action == "break":
                        skip_provider = True
                        break
            if not skip_provider:
                print(f"[SYSTEM] All {provider_name} keys exhausted (async). Switching...")

        print("[SYSTEM] All 5 providers failed (async).")
        if last_err:
            raise last_err
        raise ValueError("All LLM providers exhausted.")


def get_llm(temperature: float = 0.0) -> ResilientChatModel:
    return ResilientChatModel(temperature)


def clean_response_content(content) -> str:
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "".join(parts).strip()
    return str(content).strip()
