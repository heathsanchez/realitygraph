from __future__ import annotations

import unittest

from realitygraph.collatz_adapter import (
    FROZEN_ENDPOINT_EVIDENCE,
    HELDOUT_ENDPOINT_SEQUENCE,
    HELDOUT_NEW_ENDPOINT_EVIDENCE,
    ablated_present,
    build_promoted_ledger,
    classify_endpoint_obligation,
    empty_present,
    endpoint_bank_capability,
    run_future_endpoint_sequence,
    sham_present,
    verify_tail_to_one,
    warm_present,
)
from realitygraph.developmental_core import DevelopmentalRoute, route_residual
from realitygraph.developmental_types import ResultKind


class CollatzQCKNV1AdapterTests(unittest.TestCase):
    def test_all_promoted_endpoint_evidence_replays_exactly(self):
        for endpoint, steps in (
            *FROZEN_ENDPOINT_EVIDENCE,
            *HELDOUT_NEW_ENDPOINT_EVIDENCE,
        ):
            self.assertTrue(
                verify_tail_to_one(endpoint, steps),
                (endpoint, steps),
            )

    def test_endpoint_bank_is_independently_verified_before_construction(self):
        capability = endpoint_bank_capability()
        self.assertEqual(
            len(capability.semantics),
            len(FROZEN_ENDPOINT_EVIDENCE),
        )
        self.assertEqual(
            set(capability.guarded_inputs),
            {str(endpoint) for endpoint, _ in FROZEN_ENDPOINT_EVIDENCE},
        )

        with self.assertRaisesRegex(ValueError, "failed independent replay"):
            endpoint_bank_capability(
                ((157_755_113, 104),),
                capability_id="bad-endpoint-bank",
            )

    def test_causal_promotion_compiles_and_restarts_exactly(self):
        ledger, capability_id, rule_id = build_promoted_ledger()
        present = ledger.materialize_compiled_present()
        restarted = present.restart()

        self.assertEqual(restarted.digest, present.digest)
        self.assertEqual(restarted.text(), present.text())
        self.assertIn(capability_id, restarted.capability_graph.active_ids())
        self.assertEqual(
            {rule.rule_id for rule in restarted.meta_memory.rules},
            {rule_id},
        )
        # Historical acquisition/calibration episodes do not leak into active memory.
        self.assertEqual(restarted.meta_memory.episodes, ())

    def test_typed_residual_routing_distinguishes_compiled_from_new_identity(self):
        present = warm_present()

        known = classify_endpoint_obligation(present, 373_761_769)
        self.assertIs(known.kind, ResultKind.COMPILED)
        self.assertIs(route_residual(known), DevelopmentalRoute.TERMINAL)

        unseen = classify_endpoint_obligation(present, 733_423_337)
        self.assertIs(unseen.kind, ResultKind.UNKNOWN_IDENTITY)
        self.assertIs(route_residual(unseen), DevelopmentalRoute.SPLIT)

    def test_prospective_27_bit_compounding_controls(self):
        self.assertEqual(len(HELDOUT_ENDPOINT_SEQUENCE), 25)
        self.assertEqual(len(set(HELDOUT_ENDPOINT_SEQUENCE)), 12)

        warm = run_future_endpoint_sequence(warm_present())
        cold = run_future_endpoint_sequence(empty_present())

        # RAW_HISTORY: evidence exists outside active memory, but is not compiled.
        raw_history = (
            "test-run-35318888802",
            "test-run-35323204493",
        )
        self.assertTrue(raw_history)
        raw = run_future_endpoint_sequence(empty_present())

        sham = run_future_endpoint_sequence(sham_present())

        cap_ablated = run_future_endpoint_sequence(
            ablated_present(capability=True, repair_rule=False)
        )
        rule_ablated = run_future_endpoint_sequence(
            ablated_present(capability=False, repair_rule=True)
        )
        fully_ablated = run_future_endpoint_sequence(
            ablated_present(capability=True, repair_rule=True)
        )

        for result in (warm, cold, raw, sham, cap_ablated, rule_ablated, fully_ablated):
            self.assertEqual(result.closed_hits, 25)

        # Frozen WARM bank handles the six old endpoint identities for free;
        # only six unique unseen endpoint identities require verification.
        self.assertEqual(warm.verifier_calls, 6)
        self.assertEqual(warm.portfolio_search_calls, 0)
        self.assertEqual(warm.reused_hits, 19)

        # Without active retained knowledge all 12 unique endpoints are acquired cold.
        self.assertEqual(cold.verifier_calls, 12)
        self.assertEqual(cold.portfolio_search_calls, 12)
        self.assertEqual(raw, cold)
        self.assertEqual(sham, cold)

        # Ablating only the endpoint bank removes zero-verification reuse,
        # but the promoted repair rule still removes strategy search.
        self.assertEqual(cap_ablated.verifier_calls, 12)
        self.assertEqual(cap_ablated.portfolio_search_calls, 0)

        # Ablating only the repair rule preserves old endpoint reuse but
        # restores repair-strategy search for the six novel endpoint identities.
        self.assertEqual(rule_ablated.verifier_calls, 6)
        self.assertEqual(rule_ablated.portfolio_search_calls, 6)

        # Removing both exact retained ancestors restores the full cold path.
        self.assertEqual(fully_ablated, cold)

    def test_causal_revocation_survives_compile_and_restart(self):
        present = ablated_present(capability=True, repair_rule=True)
        self.assertEqual(present.capability_graph.active_ids(), ())
        self.assertEqual(present.meta_memory.rules, ())

        # The typed records remain in MG2 history projection but are inactive.
        self.assertTrue(present.memory.capabilities)
        self.assertTrue(present.memory.repair_rules)

    def test_unknown_future_endpoint_is_not_silently_claimed(self):
        with self.assertRaisesRegex(ValueError, "missing independent endpoint evidence"):
            run_future_endpoint_sequence(
                warm_present(),
                endpoints=(999_999_999_999_999,),
            )


if __name__ == "__main__":
    unittest.main()
