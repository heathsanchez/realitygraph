import unittest

from verified_meta_growth_v3 import run_qualification


class VerifiedMetaGrowthV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = run_qualification(write_result=False)

    def test_two_distinct_repair_rules_require_calibration_before_promotion(self):
        summary = self.summary
        self.assertTrue(summary["gates"]["acquisition_rules_candidate_only"])
        self.assertTrue(summary["gates"]["calibration_promotes_both_rules"])
        self.assertTrue(summary["gates"]["two_distinct_promoted_repair_rules"])
        self.assertEqual(
            {row["strategy_id"] for row in summary["promoted_rules"]},
            {"add_observable", "add_finite_memory_2"},
        )

    def test_future_reuses_repair_rules_without_portfolio_search(self):
        summary = self.summary
        for family in ("c", "t"):
            row = summary["future"][family]
            self.assertTrue(row["rule_hit"])
            self.assertEqual(row["portfolio_search_calls"], 0)
            self.assertEqual(row["competitor_strategy_calls"], 0)
            self.assertEqual(row["selected_strategy_calls"], 1)
            self.assertEqual(row["object_future_grammar_search_calls"], 0)

    def test_future_capabilities_are_new_and_verified(self):
        summary = self.summary
        self.assertTrue(summary["gates"]["future_c_new_verified_capability"])
        self.assertTrue(summary["gates"]["future_t_new_verified_capability"])
        self.assertNotEqual(
            summary["acquisition"]["c"]["capability_id"],
            summary["future"]["c"]["capability_id"],
        )
        self.assertNotEqual(
            summary["acquisition"]["t"]["capability_id"],
            summary["future"]["t"]["capability_id"],
        )

    def test_rule_ablation_restores_cold_portfolio_search(self):
        summary = self.summary
        self.assertTrue(summary["gates"]["rule_ablation_restores_cold_search"])
        self.assertGreater(summary["ablations"]["c"]["portfolio_search_calls"], 0)
        self.assertGreater(summary["ablations"]["t"]["portfolio_search_calls"], 0)
        self.assertFalse(summary["ablations"]["c"]["rule_hit"])
        self.assertFalse(summary["ablations"]["t"]["rule_hit"])

    def test_negative_controls_fail_closed(self):
        controls = self.summary["controls"]
        required = (
            "wrong_fingerprint_rejects_rule",
            "stale_authority_rule_rejected",
            "stale_verifier_rule_rejected",
            "sham_rule_rejected",
            "incomplete_obstruction_unknown_search",
            "partial_portfolio_unknown_search",
            "unknown_choice_preserved",
        )
        for name in required:
            self.assertTrue(controls[name], name)

    def test_exact_meta_snapshot_restart(self):
        snapshot = self.summary["snapshot"]
        self.assertTrue(snapshot["exact"])
        self.assertEqual(snapshot["before_object_digest"], snapshot["after_object_digest"])
        self.assertEqual(snapshot["before_memory_digest"], snapshot["after_memory_digest"])

    def test_inherited_v2_qualification_remains_green(self):
        inherited = self.summary["inherited_v2"]
        self.assertTrue(inherited["passed"])
        self.assertEqual(inherited["verdict"], "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2")

    def test_claim_is_explicitly_bounded(self):
        summary = self.summary
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["verdict"], "PASS_VERIFIED_META_GROWTH_V3")
        self.assertEqual(summary["closure"]["status"], "CLOSED_BOUNDED_META_GROWTH_V3")
        self.assertTrue(summary["claims"]["bounded_verified_meta_growth"])
        self.assertFalse(summary["claims"]["open_ended_meta_growth"])
        self.assertFalse(summary["claims"]["arbitrary_substrate_invention"])
        self.assertFalse(summary["claims"]["unbounded_self_development"])


if __name__ == "__main__":
    unittest.main()
