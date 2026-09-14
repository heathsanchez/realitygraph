import random
import tempfile
import unittest
from pathlib import Path

from realitygraph import Event, Field, Kernel, Law, Ledger, MG
from realitygraph.eca import (
    HiddenECA,
    all_rows,
    all_rules,
    compile_probe,
    compile_rule,
    probe_from_memory,
    rule_from_memory,
    step,
)
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

    def test_one_collision_identifies_world_law_and_transfers(self):
        hidden = HiddenECA(110)
        field = Field(all_rules())
        actions = all_rows(8)

        probe = field.choose(actions, step)
        self.assertEqual(probe.outcome_classes, 256)
        self.assertEqual(probe.largest_class, 1)
        self.assertEqual(probe.expected_survivors, 1.0)

        observed = hidden.observe(probe.action)
        collision = field.collide(probe.action, observed, step)

        self.assertEqual(collision.before, 256)
        self.assertEqual(collision.after, 1)
        self.assertTrue(field.resolved())
        self.assertEqual(field.hypotheses[0], 110)
        self.assertEqual(hidden.interactions, 1)

        memory = MG(verifier="eca_step")
        ledger = Ledger()
        compile_probe(probe.action, ledger, memory, kernel_id="field-test")
        compile_rule(
            field.hypotheses[0],
            probe.action,
            observed,
            ledger,
            memory,
            world_scope="world-A",
            kernel_id="field-test",
        )

        rng = random.Random(20260915)
        heldout = tuple(rng.randrange(2) for _ in range(64))
        predicted = step(rule_from_memory(memory, "world-A"), heldout)
        self.assertTrue(hidden.verify_heldout(heldout, predicted))
        self.assertEqual(hidden.interactions, 1)

    def test_learned_probe_compounds_across_new_world(self):
        memory = MG(verifier="eca_step")
        ledger = Ledger()

        first_field = Field(all_rules())
        actions = all_rows(8)
        probe = first_field.choose(actions, step)
        compile_probe(probe.action, ledger, memory, kernel_id="world-A")

        second_world = HiddenECA(30)
        second_field = Field(all_rules())
        inherited_probe = probe_from_memory(memory)

        self.assertEqual(inherited_probe, probe.action)

        observed = second_world.observe(inherited_probe)
        collision = second_field.collide(inherited_probe, observed, step)

        self.assertEqual(collision.before, 256)
        self.assertEqual(collision.after, 1)
        self.assertEqual(second_field.hypotheses[0], 30)
        self.assertEqual(second_world.interactions, 1)

        cold_identification_predictions = len(actions) * 256 + 256
        warm_identification_predictions = 256
        self.assertEqual(cold_identification_predictions // warm_identification_predictions, 257)

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
