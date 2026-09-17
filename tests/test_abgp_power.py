from fractions import Fraction
from pathlib import Path
import unittest

from realitygraph.abgp.manifest import load_analysis_plan
from realitygraph.abgp.power import (
    g_world_blocked_conservative_power,
    paired_exact_power,
    qualification_power_audit,
)


_ROOT = Path(__file__).resolve().parents[1]
_PLAN = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"


class ABGPPowerTests(unittest.TestCase):
    def test_power_is_near_one_for_deterministic_treatment_wins(self):
        value = paired_exact_power(
            256,
            Fraction(1, 1),
            Fraction(0, 1),
            Fraction(1, 80),
        )
        self.assertGreater(value, 0.999)

    def test_zero_effect_does_not_report_high_power(self):
        value = paired_exact_power(
            256,
            Fraction(1, 10),
            Fraction(1, 10),
            Fraction(1, 80),
        )
        self.assertLess(value, 0.20)

    def test_world_blocked_g_power_uses_max_dose_only_worst_case(self):
        n = 256
        q = Fraction(1, 2)
        delta = Fraction(3, 20)
        alpha = Fraction(1, 80)
        expected = paired_exact_power(
            n,
            (q + delta) / 2,
            (q - delta) / 2,
            alpha,
        )
        actual = g_world_blocked_conservative_power(n, q, delta, alpha)
        self.assertAlmostEqual(actual, expected)

    def test_analysis_plan_registers_pre_freeze_power_rule(self):
        plan = load_analysis_plan(_PLAN)
        self.assertEqual(plan.status, "REVIEW_PENDING")
        self.assertEqual(plan.raw["qualification"]["minimum_power"], 0.80)
        self.assertEqual(plan.raw["qualification"]["holm_component_alpha_floor"], 0.0125)
        self.assertTrue(plan.raw["qualification"]["paired_nuisance_envelope"])

    def test_power_audit_is_deterministic_and_reports_each_arm(self):
        plan = load_analysis_plan(_PLAN)
        first = qualification_power_audit(plan)
        second = qualification_power_audit(plan)
        self.assertEqual(first, second)
        self.assertEqual(set(first["arms"]), {"A", "B", "G", "P"})
        self.assertEqual(first["minimum_required_power"], 0.80)
        self.assertEqual(first["arms"]["G"]["power_model"], "world_blocked_max_dose_only_worst_case")
        for arm in ("A", "B", "G", "P"):
            self.assertIn("minimum_observed_power", first["arms"][arm])
            self.assertIn("qualified", first["arms"][arm])


if __name__ == "__main__":
    unittest.main()
