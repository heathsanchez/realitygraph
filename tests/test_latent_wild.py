import unittest

import numpy as np

from realitygraph.latent_wild import (
    apply_two_stream_stack,
    fit_two_stream_stack,
    loeo_latent_predictions,
)


class LatentWildTests(unittest.TestCase):
    def test_fold_local_transform_never_sees_held_environment(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(30, 12))
        y = np.array([0, 1] * 15)
        env = np.repeat(np.arange(3), 10)
        result = loeo_latent_predictions(
            X, y, env, pca_dim=4, learner="logistic", C=0.1, audit=True
        )
        self.assertEqual(result["folds"], 3)
        for row in result["audit"]:
            held = row["held"]
            self.assertNotIn(held, row["fit_envs"])
            self.assertEqual(set(row["fit_envs"]), set(np.unique(env)) - {held})
        self.assertEqual(result["predictions"].shape, (30,))
        self.assertTrue(np.isfinite(result["predictions"]).all())

    def test_prototype_predictions_are_probabilities(self):
        rng = np.random.default_rng(2)
        X = rng.normal(size=(40, 10))
        y = np.array([0] * 20 + [1] * 20)
        env = np.repeat(np.arange(4), 10)
        result = loeo_latent_predictions(
            X, y, env, pca_dim=4, learner="prototype", C=1.0
        )
        p = result["predictions"]
        self.assertTrue(((p > 0.0) & (p < 1.0)).all())

    def test_two_stream_stack_reduces_to_finite_probability(self):
        y = np.array([0, 0, 1, 1, 0, 1], dtype=float)
        v6 = np.array([0.1, 0.2, 0.8, 0.7, 0.3, 0.6])
        latent = np.array([0.2, 0.3, 0.7, 0.9, 0.4, 0.8])
        model = fit_two_stream_stack(v6, latent, y, ridge=0.01)
        p = apply_two_stream_stack(model, v6, latent)
        self.assertEqual(p.shape, y.shape)
        self.assertTrue(((p > 0.0) & (p < 1.0)).all())
        self.assertTrue(np.isfinite(p).all())


if __name__ == "__main__":
    unittest.main()
