import unittest

from realitygraph import Ledger, MG
from realitygraph.lab import (
    HiddenFiniteWorld,
    batch_from_memory,
    compile_identifier,
    design_separating_batch,
    identify,
    retain_batch,
)
from realitygraph.meta_worlds import (
    affine_binary,
    affine_mod,
    eca8,
    lookup_bits,
    quadratic_mod,
)


class MetaWorldTests(unittest.TestCase):
    def test_generic_batch_sizes_and_exact_identification(self):
        cases = [
            (lookup_bits(12), 12, 49152),
            (affine_binary(7), 8, 32768),
            (affine_mod(17), 2, 4913),
            (eca8(), 1, 65536),
            (quadratic_mod(7), 3, 2401),
        ]

        for family, expected_batch, expected_design in cases:
            with self.subTest(family=family.report_name):
                plan = design_separating_batch(
                    family.hypotheses,
                    family.actions,
                    family.predict,
                )
                self.assertEqual(len(plan.actions), expected_batch)
                self.assertEqual(plan.design_predictions, expected_design)
                self.assertEqual(plan.class_progress[-1], len(family.hypotheses))

                compiled = compile_identifier(
                    family.scope,
                    family.hypotheses,
                    plan.actions,
                    family.predict,
                )
                hidden = family.hypotheses[len(family.hypotheses) // 3]
                world = HiddenFiniteWorld(hidden, family.predict)
                learned = identify(world, compiled)

                self.assertEqual(learned, hidden)
                self.assertEqual(world.rounds, 1)
                self.assertEqual(world.actions_spent, expected_batch)
                self.assertTrue(world.verify(learned, family.actions))

    def test_counterfactual_field_is_paid_for_once(self):
        family = affine_binary(7)
        calls = [0]

        def counted(hypothesis, action):
            calls[0] += 1
            return family.predict(hypothesis, action)

        plan = design_separating_batch(
            family.hypotheses,
            family.actions,
            counted,
        )

        full_field = len(family.hypotheses) * len(family.actions)
        self.assertEqual(calls[0], full_field)
        self.assertEqual(plan.design_predictions, full_field)
        self.assertEqual(len(plan.actions), 8)

    def test_keep_rebuild_and_ablation(self):
        family = affine_binary(7)
        memory = MG(verifier="finite-model-family")
        ledger = Ledger()

        cold = design_separating_batch(
            family.hypotheses,
            family.actions,
            family.predict,
        )
        compiled = compile_identifier(
            family.scope,
            family.hypotheses,
            cold.actions,
            family.predict,
        )
        retain_batch(compiled, ledger, memory, kernel_id="test")

        retained = batch_from_memory(memory, family.scope)
        rebuilt = compile_identifier(
            family.scope,
            tuple(reversed(family.hypotheses)),
            retained,
            family.predict,
        )

        self.assertEqual(retained, cold.actions)
        self.assertEqual(rebuilt.compile_predictions, 2048)
        self.assertGreater(cold.design_predictions, rebuilt.compile_predictions)
        self.assertEqual(len(ledger.events), 1)

        ablated = design_separating_batch(
            tuple(reversed(family.hypotheses)),
            tuple(reversed(family.actions)),
            family.predict,
        )
        self.assertEqual(ablated.design_predictions, cold.design_predictions)

    def test_heldout_family_is_not_needed_by_generic_designer(self):
        heldout = quadratic_mod(7)
        memory = MG(verifier="finite-model-family")

        with self.assertRaises(ValueError):
            batch_from_memory(memory, heldout.scope)

        plan = design_separating_batch(
            tuple(reversed(heldout.hypotheses)),
            tuple(reversed(heldout.actions)),
            heldout.predict,
        )
        compiled = compile_identifier(
            heldout.scope,
            heldout.hypotheses,
            plan.actions,
            heldout.predict,
        )

        world = HiddenFiniteWorld(heldout.hypotheses[211], heldout.predict)
        learned = identify(world, compiled)

        self.assertEqual(len(plan.actions), 3)
        self.assertEqual(plan.design_predictions, 2401)
        self.assertEqual(world.rounds, 1)
        self.assertTrue(world.verify(learned, heldout.actions))


if __name__ == "__main__":
    unittest.main()
