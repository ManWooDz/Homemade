import copy
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from embeddings import EmbeddingError, build_request_query
from eval import production_query_embedding_check as check


FIXTURE_PATH = Path(__file__).parents[1] / "eval" / "production_query_embedding_cases.json"
BACKEND_PATH = Path(__file__).parents[1]


class RecordingEmbedder:
    def __init__(self, vectors=None, error=None):
        self.vectors = vectors
        self.error = error
        self.calls = []

    def __call__(self, texts):
        self.calls.append(list(texts))
        if self.error is not None:
            raise self.error
        return self.vectors


def _load_raw_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _passing_vectors(fixture):
    documents = fixture["documents"]
    document_index = {item["id"]: index for index, item in enumerate(documents)}
    document_vectors = []
    for index in range(len(documents)):
        vector = [0.0] * len(documents)
        vector[index] = 1.0
        document_vectors.append(vector)

    query_vectors = []
    for query_index, query in enumerate(fixture["queries"]):
        intended_index = document_index[query["intended_id"]]
        unrelated_index = document_index[query["unrelated_id"]]
        competitor_index = next(
            index
            for index in range(len(documents))
            if index not in {intended_index, unrelated_index}
        )
        vector = [0.0] * len(documents)
        vector[competitor_index] = 0.7
        if query_index == len(fixture["queries"]) - 1:
            vector[intended_index] = 0.5
            vector[unrelated_index] = 0.55
        else:
            vector[intended_index] = 0.6
            vector[unrelated_index] = 0.4
        norm = math.sqrt(sum(value * value for value in vector))
        query_vectors.append([value / norm for value in vector])
    return document_vectors, query_vectors


class ProductionQueryFixtureTests(unittest.TestCase):
    def test_frozen_fixture_keeps_wp1_corpus_and_query_taxonomy(self):
        fixture = _load_raw_fixture()

        self.assertEqual(fixture["version"], 1)
        self.assertEqual(
            [
                (
                    item["id"],
                    item["recipe_name"],
                    item["adjusted_ingredients"],
                    item["diet_tags"],
                )
                for item in fixture["documents"]
            ],
            [
                ("A1", "Stir-fried Minced Pork with Holy Basil", ["หมูสับ", "ใบกะเพรา", "กระเทียม", "พริก"], ["Spicy", "Stir Fry", "High Protein"]),
                ("A2", "Stir-fried Chicken with Holy Basil", ["ไก่สับ", "ใบกะเพรา", "กระเทียม", "พริก"], ["Spicy", "Stir Fry", "High Protein"]),
                ("B1", "Tom Yum Shrimp Soup", ["กุ้ง", "ตะไคร้", "ข่า", "ใบมะกรูด", "มะนาว"], ["Spicy", "Sour", "Soup"]),
                ("B2", "Tom Kha Chicken", ["ไก่", "กะทิ", "ข่า", "ตะไคร้"], ["Creamy", "Soup", "Thai"]),
                ("C1", "Green Curry with Chicken", ["ไก่", "กะทิ", "พริกแกงเขียวหวาน", "มะเขือเปราะ", "ใบโหระพา"], ["Spicy", "Curry", "Thai"]),
                ("C2", "Red Curry with Pork", ["หมู", "กะทิ", "พริกแกงเผ็ด", "ใบมะกรูด"], ["Spicy", "Curry", "Thai"]),
                ("D1", "Green Papaya Salad", ["มะละกอ", "มะนาว", "พริก", "ถั่วลิสง", "น้ำปลา"], ["Spicy", "Sour", "Salad"]),
                ("E1", "Mango Sticky Rice", ["มะม่วง", "ข้าวเหนียว", "กะทิ", "น้ำตาล"], ["Sweet", "Dessert", "Thai"]),
                ("E2", "Taro in Coconut Milk Dessert", ["เผือก", "กะทิ", "น้ำตาล"], ["Sweet", "Dessert", "Thai"]),
                ("F1", "Thai Fried Rice with Egg", ["ข้าวสวย", "ไข่", "ต้นหอม", "ซีอิ๊ว"], ["Quick Meal", "Stir Fry", "Thai"]),
            ],
        )
        self.assertEqual(
            Counter(item["category"] for item in fixture["queries"]),
            {
                "base_english_title_english_ingredients_thai_taste": 4,
                "base_english_title_mixed_ingredients": 2,
                "custom_thai_ingredients_thai_taste": 2,
                "custom_english_ingredients_thai_taste": 1,
                "unspecified_taste_sentinel": 1,
            },
        )
        query_ids = [item["id"] for item in fixture["queries"]]
        document_ids = {item["id"] for item in fixture["documents"]}
        self.assertEqual(len(query_ids), len(set(query_ids)))
        for query in fixture["queries"]:
            self.assertIn(query["intended_id"], document_ids)
            self.assertIn(query["unrelated_id"], document_ids)
            self.assertNotEqual(query["intended_id"], query["unrelated_id"])

        sentinel = next(item for item in fixture["queries"] if item["id"] == "Q-B2")
        self.assertEqual(
            build_request_query(
                sentinel["recipe_name"],
                sentinel["ingredient_names"],
                sentinel["taste"],
            ),
            "Tom Kha Chicken | วัตถุดิบ: chicken, coconut milk, galangal, lemongrass",
        )


class ProductionQueryEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = check.load_fixture(FIXTURE_PATH)
        document_vectors, query_vectors = _passing_vectors(self.fixture)
        self.document_embedder = RecordingEmbedder(document_vectors)
        self.query_embedder = RecordingEmbedder(query_vectors)

    def test_evaluator_uses_production_builders_and_exactly_two_ten_item_batches(self):
        with mock.patch.object(
            check,
            "build_history_document",
            wraps=check.build_history_document,
        ) as history_builder, mock.patch.object(
            check,
            "build_request_query",
            wraps=check.build_request_query,
        ) as request_builder:
            result = check.evaluate_fixture(
                self.fixture,
                document_embedder=self.document_embedder,
                query_embedder=self.query_embedder,
            )

        self.assertEqual(history_builder.call_count, 10)
        self.assertEqual(request_builder.call_count, 10)
        self.assertEqual(len(self.document_embedder.calls), 1)
        self.assertEqual(len(self.document_embedder.calls[0]), 10)
        self.assertEqual(len(self.query_embedder.calls), 1)
        self.assertEqual(len(self.query_embedder.calls[0]), 10)
        self.assertEqual(
            result["accounting"],
            {
                "calls_attempted": 2,
                "successful_calls": 2,
                "embedded_inputs_attempted": 20,
                "successful_embedded_inputs": 20,
            },
        )

    def test_evaluator_calculates_raw_cosines_ranks_and_report_only_top1(self):
        result = check.evaluate_fixture(
            self.fixture,
            document_embedder=self.document_embedder,
            query_embedder=self.query_embedder,
        )

        first = result["queries"][0]
        self.assertAlmostEqual(first["intended_cosine"], 0.5970223141259935)
        self.assertAlmostEqual(first["unrelated_cosine"], 0.3980148760839957)
        self.assertEqual(first["intended_rank"], 2)
        self.assertEqual(result["summary"]["intended_top3"], 10)
        self.assertEqual(result["summary"]["intended_over_unrelated"], 9)
        self.assertGreaterEqual(result["summary"]["mean_margin"], 0.05)
        self.assertEqual(result["summary"]["intended_top1"], 0)
        self.assertEqual(result["decision"], "PASS")

    def test_gate_enforces_top3_pairwise_and_mean_margin_but_not_top1(self):
        passing_rows = [
            {"intended_rank": 2, "margin": 0.06}
            for _ in range(9)
        ] + [{"intended_rank": 3, "margin": 0.0}]

        self.assertEqual(check.evaluate_criteria(passing_rows)["decision"], "PASS")

        only_nine_top3 = copy.deepcopy(passing_rows)
        only_nine_top3[0]["intended_rank"] = 4
        self.assertEqual(check.evaluate_criteria(only_nine_top3)["decision"], "FAIL")

        only_eight_pairwise = [
            {"intended_rank": 2, "margin": 0.07}
            for _ in range(8)
        ] + [
            {"intended_rank": 3, "margin": 0.0},
            {"intended_rank": 3, "margin": 0.0},
        ]
        pairwise_summary = check.evaluate_criteria(only_eight_pairwise)
        self.assertEqual(pairwise_summary["intended_top3"], 10)
        self.assertEqual(pairwise_summary["intended_over_unrelated"], 8)
        self.assertGreaterEqual(pairwise_summary["mean_margin"], 0.05)
        self.assertEqual(pairwise_summary["decision"], "FAIL")

        low_mean_margin = [
            {"intended_rank": 1, "margin": 0.049}
            for _ in range(10)
        ]
        self.assertEqual(check.evaluate_criteria(low_mean_margin)["decision"], "FAIL")

    def test_malformed_fixture_is_rejected_before_embedding(self):
        malformed_cases = []

        wrong_version = copy.deepcopy(self.fixture)
        wrong_version["version"] = 2
        malformed_cases.append(wrong_version)

        nine_documents = copy.deepcopy(self.fixture)
        nine_documents["documents"].pop()
        malformed_cases.append(nine_documents)

        duplicate_query_id = copy.deepcopy(self.fixture)
        duplicate_query_id["queries"][1]["id"] = duplicate_query_id["queries"][0]["id"]
        malformed_cases.append(duplicate_query_id)

        unknown_mapping = copy.deepcopy(self.fixture)
        unknown_mapping["queries"][0]["intended_id"] = "UNKNOWN"
        malformed_cases.append(unknown_mapping)

        for malformed in malformed_cases:
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    check.evaluate_fixture(
                        malformed,
                        document_embedder=self.document_embedder,
                        query_embedder=self.query_embedder,
                    )

        self.assertEqual(self.document_embedder.calls, [])
        self.assertEqual(self.query_embedder.calls, [])


