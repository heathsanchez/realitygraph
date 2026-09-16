import unittest

import numpy as np

from realitygraph.representation_genesis import (
    Program,
    apply_program,
    enumerate_programs,
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


if __name__ == "__main__":
    unittest.main()
