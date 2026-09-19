from __future__ import annotations

import unittest

from qckn_flash_win_controller_v1 import (
    authority_rejection_control,
    current_evidence_control,
    effect_authority_rejection_control,
    late_bridge_control,
    run_probe,
)


class FlashWinControllerTests(unittest.TestCase):
    def test_current_real_evidence_stays_local_without_bridge(self):
        row = current_evidence_control()
        self.assertEqual(row["cross_domain_edges"], 0)
        self.assertEqual(row["scheduler_events"], 0)
        self.assertTrue(row["ranking_unchanged"])
        self.assertEqual(row["arc_affected_domains"], ["arc"])
        self.assertEqual(row["collatz_affected_domains"], ["collatz"])

    def test_late_bridge_reprices_only_exact_destination(self):
        row = late_bridge_control()
        self.assertTrue(row["score_unchanged_before_bridge"])
        self.assertTrue(row["score_increased_after_bridge"])
        self.assertTrue(row["duplicate_cancelled"])
        self.assertTrue(row["unrelated_arc_still_open"])
        self.assertEqual(row["wrong_bridge_delta_count"], 0)
        self.assertEqual(row["bridge_delta_count"], 1)
        self.assertEqual(len(row["bus_edges"]), 1)

    def test_authority_controls(self):
        self.assertTrue(authority_rejection_control())
        self.assertTrue(effect_authority_rejection_control())

    def test_full_probe_passes(self):
        result = run_probe()
        self.assertTrue(result["passed"])
        self.assertTrue(all(result["gates"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
