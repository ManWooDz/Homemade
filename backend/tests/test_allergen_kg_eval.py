# backend/tests/test_allergen_kg_eval.py
import json
import unittest

from allergen_kg.fixtures import add_edges, make_memory_db
from allergen_kg.resolve import resolve_blocks_for_keys
from eval.allergen_kg_eval import assert_graph_status, collision_scan, empty_resolver, score_pairs, seeded_resolver
from eval.build_allergen_label_pool import canonical_sha256


class LabelsIntegrityTests(unittest.TestCase):
    def test_labels_match_the_hash_committed_before_the_seed(self):
        labels = json.load(open("eval/fixtures/allergen_kg_labels.json", encoding="utf-8"))
        self.assertEqual(canonical_sha256(labels), open("eval/fixtures/allergen_kg_labels.sha256").read().strip())


class GraphStatusGuardTests(unittest.TestCase):
    def test_seeded_arm_is_ok_for_all_nine_keys(self):
        assert_graph_status(seeded_resolver(), "ok")

    def test_empty_arm_is_empty_for_all_nine_keys(self):
        assert_graph_status(empty_resolver(), "empty")

    def test_guard_raises_on_wrong_status(self):
        with self.assertRaises(RuntimeError):
            assert_graph_status(empty_resolver(), "ok")


class ScorePairsTests(unittest.TestCase):
    ITEMS = [
        {"id": "a", "string": "กุ้งสด 100 กรัม", "allergens": ["shrimp"], "public": False},
        {"id": "b", "string": "หมูสับ 200 กรัม", "allergens": [], "public": False},
    ]

    def test_literal_positive_caught_by_both_arms(self):
        for resolver in (empty_resolver(), seeded_resolver()):
            scores = score_pairs(self.ITEMS, resolver, exclude_public=False)
            self.assertEqual(scores["literal"]["positives"], 1)
            self.assertEqual(scores["literal"]["caught"], 1)
            self.assertEqual(scores["derived_only"]["positives"], 0)
            self.assertEqual(scores["negatives"]["total"], 17)

    def test_floor_only_arm_flags_no_negatives_here(self):
        # Only the empty arm: the seeded arm's negatives depend on seed content
        # this test must not assume.
        scores = score_pairs(self.ITEMS, empty_resolver(), exclude_public=False)
        self.assertEqual(scores["negatives"], {"total": 17, "flagged": 0})

    def test_seeded_resolver_reports_ok_status(self):
        resolved = seeded_resolver()(["shrimp"])
        self.assertEqual(resolved["shrimp"].graph_status, "ok")

    def test_empty_resolver_reports_empty_status(self):
        resolved = empty_resolver()(["shrimp"])
        self.assertEqual(resolved["shrimp"].graph_status, "empty")


def _synthetic_resolver(edges):
    """Tiny in-memory graph over made-up names. Only the 'shrimp' key gets edges;
    every other key resolves to floor-only with status 'empty'."""
    db = make_memory_db()
    add_edges(db, edges)

    def resolve(keys):
        return resolve_blocks_for_keys(db, keys)
    return resolve


