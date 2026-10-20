import ast
from copy import deepcopy
from pathlib import Path
import unittest

from recipe_checks import (
    CATALOG_ALIASES, check_core, check_flavor, check_ingredients,
    check_logic, check_nutrition, ingredient_prompt_guidance, unknown_ingredients,
)


BASE = {
    "recipe_name": "Holy Basil Pork", "servings": 1,
    "adjusted_ingredients": ["หมูสับ 100 กรัม", "ใบกะเพรา 10 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
    "instructions": ["ตั้งกระทะใส่น้ำมัน", "ผัดหมูจนสุกแล้วใส่ใบกะเพรา"],
    "diet_tags": ["Thai"], "safety_warning": "ระวังความร้อน",
    "nutrition": {"basis": "per_serving", "calories": 420, "protein_g": 28, "carbs_g": 18, "fat_g": 24},
}


def recipe(**changes):
    return dict(deepcopy(BASE), **changes)


class IngredientTests(unittest.TestCase):
    def test_catalog_exactly_matches_55_seed_names_without_importing_seed(self):
        source = Path(__file__).resolve().parents[1] / "database/seed_postgres.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        seed = ast.literal_eval(next(node.value for node in tree.body if isinstance(node, ast.Assign)
                                    and any(isinstance(target, ast.Name) and target.id == "MOCK_RECIPES"
                                            for target in node.targets)))
        self.assertEqual(set(CATALOG_ALIASES), {name for item in seed for name in item["ingredients"]})
        self.assertEqual(len(CATALOG_ALIASES), 55)

    def test_all_reviewed_catalog_aliases_admit_both_directions(self):
        for canonical, aliases in CATALOG_ALIASES.items():
            for alias in aliases:
                with self.subTest(canonical=canonical, alias=alias):
                    self.assertTrue(check_ingredients(recipe(adjusted_ingredients=[alias + " 10 กรัม"]), [canonical])[0])
                    self.assertTrue(check_ingredients(recipe(adjusted_ingredients=[canonical + " 10 g"]), [alias])[0])

    def test_thai_and_mixed_script_unknowns_are_rejected(self):
        for line in ["กุ้ง 100 กรัม", "shrimp 100 กรัม", "กุ้ง100กรัม", "eggplant 100 g", "หมูสามชั้น 100 กรัม", "หมูสับผสมกุ้ง 100 กรัม"]:
            with self.subTest(line=line):
                self.assertFalse(check_ingredients(recipe(adjusted_ingredients=[line]), ["minced pork", "egg"])[0])

    def test_pantry_identity_is_not_substring_or_proxy_equivalence(self):
        for line in ["น้ำปลา ตามชอบ", "น้ำตาลเล็กน้อย", "olive oil 1 tbsp", "salt 1 g"]:
            self.assertTrue(check_ingredients(recipe(adjusted_ingredients=[line]), [])[0], line)
        for line in ["garlic 10 g", "fish sauce candy 1 g", "coconut milk 100 ml", "น้ำมันงา 1 ช้อนโต๊ะ"]:
            self.assertFalse(check_ingredients(recipe(adjusted_ingredients=[line]), [])[0], line)

    def test_direct_user_name_outside_catalog_and_preparation_note(self):
        for name in ["truffle", "เห็ดที่ผู้ใช้ระบุ", "sauce (without milk)", "pork belly (chashu)"]:
            self.assertTrue(check_ingredients(recipe(adjusted_ingredients=[name + " 10 g"]), [name])[0], name)
        self.assertFalse(check_ingredients(recipe(adjusted_ingredients=["soy sauce (gluten-free) 10 g"]), ["soy sauce"])[0])

    def test_known_quantity_errors_do_not_become_hallucination(self):
        for amount in ["0 g", "-2 g", "nan g", "inf g", "1/0 g", "ตามชอบ 0 g"]:
            candidate = recipe(adjusted_ingredients=["minced pork " + amount])
            self.assertFalse(check_ingredients(candidate, ["minced pork"])[0], amount)
            self.assertEqual(unknown_ingredients(candidate, ["minced pork"]), [])
        self.assertTrue(check_ingredients(recipe(adjusted_ingredients=["น้ำมัน 1/2 ช้อนโต๊ะ"]), [])[0])

    def test_thai_sara_am_normalization(self):
        self.assertTrue(check_ingredients(recipe(adjusted_ingredients=["นํ้าเปล่าเล็กน้อย 1 ถ้วย"]), [])[0])

    def test_ranges_preserve_every_reviewed_catalog_identity(self):
        for canonical, aliases in CATALOG_ALIASES.items():
            for name in (canonical, *aliases):
                with self.subTest(canonical=canonical, name=name):
                    candidate = recipe(adjusted_ingredients=[name + " 5-7 กรัม"])
                    self.assertEqual(check_ingredients(candidate, [canonical]), (True, "OK"))
                    self.assertEqual(unknown_ingredients(candidate, [canonical]), [])

    def test_ranges_for_counts_seasonings_and_selected_non_catalog_names(self):
        for name, selected, amount in [
            ("พริกขี้หนู", "bird's eye chilies", "5-7 เม็ด"),
            ("หมูสับ", "minced pork", "100 - 150 กรัม"),
            ("น้ำปลา", "fish sauce", "1-2 ช้อนชา"),
            ("truffle", "truffle", "5-7 g"),
            ("เห็ดที่ผู้ใช้ระบุ", "เห็ดที่ผู้ใช้ระบุ", "5-5 กรัม"),
        ]:
            with self.subTest(name=name, amount=amount):
                candidate = recipe(adjusted_ingredients=[name + " " + amount],
                                   instructions=["Boil " + name + "."], recipe_name=name)
                self.assertEqual(check_ingredients(candidate, [selected]), (True, "OK"))
                self.assertEqual(check_logic(candidate), (True, "OK"))
                self.assertEqual(check_core(candidate, [selected]), (True, "OK"))

    def test_invalid_range_values_are_quantity_errors_not_unknown_foods(self):
        for amount in ["0-7", "-1-7", "5-0", "5--7", "7-5", "nan-7", "5-inf", "1/0-2", "1-2/0", "9" * 400 + "-7"]:
            for name in ["พริกขี้หนู", "truffle"]:
                with self.subTest(amount=amount, name=name):
                    candidate = recipe(adjusted_ingredients=[name + " " + amount + " g"])
                    self.assertEqual(unknown_ingredients(candidate, [name]), [])
                    self.assertTrue(check_ingredients(candidate, [name])[1].startswith("Invalid ingredient quantity:"))

    def test_malformed_or_unselected_ranges_do_not_gain_admission(self):
        for line in ["พริกขี้หนู 5-7-9 เม็ด", "พริกขี้หนู 5-unknown เม็ด", "กุ้ง 5-7 กรัม"]:
            self.assertFalse(check_ingredients(recipe(adjusted_ingredients=[line]), ["bird's eye chilies"])[0], line)

    def test_generic_egg_is_not_a_reverse_admission_alias_for_chicken_egg(self):
        for selected, declared in [
            ("egg", "ไข่ไก่"), ("ไข่ไก่", "egg"), ("ไข่ไก่", "ไข่เป็ด"),
            ("egg", "soft-boiled egg"), ("pork", "minced pork"),
            ("minced pork", "pork"), ("beef", "beef steak"),
            ("bell pepper", "yellow bell pepper"), ("milk", "cow milk"),
            ("holy basil leaves", "thai basil"),
        ]:
            self.assertFalse(check_ingredients(recipe(adjusted_ingredients=[declared + " 1 ฟอง"]), [selected])[0])


