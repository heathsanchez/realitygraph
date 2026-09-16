import unittest

from pvsnp_developmental_closure_v1 import run_qualification
from realitygraph.fixtures.circuit_support_growth import (
    enumerate_available_states,
    joint_cost_from_states,
    nand,
    provenance_antichains,
    support_union_cost,
)


class CircuitSupportInvariantTests(unittest.TestCase):
    def test_pairwise_coavailability_is_not_closed(self):
        enumeration = enumerate_available_states(2, 3)
        triple = (0x3, 0x5, 0x7)
        self.assertEqual(
            [
                joint_cost_from_states(enumeration, pair)
                for pair in ((0x3, 0x5), (0x3, 0x7), (0x5, 0x7))
            ],
            [2, 2, 2],
        )
        self.assertEqual(joint_cost_from_states(enumeration, triple), 3)

    def test_support_antichains_factor_joint_availability(self):
        enumeration = enumerate_available_states(3, 4)
        supports = provenance_antichains(3, 4)
        functions = sorted(enumeration.min_size)
        for left_index, left in enumerate(functions):
            for right in functions[left_index:]:
                exact = joint_cost_from_states(enumeration, (left, right))
                factored = support_union_cost((left, right), supports)
                self.assertEqual(factored is not None and factored <= 4, exact is not None)
                if exact is not None:
                    self.assertEqual(factored, exact)

    def test_xor_lower_bound_is_derived_without_joint_state_lookup(self):
        supports = provenance_antichains(3, 3)
        parents = tuple(
            sorted(
                (left, right)
                for left in supports
                for right in supports
                if left <= right and nand(left, right, 3) == 0x66
            )
        )
        viable = [
            support_union_cost(pair, supports)
            for pair in parents
            if support_union_cost(pair, supports) is not None
        ]
        self.assertEqual(min(viable), 3)

    def test_three_generation_qualification_is_exact_and_bounded(self):
        summary = run_qualification(write_result=False)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["classification"], "FINITE_SIGNAL")
        self.assertEqual(summary["g1"]["route"], "COMPILED")
        self.assertEqual(summary["g2"]["route"], "COMPILED")
        self.assertEqual(summary["g3"]["route"], "COMPILED")
        self.assertEqual(summary["g1"]["xor_costs"], [3, 4])
        self.assertEqual(summary["g2"]["pair_costs"], [2, 2, 2])
        self.assertEqual(summary["g2"]["triple_cost"], 3)
        self.assertTrue(summary["g2"]["support_factorization_exact"])
        self.assertEqual(summary["g2"]["triple_checks"], 17296)
        self.assertEqual(summary["g2"]["unavailable_triples_certified"], 16303)
        self.assertEqual(summary["g2"]["triple_classification_errors"], 0)
        self.assertTrue(summary["g2"]["n4_fixed_point_matches_states"])
        self.assertEqual(summary["g3"]["future_enumeration_calls"], 0)
        self.assertEqual(summary["g3"]["future_answer"], 6)
        self.assertFalse(summary["g3"]["future_preloaded"])
        self.assertFalse(summary["g3"]["future_oracle_attacked"])
        self.assertTrue(summary["g3"]["pre_g3_is_unknown"])
        self.assertTrue(summary["g3"]["semantic_ablation_blocks_future"])
        self.assertTrue(summary["g3"]["g3_ablation_blocks_future"])
        self.assertTrue(summary["g3"]["independent_future_oracle_agrees"])
        self.assertTrue(summary["gates"]["g3_depends_on_g2"])
        self.assertTrue(summary["gates"]["g2_ablation_invalidates_g3"])
        self.assertFalse(summary["claims"]["asymptotic_lower_bound"])
        self.assertFalse(summary["claims"]["barrier_escape"])


if __name__ == "__main__":
    unittest.main()
