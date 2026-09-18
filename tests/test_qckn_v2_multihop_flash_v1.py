from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from qckn_v2_multihop_flash_v1 import main, run_probe


class MultiHopFlashGateTests(unittest.TestCase):
    def test_flash_cascades_one_then_four_then_fixed_point(self):
        result = run_probe()
        flash = result.arm("FLASH")

        self.assertEqual(flash.closure_change_counts, (1, 4, 0))
        self.assertEqual(flash.promoted_counts_by_round, (1, 0, 0))

    def test_global_search_drops_from_63_to_28(self):
        result = run_probe()

        self.assertEqual(result.arm("ISOLATED").global_search_calls, 63)
        self.assertEqual(result.arm("FLASH").global_search_calls, 28)
        self.assertEqual(
            result.arm("ISOLATED").global_search_calls
            - result.arm("FLASH").global_search_calls,
            35,
        )

    def test_bridge_is_wave_one_and_downstream_is_wave_two(self):
        result = run_probe()
        flash = result.arm("FLASH")

        self.assertEqual(flash.outcome("BRIDGE_LABEL").search_calls, 0)
        self.assertEqual(flash.outcome("BRIDGE_LABEL").route, "FLASH_WAVE_1")
        for index in range(1, 5):
            outcome = flash.outcome(f"TOKEN_TARGET_{index}")
            self.assertEqual(outcome.search_calls, 0)
            self.assertEqual(outcome.route, "FLASH_WAVE_2")

    def test_second_hop_is_created_after_bridge_and_has_new_certificate(self):
        result = run_probe()
        flash = result.arm("FLASH")

        self.assertTrue(flash.c2_created_after_bridge)
        self.assertEqual(
            flash.second_hop_capability_id,
            "multihop-standalone-pair-token-v1",
        )
        self.assertEqual(
            flash.second_hop_certificate_id,
            "cert:multihop-standalone-pair-token-v1",
        )

    def test_decoder_search_cost_is_three_in_every_arm(self):
        result = run_probe()

        self.assertTrue(all(arm.decoder_search_calls == 3 for arm in result.arms))

    def test_semantic_controls_reject_inappropriate_hops(self):
        result = run_probe()
        flash = result.arm("FLASH")

        self.assertEqual(flash.outcome("AND_LABEL_CONTROL").search_calls, 2)
        self.assertEqual(flash.outcome("AND_TOKEN_CONTROL").search_calls, 2)
        self.assertEqual(flash.outcome("OR_TOKEN_CONTROL").search_calls, 8)

        rejected = {game_id for _, game_id in flash.rejected_edges}
        self.assertIn("AND_LABEL_CONTROL", rejected)
        self.assertIn("AND_TOKEN_CONTROL", rejected)
        self.assertIn("OR_TOKEN_CONTROL", rejected)

    def test_raw_sham_and_ablation_do_not_reproduce_cascade(self):
        result = run_probe()

        self.assertEqual(result.arm("RAW_SHARED").global_search_calls, 63)
        self.assertEqual(result.arm("SHAM_FLASH").global_search_calls, 63)
        self.assertEqual(result.arm("ABLATION").global_search_calls, 63)

    def test_all_arms_end_at_same_verified_endpoint(self):
        result = run_probe()

        self.assertEqual(len({arm.endpoint_digest for arm in result.arms}), 1)

    def test_serial_source_compounding_remains_10_3_0(self):
        result = run_probe()

        self.assertEqual(result.serial_generation_search, (10, 3, 0))
        self.assertEqual(result.serial_generation_authority, (4, 7, 8))

    def test_every_multihop_gate_passes(self):
        result = run_probe()

        self.assertTrue(result.passed, result.failed_gates)
        self.assertEqual(result.failed_gates, ())


class MultiHopFlashEvidenceTests(unittest.TestCase):
    def test_metrics_keep_each_search_layer_separate(self):
        payload = run_probe().metrics()

        self.assertEqual(payload["live_obligations"], 10)
        self.assertEqual(payload["global_search_calls"]["ISOLATED"], 63)
        self.assertEqual(payload["global_search_calls"]["FLASH"], 28)
        self.assertEqual(payload["flash_search_avoided"], 35)
        self.assertEqual(payload["flash_closure_change_counts"], [1, 4, 0])
        self.assertEqual(payload["flash_promoted_counts_by_round"], [1, 0, 0])
        self.assertEqual(payload["decoder_search_calls"]["FLASH"], 3)
        self.assertEqual(payload["bridge_search_calls"]["FLASH"], 0)
        self.assertEqual(payload["downstream_search_calls"]["FLASH"], 0)
        self.assertEqual(payload["control_search_calls"]["FLASH"], 12)
        self.assertTrue(payload["c2_created_after_bridge"])
        self.assertTrue(payload["endpoint_digests_equal"])
        self.assertTrue(payload["restart_exact"])
        self.assertEqual(payload["failed_gates"], [])
        self.assertTrue(payload["passed"])

    def test_cli_writes_canonical_evidence_identical_to_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "multihop-result.json"
            stdout = io.StringIO()
            with patch.dict(
                os.environ,
                {"QCKN_MULTIHOP_RESULT_PATH": str(output_path)},
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
