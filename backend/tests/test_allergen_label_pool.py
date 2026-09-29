# backend/tests/test_allergen_label_pool.py
import unittest

import os
import tempfile

from eval.build_allergen_label_pool import (
    canonical_sha256,
    export_review_tsv,
    import_review_tsv,
    ingredient_name,
    is_garbled,
    is_public,
)


class PublicFlagTests(unittest.TestCase):
    def test_ingredient_name_strips_quantity_and_notes(self):
        self.assertEqual(ingredient_name("หมูสับ 200 กรัม"), "หมูสับ")
        self.assertEqual(ingredient_name("alpha (note) 2 ช้อน"), "alpha")

    def test_public_when_name_appears_in_public_text(self):
        self.assertTrue(is_public("alpha 1 ช้อน", "… we found alpha in a run …"))
        self.assertFalse(is_public("beta 1 ช้อน", "… we found alpha in a run …"))

    def test_single_char_name_never_public(self):
        self.assertFalse(is_public("a 1 ช้อน", "a b c"))


class CanonicalHashTests(unittest.TestCase):
    def test_hash_ignores_key_order_and_formatting(self):
        self.assertEqual(canonical_sha256({"a": 1, "b": "ก"}), canonical_sha256({"b": "ก", "a": 1}))


class ReviewTsvRoundTripTests(unittest.TestCase):
    POOL = {"items": [
        {"id": 0, "string": "alpha 1 ช้อน", "source": "benchmark", "file": "f", "allergens": ["shrimp"], "public": False},
        {"id": 1, "string": "beta น้ำ", "source": "inmu", "file": "g", "allergens": [], "public": True},
    ]}

    def test_round_trip_with_edited_allergens(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.tsv")
            export_review_tsv(self.POOL, path)
            text = open(path, encoding="utf-8-sig").read().replace("\tshrimp\t", "\tshrimp,soy\t")
            open(path, "w", encoding="utf-8-sig", newline="").write(text)
            reviewed = import_review_tsv(self.POOL, path)
        self.assertEqual(reviewed["items"][0]["allergens"], ["shrimp", "soy"])
        self.assertEqual(reviewed["items"][1]["allergens"], [])

    def test_changed_string_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.tsv")
            export_review_tsv(self.POOL, path)
            text = open(path, encoding="utf-8-sig").read().replace("beta น้ำ", "beta ???")
            open(path, "w", encoding="utf-8-sig", newline="").write(text)
            with self.assertRaises(ValueError):
                import_review_tsv(self.POOL, path)

    def test_unknown_allergen_key_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.tsv")
            export_review_tsv(self.POOL, path)
            text = open(path, encoding="utf-8-sig").read().replace("\tshrimp\t", "\tprawns\t")
            open(path, "w", encoding="utf-8-sig", newline="").write(text)
            with self.assertRaises(ValueError):
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


if __name__ == "__main__":
    unittest.main()
