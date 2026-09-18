from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from realitygraph.collatz_controller import (
    consume_worker_results,
    endpoint_bank_digest,
    export_bank_payload,
    generation2_present,
    generation3_present,
)
from realitygraph.collatz_adapter import _active_endpoint_bank


class CollatzQCKNControllerTests(unittest.TestCase):
    def test_generation2_exports_exact_restartable_bank(self):
        present = generation2_present()
        restarted = present.restart()
        self.assertEqual(restarted.digest, present.digest)
        bank = _active_endpoint_bank(restarted)
        self.assertEqual(len(bank), 16)

        payload = export_bank_payload(generation=2)
        self.assertEqual(payload["compiled_present_digest"], present.digest)
        self.assertEqual(payload["bank_digest"], endpoint_bank_digest(bank))
        self.assertEqual(
            {int(k): int(v) for k, v in payload["endpoints"].items()},
            bank,
        )

    def test_generation3_is_current_and_extends_generation2(self):
        g2=generation2_present()
        g3=generation3_present()
        b2=_active_endpoint_bank(g2)
        b3=_active_endpoint_bank(g3)
        self.assertEqual(len(b2),16)
        self.assertEqual(len(b3),17)
        self.assertEqual(set(b3)-set(b2),{17_843_037_929})
        self.assertEqual(b3[17_843_037_929],131)

        payload=export_bank_payload()
        self.assertEqual(payload["compiled_present_digest"],g3.digest)
        self.assertEqual(
            {int(k):int(v) for k,v in payload["endpoints"].items()},
            b3,
        )

    def _worker_dir(self, *, stale_digest: bool = False):
        payload = export_bank_payload(generation=2)
        prior = {int(k): int(v) for k, v in payload["endpoints"].items()}
        bank_digest = "stale" if stale_digest else payload["bank_digest"]

        # 373,761,769 is in generation 2; 505,882,345 is a later independently
        # verified endpoint but not yet active in generation 2.
        result = {
            "version": "collatz-qckn-worker-result-v1",
            "source_range": [268_435_457, 268_435_999],
            "horizon": 512,
            "guard": 10000,
            "bank_digest": bank_digest,
            "bank_size": len(prior),
            "counts": {
                "live_two_replay": 3,
                "compiled_reuse_hit": 2,
                "verified_candidate_hit": 1,
                "candidate_verifier_calls": 1,
                "closed_hit": 3,
            },
            "reuse": {"373761769": 2},
            "live_endpoint_counts": {
                "373761769": 2,
                "505882345": 1,
            },
            "candidate_acquisitions": [
                {
                    "endpoint": 505_882_345,
                    "steps_to_one": 159,
                    "first_source": 184_633_503,
                    "first_k": 35,
                    "occurrences": 1,
                }
            ],
            "unresolved": [],
        }
        directory = tempfile.mkdtemp()
        Path(directory, "shard-0.json").write_text(
            json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        )
        return directory

    def test_worker_candidates_are_reverified_promoted_restarted_and_ablatable(self):
        directory = self._worker_dir()
        report, ledger = consume_worker_results(directory,generation=2)

        self.assertEqual(report.worker_shards, 1)
        self.assertEqual(report.prior_bank_size, 16)
        self.assertEqual(report.live_hits, 3)
        self.assertEqual(report.unique_live_endpoints, 2)
        self.assertEqual(report.warm_reuse_hits, 2)
        self.assertEqual(report.warm_verifier_calls, 1)
        self.assertEqual(report.cold_verifier_calls, 2)
        self.assertEqual(report.new_unique_endpoints, 1)
        self.assertEqual(report.unresolved, 0)
        self.assertEqual(report.restarted_bank_size, 17)
        self.assertTrue(report.promoted_capability_id)
        self.assertTrue(report.ablation_restores_new_identity)

        present = ledger.materialize_compiled_present().restart()
        bank = _active_endpoint_bank(present)
        self.assertIn(505_882_345, bank)
        self.assertEqual(bank[505_882_345], 159)

    def test_stale_worker_bank_is_rejected(self):
        directory = self._worker_dir(stale_digest=True)
        with self.assertRaisesRegex(ValueError, "bank digest"):
            consume_worker_results(directory,generation=2)


if __name__ == "__main__":
    unittest.main()
