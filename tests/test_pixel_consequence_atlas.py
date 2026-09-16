import unittest

import numpy as np

from realitygraph.pixel_consequence_atlas import (
    build_2d_candidate_families,
    coarse_volume_family,
    environment_residual_correlations,
    gather_selected_matrix,
    select_magnitude_candidates,
    select_stable_candidates,
)


class PixelConsequenceAtlasTests(unittest.TestCase):
    def test_2d_families_are_invariant_to_positive_global_scale(self):
        rng = np.random.default_rng(7)
        r = rng.uniform(0.05, 3.0, size=(3, 8, 8))
        x = rng.uniform(0.05, 2.0, size=(3, 8, 8))
        a = build_2d_candidate_families({"R": r, "X": x}, box_sizes=(1,))
        b = build_2d_candidate_families({"R": 11.0 * r, "X": 5.0 * x}, box_sizes=(1,))
        self.assertEqual(set(a), set(b))
        for name in a:
            self.assertTrue(np.allclose(a[name], b[name], atol=1e-10, rtol=1e-10), name)

    def test_bilateral_families_preserve_left_right_asymmetry(self):
        left = np.full((2, 4, 8), 4.0)
        right = np.full((2, 4, 8), 1.0)
        full = np.concatenate([left, np.flip(right, axis=1)], axis=1)
        fam = build_2d_candidate_families({"R": full, "X": full}, box_sizes=(1,))
        self.assertGreater(float(fam["R_s1_left"].mean()), 3.0 * float(fam["R_s1_right"].mean()))
        self.assertTrue(np.all(fam["R_s1_diff"] > 0.0))
        self.assertTrue(np.allclose(fam["R_s1_diff"], fam["R_s1_absdiff"]))

    def test_environment_correlations_are_finite_and_shape_stable(self):
        rng = np.random.default_rng(11)
        field = rng.normal(size=(24, 3, 4))
        env = np.repeat(np.arange(3), 8)
        residual = rng.normal(size=24)
        corr = environment_residual_correlations(field, residual, env, (0, 1, 2))
        self.assertEqual(corr.shape, (3, 12))
        self.assertTrue(np.isfinite(corr).all())

    def test_stable_selector_prefers_recurrent_sign_over_larger_unstable_signal(self):
        associations = {
            "A": np.array([[0.20, 0.90], [0.22, -0.90], [0.18, 0.90]], dtype=float),
        }
        stable = select_stable_candidates(associations, train_env_indices=(0, 1, 2), k=1)
        magnitude = select_magnitude_candidates(associations, train_env_indices=(0, 1, 2), k=1)
        self.assertEqual(stable[0][1], 0)
        self.assertEqual(magnitude[0][1], 1)

    def test_selector_never_reads_excluded_future_environment(self):
        associations = {
            "A": np.array([[0.30, 0.10], [0.31, 0.11], [0.29, 0.12], [0.0, 0.0]], dtype=float),
        }
        first = select_stable_candidates(associations, train_env_indices=(0, 1, 2), k=1)
        changed = {"A": associations["A"].copy()}
        changed["A"][3] = np.array([-1000.0, 1000.0])
        second = select_stable_candidates(changed, train_env_indices=(0, 1, 2), k=1)
        self.assertEqual(first, second)

    def test_gather_selected_matrix_uses_only_named_candidates(self):
        families = {
            "A": np.arange(18, dtype=float).reshape(3, 2, 3),
            "B": (100 + np.arange(18, dtype=float)).reshape(3, 2, 3),
        }
        out = gather_selected_matrix(families, [("A", 4), ("B", 1)])
        self.assertEqual(out.shape, (3, 2))
        self.assertTrue(np.allclose(out[:, 0], families["A"].reshape(3, -1)[:, 4]))
        self.assertTrue(np.allclose(out[:, 1], families["B"].reshape(3, -1)[:, 1]))

    def test_coarse_volume_family_preserves_rows_and_is_scale_invariant(self):
        rng = np.random.default_rng(19)
        v = rng.uniform(0.05, 2.0, size=(2, 8, 8, 8))
        a = coarse_volume_family(v, bins=4)
        b = coarse_volume_family(7.0 * v, bins=4)
        self.assertEqual(a.shape, (2, 4, 4, 4))
        self.assertTrue(np.allclose(a, b, atol=1e-10, rtol=1e-10))


if __name__ == "__main__":
    unittest.main()
