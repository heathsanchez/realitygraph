import tempfile
import unittest
from pathlib import Path

from realitygraph import Kernel, Law, MG
from realitygraph.graph_coloring import GraphColoring, odd_wheel_with_leaves


class RealityGraphTests(unittest.TestCase):
    def test_learn_then_reuse_without_repaying_search(self):
        memory = MG(verifier=GraphColoring.verifier_name)
        kernel = Kernel(memory)
        domain = GraphColoring()

        a = odd_wheel_with_leaves(7, 6, 20260915, "A")
        first = kernel.solve(domain, a)
        self.assertEqual(first.consequence, "chi=4")
        self.assertGreater(first.search_nodes, 0)
        self.assertFalse(first.reused_memory)
        self.assertIn("ow", memory.laws)

        b = odd_wheel_with_leaves(9, 7, 20260916, "B")
        second = kernel.solve(domain, b)
        self.assertEqual(second.consequence, "chi=4")
        self.assertTrue(second.reused_memory)
        self.assertEqual(second.search_nodes, 0)

    def test_mg_roundtrip_and_merge_preserves_conflict(self):
        a = MG("v", [Law("x", "a->b", "s", "111")])
        b = MG("v", [Law("x", "a->c", "s", "222")])
        merged = a.merge(b)
        self.assertEqual(len(merged.laws), 2)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.mg"
            merged.save(p)
            again = MG.load(p)
            self.assertEqual(again.text(), merged.text())


if __name__ == "__main__":
    unittest.main()
