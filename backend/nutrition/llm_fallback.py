"""Batched per-ingredient LLM composition estimate for names not found in
INMU/USDA. Mirrors generators/gemini_generator.py's structure. Estimates
ONLY per-100g composition -- never the whole recipe's totals -- and its
output is NEVER written back into ingredient_nutrition."""
import json
import math
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from nutrition.lookup import MacroValues

load_dotenv()

_MODEL_NAME = "gemini-3.1-flash-lite-preview"


def _to_float_or_none(value) -> float | None:
    """The model may return a macro as a string ("50") or junk; calculator.py
    does arithmetic on these, so coerce here and treat anything
    non-numeric as missing (None) rather than letting a TypeError escape."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class NutritionLLMEstimator:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        self._client = genai.Client(api_key=self._api_key) if self._api_key else None

    def estimate(self, names: list[str]) -> list[MacroValues]:
        if not names:
            return []
        if not self._client:
            return [MacroValues(None, None, None, None) for _ in names]

        try:
            prompt = (
                "ประมาณค่าโภชนาการต่อวัตถุดิบ 100 กรัม ของวัตถุดิบต่อไปนี้แต่ละชนิด "
                "ตอบเป็น JSON array เรียงตามลำดับที่ให้มาเท่านั้น ห้ามมีข้อความอื่นปน: "
                f"{json.dumps(names, ensure_ascii=False)}\n"
                'รูปแบบ: [{"calories": ตัวเลข, "protein_g": ตัวเลข, "carbs_g": ตัวเลข, "fat_g": ตัวเลข}, ...]'
            )
            response = self._client.models.generate_content(
                model=_MODEL_NAME, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            raw = json.loads(response.text)
            if not isinstance(raw, list) or len(raw) != len(names):
                return [MacroValues(None, None, None, None) for _ in names]
            return [
                MacroValues(
                    calories=_to_float_or_none(item.get("calories")),
                    protein_g=_to_float_or_none(item.get("protein_g")),
                    carbs_g=_to_float_or_none(item.get("carbs_g")),
                    fat_g=_to_float_or_none(item.get("fat_g")),
                )
                for item in raw
            ]
        except Exception:
            return [MacroValues(None, None, None, None) for _ in names]
