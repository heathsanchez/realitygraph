import unittest

from realitygraph.safe_trajectory_gate import residual_gate


class SafeTrajectoryGateTests(unittest.TestCase):
    def test_invokes_when_residual_wins_stably(self):
        anchor = [0.40, 0.39, 0.41, 0.38, 0.37, 0.42, 0.36, 0.40]
        residual = [0.395, 0.385, 0.405, 0.376, 0.365, 0.415, 0.355, 0.397]
        out = residual_gate(anchor, residual, min_wins=7, min_mean_gain=0.002, max_worst_regret=0.001)
        self.assertTrue(out['invoke'])
        self.assertGreaterEqual(out['wins'], 7)
        self.assertGreater(out['mean_gain'], 0.002)

    def test_refuses_when_gain_is_not_recurrent(self):
        anchor = [0.40] * 8
        residual = [0.38, 0.38, 0.38, 0.38, 0.42, 0.42, 0.42, 0.42]
        out = residual_gate(anchor, residual, min_wins=7, min_mean_gain=0.0005, max_worst_regret=0.002)
        self.assertFalse(out['invoke'])
        self.assertEqual(out['wins'], 4)

    def test_refuses_single_bad_environment_even_with_positive_mean(self):
        anchor = [0.40] * 8
        residual = [0.39, 0.39, 0.39, 0.39, 0.39, 0.39, 0.39, 0.43]
        out = residual_gate(anchor, residual, min_wins=7, min_mean_gain=0.0005, max_worst_regret=0.002)
        self.assertFalse(out['invoke'])
        self.assertLess(out['worst_gain'], -0.002)


if __name__ == '__main__':
    unittest.main()
