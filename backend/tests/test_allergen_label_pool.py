# backend/tests/test_allergen_label_pool.py
import csv
import json
import os
import tempfile
import unittest

from eval.build_allergen_label_pool import (
    build_pool,
    canonical_sha256,
    clean_string,
    export_review_tsv,
    import_review_tsv,
    ingredient_name,
    is_garbled,
    is_public,
)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)


class PublicFlagTests(unittest.TestCase):
    def test_ingredient_name_strips_quantity_and_notes(self):
        self.assertEqual(ingredient_name("หมูสับ 200 กรัม"), "หมูสับ")
        self.assertEqual(ingredient_name("alpha (note) 2 ช้อน"), "alpha")

    def test_public_when_name_appears_in_public_text(self):
        self.assertTrue(is_public("alpha 1 ช้อน", "… we found alpha in a run …"))
        self.assertFalse(is_public("beta 1 ช้อน", "… we found alpha in a run …"))

    def test_single_char_name_never_public(self):
        self.assertFalse(is_public("a 1 ช้อน", "a b c"))

    def test_multi_word_name_public_via_first_token(self):
        self.assertTrue(is_public("เกลือ เล็กน้อย", "… เกลือ …"))

    def test_multi_word_name_not_public_when_neither_whole_nor_first_token_present(self):
        self.assertFalse(is_public("beta gamma 1 ช้อน", "… gamma … alpha …"))

    def test_single_char_first_token_never_public(self):
        self.assertFalse(is_public("a zzz 1 ช้อน", "a b c"))


class CanonicalHashTests(unittest.TestCase):
    def test_hash_ignores_key_order_and_formatting(self):
        self.assertEqual(canonical_sha256({"a": 1, "b": "ก"}), canonical_sha256({"b": "ก", "a": 1}))


