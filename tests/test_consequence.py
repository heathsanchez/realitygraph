import unittest

from realitygraph.consequence import (
    Consequence,
    compile_consequence_model,
    evaluate_consequences,
)
from realitygraph.empirical import EmpiricalDataset, EmpiricalSource
from realitygraph.selective import sealed_split


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


class ConsequenceFrontierTests(unittest.TestCase):
    def test_consequence_membership(self):
        self.assertTrue(Consequence("EXACT", ("A",)).contains("A"))
        self.assertFalse(Consequence("EXACT", ("A",)).contains("B"))
        self.assertTrue(Consequence("SET", ("A", "B")).contains("B"))
        self.assertTrue(Consequence("INTERVAL", low=1.0, high=2.0).contains("1.5"))
        self.assertFalse(Consequence("INTERVAL", low=1.0, high=2.0).contains("3.0"))

    def test_categorical_frontier_can_emit_exact_or_set_without_wrong(self):
        features = []
        targets = []
        for i in range(45):
            features.append((str(i / 100), str(i / 150)))
            targets.append("A")
        for i in range(45):
            features.append((str(5 + i / 100), str(5 + i / 150)))
            targets.append("B")
        for i in range(45):
            features.append((str(10 + i / 100), str(10 + i / 150)))
            targets.append("C")
        dataset = EmpiricalDataset(source(), tuple(features), tuple(targets), "deadbeef")
        split = sealed_split(dataset, "frontier-cat")
        model = compile_consequence_model(split.train, split.calibration)
        result = evaluate_consequences(split.test, model)

        self.assertEqual(result.wrong, 0)
        self.assertGreater(result.informative, 0)

    def test_numeric_intervals_are_nonvacuous_and_cover_supported_future(self):
        # Explicit bracketing fixture: every calibration/test point lies between
        # two observed training states for a linear consequence. The stability
        # gate should therefore retain a zero-extra-margin local envelope.
        train_x = list(range(0, 41, 2))
        cal_x = list(range(1, 40, 2))
        test_x = [i + 0.5 for i in range(0, 40, 2)]

        def make(xs):
            return EmpiricalDataset(
                source("numeric"),
                tuple((str(x), str(x)) for x in xs),
                tuple(str(2 * x + 3) for x in xs),
                "deadbeef",
            )

        train = make(train_x)
        calibration = make(cal_x)
        test = make(test_x)
        model = compile_consequence_model(
            train,
            calibration,
            regression_k=2,
            regression_safety_factor=1.5,
        )
        result = evaluate_consequences(test, model)

        self.assertTrue(model.regression_enabled)
        self.assertEqual(result.wrong, 0)
        self.assertEqual(result.interval, len(test_x))
        self.assertLess(model.regression_radius, model.numeric_target_span)

    def test_unknown_is_allowed_when_numeric_interval_would_be_vacuous(self):
        train = EmpiricalDataset(
            source("numeric"),
            (("0", "0"), ("1", "1"), ("2", "2"), ("3", "3")),
            ("0", "100", "0", "100"),
            "deadbeef",
        )
        calibration = EmpiricalDataset(
            source("numeric"),
            (("0.5", "0.5"), ("2.5", "2.5")),
            ("1000", "-1000"),
            "deadbeef",
        )
        model = compile_consequence_model(train, calibration)
        status = model.predict(("1.5", "1.5"))
        self.assertEqual(status.kind, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
