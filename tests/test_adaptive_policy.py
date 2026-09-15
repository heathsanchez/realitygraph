import unittest

from realitygraph.adaptive_policy import (
    FEATURE_NAMES,
    MetaBudgetPolicy,
    adaptive_memory,
    budget_from_memory,
)
from realitygraph.meta_policy import (
    MetaSearchPolicy,
    policy_memory,
    policy_from_memory,
)


class AdaptivePolicyTests(unittest.TestCase):
    def test_budget_round_trip_and_composite_memory(self):
        base = MetaSearchPolicy(
            ("d0", "d1"),
            (0.0, 0.0),
            (1.0, 1.0),
            (1.0, -1.0),
            5,
            100,
            "digest",
        )
        base_memory = policy_memory(base, "base")
        budget = MetaBudgetPolicy(
            FEATURE_NAMES,
            (0.0,) * len(FEATURE_NAMES),
            (1.0,) * len(FEATURE_NAMES),
            (0.0,) * len(FEATURE_NAMES),
            1.2,
            0.75,
            5,
            100,
            "abc",
        )
        memory = adaptive_memory(base_memory, budget, "budget")

        self.assertEqual(policy_from_memory(memory), base)
        restored = budget_from_memory(memory)
        self.assertEqual(restored, budget)
        self.assertEqual(
            restored.choose_budget((0.0,) * len(FEATURE_NAMES)),
            2,
        )


if __name__ == "__main__":
    unittest.main()
