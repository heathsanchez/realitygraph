import unittest

from realitygraph.predictive import (
    PredictiveSplit,
    binary_auc,
    build_probe_field,
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
)


class PredictiveFieldTests(unittest.TestCase):
    def test_rank_auc_matches_pairwise_tie_semantics(self):
        labels = [0, 1, 0, 1, 1, 0]
        scores = [0.1, 0.9, 0.4, 0.4, 0.8, 0.4]
        # Pairwise: positive 0.9 wins all 3, 0.8 wins all 3,
        # positive 0.4 beats 0.1 and ties two 0.4 negatives.
        expected = (3 + 3 + 1 + 1.0) / 9.0
        self.assertAlmostEqual(binary_auc(labels, scores), expected)

    def test_build_field_computes_each_probe_once(self):
        calls = {"stable": 0, "noise": 0}
        states = list(range(6))
        labels = [0, 0, 0, 1, 1, 1]
        groups = ["a", "a", "b", "b", "c", "c"]

        def stable(value):
            calls["stable"] += 1
            return value

        def noise(value):
            calls["noise"] += 1
            return value % 2

        field = build_probe_field(
            states,
            labels,
            groups,
            [("stable", stable), ("noise", noise)],
        )
        self.assertEqual(field.design_predictions, 12)
        self.assertEqual(calls, {"stable": 6, "noise": 6})

    def test_sealed_group_split_is_deterministic_and_group_disjoint(self):
        groups = tuple(f"g{i // 4}" for i in range(40))
        first = sealed_group_split(groups, "commit-a")
        second = sealed_group_split(groups, "commit-a")
        self.assertEqual(first, second)

        train_groups = {groups[i] for i in first.train}
        cal_groups = {groups[i] for i in first.calibration}
        test_groups = {groups[i] for i in first.test}
        self.assertFalse(train_groups & cal_groups)
        self.assertFalse(train_groups & test_groups)
        self.assertFalse(cal_groups & test_groups)

    def test_stable_separator_survives_and_duplicate_is_deleted(self):
        values = []
        labels = []
        groups = []
        for group in range(8):
            for j in range(20):
                label = 1 if j >= 10 else 0
                stable = (2 * label - 1) * 2 + (j % 3) * 0.01
                values.append((stable, stable, float((j * 7 + group) % 11)))
                labels.append(label)
                groups.append(f"g{group}")

        field = field_from_matrix(
            ("stable", "duplicate", "noise"),
            values,
            labels,
            groups,
        )
        split = PredictiveSplit(
            tuple(i for i, group in enumerate(groups) if group in {"g0", "g1", "g2", "g3"}),
            tuple(i for i, group in enumerate(groups) if group in {"g4", "g5"}),
            tuple(i for i, group in enumerate(groups) if group in {"g6", "g7"}),
            "fixed",
        )
        certificate = certify_predictive_batch(
            field,
            split,
            max_probes=3,
            min_calibration_gain=1e-3,
            min_sealed_gain=1e-3,
        )

        self.assertTrue(certificate.accepted)
        names = [rule.probe_name for rule in certificate.plan.rules]
        self.assertEqual(len(names), 1)
        self.assertIn(names[0], {"stable", "duplicate"})
        self.assertGreater(certificate.plan.ablation_log_loss_delta[0][1], 0.5)
        self.assertLess(certificate.sealed_metrics.log_loss, 0.05)
        self.assertEqual(certificate.sealed_metrics.auc, 1.0)

    def test_sealed_future_rejects_calibration_perfect_trap(self):
        values = []
        labels = []
        groups = []
        train_groups = {"g0", "g1", "g2"}
        cal_groups = {"g3"}
        test_groups = {"g4", "g5"}

        for group in ["g0", "g1", "g2", "g3", "g4", "g5"]:
            for j in range(20):
                label = 1 if j >= 10 else 0
                trap = label if group in train_groups | cal_groups else 1 - label
                values.append((float(trap),))
                labels.append(label)
                groups.append(group)

        field = field_from_matrix(("site-trap",), values, labels, groups)
        split = PredictiveSplit(
            tuple(i for i, group in enumerate(groups) if group in train_groups),
            tuple(i for i, group in enumerate(groups) if group in cal_groups),
            tuple(i for i, group in enumerate(groups) if group in test_groups),
            "trap",
        )
        certificate = certify_predictive_batch(
            field,
            split,
            max_probes=1,
            min_calibration_gain=1e-3,
            min_sealed_gain=1e-3,
        )

        self.assertFalse(certificate.accepted)
        self.assertLess(certificate.plan.calibration_metrics.log_loss, 0.05)
        self.assertGreater(
            certificate.sealed_metrics.log_loss,
            certificate.sealed_baseline_metrics.log_loss,
        )


if __name__ == "__main__":
    unittest.main()
