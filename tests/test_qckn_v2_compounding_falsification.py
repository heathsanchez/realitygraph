from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from qckn_v2_compounding_falsification import (
    CompoundingObstruction,
    acquire_generations,
    build_retained_state,
    main,
    run_probe,
)


class GenerationGateTests(unittest.TestCase):
    def test_acquisition_costs_use_one_unit_and_are_exactly_10_3_0(self):
        bundle = acquire_generations()

        self.assertEqual(
            tuple(item.acquisition_search_calls for item in bundle.measurements),
            (10, 3, 0),
        )

    def test_composition_stays_dependent_until_new_identity_is_certified(self):
        bundle = acquire_generations()

        self.assertEqual(
            set(bundle.dependent.dependencies),
            {bundle.parity.capability_id, bundle.decoder.capability_id},
        )
        self.assertNotEqual(
            bundle.standalone.capability_id,
            bundle.dependent.capability_id,
        )
        self.assertEqual(bundle.standalone.dependencies, ())
        self.assertNotEqual(
            bundle.standalone.certificate_id,
            bundle.dependent.certificate_id,
        )
        self.assertEqual(
            bundle.standalone.semantic_table,
            bundle.dependent.semantic_table,
        )
        self.assertEqual(bundle.measurements[2].authority_checks, 8)

    def test_promoted_decoder_identity_receives_its_own_authority_check(self):
        bundle = acquire_generations()

        self.assertIn(
            bundle.decoder.capability_id,
            {attack.capability_id for attack in bundle.attacks},
        )
        self.assertEqual(bundle.measurements[1].authority_checks, 7)


class RetentionGateTests(unittest.TestCase):
    def test_recertified_composite_contracts_active_3_to_1_without_behavior_change(self):
        state = build_retained_state(acquire_generations())

        self.assertEqual(state.decision.active_before_count, 3)
        self.assertEqual(state.decision.active_after_count, 1)
        self.assertEqual(
            state.present.capability_graph.active_ids(),
            state.decision.active_ids,
        )
        self.assertEqual(state.source_replay_before, state.source_replay_after)
        self.assertTrue(state.restart_exact)
        self.assertEqual(state.present.restart().text(), state.present.text())

    def test_ancestry_stays_in_ledger_and_provenance_not_active_memory(self):
        bundle = acquire_generations()
        state = build_retained_state(bundle)

        self.assertEqual(
            set(state.decision.deleted_from_active_ids),
            {bundle.parity.capability_id, bundle.decoder.capability_id},
        )
        self.assertEqual(
            set(state.present.capability_graph.active_ids()),
            {bundle.standalone.capability_id},
        )
        self.assertTrue(
            {bundle.parity.capability_id, bundle.decoder.capability_id}.issubset(
                set(state.decision.provenance_ids)
            )
        )
        self.assertEqual(
            {item.capability_id for item in state.present.memory.capabilities},
            {bundle.standalone.capability_id},
        )
        self.assertEqual(len(state.ledger.events), 3)

    def test_declared_decoder_recovery_moves_decoder_to_reserve_and_refuses_deletion(self):
        state = build_retained_state(
            acquire_generations(),
            require_decoder_recovery=True,
        )

        self.assertEqual(
            state.decision.reserve_ids,
            (state.bundle.decoder.capability_id,),
        )
        with self.assertRaisesRegex(CompoundingObstruction, "RecoveryUnavailable"):
            state.decision.require_removal(state.bundle.decoder.capability_id)


class TransferControlTests(unittest.TestCase):
    def test_warm_restart_beats_cold_with_identical_verified_endpoint(self):
        result = run_probe()
        cold = result.arm("COLD")
        warm = result.arm("WARM")

        self.assertEqual(cold.search_calls, 7)
        self.assertLess(warm.search_calls, cold.search_calls)
        self.assertEqual(warm.search_calls, 0)
        self.assertEqual(warm.verified_semantics, cold.verified_semantics)
        self.assertEqual(warm.authority_snapshot, cold.authority_snapshot)
        self.assertEqual(warm.verifier_id, cold.verifier_id)
        self.assertTrue(warm.used_compiled_capability)

    def test_raw_history_and_sham_do_not_receive_warm_shortcut(self):
        result = run_probe()
        cold = result.arm("COLD")

        self.assertEqual(result.arm("RAW_HISTORY").search_calls, cold.search_calls)
        self.assertEqual(result.arm("SHAM").search_calls, cold.search_calls)
        self.assertFalse(result.arm("RAW_HISTORY").used_compiled_capability)
        self.assertFalse(result.arm("SHAM").used_compiled_capability)

    def test_relevant_ablation_restores_exact_cold_cost(self):
        result = run_probe()

        self.assertEqual(
            result.arm("ANCESTOR_ABLATION").search_calls,
            result.arm("COLD").search_calls,
        )
        self.assertFalse(result.arm("ANCESTOR_ABLATION").used_compiled_capability)

    def test_every_falsification_gate_passes_without_metric_substitution(self):
        result = run_probe()

        self.assertTrue(result.passed, result.failed_gates)
        self.assertEqual(result.failed_gates, ())


class EvidenceTests(unittest.TestCase):
    def test_canonical_evidence_contains_every_separate_cost_and_causal_measure(self):
        payload = run_probe().metrics()

        self.assertEqual(
            payload["generation_acquisition_search"],
            {"G1": 10, "G2": 3, "G3": 0},
        )
        self.assertEqual(
            payload["generation_authority_checks"],
            {"G1": 4, "G2": 7, "G3": 8},
        )
        self.assertEqual(payload["active_capabilities"], {"before": 3, "after": 1})
        self.assertEqual(payload["active_declared_cost"], {"before": 8, "after": 4})
        self.assertEqual(
            payload["target_search_calls"],
            {
                "COLD": 7,
                "WARM": 0,
                "RAW_HISTORY": 7,
                "SHAM": 7,
                "ANCESTOR_ABLATION": 7,
            },
        )
        self.assertEqual(payload["reserve_item_count"], 0)
        self.assertEqual(payload["reserve_negative_control_count"], 1)
        self.assertEqual(payload["ledger_event_count"], 3)
        self.assertEqual(payload["provenance_pointer_count"], 8)
        self.assertGreater(payload["compiled_present_bytes"], 0)
        self.assertTrue(payload["restart_text_equal"])
        self.assertTrue(payload["restart_digest_equal"])
        self.assertTrue(payload["ablation_restores_cold"])
        self.assertEqual(payload["failed_gates"], [])
        self.assertTrue(payload["passed"])

    def test_cli_writes_the_same_canonical_json_it_prints(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "result.json"
            stdout = io.StringIO()
            with patch.dict(
                os.environ,
                {"QCKN_V2_RESULT_PATH": str(output_path)},
                clear=False,
            ):
                with redirect_stdout(stdout):
                    exit_code = main()

            written = output_path.read_text(encoding="utf-8")
            self.assertEqual(exit_code, 0)
            self.assertEqual(written, stdout.getvalue())
            self.assertEqual(
                written,
                json.dumps(
                    json.loads(written),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
            )


if __name__ == "__main__":
    unittest.main()
