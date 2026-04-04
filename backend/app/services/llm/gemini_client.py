from __future__ import annotations

import httpx

from app.core.config import Settings
from app.services.llm.prompt_builder import SYSTEM_PROMPT


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_response(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("Gemini API key is not configured")

        url = (
            f"{self.settings.gemini_base_url}/models/"
            f"{self.settings.gemini_model}:generateContent?key={self.settings.gemini_api_key}"
        )
        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self.settings.gemini_temperature,
                "topP": 0.95,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")

        return text
