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


if __name__ == "__main__":
    unittest.main()
