"""One-shot production-query embedding preflight with an offline evaluator."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Callable

from embeddings import (
    EmbeddingError,
    build_history_document,
    build_request_query,
    embed_history_documents,
    embed_request_queries,
)


_FIXTURE_PATH = Path(__file__).with_name("production_query_embedding_cases.json")
_REPORT_PATH = Path(__file__).resolve().parents[2] / "docs" / "handoff" / "embedding-production-query-check-result.md"
_EXPECTED_DOCUMENT_IDS = {"A1", "A2", "B1", "B2", "C1", "C2", "D1", "E1", "E2", "F1"}
_EXPECTED_QUERY_MAPPINGS = {
    "Q-A1": ("A1", "E1", "base_english_title_english_ingredients_thai_taste"),
    "Q-A2": ("A2", "D1", "base_english_title_english_ingredients_thai_taste"),
    "Q-B1": ("B1", "E2", "base_english_title_english_ingredients_thai_taste"),
    "Q-C1": ("C1", "F1", "base_english_title_english_ingredients_thai_taste"),
    "Q-C2": ("C2", "E1", "base_english_title_mixed_ingredients"),
    "Q-E1": ("E1", "B1", "base_english_title_mixed_ingredients"),
    "Q-D1": ("D1", "B2", "custom_thai_ingredients_thai_taste"),
    "Q-E2": ("E2", "A1", "custom_thai_ingredients_thai_taste"),
    "Q-F1": ("F1", "C1", "custom_english_ingredients_thai_taste"),
    "Q-B2": ("B2", "D1", "unspecified_taste_sentinel"),
}
_EXPECTED_CATEGORY_COUNTS = {
    "base_english_title_english_ingredients_thai_taste": 4,
    "base_english_title_mixed_ingredients": 2,
    "custom_thai_ingredients_thai_taste": 2,
    "custom_english_ingredients_thai_taste": 1,
    "unspecified_taste_sentinel": 1,
}
_CRITERIA = {
    "minimum_intended_top3": 10,
    "minimum_intended_over_unrelated": 9,
    "minimum_mean_margin": 0.05,
    "top1_is_gate": False,
}


def _require_string(item: dict, field: str) -> None:
    if not isinstance(item.get(field), str) or not item[field].strip():
        raise ValueError(f"Fixture field {field!r} must be a non-empty string")


def _require_string_list(item: dict, field: str) -> None:
    values = item.get(field)
    if not isinstance(values, list) or not values or any(
        not isinstance(value, str) or not value.strip() for value in values
    ):
        raise ValueError(f"Fixture field {field!r} must be a non-empty string list")


def validate_fixture(fixture: dict) -> dict:
    """Reject any fixture that differs from the frozen 10+10 preflight shape."""
    if not isinstance(fixture, dict) or fixture.get("version") != 1:
        raise ValueError("Fixture version must be 1")
    documents = fixture.get("documents")
    queries = fixture.get("queries")
    if not isinstance(documents, list) or len(documents) != 10:
        raise ValueError("Fixture must contain exactly 10 documents")
    if not isinstance(queries, list) or len(queries) != 10:
        raise ValueError("Fixture must contain exactly 10 queries")

    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("Every document must be an object")
        _require_string(document, "id")
        _require_string(document, "recipe_name")
        _require_string_list(document, "adjusted_ingredients")
        _require_string_list(document, "diet_tags")
    document_ids = [document["id"] for document in documents]
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("Document ids must be unique")
    if set(document_ids) != _EXPECTED_DOCUMENT_IDS:
        raise ValueError("Fixture must use the frozen WP1 document ids")

    for query in queries:
        if not isinstance(query, dict):
            raise ValueError("Every query must be an object")
        for field in (
            "id",
            "recipe_name",
            "taste",
            "intended_id",
            "unrelated_id",
            "category",
        ):
            _require_string(query, field)
        _require_string_list(query, "ingredient_names")
    query_ids = [query["id"] for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Query ids must be unique")
    if set(query_ids) != set(_EXPECTED_QUERY_MAPPINGS):
        raise ValueError("Fixture must use the frozen query ids")
    if Counter(query["category"] for query in queries) != _EXPECTED_CATEGORY_COUNTS:
        raise ValueError("Fixture query categories do not match the frozen counts")
    for query in queries:
        expected = _EXPECTED_QUERY_MAPPINGS[query["id"]]
        actual = (query["intended_id"], query["unrelated_id"], query["category"])
        if actual != expected:
            raise ValueError(f"Fixture mapping changed for {query['id']}")
        if query["intended_id"] not in _EXPECTED_DOCUMENT_IDS:
            raise ValueError("Intended document id is unknown")
        if query["unrelated_id"] not in _EXPECTED_DOCUMENT_IDS:
            raise ValueError("Unrelated document id is unknown")
        if query["intended_id"] == query["unrelated_id"]:
            raise ValueError("Intended and unrelated document ids must differ")
    return fixture


def load_fixture(path: str | Path = _FIXTURE_PATH) -> dict:
    with Path(path).open("r", encoding="utf-8") as fixture_file:
        fixture = json.load(fixture_file)
    return validate_fixture(fixture)


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("Embedding vectors must have equal non-zero dimensions")
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in left + right):
        raise ValueError("Embedding vectors must contain finite numbers")
    return sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))


def _call_embedder(
    embedder: Callable[[list[str]], list[list[float]]],
    texts: list[str],
    accounting: dict,
) -> list[list[float]]:
    accounting["calls_attempted"] += 1
    accounting["embedded_inputs_attempted"] += len(texts)
    vectors = embedder(texts)
    if len(vectors) != len(texts):
        raise EmbeddingError("Embedding response count did not match input count")
    accounting["successful_calls"] += 1
    accounting["successful_embedded_inputs"] += len(texts)
    return vectors


def evaluate_criteria(rows: list[dict]) -> dict:
    """Apply the frozen quality gates; top-1 remains report-only."""
    if len(rows) != 10:
        raise ValueError("Criteria require exactly 10 query rows")
    intended_top1 = sum(row["intended_rank"] == 1 for row in rows)
    intended_top3 = sum(row["intended_rank"] <= 3 for row in rows)
    intended_over_unrelated = sum(row["margin"] > 0.0 for row in rows)
    mean_margin = sum(row["margin"] for row in rows) / len(rows)
    passed = (
        intended_top3 >= _CRITERIA["minimum_intended_top3"]
        and intended_over_unrelated >= _CRITERIA["minimum_intended_over_unrelated"]
        and mean_margin >= _CRITERIA["minimum_mean_margin"]
    )
    return {
        "intended_top1": intended_top1,
        "intended_top3": intended_top3,
        "intended_over_unrelated": intended_over_unrelated,
        "mean_margin": mean_margin,
        "decision": "PASS" if passed else "FAIL",
    }


def evaluate_fixture(
    fixture: dict,
    *,
    document_embedder: Callable[[list[str]], list[list[float]]] | None = None,
    query_embedder: Callable[[list[str]], list[list[float]]] | None = None,
) -> dict:
    """Build production text, embed it in two batches, and evaluate retrieval."""
    validate_fixture(fixture)
    active_document_embedder = document_embedder or embed_history_documents
    active_query_embedder = query_embedder or embed_request_queries
    documents = [
        {
            "id": document["id"],
            "text": build_history_document(
                document["recipe_name"],
                document["adjusted_ingredients"],
                document["diet_tags"],
            ),
        }
        for document in fixture["documents"]
    ]
    queries = [
        {
            "id": query["id"],
            "text": build_request_query(
                query["recipe_name"],
                query["ingredient_names"],
                query["taste"],
            ),
            "category": query["category"],
            "intended_id": query["intended_id"],
            "unrelated_id": query["unrelated_id"],
        }
        for query in fixture["queries"]
    ]
    accounting = {
        "calls_attempted": 0,
        "successful_calls": 0,
        "embedded_inputs_attempted": 0,
        "successful_embedded_inputs": 0,
    }
    base_result = {
        "fixture_version": fixture["version"],
        "fixture": fixture,
        "criteria": dict(_CRITERIA),
        "accounting": accounting,
    }
    try:
        document_vectors = _call_embedder(
            active_document_embedder,
            [document["text"] for document in documents],
            accounting,
        )
        query_vectors = _call_embedder(
            active_query_embedder,
            [query["text"] for query in queries],
            accounting,
        )
    except EmbeddingError:
        return {
            **base_result,
            "documents": documents,
            "queries": [],
            "summary": None,
            "decision": "NO DECISION",
        }

    document_vector_by_id = {
        document["id"]: vector
        for document, vector in zip(documents, document_vectors, strict=True)
    }
    result_rows = []
    for query, query_vector in zip(queries, query_vectors, strict=True):
        scores = {
            document["id"]: _cosine(query_vector, document_vector_by_id[document["id"]])
            for document in documents
        }
        ranking = sorted(scores, key=lambda document_id: (-scores[document_id], document_id))
        intended_cosine = scores[query["intended_id"]]
        unrelated_cosine = scores[query["unrelated_id"]]
        result_rows.append(
            {
                **query,
                "intended_cosine": intended_cosine,
                "unrelated_cosine": unrelated_cosine,
                "margin": intended_cosine - unrelated_cosine,
                "intended_rank": ranking.index(query["intended_id"]) + 1,
                "top1_id": ranking[0],
                "rankings": [
                    {
                        "rank": rank,
                        "document_id": document_id,
                        "cosine": scores[document_id],
                    }
                    for rank, document_id in enumerate(ranking, start=1)
                ],
            }
        )
    summary = evaluate_criteria(result_rows)
    return {
        **base_result,
        "documents": documents,
        "queries": result_rows,
        "summary": summary,
        "decision": summary["decision"],
    }


def render_report(result: dict) -> str:
    """Render one complete, auditable report without exception or credential text."""
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    return (
        "# Production-query embedding preflight\n\n"
        f"Decision: {result['decision']}\n\n"
        "The JSON below records the frozen fixture, raw cosines and ranks, "
        "call/input accounting, criteria, and conclusion.\n\n"
        "```json\n"
        f"{payload}\n"
        "```\n"
    )


def main(
    argv: list[str] | None = None,
    *,
    document_embedder: Callable[[list[str]], list[list[float]]] | None = None,
    query_embedder: Callable[[list[str]], list[list[float]]] | None = None,
    stdout=None,
    stderr=None,
    report_path: str | Path | None = None,
) -> int:
    """Run the guarded one-shot CLI. This function never retries an embedder."""
    active_stdout = stdout or sys.stdout
    active_stderr = stderr or sys.stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-inputs", type=int)
    parser.add_argument("--fixture", type=Path, default=_FIXTURE_PATH)
    arguments = parser.parse_args(argv)
    if arguments.confirm_inputs != 20:
        print("Refusing preflight: pass --confirm-inputs 20", file=active_stderr)
        return 2
    try:
        fixture = load_fixture(arguments.fixture)
    except (OSError, json.JSONDecodeError, ValueError):
        print("Refusing preflight: fixture is invalid", file=active_stderr)
        return 2

    result = evaluate_fixture(
        fixture,
        document_embedder=document_embedder,
        query_embedder=query_embedder,
    )
    destination = Path(report_path) if report_path is not None else _REPORT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_report(result), encoding="utf-8")
    print(f"{result['decision']}: report written to {destination}", file=active_stdout)
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