class ReviewTsvRoundTripTests(unittest.TestCase):
    POOL = {"items": [
        {"id": 0, "string": "alpha 1 ช้อน", "source": "benchmark", "file": "f", "allergens": ["shrimp"], "public": False},
        {"id": 1, "string": "beta น้ำ", "source": "inmu", "file": "g", "allergens": [], "public": True},
    ]}

    def _exported(self, tmp):
        path = os.path.join(tmp, "r.tsv")
        export_review_tsv(self.POOL, path)
        return path

    def test_round_trip_with_edited_allergens(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            _write(path, _read(path).replace("\tshrimp\t", "\tshrimp,soy\t"))
            reviewed = import_review_tsv(self.POOL, path)
        self.assertEqual(reviewed["items"][0]["allergens"], ["shrimp", "soy"])
        self.assertEqual(reviewed["items"][1]["allergens"], [])

    def test_allergens_are_sorted_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            _write(path, _read(path).replace("\tshrimp\t", "\tsoy,shrimp,soy\t"))
            reviewed = import_review_tsv(self.POOL, path)
        self.assertEqual(reviewed["items"][0]["allergens"], ["shrimp", "soy"])

    def test_changed_string_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            _write(path, _read(path).replace("beta น้ำ", "beta ???"))
            with self.assertRaises(ValueError):
                import_review_tsv(self.POOL, path)

    def test_unknown_allergen_key_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            _write(path, _read(path).replace("\tshrimp\t", "\tprawns\t"))
            with self.assertRaises(ValueError):
                import_review_tsv(self.POOL, path)

    def test_duplicate_row_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            lines = _read(path).splitlines()
            _write(path, "\n".join(lines + [lines[1]]) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                import_review_tsv(self.POOL, path)

    def test_missing_row_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            lines = _read(path).splitlines()
            _write(path, "\n".join(lines[:2]) + "\n")
            with self.assertRaisesRegex(ValueError, "missing rows"):
                import_review_tsv(self.POOL, path)

    def test_unknown_id_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            _write(path, _read(path).replace("\n1\t", "\n7\t"))
            with self.assertRaises(ValueError):
                import_review_tsv(self.POOL, path)

    def test_bad_header_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            # a comma-delimited re-save collapses the header into one column
            _write(path, _read(path).replace("\t", ",", 5))
            with self.assertRaisesRegex(ValueError, "header"):
                import_review_tsv(self.POOL, path)

    def test_missing_id_column_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._exported(tmp)
            _write(path, _read(path).replace("id\tstring", "string", 1))
            with self.assertRaisesRegex(ValueError, "header"):
                import_review_tsv(self.POOL, path)


class GarbledRuleTests(unittest.TestCase):
    def test_thai_combining_mark_after_latin_is_garbled(self):
        self.assertIsNotNone(is_garbled("Febru่"))

    def test_token_mixing_thai_and_latin_letters_is_garbled(self):
        self.assertIsNotNone(is_garbled("กะperi 1 ช้อน"))

    def test_script_outside_thai_latin_is_garbled(self):
        self.assertIsNotNone(is_garbled("ข่า 1 Ωμ"))

    def test_normal_thai_with_quantity_is_kept(self):
        self.assertIsNone(is_garbled("หมูสับ 200 กรัม"))

    def test_thai_with_separate_english_word_is_kept(self):
        self.assertIsNone(is_garbled("ซอส BBQ 2 ช้อนโต๊ะ"))

    def test_parenthesised_note_is_kept(self):
        self.assertIsNone(is_garbled("กะทิ (สูตรไม่มีนมวัว) 200 มล."))

    def test_benign_typography_and_fractions_are_kept(self):
        for s in ("น้ำตาล ½ ช้อนชา", "พริก ~5 เม็ด", "น้ำเปล่า 1–2 ถ้วย", "“น้ำปลา”"):
            with self.subTest(s=s):
                self.assertIsNone(is_garbled(s))
                # also in the normalize_thai form the pool actually stores
                self.assertIsNone(is_garbled(clean_string(s)))

    def test_uppercase_latin_adjacent_to_thai_is_kept(self):
        self.assertIsNone(is_garbled("ซอสXO"))

    def test_slash_splits_tokens(self):
        self.assertIsNone(is_garbled("น้ำปลา 1 ช้อนโต๊ะ/tbsp"))

    def test_reasoning_leak_shape_is_garbled(self):
        self.assertEqual(is_garbled("ไข่ 2 ฟอง thinking: the user wants"), "reasoning-leak shape")

    def test_lowercase_latin_mixed_with_thai_still_garbled_after_clean(self):
        self.assertIsNotNone(is_garbled(clean_string("กะperi 1 ช้อน")))
        self.assertIsNotNone(is_garbled(clean_string("Febru่")))


class CleanStringTests(unittest.TestCase):
    def test_zero_width_characters_are_removed(self):
        zw = "".join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF))
        cleaned = clean_string("  ไข่" + zw + "ไก่ 2 ฟอง" + zw + " ")
        self.assertEqual(cleaned, "ไข่ไก่ 2 ฟอง")
        for c in zw:
            self.assertNotIn(c, cleaned)


class BuildPoolTests(unittest.TestCase):
    def test_base_recipe_string_survives_when_matching_benchmark_string_is_not_sampled(self):
        benchmark = {"cand": {"per_case": [
            {"recipe": {"adjusted_ingredients": ["alpha 1 cup", "kale 1 cup", "zed 1 cup"]}},
        ]}}
        with tempfile.TemporaryDirectory() as tmp:
            bench_path = os.path.join(tmp, "benchmark-x.json")
            with open(bench_path, "w", encoding="utf-8") as f:
                json.dump(benchmark, f)
            csv_path = os.path.join(tmp, "inmu.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Food_Code", "Thai_Name"])
                w.writerow(["F1", "melon"])
                w.writerow(["F2", "kale 1 cup"])
            pool = build_pool([bench_path], csv_path, 2, 1, "",
                              mock_recipes=[{"name": "r1", "ingredients": ["kale 1 cup", "kale 1 cup"]}])
        by_string = {i["string"]: i for i in pool["items"]}
        # precondition: the sample picked a different benchmark string, so 'kale 1 cup' was NOT sampled
        self.assertEqual([i["string"] for i in pool["items"] if i["source"] == "benchmark"], ["zed 1 cup"])
        self.assertEqual(by_string["kale 1 cup"]["source"], "base_recipe")
        # dedup against the pool: only one 'kale 1 cup', the INMU duplicate is dropped
        self.assertEqual(sum(1 for i in pool["items"] if i["string"] == "kale 1 cup"), 1)
        self.assertEqual([i["id"] for i in pool["items"]], list(range(len(pool["items"]))))


if __name__ == "__main__":
    unittest.main()
