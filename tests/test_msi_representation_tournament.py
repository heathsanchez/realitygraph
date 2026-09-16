import unittest
import numpy as np

from realitygraph.msi_representation_tournament import (
    approximate_univariate_consequence,
    build_structured_feature_bank,
    logistic_loss_from_logits,
    proximal_offset_logistic,
)


class MSIRepresentationTournamentTests(unittest.TestCase):
    def test_structured_bank_is_finite_deterministic_and_multi_family(self):
        rng = np.random.default_rng(7)
        x = rng.normal(size=(6, 8, 8, 8, 8)).astype(np.float32)
        bank1, names1, families1 = build_structured_feature_bank(x, grids=((1,1,1),(2,2,2)))
        bank2, names2, families2 = build_structured_feature_bank(x, grids=((1,1,1),(2,2,2)))
        self.assertEqual(bank1.shape[0], 6)
        self.assertEqual(bank1.shape[1], len(names1))
        self.assertTrue(np.isfinite(bank1).all())
        self.assertEqual(names1, names2)
        self.assertEqual(families1, families2)
        self.assertTrue(np.allclose(bank1, bank2))
        self.assertTrue({'intensity','contrast','spatial','shape_change','distribution'} <= set(families1))

    def test_univariate_consequence_prefers_true_residual_direction(self):
        rng = np.random.default_rng(11)
        n = 400
        env = np.repeat(np.arange(4), n // 4)
        signal = rng.normal(size=n)
        noise = rng.normal(size=n)
        p = 1.0 / (1.0 + np.exp(-(0.15 + 1.2 * signal)))
        y = rng.binomial(1, p)
        base = np.full(n, y.mean())
        X = np.column_stack([signal, noise]).astype(np.float64)
        score, sign_fraction = approximate_univariate_consequence(X, y, base, env, (0,1,2,3))
        self.assertGreater(score[0], score[1])
        self.assertGreaterEqual(sign_fraction[0], 0.75)

    def test_proximal_offset_logistic_improves_fixed_parent(self):
        rng = np.random.default_rng(13)
        n = 500
        x = rng.normal(size=(n, 3))
        base_logits = np.zeros(n)
        truth = 1.4 * x[:, 0] - 0.8 * x[:, 1]
        p = 1.0 / (1.0 + np.exp(-truth))
        y = rng.binomial(1, p)
        beta = proximal_offset_logistic(
            x, y, base_logits, l1=0.002, l2=0.01, max_iter=250
        )
        parent = logistic_loss_from_logits(y, base_logits).mean()
        fitted = logistic_loss_from_logits(y, base_logits + x @ beta).mean()
        self.assertLess(fitted, parent)
        self.assertGreater(np.count_nonzero(np.abs(beta) > 1e-5), 0)


if __name__ == '__main__':
    unittest.main()
