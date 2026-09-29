# backend/tests/test_allergen_kg_graph.py
import unittest

from allergen_kg.fixtures import add_edges, make_memory_db
from allergen_kg.graph import ClosureEntry, allergen_node_name, get_allergen_closure


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.db = make_memory_db()

    def tearDown(self):
        self.db.close()

    def test_missing_allergen_node_returns_empty(self):
        add_edges(self.db, [("alpha", allergen_node_name("shrimp"))])
        self.assertEqual(get_allergen_closure(self.db, "milk"), [])

    def test_one_hop(self):
        add_edges(self.db, [("alpha", "allergen:shrimp")])
        self.assertEqual(get_allergen_closure(self.db, "shrimp"), [ClosureEntry("alpha", ("alpha",))])

    def test_three_hop_chain_path_order_head_first(self):
        add_edges(self.db, [
            ("alpha", "allergen:shrimp"),
            ("beta", "alpha"),
            ("gamma", "beta"),
        ])
        closure = {e.name: e.path for e in get_allergen_closure(self.db, "shrimp")}
        self.assertEqual(closure, {
            "alpha": ("alpha",),
            "beta": ("beta", "alpha"),
            "gamma": ("gamma", "beta", "alpha"),
        })

    def test_shortest_path_wins_when_two_routes_exist(self):
        add_edges(self.db, [
            ("alpha", "allergen:shrimp"),
            ("beta", "alpha"),
            ("gamma", "beta"),
            ("gamma", "alpha"),
        ])
        closure = {e.name: e.path for e in get_allergen_closure(self.db, "shrimp")}
        self.assertEqual(closure["gamma"], ("gamma", "alpha"))

    def test_cycle_terminates(self):
        # CHECK constraint only blocks self-loops; A->B->A is insertable.
        add_edges(self.db, [
            ("alpha", "allergen:shrimp"),
            ("beta", "alpha"),
            ("alpha", "beta"),
        ])
        names = sorted(e.name for e in get_allergen_closure(self.db, "shrimp"))
        self.assertEqual(names, ["alpha", "beta"])

    def test_max_depth_caps_traversal(self):
        add_edges(self.db, [
            ("n1", "allergen:shrimp"), ("n2", "n1"), ("n3", "n2"), ("n4", "n3"),
        ])
        names = sorted(e.name for e in get_allergen_closure(self.db, "shrimp", max_depth=2))
        self.assertEqual(names, ["n1", "n2"])

    def test_other_allergens_edges_not_included(self):
        add_edges(self.db, [
            ("alpha", "allergen:shrimp"),
            ("beta", "allergen:milk"),
            ("gamma", "beta"),
        ])
        self.assertEqual([e.name for e in get_allergen_closure(self.db, "shrimp")], ["alpha"])

    def test_node_implying_two_allergens_appears_in_both(self):
        add_edges(self.db, [("alpha", "allergen:soy"), ("alpha", "allergen:gluten")])
        self.assertEqual([e.name for e in get_allergen_closure(self.db, "soy")], ["alpha"])
        self.assertEqual([e.name for e in get_allergen_closure(self.db, "gluten")], ["alpha"])


if __name__ == "__main__":
    unittest.main()