class ScorePairsBreakdownTests(unittest.TestCase):
    """New per-key / per-edge / note / floor-false-positive fields, on synthetic names."""

    EDGES = [
        ("alphaparent", "allergen:shrimp"),  # 1 hop
        ("betachild", "alphaparent"),        # 2 hops: betachild -> alphaparent -> shrimp
        ("gammaonly", "allergen:gluten"),    # different key, should not leak into shrimp
    ]
    ITEMS = [
        {"id": "lit", "string": "กุ้งสด", "allergens": ["shrimp"], "public": False},
        {"id": "one_hop", "string": "alphaparent 50 g", "allergens": ["shrimp"], "public": False},
        {"id": "two_hop", "string": "betachild 50 g", "allergens": ["shrimp"], "public": False,
         "note": "spelling variant"},
        {"id": "two_hop_2", "string": "betachild 70 g", "allergens": ["shrimp"], "public": False},
        {"id": "miss", "string": "zzzunknown", "allergens": ["shrimp"], "public": False,
         "note": "misspelled"},
        {"id": "neg", "string": "gammaonly 10 g", "allergens": [], "public": False},
    ]

    def setUp(self):
        self.scores = score_pairs(self.ITEMS, _synthetic_resolver(self.EDGES), exclude_public=False)

    def test_top_level_shape_unchanged(self):
        self.assertEqual(self.scores["literal"], {"positives": 1, "caught": 1, "caught_2plus_hop": 0})
        self.assertEqual(
            self.scores["derived_only"], {"positives": 4, "caught": 3, "caught_2plus_hop": 2})

    def test_by_key_splits_literal_derived_and_negatives(self):
        shrimp = self.scores["by_key"]["shrimp"]
        self.assertEqual(shrimp["literal"], {"positives": 1, "caught": 1})
        self.assertEqual(shrimp["derived_only"], {"positives": 4, "caught": 3, "caught_2plus_hop": 2})
        # 'neg' is a shrimp negative (gammaonly does not imply shrimp) and is not flagged.
        self.assertEqual(shrimp["negatives"], {"total": 1, "flagged": 0})
        gluten = self.scores["by_key"]["gluten"]
        self.assertEqual(gluten["derived_only"]["positives"], 0)
        # 'neg' is a gluten negative that the synthetic gluten edge DOES flag.
        self.assertEqual(gluten["negatives"]["flagged"], 1)
        self.assertEqual(set(self.scores["by_key"]), set(_all_keys()))

    def test_by_key_sums_match_top_level(self):
        for stratum in ("literal", "derived_only"):
            for field in ("positives", "caught"):
                total = sum(v[stratum][field] for v in self.scores["by_key"].values())
                self.assertEqual(total, self.scores[stratum][field])
        self.assertEqual(sum(v["negatives"]["total"] for v in self.scores["by_key"].values()),
                         self.scores["negatives"]["total"])
        self.assertEqual(sum(v["negatives"]["flagged"] for v in self.scores["by_key"].values()),
                         self.scores["negatives"]["flagged"])

    def test_caught_by_head_edge_counts_two_hop_path(self):
        by_edge = self.scores["caught_by_head_edge"]
        self.assertEqual(by_edge["shrimp|betachild -> alphaparent"], 2)
        self.assertEqual(by_edge["shrimp|alphaparent"], 1)
        self.assertEqual(sum(v for k, v in by_edge.items() if k.startswith("shrimp|")), 3)

    def test_spelling_note_items_report_caught_flag(self):
        notes = sorted(self.scores["spelling_note_items"], key=lambda r: r["id"])
        self.assertEqual(notes, [{"id": "miss", "caught": False}, {"id": "two_hop", "caught": True}])

    def test_floor_false_positives_lists_flagged_negatives(self):
        self.assertEqual(self.scores["floor_false_positives"], [{"id": "neg", "key": "gluten"}])

    def test_public_items_excluded_from_new_fields_too(self):
        items = [dict(i, public=True) if i["id"] == "two_hop" else i for i in self.ITEMS]
        scores = score_pairs(items, _synthetic_resolver(self.EDGES), exclude_public=True)
        self.assertEqual(scores["caught_by_head_edge"]["shrimp|betachild -> alphaparent"], 1)
        self.assertEqual([r["id"] for r in scores["spelling_note_items"]], ["miss"])


def _all_keys():
    from allergen_kg.floor import ALLERGEN_MAP
    return ALLERGEN_MAP


class CollisionScanTests(unittest.TestCase):
    def test_no_hits_on_empty_inputs(self):
        self.assertEqual(collision_scan([], []), [])

    def test_kg_only_node_found_in_pool_string_is_reported_with_source(self):
        from allergen_kg.floor import FLOOR_BLOCKS
        from allergen_kg.graph import get_allergen_closure
        floor_terms = {t for terms in FLOOR_BLOCKS.values() for t in terms}
        db = make_memory_db()
        from database.seed_allergen_graph import seed_allergen_graph
        seed_allergen_graph(db)
        entry = next(e for e in get_allergen_closure(db, "gluten") if e.name not in floor_terms)
        hits = collision_scan([], ["prefix " + entry.name + " suffix"])
        matching = [h for h in hits if h["node"] == entry.name and h["allergen"] == "gluten"]
        self.assertTrue(matching)
        self.assertEqual(set(matching[0]), {"node", "allergen", "matched_string", "source"})
        self.assertEqual(matching[0]["source"], "pool")
        hits_inmu = collision_scan(["prefix " + entry.name], [])
        self.assertTrue(any(h["source"] == "inmu" and h["node"] == entry.name for h in hits_inmu))


class RunCaseWiringTests(unittest.TestCase):
    """run_case must pass KG-resolved blocks to the validator only when given a resolver
    (stub generator only -- no network)."""

    CASE = {
        "case_id": "wiring",
        "ingredients": [{"name": "หมูสับ"}],
        "user_prefs": {"allergy": "แพ้กุ้ง", "taste": "", "equipment": "", "extra": ""},
        "base_recipe": {},
    }
    RECIPE = {
        "recipe_name": "test", "servings": 1,
        "adjusted_ingredients": ["หมูสับ 100 กรัม", "กุ้งสด 50 กรัม"],
        "instructions": ["ผัด"], "diet_tags": [], "safety_warning": "-",
        "nutrition": {"basis": "per_serving", "calories": 1, "protein_g": 1, "carbs_g": 1, "fat_g": 1},
    }

    class _Stub:
        def generate(self, ingredients, prefs, base_recipe):
            return dict(RunCaseWiringTests.RECIPE)

    def test_resolver_is_called_with_flagged_keys_and_allergy_is_reported(self):
        from eval.run_benchmark import run_case
        calls, real = [], seeded_resolver()

        def spy(keys):
            calls.append(list(keys))
            return real(keys)

        result = run_case(self._Stub(), self.CASE, spy)
        self.assertEqual(calls, [["shrimp"]])
        self.assertFalse(result["valid"])
        self.assertIn("Allergy violation", result["reason"])

    def test_no_resolver_keeps_legacy_path(self):
        from eval.run_benchmark import run_case
        result = run_case(self._Stub(), self.CASE)
        self.assertIn("Allergy violation", result["reason"])


if __name__ == "__main__":
    unittest.main()
