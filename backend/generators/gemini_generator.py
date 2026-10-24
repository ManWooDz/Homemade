# backend/generators/gemini_generator.py
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from generators.base import RecipeGenerator
from gemini_keys import create_client
from generators.prompts import build_recipe_prompt
from recipe_instructions import generation_schema, parse_generated_recipe

load_dotenv()

_MODEL_NAME = "gemini-3.1-flash-lite-preview"


class GeminiGenerator(RecipeGenerator):
    """Benchmark Gemini wrapper using the production structured-step protocol."""

    def __init__(self, api_key: str | None = None):
        self._client = create_client(api_key)

    def generate(self, ingredients: list, user_prefs: dict, base_recipe: dict, feedback: str | None = None) -> dict:
        if not self._client:
            return {"error": "API Key is missing. Please check your .env file."}

        try:
            prompt = build_recipe_prompt(ingredients, user_prefs, base_recipe, feedback)
            response = self._client.models.generate_content(
                model=_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=generation_schema(ingredients)),
            )
            return parse_generated_recipe(response.text, ingredients)
        except Exception as e:
            return {
                "error": "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้",
                "details": str(e),
            }
