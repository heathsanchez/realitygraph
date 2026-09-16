import json
import tempfile
import unittest

import numpy as np

from realitygraph.final_trajectory_model import export_model, apply_exported_residual


class FinalTrajectoryModelTests(unittest.TestCase):
    def test_export_round_trip_applies_anchor_then_residual(self):
        model = {
            "anchor": {"name": "a", "mean": [2.0], "scale": [2.0], "beta": [0.5], "shrinkage": 0.5},
            "residual": {"names": ["r1", "r2"], "mean": [1.0, 2.0], "scale": [1.0, 2.0], "beta": [0.25, -0.5], "shrinkage": 0.25},
        }
        base_logits = np.array([0.0, 1.0])
        anchor = np.array([2.0, 4.0])
        residual = np.array([[1.0, 2.0], [3.0, 6.0]])

        with tempfile.NamedTemporaryFile(suffix=".json") as fh:
            export_model(model, fh.name)
            loaded = json.load(open(fh.name))

        got = apply_exported_residual(base_logits, anchor, residual, loaded)
        expected = base_logits.copy()
        expected += 0.5 * ((anchor - 2.0) / 2.0) * 0.5
        expected += 0.25 * (((residual - np.array([1.0, 2.0])) / np.array([1.0, 2.0])) @ np.array([0.25, -0.5]))
        np.testing.assert_allclose(got, expected)

    def test_export_rejects_nonfinite_parameters(self):
        model = {
            "anchor": {"name": "a", "mean": [0.0], "scale": [1.0], "beta": [float("nan")], "shrinkage": 0.5},
            "residual": {"names": [], "mean": [], "scale": [], "beta": [], "shrinkage": 0.0},
        }
        with tempfile.NamedTemporaryFile(suffix=".json") as fh:
            with self.assertRaises(ValueError):
                export_model(model, fh.name)

    def test_runtime_patch_can_start_from_already_g1g2_parent(self):
        import parkinson_runtime_patch as patch

        model = {
            "anchor": {"name": "a", "mean": [0.0], "scale": [1.0], "beta": [0.0], "shrinkage": 0.5},
            "residual": {"names": [], "mean": [], "scale": [], "beta": [], "shrinkage": 0.0},
        }
        old_map = patch.runtime_signal_map
        old_bank = patch.dense_threshold_trajectory_features
        old_parent = patch.parent_probability
        try:
            patch.runtime_signal_map = lambda _: (np.zeros((64, 64)), np.ones((64, 64)))
            patch.dense_threshold_trajectory_features = lambda _: (
                np.array([[0.0]], dtype=float), ["a"], ["trajectory"]
            )
            patch.parent_probability = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must be skipped"))
            got = patch.patch_probability("unused.nii.gz", 0.7, model, already_parent=True)
            self.assertAlmostEqual(got, 0.7, places=12)
        finally:
            patch.runtime_signal_map = old_map
            patch.dense_threshold_trajectory_features = old_bank
            patch.parent_probability = old_parent


if __name__ == "__main__":
    unittest.main()
