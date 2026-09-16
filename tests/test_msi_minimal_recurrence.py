import unittest
import numpy as np

from realitygraph.msi_minimal_recurrence import (
    fit_univariate_offset,
    environment_recurrence,
    robust_median_beta,
    fit_robust_tiny_model,
)
from realitygraph.msi_representation_tournament import logistic_loss_from_logits


class MSIMinimalRecurrenceTests(unittest.TestCase):
    def test_fit_univariate_offset_recovers_positive_signal(self):
        rng = np.random.default_rng(101)
        n = 600
        x = rng.normal(size=n)
        offset = np.zeros(n)
        p = 1.0 / (1.0 + np.exp(-(1.25 * x)))
        y = rng.binomial(1, p)
        beta, gain = fit_univariate_offset(x, y, offset)
        self.assertGreater(beta, 0.5)
        self.assertGreater(gain, 0.0)

    def test_environment_recurrence_prefers_same_direction_feature(self):
        rng = np.random.default_rng(102)
        per_env = 240
        env = np.repeat(np.arange(4), per_env)
        stable = rng.normal(size=len(env))
        flipping = rng.normal(size=len(env))
        signed_flip = flipping * np.where(np.isin(env, [0, 1]), 1.0, -1.0)
        logits = 1.0 * stable + 0.9 * signed_flip
        p = 1.0 / (1.0 + np.exp(-logits))
        y = rng.binomial(1, p)
        X = np.column_stack([stable, flipping])
        stats = environment_recurrence(X, y, np.zeros(len(y)), env, (0, 1, 2, 3))
        self.assertGreater(stats['sign_fraction'][0], stats['sign_fraction'][1])
        self.assertGreater(stats['score'][0], stats['score'][1])
        self.assertGreaterEqual(stats['sign_fraction'][0], 0.75)

    def test_robust_median_beta_ignores_wrong_sign_environment(self):
        betas = np.array([
            [1.0, -0.8],
            [1.2, -1.0],
            [0.9, -0.7],
            [-5.0, 2.0],
        ])
        out = robust_median_beta(betas, min_sign_fraction=0.75)
        self.assertGreater(out[0], 0.0)
        self.assertLess(out[1], 0.0)
        self.assertAlmostEqual(out[0], 1.0, places=6)
        self.assertAlmostEqual(out[1], -0.8, places=6)

    def test_robust_tiny_model_transfers_shared_signal_to_held_environment(self):
        rng = np.random.default_rng(103)
        per_env = 300
        env = np.repeat(np.arange(5), per_env)
        stable = rng.normal(size=len(env))
        noise = rng.normal(size=len(env))
        true_logits = -0.15 + 1.15 * stable
        p = 1.0 / (1.0 + np.exp(-true_logits))
        y = rng.binomial(1, p)
        X = np.column_stack([stable, noise])
        base_logits = np.zeros(len(y))
        model = fit_robust_tiny_model(
            X, y, base_logits, env, (0, 1, 2, 3), min_sign_fraction=0.75
        )
        held = env == 4
        parent = logistic_loss_from_logits(y[held], base_logits[held]).mean()
        fitted = logistic_loss_from_logits(y[held], model['logits'][held]).mean()
        self.assertLess(fitted, parent)
        self.assertGreater(model['beta'][0], 0.0)


if __name__ == '__main__':
    unittest.main()
