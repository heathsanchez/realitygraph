import unittest

from realitygraph.evidence import (
    certify_zero_failures,
    zero_failure_upper_bound,
)


class ZeroFailureEvidenceTests(unittest.TestCase):
    def test_exact_one_sided_bound(self):
        self.assertAlmostEqual(
            zero_failure_upper_bound(59, confidence=0.95),
            1.0 - 0.05 ** (1.0 / 59.0),
        )

    def test_fifty_nine_zero_failures_earns_five_percent_bound(self):
        self.assertFalse(
            certify_zero_failures(
                58,
                confidence=0.95,
                max_error=0.05,
            ).accepted
        )
        self.assertTrue(
            certify_zero_failures(
                59,
                confidence=0.95,
                max_error=0.05,
            ).accepted
        )

    def test_no_observations_never_promotes(self):
        evidence = certify_zero_failures(
            0,
            confidence=0.95,
            max_error=0.05,
        )
        self.assertFalse(evidence.accepted)
        self.assertEqual(evidence.upper_error, 1.0)


if __name__ == "__main__":
    unittest.main()
