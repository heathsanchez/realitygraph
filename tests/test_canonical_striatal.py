import unittest

import numpy as np

from realitygraph.canonical_striatal import (
    canonical_striatal_features,
    unaligned_striatal_features,
)


def synthetic_pair(*, angle=0.0, row_shift=0.0, col_shift=0.0, scale=1.0,
                   left_amp=1.0, right_amp=1.0):
    h, w = 32, 64
    rr, cc = np.meshgrid(np.arange(h, dtype=float), np.arange(w, dtype=float), indexing="ij")
    cr = 15.5 + float(row_shift)
    cw = 31.5 + float(col_shift)

    # Longitudinal axis is anchored to the acquisition column direction.
    major = np.array([np.sin(angle), np.cos(angle)])
    minor = np.array([major[1], -major[0]])
    dr = rr - cr
    dc = cc - cw
    longitudinal = dr * major[0] + dc * major[1]
    transverse = dr * minor[0] + dc * minor[1]

    # Two smooth components give a comma-like elongated uptake field.
    putamen = np.exp(-0.5 * ((longitudinal / 10.0) ** 2 + (transverse / 2.8) ** 2))
    caudate = 0.55 * np.exp(
        -0.5 * (((longitudinal + 10.0) / 4.0) ** 2 + ((transverse - 1.5) / 4.5) ** 2)
    )
    side = putamen + caudate

    left = float(left_amp) * side
    # The production representation mirrors the right half into the same local
    # anatomical orientation before estimating a shared subject transform.
    right_original = np.flip(float(right_amp) * side, axis=0)
    full = np.concatenate([left, right_original], axis=0)
    return float(scale) * full


class CanonicalStriatalTests(unittest.TestCase):
    def test_output_is_finite_fixed_64_feature_field(self):
        maps = np.stack([synthetic_pair(), synthetic_pair(angle=0.12)], axis=0)
        out = canonical_striatal_features(maps)
        self.assertEqual(out.shape, (2, 64))
        self.assertTrue(np.isfinite(out).all())

    def test_positive_global_intensity_scale_is_removed(self):
        image = synthetic_pair(angle=0.17, left_amp=1.15, right_amp=0.82)
        a = canonical_striatal_features(image[None, :, :])
        b = canonical_striatal_features((9.0 * image)[None, :, :])
        self.assertTrue(np.allclose(a, b, atol=1e-10, rtol=1e-10))

    def test_shared_translation_is_corrected_more_than_unaligned_ablation(self):
        reference = synthetic_pair(angle=0.10)
        moved = synthetic_pair(angle=0.10, row_shift=3.0, col_shift=5.0)

        aligned = canonical_striatal_features(np.stack([reference, moved]))
        raw = unaligned_striatal_features(np.stack([reference, moved]))

        aligned_distance = float(np.linalg.norm(aligned[0] - aligned[1]))
        raw_distance = float(np.linalg.norm(raw[0] - raw[1]))
        self.assertLess(aligned_distance, 0.55 * raw_distance)

    def test_shared_rotation_is_corrected_more_than_unaligned_ablation(self):
        reference = synthetic_pair(angle=-0.05)
        rotated = synthetic_pair(angle=0.24)

        aligned = canonical_striatal_features(np.stack([reference, rotated]))
        raw = unaligned_striatal_features(np.stack([reference, rotated]))

        aligned_distance = float(np.linalg.norm(aligned[0] - aligned[1]))
        raw_distance = float(np.linalg.norm(raw[0] - raw[1]))
        self.assertLess(aligned_distance, 0.65 * raw_distance)

    def test_left_right_uptake_asymmetry_is_preserved(self):
        image = synthetic_pair(left_amp=1.35, right_amp=0.65)
        out = canonical_striatal_features(image[None, :, :])[0]
        left = out[:32]
        right = out[32:]
        self.assertGreater(float(left.mean()), 1.5 * float(right.mean()))


if __name__ == "__main__":
    unittest.main()
