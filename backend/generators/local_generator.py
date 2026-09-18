# backend/generators/local_generator.py
import json
import os

import requests

from generators.base import RecipeGenerator
from generators.prompts import build_recipe_prompt

# Character-set-only patterns (no lookahead) for vLLM's guided_json /
# response_format=json_schema decoding. Verified empirically (2026-09-18)
# against a live vLLM server: a plain allowed-character-class pattern
# reliably blocks off-schema scripts (Greek/Arabic/Tamil/Chinese) leaking
# into fields — a real failure mode observed in benchmark runs before this
# was added. A `(?=.*[Thai])` lookahead ("must contain at least one Thai
# character") was also tried and found NOT reliably enforced by this vLLM
# version's constrained-decoding backend — one field honored it, another
# didn't, with the identical pattern — so this deliberately does not rely
# on lookahead assertions, only a plain allowed-character class.
_THAI_FIELD_PATTERN = r"^[฀-๿a-zA-Z0-9 .,()\-/%:]+$"
_ENGLISH_FIELD_PATTERN = r"^[a-zA-Z0-9 .,()\-/%:']+$"

_RECIPE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "recipe_name": {"type": "string", "pattern": _ENGLISH_FIELD_PATTERN},
        "servings": {"type": "integer"},
        "adjusted_ingredients": {
            "type": "array",
            "items": {"type": "string", "pattern": _THAI_FIELD_PATTERN},
        },
        "diet_tags": {
            "type": "array",
            "items": {"type": "string", "pattern": _ENGLISH_FIELD_PATTERN},
        },
        "nutrition": {
            "type": "object",
            "properties": {
                "basis": {"type": "string"},
                "calories": {"type": "number"},
                "protein_g": {"type": "number"},
                "carbs_g": {"type": "number"},
                "fat_g": {"type": "number"},
            },
            "required": ["basis", "calories", "protein_g", "carbs_g", "fat_g"],
        },
        "instructions": {
            "type": "array",
            "items": {"type": "string", "pattern": _THAI_FIELD_PATTERN},
        },
        "safety_warning": {"type": "string", "pattern": _THAI_FIELD_PATTERN},
    },
    "required": [
        "recipe_name",
        "servings",
        "adjusted_ingredients",
        "diet_tags",
        "nutrition",
        "instructions",
        "safety_warning",
    ],
}


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
                    # json_schema (not the looser json_object) with
                    # character-class patterns per field — see
                    # _RECIPE_JSON_SCHEMA's module-level comment for why
                    # this specific form (no lookahead) was chosen.
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {"name": "recipe", "schema": _RECIPE_JSON_SCHEMA},
                    },
                    # Qwen3.5 is a hybrid thinking/non-thinking model — without this,
                    # the answer goes into a separate "reasoning" field first and
                    # "content" stays null until reasoning finishes (often never,
                    # within a reasonable token budget). Verified empirically
                    # (2026-09-18) against a live vLLM server before this benchmark
                    # was ever run for real: content was null in every test until
                    # this flag was added.
                    "chat_template_kwargs": {"enable_thinking": False},
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