class ProductionQueryCliTests(unittest.TestCase):
    def setUp(self):
        self.fixture = check.load_fixture(FIXTURE_PATH)
        document_vectors, query_vectors = _passing_vectors(self.fixture)
        self.document_embedder = RecordingEmbedder(document_vectors)
        self.query_embedder = RecordingEmbedder(query_vectors)

    def _run(self, arguments, report_path):
        return check.main(
            arguments,
            document_embedder=self.document_embedder,
            query_embedder=self.query_embedder,
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            report_path=report_path,
        )

    def test_cli_requires_exact_confirm_inputs_twenty_before_embedding(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.md"
            self.assertEqual(self._run([], report_path), 2)
            self.assertEqual(self._run(["--confirm-inputs", "19"], report_path), 2)
            self.assertFalse(report_path.exists())

        self.assertEqual(self.document_embedder.calls, [])
        self.assertEqual(self.query_embedder.calls, [])

    def test_direct_script_invocation_reaches_guard_without_api_or_import_error(self):
        environment = os.environ.copy()
        environment["GEMINI_API_KEY"] = ""

        completed = subprocess.run(
            [sys.executable, "eval/production_query_embedding_check.py"],
            cwd=BACKEND_PATH,
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "Refusing preflight: pass --confirm-inputs 20",
            completed.stderr,
        )
        self.assertNotIn("ModuleNotFoundError", completed.stderr)

    def test_cli_report_contains_fixture_raw_results_criteria_and_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.md"
            exit_code = self._run(["--confirm-inputs", "20"], report_path)
            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("Decision: PASS", report)
        self.assertIn('"fixture_version": 1', report)
        self.assertIn('"id": "Q-A1"', report)
        self.assertIn('"intended_cosine":', report)
        self.assertIn('"intended_rank": 2', report)
        self.assertIn('"embedded_inputs_attempted": 20', report)
        self.assertIn('"successful_calls": 2', report)
        self.assertIn('"minimum_intended_top3": 10', report)
        self.assertIn('"minimum_intended_over_unrelated": 9', report)
        self.assertIn('"minimum_mean_margin": 0.05', report)

    def test_api_failure_writes_no_decision_without_retry_or_secret(self):
        self.query_embedder = RecordingEmbedder(
            error=EmbeddingError("secret-key-value")
        )
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.md"
            exit_code = self._run(["--confirm-inputs", "20"], report_path)
            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 1)
        self.assertEqual(len(self.document_embedder.calls), 1)
        self.assertEqual(len(self.query_embedder.calls), 1)
        self.assertIn("Decision: NO DECISION", report)
        self.assertIn('"calls_attempted": 2', report)
        self.assertIn('"successful_calls": 1', report)
        self.assertIn('"embedded_inputs_attempted": 20', report)
        self.assertIn('"successful_embedded_inputs": 10', report)
        self.assertNotIn("secret-key-value", report)


if __name__ == "__main__":
    unittest.main()
