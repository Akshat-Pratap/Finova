"""Finova — Gemini AI Provider.

Integrates with Google Gemini API for financial discrepancy investigation.
Uses structured JSON responses validated by Pydantic.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.ai_engine.provider import AIProvider
from app.services.ai_engine.prompts import SYSTEM_PROMPT
from app.services.ai_engine.schemas import AIInvestigationResponse

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""

    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._initialized = True
            logger.info("Gemini AI provider initialized.")
        except Exception as exc:
            logger.error("Failed to initialize Gemini client: %s", exc)
            self._client = None
            self._initialized = True  # Mark as attempted

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(settings.gemini_api_key)

    async def investigate(
        self,
        context: Dict[str, Any],
        prompt: str,
    ) -> Dict[str, Any]:
        """Investigate using Gemini with retry logic."""
        self._ensure_initialized()

        if not self._client:
            raise RuntimeError("Gemini client not initialized")

        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = await self._call_gemini(full_prompt)
                parsed = self._parse_response(response)
                return parsed.model_dump()
            except Exception as exc:
                last_error = exc
                logger.warning("Gemini attempt %d failed: %s", attempt + 1, exc)

        raise RuntimeError(f"Gemini investigation failed after {max_retries + 1} attempts: {last_error}")

    async def _call_gemini(self, prompt: str) -> str:
        """Make the actual Gemini API call."""
        from google import genai as google_genai
        # Use sync client in async context — motor doesn't need true async here
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_call():
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text

        return await loop.run_in_executor(None, _sync_call)

    def _parse_response(self, raw_text: str) -> AIInvestigationResponse:
        """Parse and validate Gemini's JSON response."""
        # Extract JSON from response (may be wrapped in markdown)
        text = raw_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        return AIInvestigationResponse(**data)
