import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Translator:
    mode: str = "dev"  # dev | prod
    deepseek_api_key: str = ""
    model: str = "deepseek-chat"

    async def translate_full_text(self, text: str, target_language: str = "ru") -> str:
        if self.mode == "dev":
            return f"Перевод (заглушка, {target_language}): {text}"
        return await self._call_deepseek(
            system="You are a professional translator. Translate to Russian language ONLY. Output ONLY Russian translation, nothing else.",
            user=f"Translate this text to Russian:\n\n{text}",
        )

    async def translate_title(self, text: str, target_language: str = "ru") -> str:
        if self.mode == "dev":
            return f"[RU] {text}"
        return await self._call_deepseek(
            system="You are a professional translator. Translate to Russian language ONLY. Keep it concise and natural.",
            user=f"Translate this title to Russian:\n\n{text}",
        )

    async def extract_tldr(self, text: str, target_language: str = "ru") -> str:
        if self.mode == "dev":
            snippets = [segment.strip() for segment in text.split(".") if segment.strip()]
            tldr = ". ".join(snippets[:3]) + "."
            return tldr

        prompt = (
            "Create a TLDR summary in Russian language ONLY. "
            "Write as ONE paragraph (not bullet points). "
            "Focus on the MAIN IDEA and KEY DETAILS. "
            "Include important facts, numbers, and context. "
            "Be concise but informative (about 50-100 words). "
            "Skip disclaimers, legal notices, ads. "
            "Just the core information."
        )
        return await self._call_deepseek(system=prompt, user=text)

    async def summarize_to_bullets(self, text: str, target_language: str = "ru") -> List[str]:
        if self.mode == "dev":
            sentences = [s.strip() for s in text.split(".") if s.strip()]
            return sentences[:5]

        prompt = (
            "Summarize the following text as 3-7 bullet points in Russian. "
            "Each bullet should be one concise sentence capturing a key point. "
            "Output ONLY the bullet points, one per line, without dashes or markers. "
            "Skip disclaimers, legal notices, ads. Focus on core information."
        )
        result = await self._call_deepseek(system=prompt, user=text)
        bullets = [line.lstrip("- *").strip() for line in result.strip().splitlines() if line.strip()]
        return bullets[:7]

    async def _call_deepseek(
        self, *, system: Optional[str], user: str
    ) -> str:
        if not self.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required in prod translator mode.")

        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": 2048,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "https://api.deepseek.com/chat/completions",
                        headers=headers,
                        json=payload
                    )

                    if response.status_code == 429:
                        wait_time = 30 * (attempt + 1)
                        logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    body = response.json()

                choices = body.get("choices")
                if not choices:
                    raise RuntimeError(f"DeepSeek response missing choices: {body}")
                message = choices[0].get("message", {})
                content = message.get("content")
                if not content:
                    raise RuntimeError(f"DeepSeek response missing content: {body}")
                return content
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries - 1:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise

        raise RuntimeError(f"Failed after {max_retries} attempts due to rate limiting")
