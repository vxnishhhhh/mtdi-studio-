"""One call for every language-model provider, standard library only.

    from mtdi import llm
    llm.available()                                   # providers with a key in the environment
    reply = llm.chat([{"role": "user", "content": "hi"}], system="Be brief.")
    reply["text"], reply["provider"], reply["model"]

Keys come from the environment only: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY,
GROQ_API_KEY, XAI_API_KEY. A local model needs no key: set OLLAMA_HOST (or MTDI_LOCAL_LLM=1
for http://localhost:11434) and Ollama is tried first, so NVTRA runs offline on a Pi 5 or Mac. ``MTDI_LLM_PROVIDER`` picks one, ``MTDI_LLM_MODEL`` overrides
that pinned provider's model, ``MTDI_<PROVIDER>_MODEL`` sets one provider's model, ``MTDI_<PROVIDER>_BASE_URL`` points a provider at a proxy or a test server.
"""
import ipaddress
import json
import os
import urllib.parse
import urllib.error
import urllib.request

PROVIDERS = {
    # Local first (owner brief: "local AI as well"). llama3.2:3b fits a Pi 5 with 8 GB; on the
    # M5 Mac set MTDI_OLLAMA_MODEL to something larger. Free, private, offline.
    "ollama": {"env": "OLLAMA_HOST", "model": "llama3.2:3b", "base": "http://localhost:11434", "local": True},
    "anthropic": {"env": "ANTHROPIC_API_KEY", "model": "claude-sonnet-5-5", "base": "https://api.anthropic.com"},
    "openai": {"env": "OPENAI_API_KEY", "model": "gpt-5-mini", "base": "https://api.openai.com"},
    "gemini": {"env": "GEMINI_API_KEY", "model": "gemini-3.5-flash", "base": "https://generativelanguage.googleapis.com"},
    "groq": {"env": "GROQ_API_KEY", "model": "llama-3.3-70b-versatile", "base": "https://api.groq.com/openai"},
    "xai": {"env": "XAI_API_KEY", "model": "grok-4.5", "base": "https://api.x.ai"},
}
ORDER = ["ollama", "groq", "gemini", "anthropic", "openai", "xai"]  # local, then free tiers, then paid


class LLMError(Exception):
    pass


def _local_enabled():
    return bool(os.environ.get("OLLAMA_HOST", "").strip() or os.environ.get("MTDI_LOCAL_LLM", "").strip() in ("1", "true"))


def _key(provider):
    if PROVIDERS[provider].get("local"):
        return "local" if _local_enabled() else ""
    return os.environ.get(PROVIDERS[provider]["env"], "").strip()


def _private_or_local(host):
    """Loopback or a private LAN address (the owner's Pi serving the Mac at home)."""
    if host in ("localhost", ""):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host.endswith(".local")  # mDNS names such as raspberrypi.local
    return ip.is_loopback or ip.is_private or ip.is_link_local


# CONTEXT: plain HTTP is allowed to LAN addresses on purpose, so a Pi 5 can serve the Mac's model (or the reverse).
# GUIDE: a new provider needs an entry in PROVIDERS and ORDER; OpenAI-compatible ones need nothing else.
def _check_transport(provider, url):
    """Prompts carry project data: plain HTTP is allowed only to this machine or the home LAN."""
    parts = urllib.parse.urlparse(url)
    if parts.scheme == "https" or (parts.scheme == "http" and _private_or_local(parts.hostname or "")):
        return url
    raise LLMError(f"{provider}: refusing {parts.scheme or 'no-scheme'}:// to {parts.hostname}; "
                   "use https, or http only for localhost or a private LAN address")


def _base(provider):
    default = PROVIDERS[provider]["base"]
    if provider == "ollama" and os.environ.get("OLLAMA_HOST", "").strip():
        host = os.environ["OLLAMA_HOST"].strip()
        default = host if host.startswith("http") else "http://" + host
    return _check_transport(provider, (os.environ.get(f"MTDI_{provider.upper()}_BASE_URL", "").strip() or default).rstrip("/"))


def available():
    return [p for p in ORDER if _key(p)]


def _post(url, body, headers, timeout):
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
    except (ValueError, UnicodeDecodeError) as error:
        raise LLMError(f"invalid JSON response: {error}") from error
    except urllib.error.HTTPError as error:
        raise LLMError(f"HTTP {error.code}: {error.read()[:300].decode('utf-8', 'replace')}") from None
    except urllib.error.URLError as error:
        raise LLMError(f"unreachable: {error.reason}") from None
    if not isinstance(data, dict):
        raise LLMError(f"unexpected response: {type(data).__name__}, not a JSON object")
    return data


def chat(messages, system=None, provider=None, model=None, max_tokens=700, temperature=0.3, timeout=40):
    """Send a conversation, return {"text", "provider", "model"}. Raises LLMError.

    With no provider pinned (argument or MTDI_LLM_PROVIDER), every configured provider is tried
    in ORDER, so a sleeping Pi falls back to a free cloud tier instead of NVTRA going quiet.
    A model name (argument or MTDI_LLM_MODEL) only makes sense for one provider, so during
    fallback each provider uses MTDI_<PROVIDER>_MODEL or its own default instead."""
    pinned = provider or os.environ.get("MTDI_LLM_PROVIDER")
    if pinned:
        return _chat_one(messages, system, pinned, model, max_tokens, temperature, timeout)
    errors = []
    for candidate in available():
        try:
            # HOURS-WASTED: 0.5 - an Ollama model name was being sent to Groq. A reviewer caught it.
            scoped = os.environ.get(f"MTDI_{candidate.upper()}_MODEL") or PROVIDERS[candidate]["model"]
            return _chat_one(messages, system, candidate, scoped, max_tokens, temperature, timeout)
        except LLMError as error:
            errors.append(f"{candidate}: {error}")
    if errors:
        raise LLMError("every configured provider failed: " + "; ".join(errors))
    return _chat_one(messages, system, None, model, max_tokens, temperature, timeout)


def _chat_one(messages, system, provider, model, max_tokens, temperature, timeout):
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
        extract = lambda d: "".join(part.get("text", "") for part in d.get("content", []) if part.get("type") == "text")
    elif provider == "gemini":
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in msgs]
        body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        data = _post(f"{base}/v1beta/models/{model}:generateContent?key={key}", body, {}, timeout)
        extract = lambda d: "".join(p.get("text", "") for p in
                                    ((d.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    else:   # OpenAI-compatible: openai, groq, xai, and ollama (local)
        body = {"model": model, "messages": ([{"role": "system", "content": system}] if system else []) + msgs,
                "max_completion_tokens" if provider == "openai" else "max_tokens": max_tokens}
        if provider != "openai":
            body["temperature"] = temperature
        headers = {} if PROVIDERS[provider].get("local") else {"Authorization": "Bearer " + key}
        data = _post(base + "/v1/chat/completions", body, headers, timeout)
        extract = lambda d: ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    try:
        text = extract(data)
        if not isinstance(text, str):
            raise TypeError(type(text).__name__)
    except (AttributeError, TypeError, IndexError, KeyError) as error:
        raise LLMError(f"{provider} returned a malformed reply: {error!r}") from error
    if not text.strip():
        raise LLMError(f"{provider} returned an empty reply")
    return {"text": text.strip(), "provider": provider, "model": model}
