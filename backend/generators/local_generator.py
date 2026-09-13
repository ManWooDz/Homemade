# backend/generators/local_generator.py
import json
import os

import requests

from generators.base import RecipeGenerator
from generators.prompts import build_recipe_prompt


class LocalLLMGenerator(RecipeGenerator):
    """Calls a self-hosted vLLM OpenAI-compatible endpoint. Which model
    (Qwen 4B / 7B-9B / any other checkpoint) is used is purely a
    constructor/env-var choice — never a code change, so benchmarking
    different sizes doesn't touch this file."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self._base_url = base_url if base_url is not None else os.getenv("LOCAL_LLM_BASE_URL")
        self._model = model if model is not None else os.getenv("LOCAL_LLM_MODEL")

    def generate(self, ingredients: list, user_prefs: dict, base_recipe: dict, feedback: str | None = None) -> dict:
        if not self._base_url or not self._model:
            return {"error": "LOCAL_LLM_BASE_URL / LOCAL_LLM_MODEL is missing. Please check your .env file."}

        try:
            prompt = build_recipe_prompt(ingredients, user_prefs, base_recipe, feedback, include_example=True)
            response = requests.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
                timeout=120,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            return {
                "error": "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้ (local model)",
                "details": str(e),
            }
