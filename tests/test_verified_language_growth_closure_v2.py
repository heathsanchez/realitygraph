import unittest

from verified_language_growth_closure_v2 import run_qualification


class VerifiedLanguageGrowthClosureV2Tests(unittest.TestCase):
    def test_three_generations_share_executor_and_form_real_dependency_chain(self):
        summary = run_qualification(write_result=False)
        self.assertTrue(summary["gates"]["same_executor_g1_g2_g3"])
        self.assertTrue(summary["gates"]["executor_has_no_fixture_imports"])
        self.assertTrue(summary["gates"]["executor_has_no_generation_dispatch"])
        self.assertTrue(summary["gates"]["g2_depends_on_g1"])
        self.assertTrue(summary["gates"]["g3_depends_on_g2"])
        self.assertEqual(summary["g1"]["future_search_calls"], 0)
        self.assertEqual(summary["g2"]["future_search_calls"], 0)
        self.assertEqual(summary["g3"]["future_search_calls"], 0)

    def test_causal_ablation_chain(self):
        summary = run_qualification(write_result=False)
        self.assertTrue(summary["gates"]["g1_ablation_invalidates_g2_g3"])
        self.assertTrue(summary["gates"]["g2_ablation_invalidates_g3_preserves_g1"])
        self.assertTrue(summary["gates"]["g3_ablation_preserves_g1_g2"])

    def test_g3_lower_bound_and_growth_are_exact(self):
        summary = run_qualification(write_result=False)
        self.assertTrue(summary["gates"]["g3_two_state_language_complete"])
        self.assertTrue(summary["gates"]["g3_two_state_no_resolution"])
        self.assertTrue(summary["gates"]["g3_three_state_novel"])
        self.assertEqual(summary["g3"]["two_state_raw_count"], 64)
        self.assertEqual(summary["g3"]["three_state_raw_count"], 5832)

    def test_v2_claim_is_bounded_depth3(self):
        summary = run_qualification(write_result=False)
        self.assertTrue(summary["passed"])
        self.assertEqual(
            summary["verdict"],
            "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2",
        )
        self.assertEqual(summary["closure"]["status"], "CLOSED_BOUNDED")
        self.assertEqual(summary["closure"]["qualification_depth"], 3)
        self.assertTrue(summary["closure"]["restart_exact"])
        self.assertFalse(summary["claims"]["open_ended_closure"])
        self.assertFalse(summary["claims"]["unbounded_self_development"])


if __name__ == "__main__":
    unittest.main()
