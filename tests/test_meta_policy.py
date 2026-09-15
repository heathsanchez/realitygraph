import unittest

from realitygraph.meta_policy import (
    MetaSearchPolicy,
    fit_ridge_ranker,
    policy_from_memory,
    policy_memory,
)
from realitygraph.mg import MG


class MetaPolicyTests(unittest.TestCase):
    def test_ranker_learns_direction(self):
        examples = [(0.0, 1.0), (1.0, 0.0), (2.0, 0.0), (3.0, 1.0)]
        targets = [0.0, 1.0, 2.0, 3.0]
        means, scales, weights = fit_ridge_ranker(examples, targets)
        policy = MetaSearchPolicy(
            ("a", "b"), means, scales, weights, 2, 4, "digest"
        )
        self.assertGreater(policy.score((3.0, 0.0)), policy.score((0.0, 1.0)))

    def test_policy_round_trips_through_mg(self):
        policy = MetaSearchPolicy(
            ("effect", "corr"),
            (0.1, 0.2),
            (1.1, 1.2),
            (2.1, -0.4),
            3,
            100,
            "abc123",
        )
        text = policy_memory(policy, "train100").text()
        restarted = MG.parse(text)
        rebuilt = policy_from_memory(restarted)
        self.assertEqual(rebuilt, policy)


if __name__ == "__main__":
    unittest.main()
