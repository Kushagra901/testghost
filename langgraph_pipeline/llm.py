"""
TestGhost — Provider-agnostic LLM interface.
Supports Gemini (Google GenAI), Anthropic Claude, Groq, and OpenRouter.
Provider is switched via the LLM_PROVIDER environment variable.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
    """
    Unified async function to call the configured LLM provider.
    Honors LLM_TIMEOUT_SECONDS to prevent pipeline hangs.
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower().strip()
    timeout = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))

    if provider in ("gemini", "google"):
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")

        client = genai.Client(api_key=api_key)

        def _sync_gemini_call() -> str:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.2,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config,
            )
            return response.text or ""

        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _sync_gemini_call),
            timeout=timeout,
        )

    elif provider == "anthropic":
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        model_name = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")

        client = anthropic.Anthropic(api_key=api_key)

        def _sync_anthropic_call() -> str:
            response = client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text.strip()

        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _sync_anthropic_call),
            timeout=timeout,
        )

    elif provider in ("groq", "openrouter"):
        import httpx

        if provider == "groq":
            api_key = os.environ.get("GROQ_API_KEY", "")
            base_url = "https://api.groq.com/openai/v1"
            model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        else:
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
            base_url = "https://openrouter.ai/api/v1"
            model_name = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Supported: gemini, anthropic, groq, openrouter."
        )
