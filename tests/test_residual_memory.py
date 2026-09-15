from __future__ import annotations

import unittest

from realitygraph.mg import MG
from realitygraph.predictive import CompiledPredictiveModel, ThresholdRule
from realitygraph.residual import CompiledResidualModel
from realitygraph.residual_memory import (
    add_residual_to_memory,
    applicable_residual_laws,
    law_to_residual_model,
    residual_parent_law_id,
    residual_to_law,
)
from realitygraph.transfer_memory import model_memory, model_to_law


class ResidualMemoryTests(unittest.TestCase):
    def setUp(self):
        self.sources = (("https://example.test/data", "abc123"),)
        self.probes = ("x", "y")
        base_model = CompiledPredictiveModel(
            (ThresholdRule(0, "x", 0.5),),
            (((0,), 0.2, 8), ((1,), 0.8, 9)),
            0.5,
            min_support=4,
        )
        self.base_law = model_to_law(
            self.sources, base_model, provenance="base"
        )
        self.base_memory = model_memory(self.base_law)

        residual_model = CompiledResidualModel(
            (ThresholdRule(1, "y", 1.5),),
            (((0,), 0.25, 7), ((1,), -0.15, 6)),
            min_support=4,
        )
        self.residual_law = residual_to_law(
            self.sources,
            residual_model,
            parent_law_id=self.base_law.id,
            provenance="child",
        )

    def test_round_trip(self):
        model = law_to_residual_model(self.residual_law, self.probes)
        self.assertEqual(model.rules[0].probe_name, "y")
        self.assertEqual(residual_parent_law_id(self.residual_law), self.base_law.id)

    def test_parent_is_required_for_applicability(self):
        memory = add_residual_to_memory(self.base_memory, self.residual_law)
        self.assertEqual(
            len(applicable_residual_laws(memory, self.sources, self.probes)), 1
        )

        child_only = MG(memory.verifier, (self.residual_law,))
        self.assertEqual(
            applicable_residual_laws(child_only, self.sources, self.probes), ()
        )

    def test_schema_is_checked(self):
        memory = add_residual_to_memory(self.base_memory, self.residual_law)
        self.assertEqual(
            applicable_residual_laws(memory, self.sources, ("x",)), ()
        )


if __name__ == "__main__":
    unittest.main()