class CookingTests(unittest.TestCase):
    def test_reviewed_directional_step_and_title_references(self):
        references = {
            "minced pork": ("pork", "หมู", "เนื้อหมู"),
            "pork belly (chashu)": ("pork", "หมู", "ชาชู"),
            "beef steak": ("beef", "เนื้อวัว"),
            "soft-boiled egg": ("egg", "ไข่"),
            "ไข่ไก่": ("egg", "ไข่"),
            "holy basil leaves": ("basil",),
            "yellow bell pepper": ("bell pepper", "พริกหวาน"),
            "black pepper": ("pepper", "พริกไทย"),
            "palm sugar": ("sugar", "น้ำตาล"),
            "olive oil": ("oil", "น้ำมัน"),
            "vegetable oil": ("oil", "น้ำมัน"),
            "cow milk": ("milk", "นม"),
            "pork": ("หมู", "เนื้อหมู"), "chicken": ("ไก่",), "beef": ("เนื้อวัว",),
        }
        for declared, short_names in references.items():
            for short in short_names:
                with self.subTest(declared=declared, short=short):
                    candidate = recipe(adjusted_ingredients=[declared + " 10 g"],
                                       instructions=["Boil " + short + "."], recipe_name=short)
                    self.assertEqual(check_logic(candidate), (True, "OK"))
                    self.assertEqual(check_core(candidate, [declared]), (True, "OK"))

    def test_chicken_egg_must_be_declared_and_generic_egg_must_be_unambiguous(self):
        missing = recipe(instructions=["ต้มไข่ให้สุก"])
        self.assertIn("Undeclared ingredient", check_logic(missing)[1])
        for declared, short in [
            (["ไข่ไก่ 1 ฟอง", "ไข่ต้มยางมะตูม 1 ฟอง"], "ไข่"),
            (["หมูสับ 100 กรัม", "หมูสามชั้นชาชู 100 กรัม"], "หมู"),
        ]:
            candidate = recipe(adjusted_ingredients=declared, instructions=["ต้ม" + short], recipe_name=short)
            self.assertIn("Ambiguous ingredient", check_logic(candidate)[1])
            self.assertIn("Ambiguous named ingredient", check_core(candidate, [])[1])

    def test_similar_foods_do_not_become_directional_substitutes(self):
        for declared, used in [
            ("ไข่ไก่", "ไข่เป็ด"), ("egg", "ไข่ไก่"), ("egg", "eggplant"),
            ("ไข่ไก่", "egg noodles"), ("holy basil leaves", "thai basil"),
            ("holy basil leaves", "โหระพา"), ("cow milk", "soy milk"),
            ("cow milk", "นมอัลมอนด์"), ("minced pork", "หมูสามชั้น"),
            ("bell pepper", "yellow bell pepper"),
        ]:
            with self.subTest(declared=declared, used=used):
                candidate = recipe(adjusted_ingredients=[declared + " 10 g"], instructions=["Boil " + used + "."])
                self.assertFalse(check_logic(candidate)[0])

    def test_longer_different_foods_do_not_match_short_declared_names(self):
        for items, instruction in [
            (["หมูสับ 100 g", "น้ำเปล่า 100 ml"], "เติมน้ำส้มสายชูแล้วต้มหมูสับให้สุก"),
            (["egg 1 g"], "Boil egg noodles."),
            (["ข่า 1 g"], "ต้มข้าวสวยให้ร้อน"),
        ]:
            self.assertFalse(check_logic(recipe(adjusted_ingredients=items, instructions=[instruction]))[0])

    def test_every_used_pantry_ingredient_must_be_declared(self):
        for name in ["น้ำปลา", "น้ำเปล่า", "น้ำตาล", "น้ำมัน", "เกลือ"]:
            candidate = recipe(adjusted_ingredients=["หมูสับ 100 กรัม"], instructions=["ใส่หมูสับและ" + name])
            self.assertFalse(check_logic(candidate)[0], name)
            self.assertIn("Undeclared ingredient", check_logic(candidate)[1])

    def test_aliases_and_short_references_require_one_declared_target(self):
        self.assertTrue(check_logic(BASE)[0])
        ambiguous = recipe(adjusted_ingredients=["หมูสับ 100 กรัม", "หมูสามชั้นชาชู 100 กรัม"], instructions=["ต้มหมูจนร้อน"])
        self.assertFalse(check_logic(ambiguous)[0])
        self.assertIn("Ambiguous ingredient", check_logic(ambiguous)[1])
        self.assertTrue(check_logic(recipe(adjusted_ingredients=["หมูสับ 100 กรัม"], instructions=["ต้มหมูสับจนสุก"]))[0])

    def test_negative_mentions_do_not_hide_later_positive_addition(self):
        candidate = recipe(instructions=["ห้ามใส่น้ำปลา แต่เติมน้ำปลาในหมู"])
        self.assertFalse(check_logic(candidate)[0])
        self.assertTrue(check_logic(recipe(instructions=["ต้มหมูให้สุก ห้ามใส่น้ำปลา"]))[0])
        self.assertTrue(check_logic(recipe(instructions=["Cook pork. Do not add fish sauce."]))[0])

    def test_oil_must_be_used_at_or_before_frying(self):
        for instructions in [["ทอดหมูจนสุก"], ["Fry pork until cooked."], ["Frying pork."], ["ทอดหมูโดยไม่ใช้น้ำมัน"], ["ผัดหมู", "ใส่น้ำมัน"]]:
            with self.subTest(instructions=instructions):
                self.assertFalse(check_logic(recipe(instructions=instructions))[0])
        self.assertTrue(check_logic(recipe(instructions=["Heat oil.", "Stir-fry pork until cooked."]))[0])
        self.assertTrue(check_logic(recipe(instructions=["ผัดหมูกับน้ำมันจนสุก"]))[0])

    def test_explicit_non_oil_methods_are_not_blanket_rejected(self):
        for instruction in ["ทอดหมูในหม้อทอดลมร้อน", "ทอดหมูในหม้อทอดไร้น้ำมัน", "Air-fry pork until cooked.", "Dry-fry pork.", "ผัดน้ำให้หมูสุก"]:
            candidate = recipe(adjusted_ingredients=["หมูสับ 100 กรัม", "น้ำ 1 ถ้วย"], instructions=[instruction])
            self.assertTrue(check_logic(candidate)[0], (instruction, check_logic(candidate)))

    def test_stock_claims_remain_prohibited(self):
        self.assertEqual(check_logic(recipe(safety_warning="ต้องซื้อวัตถุดิบเพิ่ม")), (False, "Prohibited stock conclusion"))


