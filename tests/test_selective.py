import unittest

from realitygraph.empirical import EmpiricalDataset, EmpiricalSource
from realitygraph.selective import (
    compile_selective_model,
    evaluate_selective,
    sealed_split,
)


def source(kind="categorical"):
    return EmpiricalSource(
        "tiny",
        "test",
        "https://archive.ics.uci.edu/example",
        "10.24432/TEST",
        "iris",
        ("x", "y"),
        "target",
        "CC BY 4.0",
        "deadbeef",
        kind,
    )


class SelectiveFutureTests(unittest.TestCase):
    def test_sealed_split_is_deterministic_and_seed_sensitive(self):
        dataset = EmpiricalDataset(
            source(),
            tuple((str(i), str(i % 3)) for i in range(30)),
            tuple("A" if i % 2 == 0 else "B" for i in range(30)),
            "deadbeef",
        )
        a = sealed_split(dataset, "commit-a")
        b = sealed_split(dataset, "commit-a")
        c = sealed_split(dataset, "commit-b")

        self.assertEqual(a.train.features, b.train.features)
        self.assertEqual(a.test.features, b.test.features)
        self.assertNotEqual(a.test.features, c.test.features)
        self.assertEqual(
            len(a.train.features) + len(a.calibration.features) + len(a.test.features),
            30,
        )

    def test_categorical_certificates_can_accept_supported_future(self):
        features = []
        targets = []
        for i in range(30):
            features.append((str(i / 100), str(i / 200)))
            targets.append("A")
        for i in range(30):
            features.append((str(10 + i / 100), str(10 + i / 200)))
            targets.append("B")
        dataset = EmpiricalDataset(source(), tuple(features), tuple(targets), "deadbeef")
        split = sealed_split(dataset, "clustered")
        model = compile_selective_model(split.train, split.calibration)
        result = evaluate_selective(split.test, model)

        self.assertEqual(result.wrong, 0)
        self.assertGreater(result.correct, 0)
        self.assertGreater(len(model.balls), 0)

    def test_numeric_future_requires_repeated_exact_state(self):
        dataset = EmpiricalDataset(
            source("numeric"),
            (
                ("1", "2"),
                ("1", "2"),
                ("1", "2"),
                ("9", "9"),
                ("9", "9"),
                ("9", "9"),
                ("7", "7"),
                ("8", "8"),
                ("6", "6"),
                ("5", "5"),
            ),
            ("3", "3", "3", "4", "4", "4", "1", "2", "5", "6"),
            "deadbeef",
        )
        split = sealed_split(dataset, "numeric")
        model = compile_selective_model(split.train, split.calibration)
        result = evaluate_selective(split.test, model)

        self.assertEqual(result.wrong, 0)
        self.assertEqual(result.correct + result.unknown, result.total)

    def test_conflicting_ball_votes_abstain(self):
        # Directly exercise the public predictor invariant via a model learned
        # from overlapping evidence: any conflict must route to UNKNOWN.
        dataset = EmpiricalDataset(
            source(),
            (
                ("0.0", "0.0"),
                ("0.1", "0.0"),
                ("0.2", "0.0"),
                ("1.0", "1.0"),
                ("1.1", "1.0"),
                ("1.2", "1.0"),
                ("0.05", "0.0"),
                ("1.05", "1.0"),
                ("0.15", "0.0"),
                ("1.15", "1.0"),
            ),
            ("A", "A", "A", "B", "B", "B", "A", "B", "A", "B"),
            "deadbeef",
        )
        split = sealed_split(dataset, "abstain")
        model = compile_selective_model(split.train, split.calibration)
        result = evaluate_selective(split.test, model)
        self.assertEqual(result.wrong, 0)


if __name__ == "__main__":
    unittest.main()
