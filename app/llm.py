"""Provider-agnostic LLM layer. Gemini over REST (no SDK). Switch with LLM_PROVIDER."""
import httpx

from .config import settings


async def complete(system: str, user: str, temperature: float = 0.1) -> str:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        return await _gemini(system, user, temperature)
    if provider == "openai":
        return await _openai(system, user, temperature)
    if provider == "anthropic":
        return await _anthropic(system, user, temperature)
    if provider == "groq":
        return await _groq(system, user, temperature)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


async def _gemini(system: str, user: str, temperature: float) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.llm_model}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": temperature},
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, params={"key": settings.gemini_api_key}, json=body)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _openai(system: str, user: str, temperature: float) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.llm_model, temperature=temperature,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content.strip()


async def _anthropic(system: str, user: str, temperature: float) -> str:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.llm_model, max_tokens=1024, temperature=temperature,
        system=system, messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


async def _groq(system: str, user: str, temperature: float) -> str:
    from groq import AsyncGroq
    client = AsyncGroq(api_key=settings.groq_api_key)
    resp = await client.chat.completions.create(
        model=settings.llm_model, temperature=temperature,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content.strip()