class FlavorTests(unittest.TestCase):
    def test_explicit_same_pan_continuations_and_negated_separation(self):
        candidate = recipe(recipe_name="Pad Thai", adjusted_ingredients=["cow milk 50 ml", "fish sauce 5 ml"])
        for steps in [
            ["Stir-fry cow milk in the pan.", "Add fish sauce to the same pan and stir-fry together."],
            ["ผัดนมวัวแล้วเติมน้ำปลาในกระทะเดิมผัดรวมกัน"],
            ["ผัดนมวัวกับน้ำปลารวมกัน ไม่ต้องแยก"],
        ]:
            self.assertFalse(check_flavor(dict(candidate, instructions=steps))[0], steps)
        self.assertTrue(check_flavor(dict(candidate, instructions=["Stir-fry fish sauce.", "Serve cow milk separately."]))[0])

    def test_only_named_context_positive_same_stirfry_rejects(self):
        for title, pair, instruction, rule in [
            ("Pad Thai", ["นมวัว 50 ml", "น้ำปลา 1 ช้อนชา"], "ผัดเส้นกับนมวัวและน้ำปลาในกระทะเดียวกัน", "F01"),
            ("Pad Kra Pao Pork", ["ช็อกโกแลต 10 g", "กระเทียม 5 g"], "ผัดหมูกับช็อกโกแลตและกระเทียมรวมกัน", "F02"),
        ]:
            candidate = recipe(recipe_name=title, adjusted_ingredients=pair, instructions=[instruction])
            self.assertFalse(check_flavor(candidate)[0])
            self.assertIn(rule, check_flavor(candidate)[1])

    def test_published_savory_counterexamples_do_not_trigger_universal_bans(self):
        for title, items in [
            ("Chicken Curry", ["cow milk 50 ml", "fish sauce 5 ml"]),
            ("Tom Yum", ["evaporated milk 50 ml", "fish sauce 5 ml"]),
            ("Mole", ["chocolate 10 g", "garlic 5 g"]),
            ("Coconut Curry", ["coconut milk 100 ml", "fish sauce 5 ml"]),
        ]:
            self.assertTrue(check_flavor(recipe(recipe_name=title, adjusted_ingredients=items))[0], title)

    def test_negation_separate_components_and_ambiguous_use_are_not_pair_evidence(self):
        candidate = recipe(recipe_name="Pad Thai", adjusted_ingredients=["cow milk 50 ml", "fish sauce 5 ml"])
        for instruction in ["ผัดเส้นกับน้ำปลา ไม่ใส่นมวัว", "ผัดเส้นกับน้ำปลา เสิร์ฟนมวัวแยกต่างหาก", "นมวัวและน้ำปลา", "Mix cow milk and fish sauce. Do not stir-fry.", "Deep-fry cow milk and fish sauce."]:
            self.assertTrue(check_flavor(dict(candidate, instructions=[instruction]))[0], instruction)
        self.assertFalse(check_flavor(dict(candidate, instructions=["ห้ามใส่นมวัว แต่ผัดนมวัวกับน้ำปลา"] ))[0])

    def test_generic_or_plant_milk_is_not_assumed_to_be_cow_milk(self):
        for name in ["milk", "coconut milk", "oat milk"]:
            candidate = recipe(recipe_name="Pad Thai", adjusted_ingredients=[name + " 100 ml", "fish sauce 5 ml"], instructions=["Stir-fry " + name + " with fish sauce."])
            self.assertTrue(check_flavor(candidate)[0], name)


