import unittest

from realitygraph.empirical import (
    EmpiricalDataset,
    EmpiricalSource,
    compile_identity,
    design_target_batch,
    evaluate_target_plan,
    parse_dataset,
)
from realitygraph.empirical_sources import uci_sources


class EmpiricalTests(unittest.TestCase):
    def test_sources_are_public_licensed_and_distinct(self):
        sources = uci_sources()
        self.assertGreaterEqual(len(sources), 8)
        self.assertEqual(len({source.name for source in sources}), len(sources))
        self.assertTrue(all(source.license == "CC BY 4.0" for source in sources))
        self.assertTrue(all(source.url.startswith("https://archive.ics.uci.edu/") for source in sources))
        self.assertTrue(all(source.doi.startswith("10.24432/") for source in sources))

    def test_identity_quotients_exact_duplicate_measurements(self):
        source = EmpiricalSource(
            "tiny",
            "test",
            "https://archive.ics.uci.edu/example",
            "10.24432/TEST",
            "iris",
            ("a", "b", "c", "d"),
            "target",
        )
        dataset = EmpiricalDataset(
            source,
            (
                ("1", "2", "3", "4"),
                ("1", "2", "3", "4"),
                ("1", "2", "9", "4"),
            ),
            ("x", "x", "y"),
            "deadbeef",
        )
        model, _ = compile_identity(dataset)
        self.assertEqual(len(model.representative_rows), 2)
        self.assertEqual(model.identify_row(0)[0], "UNKNOWN")
        self.assertEqual(model.identify_row(1)[0], "UNKNOWN")
        self.assertEqual(model.identify_row(2)[0], "IDENTIFIED")

    def test_target_kernel_uses_goal_coarser_than_full_identity(self):
        source = EmpiricalSource(
            "tiny",
            "test",
            "https://archive.ics.uci.edu/example",
            "10.24432/TEST",
            "iris",
            ("a", "b", "c", "d"),
            "target",
        )
        dataset = EmpiricalDataset(
            source,
            (
                ("0", "0", "alpha", "1"),
                ("1", "0", "alpha", "2"),
                ("0", "1", "beta", "1"),
                ("1", "1", "beta", "2"),
            ),
            ("A", "A", "B", "B"),
            "deadbeef",
        )
        identity, _ = compile_identity(dataset)
        target = design_target_batch(dataset)
        correct, unknown, wrong = evaluate_target_plan(dataset, target)

        self.assertGreater(len(identity.feature_indices), len(target.feature_indices))
        self.assertEqual((correct, unknown, wrong), (4, 0, 0))
        self.assertEqual(len(target.feature_indices), 1)

    def test_conflicting_identical_measurements_become_unknown(self):
        source = EmpiricalSource(
            "tiny",
            "test",
            "https://archive.ics.uci.edu/example",
            "10.24432/TEST",
            "iris",
            ("a", "b", "c", "d"),
            "target",
        )
        dataset = EmpiricalDataset(
            source,
            (
                ("1", "2", "3", "4"),
                ("1", "2", "3", "4"),
                ("9", "2", "3", "4"),
            ),
            ("A", "B", "A"),
            "deadbeef",
        )
        target = design_target_batch(dataset)
        correct, unknown, wrong = evaluate_target_plan(dataset, target)

        self.assertEqual(wrong, 0)
        self.assertEqual(unknown, 2)
        self.assertEqual(correct, 1)
        self.assertGreater(target.unresolved_rows, 0)

    def test_real_parsers_have_declared_width(self):
        iris = uci_sources()[0]
        features, targets = parse_dataset(
            iris,
            "5.1,3.5,1.4,0.2,Iris-setosa\n"
            "6.3,3.3,6.0,2.5,Iris-virginica\n",
        )
        self.assertEqual(len(features), 2)
        self.assertEqual(len(features[0]), 4)
        self.assertEqual(targets, ["Iris-setosa", "Iris-virginica"])


if __name__ == "__main__":
    unittest.main()
