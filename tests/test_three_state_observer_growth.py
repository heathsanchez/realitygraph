import unittest

from realitygraph.developmental_executor import execute_generation
from realitygraph.fixtures.generation_specs_v2 import (
    initial_v2_state,
    make_g1_spec,
    make_g2_spec,
)
from realitygraph.fixtures.three_state_observer_growth import (
    SEQUENCE_CARRIER,
    TARGET_SIGNATURE,
    enumerate_three_state_candidates,
    enumerate_two_state_denotations,
    target_contains_11,
)


def seeded_g2_result():
    state0 = initial_v2_state()
    result1 = execute_generation(state0, make_g1_spec())
    result2 = execute_generation(result1.state, make_g2_spec(result1.state))
    return result2


class ThreeStateObserverGrowthTests(unittest.TestCase):
    def test_sequence_carrier_is_complete_through_length_four(self):
        self.assertEqual(len(SEQUENCE_CARRIER), 31)
        self.assertEqual(SEQUENCE_CARRIER[0], "")
        self.assertEqual(target_contains_11(""), "0")
        self.assertEqual(target_contains_11("1010"), "0")
        self.assertEqual(target_contains_11("0011"), "1")
        self.assertEqual(
            TARGET_SIGNATURE,
            "".join(
                target_contains_11(sequence)
                for sequence in sorted(SEQUENCE_CARRIER)
            ),
        )

    def test_two_state_language_is_complete_and_cannot_realize_target(self):
        result2 = seeded_g2_result()
        enumeration = enumerate_two_state_denotations(result2.capability)
        self.assertEqual(enumeration.raw_machine_count, 64)
        self.assertTrue(enumeration.complete)
        self.assertNotIn(TARGET_SIGNATURE, enumeration.semantic_signatures)

    def test_three_state_space_contains_a_verified_target_candidate(self):
        result2 = seeded_g2_result()
        enumeration = enumerate_three_state_candidates(result2.capability)
        self.assertEqual(enumeration.raw_machine_count, 5832)
        self.assertTrue(enumeration.complete)
        matching = [
            constructor
            for constructor in enumeration.constructors
            if constructor.semantic_signature == TARGET_SIGNATURE
        ]
        self.assertTrue(matching)
        self.assertTrue(
            all(
                result2.capability.capability_id in constructor.dependencies
                for constructor in matching
            )
        )


if __name__ == "__main__":
    unittest.main()
