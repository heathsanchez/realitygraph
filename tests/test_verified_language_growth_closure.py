from __future__ import annotations

import unittest

from verified_language_growth_closure_v1 import run_qualification


class VerifiedLanguageGrowthClosureTests(unittest.TestCase):
    def test_full_bounded_recursive_language_growth_qualification(self):
        summary = run_qualification(write_result=False)
        self.assertTrue(summary["passed"])
        self.assertEqual(
            summary["verdict"],
            "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1",
        )
        required = (
            "g1_old_language_complete",
            "g1_old_language_no_resolution",
            "g1_extensional_novelty",
            "g1_independently_verified",
            "g1_restart_exact",
            "g1_future_reuse_zero_search",
            "g1_composition_verified",
            "g1_attack_survives",
            "g1_ablation_restores_old_limit",
            "g2_stateless_language_complete",
            "g2_stateless_no_resolution",
            "g2_stateful_novelty",
            "g2_depends_on_g1",
            "g2_restart_exact",
            "g2_future_reuse_zero_search",
            "g2_attack_survives",
            "g1_ablation_invalidates_g2",
            "g2_only_ablation_preserves_g1",
            "unknown_search_blocks_growth",
            "unknown_choice_preserved",
            "stale_certificate_rejected",
            "sham_extension_rejected",
            "closed_bounded",
        )
        for gate in required:
            with self.subTest(gate=gate):
                self.assertTrue(summary["gates"][gate])

    def test_second_generation_is_a_real_recursive_edge(self):
        summary = run_qualification(write_result=False)
        self.assertIn(
            summary["g1"]["constructor_id"],
            summary["g2"]["constructor_dependencies"],
        )
        self.assertIn(
            summary["g1"]["capability_id"],
            summary["g2"]["capability_dependencies"],
        )
        self.assertGreater(summary["g1"]["grammar_search_calls"], 0)
        self.assertGreater(summary["g2"]["grammar_search_calls"], 0)
        self.assertEqual(summary["g1"]["future_search_calls"], 0)
        self.assertEqual(summary["g2"]["future_search_calls"], 0)

    def test_claim_is_explicitly_bounded(self):
        summary = run_qualification(write_result=False)
        self.assertEqual(summary["closure"]["status"], "CLOSED_BOUNDED")
        self.assertFalse(summary["claims"]["open_ended_closure"])
        self.assertFalse(summary["claims"]["unbounded_self_development"])
        self.assertFalse(summary["claims"]["lowest_level_substrate_invented"])


if __name__ == "__main__":
    unittest.main()
