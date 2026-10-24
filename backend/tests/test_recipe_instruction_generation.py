"""Exercise the actual provider boundary and existing correction loop offline."""
import json
import ast
from pathlib import Path
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import main
from eval.metrics import check_instruction_consistency, summarize_run
from eval.run_benchmark import run_case
from recipe_instructions import FORMAT_ERROR, generation_schema, normalize_generated_recipe
from test_recipe_instructions import SELECTED, wire_recipe
from test_generate_handler import _STUB_NUTRITION_RESULT


class InstructionGenerationTests(unittest.TestCase):
    def test_time_only_failures_do_not_retry_an_otherwise_valid_recipe(self):
        for time in (None, {"min_minutes": -1, "max_minutes": 10}, "invalid"):
            with self.subTest(time=time):
                recipe, attempts, calls = self.run_responses([{**wire_recipe(), "estimated_total_time": time}])
                self.assertIsNone(recipe["estimated_total_time"])
                self.assertEqual([attempt["status"] for attempt in attempts], ["pass"])
                self.assertEqual(len(calls), 1)
        raw = wire_recipe()
        raw.pop("estimated_total_time")
        recipe, attempts, calls = self.run_responses([raw])
        self.assertIsNone(recipe["estimated_total_time"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(attempts[0]["status"], "pass")

    def run_responses(self, responses, prefs=None, selected=SELECTED):
        captured = []

        def generate_content(**kwargs):
            captured.append(kwargs)
            response = responses[min(len(captured) - 1, len(responses) - 1)]
            if isinstance(response, Exception):
                raise response
            return SimpleNamespace(text=response if isinstance(response, str) else json.dumps(response, ensure_ascii=False))

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch("main.client", client):
            recipe, attempts = main.run_generation_with_validation(main.call_agentic_llm, selected, selected, prefs or {}, {}, {})
        return recipe, attempts, captured

    def test_salad_passes_actual_boundary_and_uses_dynamic_schema(self):
        recipe, attempts, calls = self.run_responses([wire_recipe()])
        self.assertEqual([attempt["status"] for attempt in attempts], ["pass"])
        self.assertIn("คลุกเคล้า", recipe["instructions"][0])
        self.assertEqual(calls[0]["config"].response_json_schema, generation_schema(SELECTED))
        self.assertIn('"estimated_total_time": {"min_minutes": 15, "max_minutes": 20}', calls[0]["contents"])
        self.assertIn("รวมเวลาเตรียม ปรุง และรอ", calls[0]["contents"])
        self.assertIn("ถ้าประเมินไม่ได้ให้ส่ง null", calls[0]["contents"])

    def test_bad_json_unknown_food_and_free_text_get_existing_feedback_retry(self):
        for invalid in ("not JSON", {**wire_recipe(), "instructions": ["ใส่กุ้งกับทุเรียน"]},
                        {**wire_recipe(), "instructions": [{"action": "mix", "ingredients": ["i999"], "excluded": []}]}):
            with self.subTest(invalid=invalid):
                recipe, attempts, calls = self.run_responses([invalid, wire_recipe()])
                self.assertIsNotNone(recipe)
                self.assertEqual([attempt["status"] for attempt in attempts], ["fail", "pass"])
                self.assertIn(attempts[0]["reason"], calls[1]["contents"])

    def test_format_failure_exhausts_three_attempts_and_provider_error_stops(self):
        recipe, attempts, calls = self.run_responses([{}])
        self.assertIsNone(recipe)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(attempt["status"] == "fail" for attempt in attempts))
        recipe, attempts, calls = self.run_responses([RuntimeError("provider unavailable")])
        self.assertIn("error", recipe)
        self.assertEqual(len(calls), 1)

    def test_declared_allergen_is_still_rejected_but_exclusion_is_allowed(self):
        raw = wire_recipe()
        selected = SELECTED + ["shrimp"]
        raw["adjusted_ingredients"].append("กุ้ง 100 กรัม")
        raw["instructions"][0]["ingredients"].append("i3")
        recipe, attempts, _ = self.run_responses([raw], {"allergies": "แพ้กุ้ง"}, selected)
        self.assertIsNone(recipe)
        self.assertTrue(attempts[0]["reason"].startswith("Allergy violation:"))
        raw = wire_recipe()
        raw["instructions"][0]["excluded"] = ["i3"]
        recipe, attempts, _ = self.run_responses([raw], {"allergies": "แพ้กุ้ง"}, selected)
        self.assertIsNotNone(recipe)

    def test_catalog_names_and_reviewed_aliases_do_not_need_word_scanning(self):
        from recipe_checks import CATALOG_ALIASES, check_ingredients, check_logic
        for canonical, aliases in CATALOG_ALIASES.items():
            for name in (canonical, *aliases):
                with self.subTest(canonical=canonical, name=name):
                    raw = wire_recipe()
                    raw["recipe_name"] = "Prepared Food"
                    raw["adjusted_ingredients"] = [name + " 100 กรัม"]
                    raw["instructions"] = [{"action": "cut", "ingredients": ["i1"], "excluded": []}]
                    recipe = normalize_generated_recipe(raw, [canonical])
                    self.assertTrue(check_logic(recipe)[0])
                    self.assertTrue(check_ingredients(recipe, [canonical])[0])

    def test_all_seeded_menu_inventories_roundtrip_without_importing_seed(self):
        from recipe_checks import check_ingredients, check_logic
        source = Path(__file__).resolve().parents[1] / "database" / "seed_postgres.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        menus = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == "MOCK_RECIPES" for target in node.targets))
        self.assertEqual(len(menus), 9)
        for menu in menus:
            with self.subTest(menu=menu["name"]):
                selected = menu["ingredients"]
                raw = wire_recipe()
                raw["adjusted_ingredients"] = [f"{item['name']} {item['quantity_g']} กรัม" for item in menu["ingredient_quantities"]]
                raw["instructions"] = [{"action": "mix", "ingredients": [f"i{index}" for index in range(1, len(selected) + 1)], "excluded": []}]
                recipe = normalize_generated_recipe(raw, selected)
                self.assertTrue(check_logic(recipe)[0])
                self.assertTrue(check_ingredients(recipe, selected)[0])

    def test_metrics_separate_errors_legacy_prose_and_structured_consistency(self):
        case = {"case_id": "synthetic", "ingredients": [{"name": name} for name in SELECTED], "user_prefs": {}, "base_recipe": {}}
        results = []
        for response, status in (({"error": "provider"}, "provider_error"), ({FORMAT_ERROR: "format"}, "format_error")):
            generator = SimpleNamespace(generate=lambda *args, response=response: response)
            result = run_case(generator, case)
            self.assertEqual(result["generation_status"], status)
            self.assertIsNone(result["hallucinated"])
            results.append(result)
        recipe = normalize_generated_recipe(wire_recipe(), SELECTED)
        self.assertEqual(check_instruction_consistency(recipe), "valid")
        legacy = deepcopy(recipe)
        legacy.pop("_instruction_plan")
        legacy["instructions"] = ["ใส่ทุเรียน"]
        self.assertEqual(check_instruction_consistency(legacy), "unknown")
        recipe["instructions"][0] += " ใส่ทุเรียน"
        self.assertEqual(check_instruction_consistency(recipe), "invalid")
        summary = summarize_run(results)
        self.assertEqual(summary["generator_error_count"], 1)
        self.assertEqual(summary["format_error_count"], 1)
        self.assertEqual(summary["hallucination_evaluated_n"], 0)
        self.assertIsNone(summary["hallucination_rate"])


class InstructionPublicBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_history_and_nutrition_receive_strings_without_private_plan(self):
        recipe = normalize_generated_recipe(wire_recipe(), SELECTED)
        original = deepcopy(recipe)
        request = main.GenerateRecipeTextRequest(recipe={"name": "Fresh Power Salad"}, ingredients=SELECTED, preferences={})
        with patch("main.call_agentic_llm", return_value=recipe), \
             patch("main.get_personalization_for_request", new=AsyncMock(return_value=None)), \
             patch("main.compute_recipe_nutrition", return_value=_STUB_NUTRITION_RESULT) as compute, \
             patch("main.save_generate_history", return_value=None) as history:
            response = await main.generate_recipe_text(request, current_user=SimpleNamespace(id=7), db=MagicMock())
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["estimated_total_time"], {"min_minutes": 5, "max_minutes": 10})
        self.assertEqual(history.call_args.args[3]["estimated_total_time"], response["data"]["estimated_total_time"])
        self.assertNotIn("_instruction_plan", response["data"])
        self.assertNotIn("_instruction_plan", history.call_args.args[3])
        self.assertEqual(compute.call_args.kwargs["instructions"], recipe["instructions"])
        self.assertEqual(recipe, original)
