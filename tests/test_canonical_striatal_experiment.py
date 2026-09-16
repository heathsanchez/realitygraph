import unittest

from realitygraph.canonical_striatal_experiment import future_consequence


class CanonicalStriatalExperimentTests(unittest.TestCase):
    def test_joint_pass_requires_both_metrics_positive_in_both_futures(self):
        good = future_consequence([0.01, 0.02], [0.003, 0.001], [0.0, 0.0], [0.0, 0.0])
        self.assertTrue(good["aligned_pass"])

        ll_only = future_consequence([0.01, 0.02], [0.003, -0.001], [0.0, 0.0], [0.0, 0.0])
        self.assertFalse(ll_only["aligned_pass"])

    def test_alignment_is_causal_only_when_ablation_loses_protected_consequence(self):
        causal = future_consequence(
            [0.01, 0.02], [0.003, 0.001],
            [0.01, -0.002], [0.002, 0.001],
        )
        self.assertTrue(causal["aligned_pass"])
        self.assertFalse(causal["ablation_pass"])
        self.assertTrue(causal["alignment_causal"])

        redundant = future_consequence(
            [0.01, 0.02], [0.003, 0.001],
            [0.004, 0.003], [0.001, 0.002],
        )
        self.assertTrue(redundant["aligned_pass"])
        self.assertTrue(redundant["ablation_pass"])
        self.assertFalse(redundant["alignment_causal"])


if __name__ == "__main__":
    unittest.main()
