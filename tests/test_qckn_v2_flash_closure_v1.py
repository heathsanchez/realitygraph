from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from qckn_v2_flash_closure_v1 import main, run_probe


class FlashClosureGateTests(unittest.TestCase):
    def test_flash_reduces_global_search_from_65_to_23(self):
        result = run_probe()

        self.assertEqual(result.arm("ISOLATED").global_search_calls, 65)
        self.assertEqual(result.arm("FLASH").global_search_calls, 23)
        self.assertEqual(
            result.arm("ISOLATED").global_search_calls
            - result.arm("FLASH").global_search_calls,
            42,
        )

    def test_one_compiled_promotion_recloses_six_live_games_before_search(self):
        result = run_probe()
        flash = result.arm("FLASH")

        self.assertEqual(flash.closure_change_counts, (6, 0))
        self.assertEqual(len(flash.flash_resolved_before_search), 6)
        self.assertTrue(
            all(
                flash.outcome(game_id).search_calls == 0
                for game_id in flash.flash_resolved_before_search
            )
        )

    def test_semantic_controls_reject_flash_and_keep_cold_search(self):
        result = run_probe()
        flash = result.arm("FLASH")

        self.assertEqual(flash.outcome("AND_CONTROL").search_calls, 2)
        self.assertEqual(flash.outcome("OR_CONTROL").search_calls, 8)
        rejected_ids = {game_id for _, game_id in flash.rejected_edges}
        self.assertIn("AND_CONTROL", rejected_ids)
        self.assertIn("OR_CONTROL", rejected_ids)

    def test_raw_sham_and_ablation_do_not_reproduce_flash(self):
        result = run_probe()

        self.assertEqual(result.arm("RAW_SHARED").global_search_calls, 65)
        self.assertEqual(result.arm("SHAM_FLASH").global_search_calls, 65)
        self.assertEqual(result.arm("ABLATION").global_search_calls, 65)
        self.assertEqual(result.arm("FLASH").global_search_calls, 23)

    def test_every_arm_reaches_same_verified_endpoint(self):
        result = run_probe()

        self.assertEqual(
            len({arm.endpoint_digest for arm in result.arms}),
            1,
        )

    def test_serial_compounding_and_reminimised_present_are_preserved(self):
        result = run_probe()

        self.assertEqual(result.serial_generation_search, (10, 3, 0))
        self.assertEqual(result.serial_generation_authority, (4, 7, 8))
        self.assertEqual(len(result.active_capability_ids), 1)
        self.assertTrue(result.restart_exact)

    def test_every_flash_falsification_gate_passes(self):
        result = run_probe()

        self.assertTrue(result.passed, result.failed_gates)
        self.assertEqual(result.failed_gates, ())


class FlashClosureEvidenceTests(unittest.TestCase):
    def test_metrics_keep_search_authority_and_propagation_separate(self):
        payload = run_probe().metrics()

        self.assertEqual(payload["live_obligations"], 10)
        self.assertEqual(payload["global_search_calls"]["ISOLATED"], 65)
        self.assertEqual(payload["global_search_calls"]["FLASH"], 23)
        self.assertEqual(payload["flash_search_avoided"], 42)
        self.assertEqual(payload["flash_resolved_before_search_count"], 6)
        self.assertEqual(payload["flash_closure_change_counts"], [6, 0])
        self.assertEqual(payload["flash_fixed_point_rounds"], 2)
        self.assertEqual(payload["global_search_calls"]["RAW_SHARED"], 65)
        self.assertEqual(payload["global_search_calls"]["SHAM_FLASH"], 65)
        self.assertEqual(payload["global_search_calls"]["ABLATION"], 65)
        self.assertTrue(payload["endpoint_digests_equal"])
        self.assertTrue(payload["restart_exact"])
        self.assertEqual(payload["failed_gates"], [])
        self.assertTrue(payload["passed"])

    def test_cli_writes_canonical_evidence_identical_to_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "flash-result.json"
            stdout = io.StringIO()
            with patch.dict(
                os.environ,
                {"QCKN_FLASH_RESULT_PATH": str(output_path)},
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
