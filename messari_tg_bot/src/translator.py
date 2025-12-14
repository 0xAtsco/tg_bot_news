import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Translator:
    mode: str = "dev"  # dev | prod
    openrouter_api_key: str = ""
    translate_model: str = "mistralai/mixtral-8x7b-instruct"
    tldr_model: str = "mistralai/mixtral-8x7b-instruct"

    async def translate_full_text(self, text: str, target_language: str = "ru") -> str:
        if self.mode == "dev":
            return f"Перевод (заглушка, {target_language}): {text}"
        return await self._call_openrouter(
            model=self.translate_model,
            system=f"You are a professional translator. Translate the following text to Russian language ONLY. Output ONLY the Russian translation, nothing else. Preserve the meaning and structure. Use neutral business tone.",
            user=f"Translate this text to Russian:\n\n{text}",
        )

    async def summarize_to_bullets(
        self,
        text: str,
        target_language: str = "ru",
        min_bullets: int = 3,
        max_bullets: int = 7,
    ) -> List[str]:
        if self.mode == "dev":
            snippets = [segment.strip() for segment in text.split(".") if segment.strip()]
            bullets: List[str] = []
            for idx, snippet in enumerate(snippets[:max_bullets]):
                bullets.append(f"Пункт {idx + 1}: {snippet}")
            while len(bullets) < min_bullets:
                bullets.append(f"Пункт {len(bullets) + 1}: доп. резюме отсутствует")
            return bullets

        prompt = (
            f"Create {min_bullets}-{max_bullets} bullet point summary in Russian language ONLY. "
            f"Each bullet should be 1-2 sentences, concise and fact-focused. "
            f"Preserve key facts and numbers. Output ONLY in Russian, no English words. "
            f"Start each bullet with '- ' (dash and space). "
            f"IMPORTANT: Skip disclaimers, legal notices, advertisements, and promotional content. "
            f"Focus only on the main content and key insights."
        )
        response = await self._call_openrouter(
            model=self.tldr_model, system=prompt, user=text, usage_include=True
        )
        bullets = [line.strip(" -•\t") for line in response.split("\n") if line.strip()]
        if len(bullets) < min_bullets:
            bullets.extend(["(пусто)"] * (min_bullets - len(bullets)))
        return bullets[:max_bullets]

    async def _call_openrouter(
        self, *, model: str, system: Optional[str], user: str, usage_include: bool = False
    ) -> str:
        if not self.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required in prod translator mode.")

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if usage_include:
            payload["usage"] = {"include": True}

        # Retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(
                    base_url="https://openrouter.ai/api/v1",
                    timeout=60.0,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                ) as client:
                    response = await client.post("/chat/completions", headers=headers, json=payload)
                    response.raise_for_status()
                    body = response.json()

                choices = body.get("choices")
                if not choices:
                    raise RuntimeError(f"OpenRouter response missing choices: {body}")
                message = choices[0].get("message", {})
                content = message.get("content")
                if not content:
                    raise RuntimeError(f"OpenRouter response missing content: {body}")
                return content
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Network error calling OpenRouter (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to call OpenRouter after {max_retries} attempts: {e}")
                    raise
