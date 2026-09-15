import unittest

from realitygraph.meta_policy import (
    MetaSearchPolicy,
    policy_memory,
)
from realitygraph.recursive_policy import (
    BUDGET_FEATURE_NAMES,
    TRUST_FEATURE_NAMES,
    RecursiveSearchPolicy,
    recursive_from_memory,
    recursive_memory,
)


class RecursivePolicyTests(unittest.TestCase):
    def test_round_trip_and_parent_replacement(self):
        base = MetaSearchPolicy(
            ("d0", "d1"),
            (0.0, 0.0),
            (1.0, 1.0),
            (1.0, -1.0),
            5,
            100,
            "digest",
        )
        parent = policy_memory(
            base,
            "base",
        )
        policy = RecursiveSearchPolicy(
            ("d0", "d1"),
            (0.0, 0.0),
            (1.0, 1.0),
            (0.5, 0.25),
            0.5,
            BUDGET_FEATURE_NAMES,
            (0.0,)
            * len(BUDGET_FEATURE_NAMES),
            (1.0,)
            * len(BUDGET_FEATURE_NAMES),
            (0.0,)
            * len(BUDGET_FEATURE_NAMES),
            1.2,
            0.75,
            5,
            TRUST_FEATURE_NAMES,
            (0.0,)
            * len(TRUST_FEATURE_NAMES),
            (1.0,)
            * len(TRUST_FEATURE_NAMES),
            (0.0,)
            * len(TRUST_FEATURE_NAMES),
            0.8,
            0.4,
            20,
            1,
            "parent",
        )

        memory = recursive_memory(
            parent,
            policy,
            "g1",
        )
        restored = recursive_from_memory(
            memory
        )
        self.assertEqual(
            restored,
            policy,
        )
        self.assertEqual(
            restored.choose_budget(
                (0.0,)
                * len(BUDGET_FEATURE_NAMES)
            ),
            2,
        )
        self.assertAlmostEqual(
            restored.trust_score(
                (0.0,)
                * len(TRUST_FEATURE_NAMES)
            ),
            0.8,
        )

        next_policy = RecursiveSearchPolicy(
            **{
                **policy.__dict__,
                "generation": 2,
                "training_worlds": 40,
                "parent_sha256":
                    "next-parent",
            }
        )
        replaced = recursive_memory(
            memory,
            next_policy,
            "g2",
        )
        self.assertEqual(
            len([
                law
                for law
                in replaced.laws.values()
                if law.id
                == "recursive-search-policy"
            ]),
            1,
        )
        self.assertEqual(
            recursive_from_memory(
                replaced
            ).generation,
            2,
        )


if __name__ == "__main__":
    unittest.main()
