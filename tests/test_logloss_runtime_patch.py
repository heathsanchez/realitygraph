import unittest

from parkinson_runtime_logloss_patch import apply_meta_prediction


class LogLossRuntimePatchTests(unittest.TestCase):
    def test_apply_meta_prediction_uses_exported_family(self):
        meta = {
            'family': 'two_stage_logit',
            'params': {'anchor_scale': 0.5, 'residual_scale': 0.25},
        }
        got = apply_meta_prediction(0.2, 0.4, 0.8, meta)
        self.assertGreater(got, 0.2)
        self.assertLess(got, 0.8)

    def test_identity_meta_returns_full(self):
        meta = {'family': 'identity_full', 'params': {}}
        got = apply_meta_prediction(0.2, 0.4, 0.8, meta)
        self.assertAlmostEqual(got, 0.8, places=12)


if __name__ == '__main__':
    unittest.main()
