import unittest

from realitygraph.abgp.arm_a import generate_a_dev_records
from realitygraph.abgp.arm_g import generate_g_dev_records


class ABGPArmAGTests(unittest.TestCase):
    def test_a_messages_are_nonidentifying_and_budgeted(self):
        records = generate_a_dev_records(24)
        self.assertEqual(len(records), 24)
        for record in records:
            self.assertGreater(record.compatible_optimal_action_count, 1)
            self.assertEqual(record.verifier_message_count, 1)
            self.assertEqual(record.repair_round_count, 1)
            self.assertEqual(record.equal_compute_units, record.verifier_compute_units)
            self.assertTrue(record.seed_digest)

    def test_a_is_deterministic_from_dev_seeds(self):
        self.assertEqual(generate_a_dev_records(16), generate_a_dev_records(16))

    def test_g_preclassifies_and_matches_corruption(self):
        records = generate_g_dev_records(8)
        self.assertEqual(len(records), 8 * 5)
        by_world = {}
        for record in records:
            by_world.setdefault(record.world_index, []).append(record)
            self.assertTrue(record.relevance_computed_before_corruption)
            self.assertEqual(record.relevant_corruption_count, record.irrelevant_corruption_count)
            self.assertEqual(record.relevant_corruption_magnitude, record.irrelevant_corruption_magnitude)
            self.assertTrue(record.seed_digest)
            if record.dose > 0:
                self.assertGreater(record.relevant_corruption_count, 0)
        for world_records in by_world.values():
            self.assertEqual(
                [r.dose for r in sorted(world_records, key=lambda r: r.dose)],
                [0.0, 0.1, 0.25, 0.5, 1.0],
            )

    def test_g_is_deterministic_from_dev_seeds(self):
        self.assertEqual(generate_g_dev_records(6), generate_g_dev_records(6))


if __name__ == "__main__":
    unittest.main()
