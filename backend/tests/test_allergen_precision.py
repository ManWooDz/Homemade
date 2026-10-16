"""Regression checks for ingredient identity, scoped claims and real UI preferences."""
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from allergen_kg.fixtures import make_memory_db
from allergen_kg.floor import ALLERGEN_LABELS, ALLERGEN_MAP, parse_allergy_preferences
from allergen_kg.match import find_allergy_violation, format_violation_reason
from allergen_kg.resolve import floor_only, resolve_blocks_for_keys
from database.seed_allergen_graph import seed_allergen_graph
from main import (
    AllergyPreferencesRequest, GenerateRecipeTextRequest, build_allergy_exhaustion_message,
    check_allergy, generate_recipe_text, validate_allergy_preferences,
)
from personalization.context import _is_allergy_safe
from nutrition.calculator import NutritionResult


def recipe(*lines):
    return {"adjusted_ingredients": list(lines)}


class IngredientIdentityAndClaimsTests(unittest.TestCase):
    def setUp(self):
        self.db = make_memory_db()
        self.addCleanup(self.db.close)
        seed_allergen_graph(self.db)

    def violation(self, key, *lines, seeded=True):
        blocks = resolve_blocks_for_keys(self.db, [key]) if seeded else {key: floor_only(key, "unavailable")}
        return find_allergy_violation(recipe(*lines), {}, blocks)

    def test_false_positive_fixes_preserve_true_positive_controls(self):
        cases = [
            ("fish", "ปลาหมึกสด 200 กรัม", "ปลา 200 กรัม"),
            ("egg", "eggplant 200 g", "egg 2 ฟอง"),
            ("egg", "ไข่มดแดง 100 กรัม", "ไข่ไก่ 2 ฟอง"),
            ("milk", "ขนมจีน 100 กรัม", "นมวัว 100 มล."),
            ("milk", "แหนม 100 กรัม", "ครีม 100 มล."),
            ("gluten", "แป้งข้าวเจ้า 100 กรัม", "แป้งสาลี 100 กรัม"),
            ("gluten", "แป้งข้าวโพด 100 กรัม", "wheat flour 100 g"),
            ("sesame", "รายงานงานครัว", "งาดำ 1 ช้อนชา"),
            ("sesame", "เงาะ 2 ลูก", "sesame seeds 1 ช้อนชา"),
        ]
        for seeded in (False, True):
            for key, safe, unsafe in cases:
                with self.subTest(key=key, seeded=seeded):
                    self.assertIsNone(self.violation(key, safe, seeded=seeded))
                    self.assertIsNotNone(self.violation(key, unsafe, seeded=seeded))

    def test_unrelated_compound_never_exempts_another_constituent(self):
        for key, line in [
            ("fish", "ปลาหมึกผสมน้ำปลา"),
            ("egg", "eggplant with eggs"),
            ("gluten", "แป้งข้าวเจ้าผสมแป้งสาลี"),
            ("milk", "ขนมจีน (มีนมวัว)"),
            ("sesame", "เงาะโรยงาดำ"),
        ]:
            with self.subTest(key=key):
                self.assertIsNotNone(self.violation(key, line))

    def test_explicit_delimited_absence_claims_do_not_block_mentions_only(self):
        for line in [
            "กะทิ (ไม่มีนมวัว) 100 มล.",
            "กะทิ (สูตรไม่มีส่วนผสมของนม) 100 มล.",
            "กะทิ (ปราศจากนมวัว) 100 มล.",
            "กะทิ (without milk) 100 มล.",
            "กะทิ (milk-free) 100 มล.",
        ]:
            with self.subTest(line=line):
                self.assertIsNone(self.violation("milk", line))

    def test_claims_cannot_override_known_composition_or_positive_mentions(self):
        for key, lines in [
            ("shrimp", ["กะปิ (ไม่มีส่วนผสมของกุ้ง)"]),
            ("milk", ["นมวัว (ไม่มีนม)"]),
            ("milk", ["กะทิ (ไม่มีนมวัว)", "ครีม 1 ช้อนโต๊ะ"]),
            ("milk", ["กะทิ (ไม่มีนมวัว) + นมผง"]),
            ("milk", ["กะทิ (ไม่มีนมวัว แต่มีครีม)"]),
            ("gluten", ["ซีอิ๊วขาว (ปราศจากกลูเตน)"]),
            ("sesame", ["ทาฮินี (ไม่มีงา)"]),
        ]:
            with self.subTest(key=key, lines=lines):
                self.assertIsNotNone(self.violation(key, *lines))

    def test_unsupported_conditional_claims_remain_blocked(self):
        for line in ["กะทิ (อาจไม่มีนมวัว)", "กะทิ (ตรวจสอบว่าไม่มีนมวัว)",
                     "กะทิ (ไม่มีนมวัว?)", "กะทิ ไม่มีนมวัว",
                     "กะทิ (ไม่มีนมวัว หากเปลี่ยนสูตร)", "กะทิ (milk-free if substituted)",
                     "กะทิ (milk-free?)", "กะทิ (ไม่มีนมวัว) หากเปลี่ยนสูตร",
                     "กะทิ (ไม่มีนมวัว, ถ้าเลือกสูตรนี้)"]:
            with self.subTest(line=line):
                self.assertIsNotNone(self.violation("milk", line))

    def test_literal_derived_and_evidence_provenance_are_independent(self):
        self.assertEqual(self.violation("shrimp", "กุ้ง").match_kind, "literal")
        for key, line in [("shellfish", "ปลาหมึก"), ("shellfish", "scallop"),
                          ("fish", "anchovy"), ("sesame", "sesame seeds"), ("nut", "เม็ดมะม่วง")]:
            self.assertEqual(self.violation(key, line).match_kind, "literal")
        for seeded in (False, True):
            found = self.violation("shrimp", "กะปิ", seeded=seeded)
            self.assertEqual(found.match_kind, "derived")
            self.assertEqual(found.matched_via, "kg" if seeded else "floor")
            self.assertIn("ส่วนประกอบ", format_violation_reason(found))
        self.assertEqual(self.violation("fish", "น้ำปลา").match_kind, "derived")
        self.assertTrue(self.violation("gluten", "แป้ง 100 กรัม").uncertain)

    def test_shared_policy_applies_to_legacy_personalization_and_input_messages(self):
        prefs = {"allergies": "แพ้ปลา"}
        blocks = resolve_blocks_for_keys(self.db, ["fish"])
        safe = recipe("ปลาหมึก 100 กรัม")
        self.assertEqual(check_allergy(safe, prefs), (True, "OK"))
        self.assertEqual(check_allergy(safe, prefs, blocks), (True, "OK"))
        self.assertTrue(_is_allergy_safe(SimpleNamespace(**safe), prefs, blocks))
        self.assertNotIn("ปลาหมึก", build_allergy_exhaustion_message(["ปลาหมึก"], prefs, blocks))
        unsafe = recipe("ปลาหมึกผสมน้ำปลา")
        self.assertFalse(check_allergy(unsafe, prefs)[0])
        self.assertFalse(_is_allergy_safe(SimpleNamespace(**unsafe), prefs, blocks))


