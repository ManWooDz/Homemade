# backend/generators/gemini_generator.py
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from generators.base import RecipeGenerator
from generators.prompts import build_recipe_prompt

load_dotenv()

_MODEL_NAME = "gemini-3.1-flash-lite-preview"


class GeminiGenerator(RecipeGenerator):
    """Gemini-backed implementation of RecipeGenerator. New,
    interface-conforming twin of main.py's call_agentic_llm() built for the
    generator benchmark — main.py itself is untouched this milestone."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None

    def generate(self, ingredients: list, user_prefs: dict, base_recipe: dict, feedback: str | None = None) -> dict:
        if not self._client:
            return {"error": "API Key is missing. Please check your .env file."}

        try:
            prompt = build_recipe_prompt(ingredients, user_prefs, base_recipe, feedback)
            response = self._client.models.generate_content(
                model=_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)
        except Exception as e:
            return {
                "error": "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้",
                "details": str(e),
            }
