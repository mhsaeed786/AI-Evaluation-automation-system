"""Google Gemini provider adapter."""

import logging
from typing import Any, Dict, List, Optional

from . import BaseProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    name = "gemini"
    supports_streaming = True
    supports_tools = False

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")
        return self._client

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        genai = self._get_client()
        model_name = model or self.config.get("default_model", "gemini-2.0-flash")

        system_text = ""
        contents = []
        for m in messages:
            if m["role"] == "system":
                system_text += m["content"] + "\n"
            elif m["role"] == "user":
                contents.append({"role": "user", "parts": [m["content"]]})
            elif m["role"] == "assistant":
                contents.append({"role": "model", "parts": [m["content"]]})

        genai_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_text.strip() or None,
        )

        response = await genai_model.generate_content_async(
            contents,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

        content = response.text if response.text else ""
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        return LLMResponse(
            content=content,
            provider=self.name,
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=self.calculate_cost(prompt_tokens, completion_tokens),
        )
