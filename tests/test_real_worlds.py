import unittest

from realitygraph import Ledger, MG
from realitygraph.lab import (
    HiddenFiniteWorld,
    batch_from_memory,
    compile_identifier,
    compile_plan,
    design_separating_batch,
    identify,
    retain_batch,
)
from realitygraph.real_worlds import real_world_suite


class RealWorldMechanismTests(unittest.TestCase):
    def test_dozen_plus_categories_and_dozen_plus_mechanisms(self):
        families = real_world_suite()
        self.assertGreaterEqual(len(families), 40)
        self.assertGreaterEqual(len({f.category for f in families}), 10)
        self.assertGreaterEqual(len({f.mechanism for f in families}), 10)

    def test_every_family_separates_compiles_without_recompute_and_verifies(self):
        for family in real_world_suite():
            with self.subTest(family=family.report_name):
                calls = [0]

                def counted(h, a):
                    calls[0] += 1
                    return family.predict(h, a)

                plan = design_separating_batch(
                    family.hypotheses,
                    family.actions,
                    counted,
                )
                expected = len(family.hypotheses) * len(family.actions)
                self.assertEqual(calls[0], expected)
                self.assertEqual(plan.design_predictions, expected)
                self.assertEqual(
                    plan.class_progress[-1],
                    len(family.hypotheses),
                )

                before_compile = calls[0]
                compiled = compile_plan(family.scope, plan)
                self.assertEqual(compiled.compile_predictions, 0)
                self.assertEqual(calls[0], before_compile)

                hidden = family.hypotheses[len(family.hypotheses) // 2]
                world = HiddenFiniteWorld(hidden, family.predict)
                learned = identify(world, compiled)
                self.assertEqual(learned, hidden)
                self.assertEqual(world.rounds, 1)
                self.assertTrue(world.verify(learned, family.actions))

    def test_retained_batches_are_irreducible(self):
        # Stronger than merely separating: no retained probe is individually
        # redundant after backward minimization.
        for family in real_world_suite():
            plan = design_separating_batch(
                family.hypotheses,
                family.actions,
                family.predict,
            )
            if len(plan.actions) <= 1:
                continue
            for i in range(len(plan.actions)):
                trial = plan.actions[:i] + plan.actions[i + 1 :]
                signatures = {
                    tuple(family.predict(h, a) for a in trial)
                    for h in family.hypotheses
                }
                self.assertLess(
                    len(signatures),
                    len(family.hypotheses),
                    msg=f"{family.report_name}: action {i} was redundant",
                )

    def test_mg_restart_rebuilds_all_families_exactly(self):
        memory = MG(verifier="finite-mechanism-exact")
        ledger = Ledger()

        for family in real_world_suite():
            plan = design_separating_batch(
                family.hypotheses,
                family.actions,
                family.predict,
            )
            compiled = compile_plan(family.scope, plan)
            retain_batch(compiled, ledger, memory, kernel_id="test")

        self.assertEqual(len(ledger.events), len(real_world_suite()))

        for family in real_world_suite():
            batch = batch_from_memory(memory, family.scope)
            rebuilt = compile_identifier(
                family.scope,
                family.hypotheses,
                batch,
                family.predict,
            )
            hidden = family.hypotheses[-1]
            world = HiddenFiniteWorld(hidden, family.predict)
            self.assertEqual(identify(world, rebuilt), hidden)
            self.assertTrue(world.verify(hidden, family.actions))


if __name__ == "__main__":
    unittest.main()
