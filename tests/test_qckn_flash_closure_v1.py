from __future__ import annotations

import unittest

from qckn_flash_closure_v1 import (
    independent_positive_cost,
    run_negative_flash,
    run_positive_flash,
    run_probe,
)


class QCKNFlashClosureQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_probe()

    def test_frozen_independent_baseline(self):
        self.assertEqual(independent_positive_cost(), (108, 16))

    def test_positive_flash_reduces_search_and_wall_rounds(self):
        positive = self.result["positive"]
        self.assertEqual(positive["independent_search_calls"], 108)
        self.assertLess(positive["flash_search_calls"], 108)
        self.assertLess(positive["flash_wall_rounds"], 16)
        self.assertGreater(positive["search_calls_avoided"], 0)

    def test_composition_propagates_laterally(self):
        events = self.result["positive"]["flash_events"]
        parity_event = next(
            row for row in events
            if row["event_id"] == "flash-parity-v1"
        )
        self.assertIn(
            "flash-pair-label-v1",
            parity_event["generated_capabilities"],
        )
        label_targets = {
            f"2{index}-target-label"
            for index in range(1, 7)
        }
        self.assertTrue(label_targets.issubset(set(parity_event["discharged"])))
        self.assertGreaterEqual(parity_event["flash_radius"], 8)

    def test_negative_results_are_capital(self):
        negative = self.result["negative_capital"]
        self.assertEqual(negative["independent_search_calls"], 16)
        self.assertEqual(negative["flash_wall_rounds"], 1)
        self.assertLess(negative["flash_search_calls"], 16)
        self.assertGreaterEqual(negative["obstruction_count"], 3)
        self.assertGreater(negative["pruned_candidate_occurrences"], 0)

    def test_sham_and_order_controls(self):
        controls = self.result["controls"]
        self.assertTrue(controls["sham_rejected_without_mutation"])
        self.assertTrue(
            controls["admission_order_compiled_state_invariant"]
        )

    def test_revocation_is_causal_not_global_reset(self):
        revocation = self.result["revocation"]
        self.assertTrue(revocation["exact_reopen"])
        self.assertTrue(revocation["decoder_targets_preserved"])
        self.assertEqual(
            revocation["active_after_revocation"],
            ["flash-decoder-v1"],
        )

    def test_all_declared_gates_pass(self):
        self.assertTrue(self.result["passed"])
        self.assertTrue(all(self.result["gates"].values()))


class QCKNFlashClosureDeterminism(unittest.TestCase):
    def test_positive_fixture_is_repeatable(self):
        left = run_positive_flash()
        right = run_positive_flash()
        self.assertEqual(left.search_calls, right.search_calls)
        self.assertEqual(left.rounds, right.rounds)
        self.assertEqual(
            left.engine.compiled_present().digest,
            right.engine.compiled_present().digest,
        )
        self.assertEqual(
            left.engine.discharged_obligation_ids(),
            right.engine.discharged_obligation_ids(),
        )

    def test_negative_fixture_is_repeatable(self):
        left = run_negative_flash()
        right = run_negative_flash()
        self.assertEqual(left.search_calls, right.search_calls)
        self.assertEqual(left.rounds, right.rounds)
        self.assertEqual(
            sorted(left.engine.obstructions),
            sorted(right.engine.obstructions),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
