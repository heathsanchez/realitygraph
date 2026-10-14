"""Frozen causal guard: immutable native warrant versus moving-head freshness."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from current_native import classify_current_head

ORIGINAL = "d20f010dc809f2bb8f94969ccc8ed1691bad2531"
ADVANCED = "f9254e257357eb9fce947e3ac01d428e4ba11d6a"

class NativeCurrentStatusTests(unittest.TestCase):
    def test_same_head_both_observations(self):
        self.assertEqual(classify_current_head(ORIGINAL, ORIGINAL, ORIGINAL),
                         "CHECKED_AT_LATEST_OBSERVED_HEAD_ONLY")

    def test_head_moves_while_proof_is_being_checked(self):
        self.assertEqual(classify_current_head(ORIGINAL, ADVANCED, ORIGINAL),
                         "UNKNOWN_BRANCH_HEAD_ADVANCED_DURING_OR_BEFORE_REPLAY")

    def test_head_already_moved_before_start(self):
        self.assertEqual(classify_current_head(ADVANCED, ADVANCED, ORIGINAL),
                         "UNKNOWN_BRANCH_HEAD_ADVANCED_DURING_OR_BEFORE_REPLAY")

    def test_cannot_reinterpret_lost_live_api_as_current(self):
        self.assertEqual(classify_current_head(None, ORIGINAL, ORIGINAL),
                         "UNKNOWN_LIVE_BRANCH_OBSERVATION_UNAVAILABLE")
        self.assertEqual(classify_current_head(ORIGINAL, None, ORIGINAL),
                         "UNKNOWN_LIVE_BRANCH_OBSERVATION_UNAVAILABLE")

if __name__ == "__main__":
    unittest.main()
