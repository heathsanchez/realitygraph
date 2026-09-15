from __future__ import annotations

import unittest

from realitygraph.mg import MG
from realitygraph.predictive import CompiledPredictiveModel, ThresholdRule
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
    exact_restart,
)
from realitygraph.transfer_memory import model_memory, model_to_law


class RetainedCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.sources = (("https://example.test/data", "abc123"),)
        self.probes = ("x", "y")
        self.model = CompiledPredictiveModel(
            (ThresholdRule(0, "x", 0.5),),
            (((0,), 0.2, 8), ((1,), 0.8, 9)),
            0.5,
            min_support=4,
        )
        self.law = model_to_law(
            self.sources,
            self.model,
            provenance="unit-lineage",
        )
        self.memory = model_memory(self.law)

    def test_restart_is_exact(self):
        text = self.memory.text()
        restarted = exact_restart(text)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.laws, self.memory.laws)

    def test_applicability_uses_scope_and_schema(self):
        matches = applicable_transfer_capabilities(
            self.memory, self.sources, self.probes
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].law_id, self.law.id)

        self.assertEqual(
            applicable_transfer_capabilities(
                self.memory,
                (("https://example.test/other", "zzz"),),
                self.probes,
            ),
            (),
        )
        self.assertEqual(
            applicable_transfer_capabilities(
                self.memory, self.sources, ("y",)
            ),
            (),
        )

    def test_lineage_ablation_removes_only_capability(self):
        ablated = ablate_capability(self.memory, self.law.id)
        self.assertNotIn(self.law.id, ablated.laws)
        self.assertEqual(
            applicable_transfer_capabilities(
                ablated, self.sources, self.probes
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