class PreferenceClarificationTests(unittest.TestCase):
    def test_scoped_positive_negative_and_bare_pills(self):
        for text, expected in [
            ("ไม่แพ้นม", []), ("แพ้กุ้ง แต่ไม่แพ้นม", ["shrimp"]),
            ("แพ้นมและกุ้ง", ["shrimp", "milk"]), ("ถั่วเหลือง", ["soy"]),
            ("แพ้นม / ผลิตภัณฑ์จากนม", ["milk"]), ("กุ้ง/อาหารทะเล", ["shrimp", "shellfish", "fish"]),
            ("งา", ["sesame"]), ("แพ้งา", ["sesame"]),
            ("allergic to shrimp but not allergic to milk", ["shrimp"]),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_allergy_preferences({"allergies": text}), (expected, False))

    def test_ambiguous_unknown_contradictory_and_oversized_inputs_require_clarification(self):
        for text in ["ชอบอาหารทะเล", "ลดแป้ง", "แพ้ควินัว", "อื่น ๆ", "แพ้",
                     "แพ้กุ้ง แพ้", "แพ้ไม่แพ้นม", "แพ้กุ้งแต่ไม่แพ้",
                     "แพ้นม แต่ไม่แพ้นม", "กุ้งและควินัว", "งา" * 1001]:
            with self.subTest(text=text):
                self.assertTrue(parse_allergy_preferences({"allergies": text})[1])
        self.assertTrue(parse_allergy_preferences({"allergy": "แพ้นม", "allergies": "ไม่แพ้นม"})[1])

    def test_singular_gate_and_no_allergy_values_remain_compatible(self):
        self.assertEqual(parse_allergy_preferences({"allergy": "ชอบอาหารทะเล"}), ([], False))
        self.assertEqual(parse_allergy_preferences({"allergy": "กุ้ง", "allergies": "แพ้นม"}), (["milk"], False))
        for text in ["", "none", "ไม่มี", "ไม่มีอาการแพ้", "ไม่มีข้อจำกัด", "ไม่แพ้อาหาร"]:
            self.assertEqual(parse_allergy_preferences({"allergies": text}), ([], False))


class PreflightAndGenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_ambiguous_input_never_reaches_graph_retrieval_provider_or_history(self):
        for text in ["ชอบอาหารทะเล", "ลดแป้ง", "แพ้นม แต่ไม่แพ้นม", "แพ้ควินัว"]:
            with self.subTest(text=text):
                preferences = {"taste": "", "allergies": text, "equipment": "", "extra": ""}
                req = GenerateRecipeTextRequest(recipe={"name": "Custom Recipe from Fridge"},
                    ingredients=[{"name": "หมูสับ"}], preferences=preferences)
                with patch("main.resolve_blocks_for_request") as graph, \
                     patch("main.get_personalization_for_request", new_callable=AsyncMock) as retrieval, \
                     patch("main.call_agentic_llm") as provider, \
                     patch("main.compute_recipe_nutrition") as nutrition, \
                     patch("main.save_generate_history") as history:
                    result = await generate_recipe_text(req, current_user=SimpleNamespace(id=7), db=MagicMock())
                    preflight = validate_allergy_preferences(
                        AllergyPreferencesRequest(preferences=preferences), current_user=SimpleNamespace(id=7))
                self.assertEqual(result, preflight)
                self.assertEqual(result["code"], "allergy_preferences_ambiguous")
                self.assertEqual(result["field"], "preferences.allergies")
                for seam in (graph, retrieval, provider, nutrition, history):
                    seam.assert_not_called()

    async def test_sesame_frontend_payload_retries_derived_ingredient(self):
        safe = {
            "recipe_name": "Pork", "servings": 1, "adjusted_ingredients": ["หมูสับ 100 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
            "instructions": ["ใส่น้ำมันผัดหมูให้สุก"], "diet_tags": ["Thai"], "safety_warning": "ระวังความร้อน",
            "nutrition": {"basis": "per_serving", "calories": 300, "protein_g": 15, "carbs_g": 10, "fat_g": 10},
        }
        unsafe = deepcopy(safe)
        unsafe["adjusted_ingredients"].append("ทาฮินี (ไม่มีงา) 1 ช้อนโต๊ะ")
        db = make_memory_db()
        self.addCleanup(db.close)
        seed_allergen_graph(db)
        blocks = resolve_blocks_for_keys(db, ["sesame"])
        req = GenerateRecipeTextRequest(recipe={"name": "Custom Recipe from Fridge"},
            ingredients=[{"name": "หมูสับ"}, {"name": "ทาฮินี (ไม่มีงา)"}], preferences={"allergies": "แพ้งา"})
        partial = NutritionResult(safe["nutrition"], True, ["test estimate"])
        with patch("main.resolve_blocks_for_request", return_value=blocks), \
             patch("main.get_personalization_for_request", new=AsyncMock(return_value=None)), \
             patch("main.call_agentic_llm", side_effect=[unsafe, safe]) as provider, \
             patch("main.SessionLocal") as sessions, \
             patch("main.compute_recipe_nutrition", return_value=partial), \
             patch("main.save_generate_history", return_value=1):
            result = await generate_recipe_text(req, current_user=SimpleNamespace(id=7), db=MagicMock())
        self.assertEqual(result["status"], "success")
        self.assertEqual(provider.call_count, 2)
        self.assertIn("Allergy violation:", provider.call_args.kwargs["feedback"])
        self.assertIn("sesame", provider.call_args.kwargs["feedback"])
