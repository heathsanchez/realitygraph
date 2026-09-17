import unittest

from realitygraph.abgp.analysis import (
    analyze_a,
    analyze_b,
    analyze_g,
    analyze_p,
    g_world_blocked_randomization_pvalue,
)
from realitygraph.abgp.arm_p import run_p_dev_records


class ABGPFinalLockClarificationTests(unittest.TestCase):
    def test_a_uses_task_as_unit_and_information_matched_bayes_control(self):
        treatment = [1] * 32
        equal_recheck = [0] * 8 + [1] * 24
        information_matched_bayes = [0] * 10 + [1] * 22
        result = analyze_a(
            {
                "treatment": treatment,
                "baselines": {
                    "equal_compute_recheck": equal_recheck,
                    "information_matched_bayes": information_matched_bayes,
                },
                "hard_gates": {
                    "message_nonidentifying": True,
                    "single_message": True,
                    "single_repair_round": True,
                    "compute_budget_matched": True,
                    "information_budget_matched": True,
                },
            }
        )
        self.assertEqual(result["inferential_unit"], "paired_task")
        self.assertEqual(
            set(result["component_pvalues"]),
            {"equal_compute_recheck", "information_matched_bayes"},
        )
        self.assertAlmostEqual(result["effect"], 8 / 32)

    def test_b_is_direction_stratified_and_interventions_remain_nested(self):
        directions = [f"d{i}" for i in range(12) for _ in range(3)]
        n = len(directions)
        result = analyze_b(
            {
                "treatment": [1] * n,
                "wrong_class": [0] * n,
                "shuffled_coupling": [0] * n,
                "direction_labels": directions,
                "intervention_agreement": [1] * (n * 4),
                "bisimulation_separator_agreement": [1] * n,
                "hard_gates": {
                    "grammar_independence": True,
                    "no_translation": True,
                    "bisimulation_separator_present": True,
                },
            }
        )
        self.assertEqual(result["analysis_mode"], "DIRECTION_STRATIFIED_IUT")
        self.assertEqual(result["inferential_unit"], "world_within_ordered_grammar_direction")
        self.assertEqual(result["direction_count"], 12)
        self.assertEqual(result["interventions_per_unit"], 4)
        self.assertTrue(result["bisimulation_separator_gate"])

    def test_g_randomizes_one_joint_relevance_swap_per_world(self):
        pairs = []
        for world_id in range(4):
            for weight in (2, 5, 10, 20):
                pairs.append(
                    {
                        "world_id": world_id,
                        "weight": weight,
                        "relevant": 1,
                        "irrelevant": 0,
                    }
                )
        result = analyze_g(
            {
                "pairs": pairs,
                "max_dose_relevant": [1] * 4,
                "max_dose_irrelevant": [0] * 4,
                "hard_gates": {"preclassified": True, "matched_corruption": True},
            }
        )
        self.assertEqual(result["inferential_unit"], "world")
        self.assertEqual(result["randomization_unit"], "world")
        self.assertEqual(result["world_count"], 4)
        self.assertAlmostEqual(
            result["raw_pvalue"],
            g_world_blocked_randomization_pvalue([37] * 4, 148),
        )

    def test_p_restart_and_deletion_boundary_is_mechanically_auditable(self):
        records = run_p_dev_records(8)
        self.assertTrue(records)
        for record in records:
            self.assertEqual(record.cross_restart_state_keys, ("retained_object_bytes",))
            self.assertEqual(len(record.post_restart_environment_digest), 64)
            self.assertEqual(record.future_source_example_reads, 0)
            self.assertEqual(record.future_search_state_reads, 0)
            self.assertEqual(record.future_verifier_state_reads, 0)
            self.assertEqual(record.future_reconstruction_calls, 0)
            self.assertEqual(record.future_acquisition_cache_reads, 0)
            self.assertFalse(record.lineage_present_after_deletion)
            self.assertEqual(record.reacquisition_procedure_id, "P_ACQUIRE_V1")
            self.assertGreater(record.reacquisition_procedure_entries, 0)
            self.assertEqual(record.untracked_regeneration_count, 0)
            self.assertTrue(record.bisimulation_separating_task)

    def test_p_bisimulation_control_and_reacquisition_are_primary_gates(self):
        n = 32
        retained = [1] * n
        cold = [0] * 10 + [1] * 22
        result = analyze_p(
            {
                "retained": retained,
                "baselines": {
                    "cold": cold,
                    "equal_compute_recheck": [0] * 9 + [1] * 23,
                    "verbal_rule_negative": [0] * 11 + [1] * 21,
                    "size_matched_sham": [0] * 12 + [1] * 20,
                    "wrong_class_object": [0] * 13 + [1] * 19,
                    "target_only_bisimulation": [0] * 8 + [1] * 24,
                },
                "hard_gates": {
                    "zero_verifier": True,
                    "zero_search": True,
                    "label_free": True,
                    "source_distinct": True,
                    "restart_boundary_audited": True,
                    "bisimulation_separator_present": True,
                    "lineage_removed": True,
                    "reacquisition_tracked": True,
                    "no_untracked_regeneration": True,
                },
                "post_deletion_accuracy": sum(cold) / n,
                "cold_accuracy": sum(cold) / n,
                "reacquisition_search_count": 1,
                "reacquisition_procedure_entries": 1,
                "untracked_regeneration_count": 0,
            }
        )
        self.assertEqual(result["inferential_unit"], "source_distinct_future_task")
        self.assertIn("target_only_bisimulation", result["component_pvalues"])
        self.assertTrue(result["targeted_deletion_gate"])
        self.assertTrue(result["reacquisition_gate"])


if __name__ == "__main__":
    unittest.main()