class CoreNutritionTests(unittest.TestCase):
    def test_core_uses_output_not_inventory_and_allows_changed_protein(self):
        self.assertTrue(check_core(recipe(recipe_name="Pork steak"), ["minced pork"])[0])
        self.assertFalse(check_core(recipe(recipe_name="Beef steak"), ["beef steak", "minced pork"])[0])
        self.assertFalse(check_core(recipe(recipe_name="Shrimp soup"), ["minced pork"])[0])
        self.assertTrue(check_core(recipe(recipe_name="Fried rice", adjusted_ingredients=["rice 100 g"]), ["rice"])[0])
        self.assertFalse(check_core(recipe(recipe_name="Fried rice"), ["minced pork"])[0])

    def test_core_longest_names_and_absence_claims(self):
        for name in ["Pork Soup free from shrimp and milk", "No shrimp or egg pork soup"]:
            self.assertTrue(check_core(recipe(recipe_name=name), ["minced pork"])[0], name)
        self.assertTrue(check_core(recipe(recipe_name="Egg-free pork soup"), ["minced pork"])[0])
        self.assertTrue(check_core(recipe(recipe_name="Pork soup without shrimp"), ["minced pork"])[0])
        self.assertFalse(check_core(recipe(recipe_name="Eggplant soup", adjusted_ingredients=["egg 100 g"]), ["egg"])[0])
        self.assertTrue(check_core(recipe(recipe_name="Egg soup", adjusted_ingredients=["soft-boiled egg 100 g"]), ["soft-boiled egg"])[0])

    def test_nutrition_project_bound_without_calorie_ceiling(self):
        for E, P, C, F, expected in [(420,28,18,24,True),(1800,80,150,100,True),(200,10,150,5,True),(300,10000,10000,10000,False),(100,1000,0,0,False),(100,0,0,200,False),(0,0,0,0,False),(100,100,0,51,True),(100,100,0,51.1,False)]:
            candidate = recipe(nutrition=dict(BASE["nutrition"], calories=E, protein_g=P, carbs_g=C, fat_g=F))
            self.assertEqual(check_nutrition(candidate)[0], expected, (E,P,C,F))

    def test_huge_nonfinite_and_negative_values_fail_without_throwing(self):
        for key in ["calories", "protein_g", "carbs_g", "fat_g"]:
            for value in [10**400, float("nan"), float("inf"), -1, True]:
                self.assertFalse(check_nutrition(recipe(nutrition=dict(BASE["nutrition"], **{key:value})))[0])

    def test_prompt_uses_actual_input_names_and_declares_pantry(self):
        prompt = ingredient_prompt_guidance(["minced pork", "chives", "chili paste"])
        for text in ["หมูสับ", "กุยช่าย", "น้ำพริกเผา", "ทุกวัตถุดิบที่ใช้ในขั้นตอน", "adjusted_ingredients", "ตามชอบ", "เฉพาะผัดไทย/ผัดกะเพรา"]:
            self.assertIn(text, prompt)
        self.assertNotIn("มะกอกคาลามาตา", prompt)
        self.assertIn("ปริมาณเดียว", prompt)


if __name__ == "__main__":
    unittest.main()
