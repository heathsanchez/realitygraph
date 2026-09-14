import tempfile
import unittest
from pathlib import Path

from realitygraph import Event, Kernel, Law, Ledger, MG
from realitygraph.graph_coloring import GraphColoring, odd_wheel_with_leaves


class RealityGraphTests(unittest.TestCase):
    def test_learn_then_reuse_without_repaying_search(self):
        memory = MG(verifier=GraphColoring.verifier_name)
        ledger = Ledger()
        kernel = Kernel(memory, ledger, kernel_id="test")
        domain = GraphColoring()

        a = odd_wheel_with_leaves(7, 6, 20260915, "A")
        first = kernel.solve(domain, a)
        self.assertEqual(first.consequence, "chi=4")
        self.assertGreater(first.search_nodes, 0)
        self.assertFalse(first.reused_memory)
        self.assertIn("ow", memory.laws)
        self.assertIsNotNone(first.ledger_event)
        self.assertEqual(len(ledger.events), 1)

        b = odd_wheel_with_leaves(9, 7, 20260916, "B")
        second = kernel.solve(domain, b)
        self.assertEqual(second.consequence, "chi=4")
        self.assertTrue(second.reused_memory)
        self.assertEqual(second.search_nodes, 0)
        self.assertEqual(len(ledger.events), 1)

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

    def test_ledger_merges_concurrent_edits_without_overwrite(self):
        base = Event.add(Law("x", "base", "s", "seed"), "seed")
        left = Ledger([base])
        right = Ledger([base])

        left.append_add(Law("x", "left", "s", "left"), "K-left", parents=[base.id])
        right.append_add(Law("x", "right", "s", "right"), "K-right", parents=[base.id])

        merged = left.merge(right)
        present = merged.materialize("v")

        self.assertEqual(len(present.laws), 2)
        self.assertEqual(
            {law.expr for law in present.laws.values()},
            {"left", "right"},
        )
        self.assertEqual(merged.digest(), right.merge(left).digest())

    def test_revoke_only_kills_versions_it_causally_observed(self):
        base = Event.add(Law("x", "base", "s", "seed"), "seed")

        revoke_branch = Ledger([base])
        revoke_branch.append_revoke("x", "K-revoke", "bad here", parents=[base.id])

        edit_branch = Ledger([base])
        newer = edit_branch.append_add(
            Law("x", "concurrent-new", "s", "new"),
            "K-edit",
            parents=[base.id],
        )

        merged = revoke_branch.merge(edit_branch)
        present = merged.materialize("v")
        self.assertEqual([law.expr for law in present.laws.values()], ["concurrent-new"])

        merged.append_revoke("x", "K-later", "now observed", parents=[newer.id])
        self.assertEqual(merged.materialize("v").laws, {})


if __name__ == "__main__":
    unittest.main()
