# backend/tests/test_allergen_kg_resolve.py
import unittest
from unittest.mock import patch

from allergen_kg.fixtures import add_edges, make_memory_db
from allergen_kg.floor import FLOOR_BLOCKS
from allergen_kg.resolve import (
    TermInfo,
    resolve_allergy_blocks,
    resolve_blocks_for_keys,
    unavailable_blocks,
)


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.db = make_memory_db()

    def tearDown(self):
        self.db.close()

    def test_ok_status_unions_floor_and_closure(self):
        add_edges(self.db, [("alpha", "allergen:shrimp"), ("beta", "alpha")])
        resolved = resolve_blocks_for_keys(self.db, ["shrimp"])["shrimp"]
        self.assertEqual(resolved.graph_status, "ok")
        for term in FLOOR_BLOCKS["shrimp"]:
            self.assertIn(term, resolved.terms)
        self.assertEqual(resolved.terms["beta"], TermInfo("kg", ("beta", "alpha")))

    def test_term_in_both_floor_and_closure_reports_kg(self):
        add_edges(self.db, [("กุ้ง", "allergen:shrimp")])
        resolved = resolve_blocks_for_keys(self.db, ["shrimp"])["shrimp"]
        self.assertEqual(resolved.terms["กุ้ง"], TermInfo("kg", ("กุ้ง",)))

    def test_empty_graph_is_floor_only_and_logged(self):
        with self.assertLogs("allergen_kg", level="WARNING") as logs:
            resolved = resolve_blocks_for_keys(self.db, ["shrimp"])["shrimp"]
        self.assertEqual(resolved.graph_status, "empty")
        self.assertEqual(set(resolved.terms), set(FLOOR_BLOCKS["shrimp"]))
        self.assertTrue(all(t.matched_via == "floor" for t in resolved.terms.values()))
        self.assertIn("shrimp", logs.output[0])

    def test_query_error_is_unavailable_and_logged(self):
        with patch("allergen_kg.resolve.get_allergen_closure", side_effect=RuntimeError("db down")):
            with self.assertLogs("allergen_kg", level="ERROR"):
                resolved = resolve_blocks_for_keys(self.db, ["milk"])["milk"]
        self.assertEqual(resolved.graph_status, "unavailable")
        self.assertEqual(set(resolved.terms), set(FLOOR_BLOCKS["milk"]))

    def test_two_allergies_both_resolved(self):
        add_edges(self.db, [("alpha", "allergen:shrimp")])
        resolved = resolve_allergy_blocks(self.db, {"allergy": "แพ้กุ้งและนม"})
        self.assertEqual(list(resolved), ["shrimp", "milk"])
        self.assertEqual(resolved["shrimp"].graph_status, "ok")
        self.assertEqual(resolved["milk"].graph_status, "empty")

    def test_no_allergy_resolves_nothing(self):
        self.assertEqual(resolve_allergy_blocks(self.db, {"allergy": ""}), {})

    def test_unavailable_blocks_is_floor_only(self):
        with self.assertLogs("allergen_kg", level="WARNING"):
            resolved = unavailable_blocks({"allergy": "แพ้ไข่"})
        self.assertEqual(list(resolved), ["egg"])
        self.assertEqual(resolved["egg"].graph_status, "unavailable")
        self.assertEqual(set(resolved["egg"].terms), set(FLOOR_BLOCKS["egg"]))


if __name__ == "__main__":
    unittest.main()
