"""Embedding helpers for recipe-history retrieval."""
import math
import os
from collections.abc import Iterable

from google import genai
from google.genai import types

from nutrition.parser import parse_ingredient_string


_MODEL_NAME = "gemini-embedding-001"
_DIMENSION = 768
_CUSTOM_RECIPE_PREFIX = "custom recipe"
_UNSPECIFIED_TASTE = "ไม่ระบุ"


class EmbeddingError(RuntimeError):
    """Raised when an embedding request cannot produce valid vectors."""


def _stable_unique(values: Iterable[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            unique.append(cleaned)
    return unique


def build_history_document(recipe_name, adjusted_ingredients, diet_tags) -> str:
    """Build a deterministic document for a generated recipe in history."""
    ingredient_names = _stable_unique(
        parse_ingredient_string(raw).name
        for raw in adjusted_ingredients
        if raw.strip()
    )
    sections = [recipe_name.strip()] if recipe_name.strip() else []
    if ingredient_names:
        sections.append(f"วัตถุดิบ: {', '.join(ingredient_names)}")
    tags = _stable_unique(diet_tags)
    if tags:
        sections.append(f"diet_tags: {', '.join(tags)}")
    return " | ".join(sections)


def build_request_query(recipe_name, ingredient_names, taste) -> str:
    """Build a deterministic retrieval query for a generation request."""
    title = recipe_name.strip()
    sections = []
    if title and not title.casefold().startswith(_CUSTOM_RECIPE_PREFIX):
        sections.append(title)
    ingredients = _stable_unique(ingredient_names)
    if ingredients:
        sections.append(f"วัตถุดิบ: {', '.join(ingredients)}")
    cleaned_taste = taste.strip()
    if cleaned_taste and cleaned_taste != _UNSPECIFIED_TASTE:
        sections.append(f"taste: {cleaned_taste}")
    return " | ".join(sections)


def _create_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EmbeddingError("GEMINI_API_KEY is required to create embeddings")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=5000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def _validate_and_normalize(response, expected_count: int) -> list[list[float]]:
    embeddings = getattr(response, "embeddings", None)
    if embeddings is None or len(embeddings) != expected_count:
        raise EmbeddingError("Embedding response count did not match input count")

    normalized: list[list[float]] = []
    for embedding in embeddings:
        values = getattr(embedding, "values", None)
        if values is None or len(values) != _DIMENSION:
            raise EmbeddingError("Embedding response had an invalid dimension")
        if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
            raise EmbeddingError("Embedding response contained non-finite values")
        vector = [float(value) for value in values]
        norm = math.hypot(*vector)
        if not math.isfinite(norm) or norm == 0.0:
            raise EmbeddingError("Embedding response contained an invalid-norm vector")
        normalized.append([value / norm for value in vector])
    return normalized


def _embed(texts: list[str], task_type: str, client=None) -> list[list[float]]:
    if not texts:
        return []
    try:
        active_client = client if client is not None else _create_client()
        response = active_client.models.embed_content(
            model=_MODEL_NAME,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=_DIMENSION,
            ),
        )
    except EmbeddingError:
        raise
    except Exception as error:
        raise EmbeddingError("Embedding request failed") from error
    return _validate_and_normalize(response, len(texts))


def embed_history_documents(texts, *, client=None) -> list[list[float]]:
    """Embed recipe-history documents with Gemini's document task type."""
    return _embed(texts, "RETRIEVAL_DOCUMENT", client=client)


def embed_request_queries(texts, *, client=None) -> list[list[float]]:
    """Embed retrieval queries with Gemini's query task type."""
    return _embed(texts, "RETRIEVAL_QUERY", client=client)
