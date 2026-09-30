# backend/tests/test_allergen_kg_endpoint.py
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

from allergen_kg.fixtures import add_edges, make_memory_db
from allergen_kg.resolve import ResolvedAllergen, TermInfo
from main import (
    GenerateRecipeTextRequest,
    _LLM_FORBIDDEN_KEY as LLM_FORBIDDEN_KEY,
    _LLM_FORBIDDEN_SUFFIX as LLM_FORBIDDEN_SUFFIX,
    build_llm_prefs,
    generate_recipe_text,
    resolve_blocks_for_request,
    run_generation_with_validation,
)
from nutrition.calculator import NutritionResult

_STUB_NUTRITION = NutritionResult(
    nutrition={"basis": "per_serving", "calories": 1.0, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
    partially_estimated=False,
    partially_estimated_reasons=[],
)

SAFE = {
    "recipe_name": "Test Dish",
    "servings": 2,
    "adjusted_ingredients": ["หมูสับ 200 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
    "diet_tags": ["Thai"],
    "nutrition": {"basis": "per_serving", "calories": 400, "protein_g": 20, "carbs_g": 10, "fat_g": 20},
    "instructions": ["1. ตั้งกระทะใส่น้ำมันแล้วผัดหมู"],
    "safety_warning": "ระวังความร้อน",
}


def with_ingredient(name):
    r = deepcopy(SAFE)
    r["adjusted_ingredients"] = [f"{name} 1 ช้อนโต๊ะ", "น้ำมัน 1 ช้อนโต๊ะ"]
    return r


def request(allergy):
    return GenerateRecipeTextRequest(
        recipe={"name": "Custom"},
        ingredients=[{"id": 1, "name": "หมูสับ"}],
        preferences={"allergy": allergy, "taste": "", "equipment": "", "extra": ""},
    )


class ResolveForRequestTests(unittest.TestCase):
    def test_no_allergy_never_opens_a_session(self):
        with patch("main.SessionLocal") as session_factory:
            self.assertEqual(resolve_blocks_for_request({"allergy": ""}), {})
        session_factory.assert_not_called()

    def test_database_url_unset_gives_floor_only(self):
        with patch("main.SessionLocal", None):
            resolved = resolve_blocks_for_request({"allergy": "แพ้กุ้ง"})
        self.assertEqual(resolved["shrimp"].graph_status, "unavailable")
        self.assertIn("กุ้ง", resolved["shrimp"].terms)

    def test_session_failure_gives_floor_only(self):
        def broken():
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        with patch("main.SessionLocal", broken):
            resolved = resolve_blocks_for_request({"allergy": "แพ้กุ้ง"})
        self.assertEqual(resolved["shrimp"].graph_status, "unavailable")

    def test_uses_seeded_graph(self):
        db = make_memory_db()
        add_edges(db, [("alpha", "allergen:shrimp"), ("beta", "alpha")])
        with patch("main.SessionLocal", lambda: db):
            resolved = resolve_blocks_for_request({"allergy": "แพ้กุ้ง"})
        self.assertEqual(resolved["shrimp"].graph_status, "ok")
        self.assertIn("beta", resolved["shrimp"].terms)


class ForbiddenWordingScopeTests(unittest.TestCase):
    """The wording must describe what the checker really does: it scans only adjusted_ingredients."""

    def test_wording_scopes_the_ban_to_the_ingredient_list(self):
        self.assertIn("adjusted_ingredients", LLM_FORBIDDEN_KEY)
        self.assertIn("ไม่มี...", LLM_FORBIDDEN_KEY)  # rejected even inside a negation note
        self.assertIn("adjusted_ingredients", LLM_FORBIDDEN_SUFFIX)

    def test_wording_does_not_forbid_steps_or_safety_warning(self):
        self.assertNotIn("ขั้นตอน หรือหมายเหตุใดๆ", LLM_FORBIDDEN_SUFFIX)
        self.assertIn("safety_warning", LLM_FORBIDDEN_SUFFIX)
        self.assertIn("instructions", LLM_FORBIDDEN_SUFFIX)
        self.assertIn("ได้ตามปกติ", LLM_FORBIDDEN_SUFFIX)

    def test_suffix_keeps_single_leading_separator(self):
        # eval/retry_convergence tests split the value on this separator to recover the term list
        self.assertTrue(LLM_FORBIDDEN_SUFFIX.startswith(" — "))
        self.assertEqual(LLM_FORBIDDEN_SUFFIX.count(" — "), 1)


def resolved_with(**terms_by_key):
    """{key: ResolvedAllergen} from {key: {term: matched_via}}; no DB involved."""
    return {
        key: ResolvedAllergen(
            terms={t: TermInfo(via, (t, "alpha") if via == "kg" else None) for t, via in terms.items()},
            graph_status="ok",
        )
        for key, terms in terms_by_key.items()
    }


class BuildLlmPrefsTests(unittest.TestCase):
    def test_empty_or_none_blocks_return_prefs_unchanged(self):
        prefs = {"allergies": "กุ้ง", "taste": ""}
        for blocks in ({}, None):
            with self.subTest(blocks=blocks):
                self.assertIs(build_llm_prefs(prefs, blocks), prefs)

    def test_adds_forbidden_key_and_does_not_mutate_input(self):
        prefs = {"allergies": "กุ้ง", "taste": ""}
        snapshot = deepcopy(prefs)
        out = build_llm_prefs(prefs, resolved_with(shrimp={"กุ้ง": "floor"}))
        self.assertEqual(prefs, snapshot)
        self.assertIsNot(out, prefs)
        self.assertEqual(out[LLM_FORBIDDEN_KEY], "กุ้ง" + LLM_FORBIDDEN_SUFFIX)
        self.assertEqual({k: v for k, v in out.items() if k != LLM_FORBIDDEN_KEY}, snapshot)

    def test_terms_are_sorted_deduplicated_union_across_allergens(self):
        resolved = resolved_with(
            shrimp={"prawn": "floor", "กุ้ง": "floor", "shrimp": "floor"},
            shellfish={"crab": "floor", "prawn": "floor"},
        )
        out = build_llm_prefs({}, resolved)
        expected_terms = sorted({"prawn", "กุ้ง", "shrimp", "crab"})
        self.assertEqual(out[LLM_FORBIDDEN_KEY], ", ".join(expected_terms) + LLM_FORBIDDEN_SUFFIX)

    def test_includes_kg_chain_only_terms(self):
        resolved = resolved_with(shrimp={"กุ้ง": "floor", "น้ำพริกกุ้งเสียบ": "kg"})
        out = build_llm_prefs({}, resolved)
        self.assertIn("น้ำพริกกุ้งเสียบ", out[LLM_FORBIDDEN_KEY])
        self.assertEqual(resolved["shrimp"].terms["น้ำพริกกุ้งเสียบ"].matched_via, "kg")

    def test_does_not_depend_on_the_database(self):
        with patch("main.SessionLocal", side_effect=AssertionError("DB touched")):
            build_llm_prefs({}, resolved_with(shrimp={"กุ้ง": "floor"}))


class RunGenerationTests(unittest.TestCase):
    def test_returns_first_passing_recipe_and_logs_attempts(self):
        blocks = {}
        outputs = [with_ingredient("กุ้ง"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        final, log = run_generation_with_validation(
            fake, ["หมูสับ"], ["หมูสับ"], {"allergy": "แพ้กุ้ง"}, {"name": "x"}, blocks)
        self.assertEqual(final["recipe_name"], "Test Dish")
        self.assertEqual([e["status"] for e in log], ["fail", "pass"])
        self.assertEqual(feedbacks[0], None)
        self.assertTrue(feedbacks[1].startswith("Allergy violation:"))

    def test_exhaustion_returns_none(self):
        final, log = run_generation_with_validation(
            lambda *a, **k: with_ingredient("กุ้ง"), ["หมูสับ"], ["หมูสับ"],
            {"allergy": "แพ้กุ้ง"}, {"name": "x"}, {})
        self.assertIsNone(final)
        self.assertEqual(len(log), 3)

    def test_generator_gets_llm_prefs_while_validation_uses_user_prefs(self):
        seen = []

        def fake(ingredients, prefs, base_recipe, feedback=None):
            seen.append(prefs)
            return with_ingredient("กุ้ง")  # violates the allergy under user_prefs

        # The two prefs deliberately disagree: only user_prefs states an allergy. If
        # validation used llm_prefs it would accept the shrimp recipe; if the generator
        # got user_prefs it would not see the {"allergies": ""} object.
        user_prefs = {"allergies": "แพ้กุ้ง"}
        llm_prefs = {"allergies": ""}
        final, log = run_generation_with_validation(
            fake, ["หมูสับ"], ["หมูสับ"], user_prefs, {"name": "x"}, {}, llm_prefs=llm_prefs)
        self.assertIsNone(final)
        self.assertEqual(log[0]["status"], "fail")
        self.assertTrue(log[0]["reason"].startswith("Allergy violation:"), log)
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(p is llm_prefs for p in seen))
        self.assertEqual(seen[0], {"allergies": ""})

    def test_llm_prefs_default_is_user_prefs(self):
        seen = []

        def fake(ingredients, prefs, base_recipe, feedback=None):
            seen.append(prefs)
            return deepcopy(SAFE)

        user_prefs = {"allergy": ""}
        run_generation_with_validation(fake, ["หมูสับ"], ["หมูสับ"], user_prefs, {"name": "x"}, {})
        self.assertIs(seen[0], user_prefs)

    def test_generator_error_short_circuits(self):
        final, log = run_generation_with_validation(
            lambda *a, **k: {"error": "no key"}, [], [], {}, {"name": "x"}, {})
        self.assertEqual(final, {"error": "no key"})
        self.assertEqual(log, [{"attempt": 1, "status": "error", "reason": "no key"}])


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch("main.compute_recipe_nutrition", return_value=_STUB_NUTRITION)
        patcher.start()
        self.addCleanup(patcher.stop)

        history_patcher = patch("main.save_generate_history", return_value=101)
        history_patcher.start()
        self.addCleanup(history_patcher.stop)

    async def test_endpoint_feeds_kg_chain_reason_back_to_generator(self):
        db = make_memory_db()
        add_edges(db, [("alpha", "allergen:shrimp"), ("beta", "alpha")])
        outputs = [with_ingredient("beta"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        with patch("main.SessionLocal", lambda: db), patch("main.call_agentic_llm", side_effect=fake):
            response = await generate_recipe_text(request("แพ้กุ้ง"), current_user=SimpleNamespace(id=7), db=MagicMock())

        self.assertEqual(response["status"], "success")
        self.assertEqual(feedbacks[1], "Allergy violation: 'beta' → alpha → กุ้ง (ผู้ใช้แพ้ shrimp)")

    async def _assert_frontend_allergies_block(self, allergies):
        # Exactly what the frontend sends: plural "allergies" (comma-joined pill labels),
        # no "allergy" key at all. Before the fix the whole allergy check never fired.
        frontend_request = GenerateRecipeTextRequest(
            recipe={"name": "Custom"},
            ingredients=[{"id": 1, "name": "หมูสับ"}],
            preferences={"taste": "", "allergies": allergies, "equipment": "", "extra": ""},
        )
        db = make_memory_db()
        outputs = [with_ingredient("กุ้ง"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        with patch("main.SessionLocal", lambda: db), patch("main.call_agentic_llm", side_effect=fake):
            response = await generate_recipe_text(frontend_request, current_user=SimpleNamespace(id=7), db=MagicMock())

        self.assertEqual(response["status"], "success")
        self.assertEqual(len(feedbacks), 2)
        self.assertIsNone(feedbacks[0])
        self.assertTrue(feedbacks[1].startswith("Allergy violation:"), feedbacks[1])

    async def test_endpoint_blocks_with_create_recipe_pill_value(self):
        # CreateRecipe.jsx pill label, with the "แพ้" prefix.
        await self._assert_frontend_allergies_block("แพ้อาหารทะเล")

    async def test_endpoint_blocks_with_custom_cooking_page_pill_value(self):
        # CustomCookingPage.jsx pill label: NO "แพ้" prefix.
        await self._assert_frontend_allergies_block("กุ้ง/อาหารทะเล")

    async def _exhausted_response(self, ingredient_names, allergies, produce):
        req = GenerateRecipeTextRequest(
            recipe={"name": "Custom"},
            ingredients=[{"id": i, "name": n} for i, n in enumerate(ingredient_names, 1)],
            preferences={"taste": "", "allergies": allergies, "equipment": "", "extra": ""},
        )
        calls = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            calls.append(user_prefs)
            return produce()

        with patch("main.SessionLocal", lambda: make_memory_db()), \
                patch("main.call_agentic_llm", side_effect=fake):
            response = await generate_recipe_text(req, current_user=SimpleNamespace(id=7), db=MagicMock())
        return response, calls

    async def test_endpoint_generator_receives_forbidden_terms_and_original_allergies_text(self):
        response, calls = await self._exhausted_response(
            ["หมูสับ"], "แพ้กุ้ง", lambda: with_ingredient("กุ้ง"))
        self.assertEqual(response["status"], "error")
        self.assertEqual(len(calls), 3)
        for prefs in calls:
            self.assertIn(LLM_FORBIDDEN_KEY, prefs)
            self.assertIn("กุ้ง", prefs[LLM_FORBIDDEN_KEY])
            self.assertEqual(prefs["allergies"], "แพ้กุ้ง")

    async def test_allergy_exhaustion_names_the_users_violating_ingredients(self):
        response, _ = await self._exhausted_response(
            ["กุ้งสด", "หมูสับ", "กะปิ"], "แพ้กุ้ง", lambda: with_ingredient("กุ้ง"))
        self.assertEqual(response["status"], "error")
        message = response["message"]
        self.assertIn("อาการแพ้", message)
        self.assertIn("กุ้งสด", message)
        self.assertIn("กะปิ", message)
        self.assertNotIn("หมูสับ", message)
        self.assertIn("เอาวัตถุดิบเหล่านี้ออก", message)
        self.assertNotIn("Failed to generate", message)

    async def test_allergy_exhaustion_without_violating_user_ingredient(self):
        response, _ = await self._exhausted_response(
            ["หมูสับ", "ผักกาด"], "แพ้กุ้ง", lambda: with_ingredient("กุ้ง"))
        self.assertEqual(response["status"], "error")
        message = response["message"]
        self.assertIn("อาการแพ้", message)
        self.assertIn("หาสูตรที่ปลอดภัย", message)
        self.assertIn("ลองเปลี่ยนวัตถุดิบ", message)
        self.assertNotIn("เอาวัตถุดิบเหล่านี้ออก", message)
        self.assertNotIn("หมูสับ", message)

    async def test_non_allergy_failure_keeps_generic_message(self):
        def no_oil():
            r = deepcopy(SAFE)
            r["instructions"] = ["1. ผัดหมูให้สุก"]
            return r

        response, _ = await self._exhausted_response(["หมูสับ"], "แพ้กุ้ง", no_oil)
        self.assertEqual(response, {
            "status": "error",
            "message": "Failed to generate a valid recipe after multiple attempts due to validation failures.",
        })

    async def test_generator_error_path_unchanged(self):
        response, _ = await self._exhausted_response(
            ["หมูสับ"], "แพ้กุ้ง", lambda: {"error": "no key"})
        self.assertEqual(response, {"status": "error", "message": "no key"})

    async def test_endpoint_still_blocks_floor_when_db_unset(self):
        outputs = [with_ingredient("กุ้ง"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        with patch("main.SessionLocal", None), patch("main.call_agentic_llm", side_effect=fake):
            response = await generate_recipe_text(request("แพ้กุ้ง"), current_user=SimpleNamespace(id=7), db=MagicMock())

        self.assertEqual(response["status"], "success")
        self.assertEqual(feedbacks[1], "Allergy violation: พบ 'กุ้ง' ในสูตร (ผู้ใช้แพ้ shrimp)")


if __name__ == "__main__":
    unittest.main()
