import unittest

import numpy as np

from realitygraph.representation_genesis import (
    Program,
    apply_program,
    enumerate_programs,
    fit_residual_decoder,
    mixed_evidence_invoke,
    predict_residual_decoder,
    program_complexity,
)


class RepresentationGenesisTests(unittest.TestCase):
    def test_frozen_selective_representation_grammars_are_present(self):
        programs = enumerate_programs()
        bilateral = {p.bilateral for p in programs}
        self.assertTrue({"raw", "sum", "diff", "absdiff"}.issubset(bilateral))

    def test_absdiff_is_zero_for_bilateral_mirror_symmetry(self):
        left = np.arange(32 * 64, dtype=np.float64).reshape(32, 64)
        right = np.flip(left, axis=0)
        image = np.concatenate([left, right], axis=0)[None, :, :]

        program = Program(
            source="R",
            intensity="identity",
            bilateral="absdiff",
            pooling="grid4_mean",
        )
        out = apply_program({"R": image, "X": image}, program)
        self.assertEqual(out.shape, (1, 16))
        self.assertTrue(np.allclose(out, 0.0))

    def test_sum_diff_absdiff_have_distinct_consequences(self):
        left = np.ones((32, 64), dtype=np.float64)
        right = np.zeros((32, 64), dtype=np.float64)
        image = np.concatenate([left, right], axis=0)[None, :, :]
        maps = {"R": image, "X": image}

        values = {}
        for bilateral in ("sum", "diff", "absdiff"):
            program = Program(
                source="R",
                intensity="identity",
                bilateral=bilateral,
                pooling="grid4_mean",
            )
            values[bilateral] = apply_program(maps, program)

        self.assertTrue(np.all(values["sum"] > 0))
        self.assertTrue(np.all(values["diff"] > 0))
        self.assertTrue(np.all(values["absdiff"] > 0))
        self.assertTrue(np.allclose(values["diff"], values["absdiff"]))

    def test_program_enumeration_is_deterministic_and_complexity_ordered(self):
        a = enumerate_programs()
        b = enumerate_programs()
        self.assertEqual(a, b)
        self.assertGreater(len(a), 20)
        self.assertEqual(
            min(a, key=program_complexity),
            Program("R", "identity", "raw", "grid4_mean"),
        )

    def test_q90_scale_is_invariant_to_positive_global_scale(self):
        rng = np.random.default_rng(7)
        image = rng.uniform(0.1, 3.0, size=(2, 64, 64))
        program = Program(
            source="R",
            intensity="q90_scale",
            bilateral="raw",
            pooling="grid4_mean",
        )
        a = apply_program({"R": image, "X": image}, program)
        b = apply_program({"R": 11.0 * image, "X": 11.0 * image}, program)
        self.assertTrue(np.allclose(a, b, atol=1e-10, rtol=1e-10))

    def test_residual_decoder_does_not_read_future_labels(self):
        rng = np.random.default_rng(19)
        x = rng.normal(size=(30, 4))
        env = np.repeat(np.arange(3), 10)
        y = (x[:, 0] + 0.25 * x[:, 1] > 0).astype(int)
        base = np.full(30, 0.5)

        first = fit_residual_decoder(x, y, base, env, (0, 1))
        changed = y.copy()
        changed[env == 2] = 1 - changed[env == 2]
        second = fit_residual_decoder(x, changed, base, env, (0, 1))

        self.assertTrue(np.allclose(first.mean, second.mean))
        self.assertTrue(np.allclose(first.scale, second.scale))
        self.assertTrue(np.allclose(first.direction, second.direction))
        self.assertAlmostEqual(first.score_mean, second.score_mean)
        self.assertAlmostEqual(first.score_scale, second.score_scale)
        self.assertAlmostEqual(first.delta, second.delta)

    def test_constant_representation_refuses_change(self):
        x = np.ones((24, 3), dtype=float)
        env = np.repeat(np.arange(3), 8)
        y = np.tile([0, 1], 12)
        base = np.full(24, 0.5)

        model = fit_residual_decoder(x, y, base, env, (0, 1, 2))
        pred = predict_residual_decoder(model, x, base)

        self.assertAlmostEqual(model.delta, 0.0)
        self.assertTrue(np.allclose(pred, base))

    def test_residual_decoder_improves_a_shared_linear_signal(self):
        x0 = np.linspace(-2.5, 2.5, 60)
        x = np.column_stack([x0, 0.1 * np.sin(x0)])
        env = np.tile(np.arange(3), 20)
        y = (x0 > 0).astype(int)
        base = np.full(60, 0.5)

        model = fit_residual_decoder(x, y, base, env, (0, 1, 2))
        pred = predict_residual_decoder(model, x, base)

        def loss(p):
            p = np.clip(p, 1e-9, 1 - 1e-9)
            return float(np.mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))))

        self.assertGreater(model.delta, 0.0)
        self.assertLess(loss(pred), loss(base))

    def test_mixed_evidence_controller_invokes_only_on_mixed_positive_evidence(self):
        self.assertTrue(mixed_evidence_invoke([0.004, 0.002, -0.0001], 1e-4))
        self.assertFalse(mixed_evidence_invoke([0.004, 0.002, 0.001], 1e-4))
        self.assertFalse(mixed_evidence_invoke([-0.004, -0.002, -0.001], 1e-4))
        self.assertFalse(mixed_evidence_invoke([0.0, 0.0, 0.0], 1e-4))


if __name__ == "__main__":
    unittest.main()
