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

    def test_nonempty_partial_graph_is_not_ready_for_declared_allergy(self):
        from allergen_kg.resolve import allergy_blocks_ready

        add_edges(self.db, [("crab", "allergen:shellfish")])
        preferences = {"allergies": "shellfish"}
        resolved = resolve_allergy_blocks(self.db, preferences)
        self.assertEqual(resolved["shellfish"].graph_status, "ok")
        self.assertFalse(allergy_blocks_ready(preferences, resolved))

    def test_seeded_graph_is_ready_for_each_of_the_ten_declared_keys(self):
        from allergen_kg.resolve import allergy_blocks_ready
        from database.seed_allergen_graph import seed_allergen_graph

        seed_allergen_graph(self.db)
        for key in ("shrimp", "peanut", "milk", "egg", "gluten", "shellfish", "fish", "soy", "nut", "sesame"):
            with self.subTest(key=key):
                preferences = {"allergies": "ถั่วเปลือกแข็ง" if key == "nut" else key}
                self.assertTrue(allergy_blocks_ready(preferences, resolve_allergy_blocks(self.db, preferences)))

    def test_known_missing_term_or_floor_provenance_does_not_establish_readiness(self):
        from allergen_kg.resolve import ResolvedAllergen, allergy_blocks_ready
        from database.seed_allergen_graph import seed_allergen_graph

        seed_allergen_graph(self.db)
        preferences = {"allergies": "sesame"}
        resolved = resolve_allergy_blocks(self.db, preferences)
        for replacement in (None, TermInfo("floor", None)):
            with self.subTest(replacement=replacement):
                terms = dict(resolved["sesame"].terms)
                if replacement is None:
                    terms.pop("tahini")
                else:
                    terms["tahini"] = replacement
                self.assertFalse(allergy_blocks_ready(preferences, {"sesame": ResolvedAllergen(terms, "ok")}))

    def test_every_declared_key_must_be_present_and_ready(self):
        from allergen_kg.resolve import allergy_blocks_ready
        from database.seed_allergen_graph import seed_allergen_graph

        seed_allergen_graph(self.db)
        sesame = resolve_allergy_blocks(self.db, {"allergies": "sesame"})
        self.assertFalse(allergy_blocks_ready({"allergies": "sesame, milk"}, sesame))
        self.assertFalse(allergy_blocks_ready({"allergies": "sesame"}, None))
        self.assertFalse(allergy_blocks_ready({"allergies": "ลดแป้ง"}, sesame))

    def test_extra_terms_and_equivalent_path_do_not_fail_readiness(self):
        from allergen_kg.resolve import ResolvedAllergen, allergy_blocks_ready
        from database.seed_allergen_graph import seed_allergen_graph

        seed_allergen_graph(self.db)
        preferences = {"allergies": "sesame"}
        resolved = resolve_allergy_blocks(self.db, preferences)["sesame"]
        terms = dict(resolved.terms)
        terms["tahini"] = TermInfo("kg", ("tahini",))
        terms["test sesame condiment"] = TermInfo("kg", ("test sesame condiment", "เมล็ดงา"))
        self.assertTrue(allergy_blocks_ready(preferences, {"sesame": ResolvedAllergen(terms, "ok")}))

    def test_no_declared_allergy_does_not_require_a_graph(self):
        from allergen_kg.resolve import allergy_blocks_ready

        for preferences in ({}, {"allergies": "ไม่มีอาการแพ้"}, {"allergy": ""}):
            with self.subTest(preferences=preferences):
                self.assertTrue(allergy_blocks_ready(preferences, None))

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

    def test_first_query_failure_skips_db_for_remaining_keys(self):
        with patch("allergen_kg.resolve.get_allergen_closure", side_effect=RuntimeError("db down")) as closure:
            with self.assertLogs("allergen_kg", level="ERROR"):
                resolved = resolve_blocks_for_keys(self.db, ["shrimp", "milk"])
        self.assertEqual(closure.call_count, 1)
        for key in ("shrimp", "milk"):
            self.assertEqual(resolved[key].graph_status, "unavailable")
            self.assertEqual(set(resolved[key].terms), set(FLOOR_BLOCKS[key]))
            self.assertTrue(all(t.matched_via == "floor" for t in resolved[key].terms.values()))

    def test_failing_rollback_logs_warning_and_does_not_raise(self):
        with patch("allergen_kg.resolve.get_allergen_closure", side_effect=RuntimeError("db down")),                 patch.object(self.db, "rollback", side_effect=RuntimeError("rollback broke")):
            with self.assertLogs("allergen_kg", level="WARNING") as logs:
                resolved = resolve_blocks_for_keys(self.db, ["milk"])
        self.assertEqual(resolved["milk"].graph_status, "unavailable")
        self.assertTrue(any("rollback" in line.lower() for line in logs.output))

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
