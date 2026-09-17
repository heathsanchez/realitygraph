import json
import tempfile
import unittest
from pathlib import Path


class FinalCandidateTests(unittest.TestCase):
    def api(self):
        from realitygraph.abgp.final_candidate import build_final_lock_candidate
        return build_final_lock_candidate

    def test_candidate_is_review_only_and_binds_implementation_and_power(self):
        candidate = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        self.assertEqual(candidate['schema'], 'abgp.final-lock-candidate.v1')
        self.assertEqual(candidate['status'], 'REVIEW_PENDING')
        self.assertFalse(candidate['confirmatory_execution_enabled'])
        self.assertFalse(candidate['freeze_authorized'])
        self.assertFalse(candidate['confirmatory_namespace_used'])
        self.assertTrue(candidate['implementation_qualification']['implementation_qualified'])
        self.assertFalse(candidate['planning_proposal']['approved_by_collaborators'])
        self.assertFalse(candidate['planning_proposal']['complete_pass_power_qualified'])
        self.assertEqual(candidate['planning_proposal']['status'], 'JOINT_REVIEW_REQUIRED')
        self.assertEqual(candidate['joint_review_required'], True)

    def test_candidate_requests_only_pre_freeze_joint_decisions(self):
        candidate = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        self.assertEqual(candidate['joint_decisions_requested'], [
            'approve_or_revise_planning_alternatives',
            'approve_B_world_all_four_planning_agreement',
            'approve_P_deletion_closeness_as_mechanical_gate',
            'confirm_text_implementation_consistency',
        ])
        self.assertFalse(candidate['scientific_pass_criteria_changed'])
        self.assertFalse(candidate['sample_counts_changed'])
        self.assertEqual(candidate['confirmatory_namespace_identifier'], 'ABGP-CONFIRM-v1')

    def test_candidate_hashes_every_bound_review_file(self):
        candidate = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        hashes = candidate['bound_file_hashes']
        required = {
            'preregistration/abgp-design-manifest-v1.json',
            'preregistration/abgp-analysis-plan-v1.json',
            'realitygraph/abgp/analysis.py',
            'realitygraph/abgp/executed_a.py',
            'realitygraph/abgp/executed_b.py',
            'realitygraph/abgp/executed_g.py',
            'realitygraph/abgp/executed_p_structural.py',
            'realitygraph/abgp/executed_matrix.py',
            'realitygraph/abgp/implementation_qualification.py',
            'realitygraph/abgp/planning_review.py',
        }
        self.assertTrue(required <= set(hashes))
        self.assertTrue(all(len(value) == 64 for value in hashes.values()))
        self.assertEqual(len(candidate['candidate_digest']), 64)

    def test_writer_is_canonical(self):
        from realitygraph.abgp.final_candidate import write_final_lock_candidate
        candidate = self.api()(a_count=8, b_worlds_per_direction=2, g_worlds=4, p_count=3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.json'
            write_final_lock_candidate(path, candidate)
            text = path.read_text(encoding='utf-8')
            self.assertTrue(text.endswith('\n'))
            self.assertEqual(json.loads(text), candidate)

    def test_confirmatory_namespace_is_rejected(self):
        with self.assertRaises(ValueError):
            self.api()(a_count=4, b_worlds_per_direction=1, g_worlds=2, p_count=1,
                       namespace='ABGP-CONFIRM-v1')


if __name__ == '__main__':
    unittest.main()
