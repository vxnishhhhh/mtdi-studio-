"""One call for every language-model provider, standard library only.

    from mtdi import llm
    llm.available()                                   # providers with a key in the environment
    reply = llm.chat([{"role": "user", "content": "hi"}], system="Be brief.")
    reply["text"], reply["provider"], reply["model"]

Keys come from the environment only: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY,
GROQ_API_KEY, XAI_API_KEY. ``MTDI_LLM_PROVIDER`` picks one, ``MTDI_LLM_MODEL`` overrides
the model, ``MTDI_<PROVIDER>_BASE_URL`` points a provider at a proxy or a test server.
"""
import json
import os
import urllib.error
import urllib.request

PROVIDERS = {
    "anthropic": {"env": "ANTHROPIC_API_KEY", "model": "claude-sonnet-5-5", "base": "https://api.anthropic.com"},
    "openai": {"env": "OPENAI_API_KEY", "model": "gpt-5-mini", "base": "https://api.openai.com"},
    "gemini": {"env": "GEMINI_API_KEY", "model": "gemini-3.5-flash", "base": "https://generativelanguage.googleapis.com"},
    "groq": {"env": "GROQ_API_KEY", "model": "llama-3.3-70b-versatile", "base": "https://api.groq.com/openai"},
    "xai": {"env": "XAI_API_KEY", "model": "grok-4.5", "base": "https://api.x.ai"},
}
ORDER = ["anthropic", "openai", "gemini", "groq", "xai"]


class LLMError(Exception):
    pass


def _key(provider):
    return os.environ.get(PROVIDERS[provider]["env"], "").strip()


def _base(provider):
    return os.environ.get(f"MTDI_{provider.upper()}_BASE_URL", PROVIDERS[provider]["base"]).rstrip("/")


def available():
    return [p for p in ORDER if _key(p)]


def _post(url, body, headers, timeout):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise LLMError(f"HTTP {error.code}: {error.read()[:300].decode('utf-8', 'replace')}") from None
    except urllib.error.URLError as error:
        raise LLMError(f"unreachable: {error.reason}") from None


def chat(messages, system=None, provider=None, model=None, max_tokens=700, temperature=0.3, timeout=40):
    """Send a conversation, return {"text", "provider", "model"}. Raises LLMError."""
    provider = provider or os.environ.get("MTDI_LLM_PROVIDER") or (available() or [None])[0]
    if provider not in PROVIDERS:
        raise LLMError("no language model configured: set one of " +
                       ", ".join(PROVIDERS[p]["env"] for p in ORDER))
    key = _key(provider)
    if not key:
        raise LLMError(f"{PROVIDERS[provider]['env']} is not set")
    model = model or os.environ.get("MTDI_LLM_MODEL") or PROVIDERS[provider]["model"]
    base = _base(provider)
    msgs = [{"role": m["role"], "content": str(m["content"])} for m in messages]
    if provider == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "temperature": temperature, "messages": msgs}
        if system:
            body["system"] = system
        data = _post(base + "/v1/messages", body,
                     {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout)
        text = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
    elif provider == "gemini":
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in msgs]
        body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        data = _post(f"{base}/v1beta/models/{model}:generateContent?key={key}", body, {}, timeout)
        parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
    else:   # OpenAI-compatible: openai, groq, xai
        body = {"model": model, "messages": ([{"role": "system", "content": system}] if system else []) + msgs,
                "max_completion_tokens" if provider == "openai" else "max_tokens": max_tokens}
        if provider != "openai":
            body["temperature"] = temperature
        data = _post(base + "/v1/chat/completions", body, {"Authorization": "Bearer " + key}, timeout)
        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    if not text.strip():
        raise LLMError(f"{provider} returned an empty reply")
    return {"text": text.strip(), "provider": provider, "model": model}
