import unittest

from realitygraph.abgp.arm_p import (
    RetainedStructure,
    acquire_dev_structure,
    run_p_dev_records,
)


class ABGPArmPTests(unittest.TestCase):
    def test_retained_structure_restart_is_byte_exact(self):
        structure = acquire_dev_structure()
        text = structure.to_text()
        restored = RetainedStructure.from_text(text)
        self.assertEqual(restored, structure)
        self.assertEqual(restored.to_text(), text)
        self.assertEqual(restored.digest, structure.digest)

    def test_future_boundary_has_zero_verifier_and_zero_search(self):
        records = run_p_dev_records(24)
        for record in records:
            self.assertEqual(record.future_verifier_calls, 0)
            self.assertEqual(record.future_reconstruction_search_count, 0)
            self.assertFalse(record.applicability_used_target_labels)
            self.assertTrue(record.source_distinct)
            self.assertFalse(record.forbidden_shared_features)

    def test_sham_wrong_class_and_targeted_deletion_are_causal_controls(self):
        records = run_p_dev_records(24)
        for record in records:
            self.assertNotEqual(record.retained_object_digest, record.sham_object_digest)
            self.assertNotEqual(record.retained_object_digest, record.wrong_class_object_digest)
            self.assertGreater(record.reacquisition_search_count_after_deletion, 0)
            self.assertEqual(record.post_deletion_correct, record.cold_correct)

    def test_p_is_deterministic_from_dev_seeds(self):
        self.assertEqual(run_p_dev_records(16), run_p_dev_records(16))


if __name__ == "__main__":
    unittest.main()
