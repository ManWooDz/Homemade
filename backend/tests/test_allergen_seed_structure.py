import unittest
from collections import defaultdict

from sqlalchemy import func, select

from allergen_kg.fixtures import make_memory_db
from allergen_kg.floor import ALLERGEN_MAP, FLOOR_BLOCKS
from allergen_kg.graph import ALLERGEN_NODE_PREFIX, allergen_node_name, get_allergen_closure
from allergen_kg.match import head_contains_other_terms
from database.models import AllergenEdge, IngredientNode
from database.seed_allergen_graph import EDGES, seed_allergen_graph


class SeedStructureTests(unittest.TestCase):
    def setUp(self):
        self.db = make_memory_db()
        seed_allergen_graph(self.db)

    def tearDown(self):
        self.db.close()

    def _closure(self, key):
        return get_allergen_closure(self.db, key)

    def test_floor_parity_every_floor_term_is_a_one_hop_edge(self):
        for key, terms in FLOOR_BLOCKS.items():
            one_hop = {e.name for e in self._closure(key) if len(e.path) == 1}
            for term in terms:
                with self.subTest(key=key, term=term):
                    self.assertIn(term, one_hop)

    def test_every_allergen_target_is_a_known_key_and_no_allergen_source(self):
        for source, target, _citation in EDGES:
            with self.subTest(edge=(source, target)):
                self.assertFalse(source.startswith(ALLERGEN_NODE_PREFIX))
                if target.startswith(ALLERGEN_NODE_PREFIX):
                    self.assertIn(target[len(ALLERGEN_NODE_PREFIX):], ALLERGEN_MAP)

    def test_every_edge_has_a_citation(self):
        for source, target, citation in EDGES:
            with self.subTest(edge=(source, target)):
                self.assertTrue(citation and citation.strip())

    def test_no_empty_or_whitespace_node_names(self):
        # An empty term is a substring of every string and would block every recipe.
        for (name,) in self.db.execute(select(IngredientNode.name)).all():
            with self.subTest(name=repr(name)):
                self.assertTrue(name.strip())
                self.assertEqual(name, name.strip())

    def test_no_cycles(self):
        graph = defaultdict(list)
        for source, target, _ in EDGES:
            graph[source].append(target)
        state = {}

        def visit(node):
            state[node] = "active"
            for nxt in graph[node]:
                if state.get(nxt) == "active":
                    self.fail(f"cycle through {node} -> {nxt}")
                if nxt not in state:
                    visit(nxt)
            state[node] = "done"

        for node in list(graph):
            if node not in state:
                visit(node)

    def test_idempotent(self):
        before = self.db.scalar(select(func.count()).select_from(AllergenEdge))
        again = seed_allergen_graph(self.db)
        self.assertEqual(again, {"nodes_added": 0, "edges_added": 0})
        self.assertEqual(self.db.scalar(select(func.count()).select_from(AllergenEdge)), before)

    def test_all_nine_allergen_nodes_exist(self):
        names = set(self.db.scalars(select(IngredientNode.name).where(IngredientNode.node_type == "allergen")))
        self.assertEqual(names, {allergen_node_name(k) for k in ALLERGEN_MAP})

    def test_at_least_one_non_redundant_chain_of_two_or_more_hops(self):
        found = []
        for key in ALLERGEN_MAP:
            closure = self._closure(key)
            all_terms = sorted(set(FLOOR_BLOCKS[key]) | {e.name for e in closure})
            for entry in closure:
                if len(entry.path) >= 2 and not head_contains_other_terms(entry.name, all_terms):
                    found.append((key, entry.path))
        self.assertTrue(found, "no genuine multi-hop chain: every >=2-hop head already contains a shorter term")

    def test_redundant_chain_is_detected_as_redundant(self):
        # Guard on the direction of the non-redundancy check (synthetic names).
        self.assertEqual(head_contains_other_terms("alpha soup", ["alpha", "shrimp"]), ["alpha"])


if __name__ == "__main__":
    unittest.main()
