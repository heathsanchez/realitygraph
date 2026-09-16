import unittest

import numpy as np

from realitygraph.logloss_meta import (
    apply_family,
    fit_family,
    fit_leave_environment_out,
    log_loss,
)


class LogLossMetaTests(unittest.TestCase):
    def test_affine_calibration_reduces_known_overconfidence(self):
        y = np.array([0, 0, 0, 1, 1, 1] * 20, dtype=int)
        truth = np.array([0.12, 0.20, 0.35, 0.65, 0.80, 0.88] * 20, dtype=float)
        z = np.log(truth / (1 - truth))
        full = 1.0 / (1.0 + np.exp(-1.8 * z))
        streams = {'parent': full, 'anchor': full, 'full': full}

        params = fit_family('affine_full', streams, y)
        got = apply_family('affine_full', params, streams)
        self.assertLess(log_loss(y, got), log_loss(y, full))
        self.assertTrue(np.isfinite(got).all())
        self.assertTrue(((got > 0) & (got < 1)).all())

    def test_two_stage_logit_can_recover_useful_residual_shrinkage(self):
        y = np.array([0, 0, 1, 1] * 30, dtype=int)
        parent = np.array([0.20, 0.35, 0.65, 0.80] * 30, dtype=float)
        zp = np.log(parent / (1 - parent))
        za = zp + np.array([-0.2, -0.1, 0.1, 0.2] * 30)
        zf = za + np.array([-0.8, -0.4, 0.4, 0.8] * 30)
        anchor = 1.0 / (1.0 + np.exp(-za))
        full = 1.0 / (1.0 + np.exp(-zf))
        streams = {'parent': parent, 'anchor': anchor, 'full': full}

        params = fit_family('two_stage_logit', streams, y)
        got = apply_family('two_stage_logit', params, streams)
        self.assertLessEqual(log_loss(y, got), log_loss(y, full) + 1e-9)
        self.assertGreaterEqual(params['anchor_scale'], 0.0)
        self.assertGreaterEqual(params['residual_scale'], 0.0)

    def test_leave_environment_out_returns_complete_predictions(self):
        env = np.repeat(np.arange(4), 8)
        y = np.tile(np.array([0, 0, 0, 0, 1, 1, 1, 1]), 4)
        parent = np.tile(np.array([.2, .25, .3, .35, .65, .7, .75, .8]), 4)
        full = np.clip(parent ** 1.3, 1e-5, 1 - 1e-5)
        streams = {'parent': parent, 'anchor': parent, 'full': full}

        result = fit_leave_environment_out('temperature_full', streams, y, env)
        pred = result['predictions']
        self.assertEqual(pred.shape, y.shape)
        self.assertTrue(np.isfinite(pred).all())
        self.assertTrue(((pred > 0) & (pred < 1)).all())
        self.assertEqual(result['folds'], 4)


if __name__ == '__main__':
    unittest.main()
