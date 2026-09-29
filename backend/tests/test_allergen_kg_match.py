# backend/tests/test_allergen_kg_match.py
import unittest

from allergen_kg.match import (
    Violation,
    find_allergy_violation,
    format_violation_reason,
    head_contains_other_terms,
)
from allergen_kg.resolve import ResolvedAllergen, TermInfo, floor_only
from main import check_allergy, validate_recipe


def recipe(*ingredients):
    return {"adjusted_ingredients": list(ingredients)}


def shrimp_with(extra_terms):
    base = floor_only("shrimp", "ok").terms
    return {"shrimp": ResolvedAllergen(terms={**base, **extra_terms}, graph_status="ok")}


class FindViolationTests(unittest.TestCase):
    def test_two_hop_kg_match_reports_path(self):
        blocks = shrimp_with({
            "alpha": TermInfo("kg", ("alpha",)),
            "beta": TermInfo("kg", ("beta", "alpha")),
        })
        v = find_allergy_violation(recipe("beta 1 ช้อน"), {"allergy": "แพ้กุ้ง"}, blocks)
        self.assertEqual(v, Violation("beta", "shrimp", "kg", ("beta", "alpha")))

    def test_deepest_chain_preferred_when_several_terms_match(self):
        blocks = shrimp_with({"beta": TermInfo("kg", ("beta", "alpha"))})
        v = find_allergy_violation(recipe("กุ้งสด", "beta"), {"allergy": "แพ้กุ้ง"}, blocks)
        self.assertEqual(v.term, "beta")

    def test_floor_term_still_blocks_when_graph_empty(self):
        blocks = {"shrimp": floor_only("shrimp", "empty")}
        v = find_allergy_violation(recipe("กะปิ 1 ช้อนชา"), {"allergy": "แพ้กุ้ง"}, blocks)
        self.assertEqual(v, Violation("กะปิ", "shrimp", "floor", None))

    def test_detected_key_missing_from_resolved_uses_floor(self):
        v = find_allergy_violation(recipe("นมสด"), {"allergy": "แพ้นม"}, {})
        self.assertEqual((v.term, v.allergen_key, v.matched_via), ("นม", "milk", "floor"))

    def test_resolved_key_checked_even_with_empty_prefs(self):
        blocks = shrimp_with({"beta": TermInfo("kg", ("beta", "alpha"))})
        v = find_allergy_violation(recipe("beta"), {}, blocks)
        self.assertEqual(v.allergen_key, "shrimp")

    def test_sara_am_decomposed_text_still_matches(self):
        blocks = shrimp_with({"ทดสอบน้ำ": TermInfo("kg", ("ทดสอบน้ำ", "alpha"))})
        decomposed = "ทดสอบน" + "้ํา"  # tone mark + NIKHAHIT + SARA AA
        v = find_allergy_violation(recipe(decomposed + " 1 ถ้วย"), {"allergy": "แพ้กุ้ง"}, blocks)
        self.assertEqual(v.term, "ทดสอบน้ำ")

    def test_two_allergies_second_one_caught(self):
        blocks = {"shrimp": floor_only("shrimp", "ok"), "milk": floor_only("milk", "ok")}
        v = find_allergy_violation(recipe("ครีม 50 มล."), {"allergy": "แพ้กุ้งและนม"}, blocks)
        self.assertEqual(v.allergen_key, "milk")

    def test_no_violation(self):
        blocks = shrimp_with({"beta": TermInfo("kg", ("beta", "alpha"))})
        self.assertIsNone(find_allergy_violation(recipe("หมูสับ"), {"allergy": "แพ้กุ้ง"}, blocks))


class ReasonFormatTests(unittest.TestCase):
    def test_kg_reason_has_full_chain(self):
        reason = format_violation_reason(Violation("gamma", "shrimp", "kg", ("gamma", "beta", "alpha")))
        self.assertEqual(reason, "Allergy violation: 'gamma' → beta → alpha → กุ้ง (ผู้ใช้แพ้ shrimp)")
        self.assertEqual(reason.count("→"), 3)

    def test_floor_reason_unchanged_format(self):
        reason = format_violation_reason(Violation("กะปิ", "shrimp", "floor", None))
        self.assertEqual(reason, "Allergy violation: พบ 'กะปิ' ในสูตร (ผู้ใช้แพ้ shrimp)")


class NonRedundancyHelperTests(unittest.TestCase):
    def test_head_containing_existing_term_is_redundant(self):
        # Direction check: "alpha" sits INSIDE the head "alpha soup",
        # so the 1-hop node already catches it -> redundant chain.
        self.assertEqual(head_contains_other_terms("alpha soup", ["alpha", "shrimp"]), ["alpha"])

    def test_head_not_containing_any_term_is_non_redundant(self):
        self.assertEqual(head_contains_other_terms("gamma mix", ["alpha", "beta", "shrimp"]), [])

    def test_head_itself_is_ignored(self):
        self.assertEqual(head_contains_other_terms("gamma", ["gamma", "alpha"]), [])


class CheckAllergyWrapperTests(unittest.TestCase):
    def test_legacy_path_unchanged_when_resolved_blocks_is_none(self):
        self.assertEqual(
            check_allergy(recipe("กะปิ 1 ช้อนชา"), {"allergy": "แพ้กุ้ง"}),
            (False, "Allergy violation: พบ 'กะปิ' ในสูตร (ผู้ใช้แพ้ shrimp)"),
        )
        self.assertEqual(check_allergy(recipe("หมูสับ"), {"allergy": "แพ้กุ้ง"}), (True, "OK"))

    def test_kg_path_returns_chain_reason(self):
        blocks = shrimp_with({"beta": TermInfo("kg", ("beta", "alpha"))})
        valid, msg = check_allergy(recipe("beta"), {"allergy": "แพ้กุ้ง"}, blocks)
        self.assertFalse(valid)
        self.assertTrue(msg.startswith("Allergy violation:"))
        self.assertIn("'beta' → alpha → กุ้ง", msg)

    def test_validate_recipe_threads_resolved_blocks(self):
        full = {
            "recipe_name": "Test",
            "servings": 1,
            "adjusted_ingredients": ["beta 1 ช้อน", "น้ำมัน 1 ช้อนโต๊ะ"],
            "diet_tags": ["Thai"],
            "nutrition": {"basis": "per_serving", "calories": 300, "protein_g": 10, "carbs_g": 10, "fat_g": 10},
            "instructions": ["1. ตั้งกระทะใส่น้ำมัน"],
            "safety_warning": "ระวังความร้อน",
        }
        blocks = shrimp_with({"beta": TermInfo("kg", ("beta", "alpha"))})
        result = validate_recipe(full, [], {"allergy": "แพ้กุ้ง"}, resolved_blocks=blocks)
        self.assertEqual(result["status"], "fail")
        self.assertIn("'beta' → alpha → กุ้ง", result["reason"])
        self.assertEqual(validate_recipe(full, [], {"allergy": "แพ้กุ้ง"})["status"], "pass")


if __name__ == "__main__":
    unittest.main()
