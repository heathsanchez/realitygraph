import unittest
from dataclasses import dataclass

from realitygraph.transfer import assess_transfer


@dataclass
class Metrics:
    log_loss: float
    max_group_harm: float = 0.0


@dataclass
class Rule:
    probe_name: str


@dataclass
class Plan:
    rules: tuple[Rule, ...]


@dataclass
class Certificate:
    accepted: bool
    sealed_baseline_metrics: Metrics
    sealed_metrics: Metrics
    plan: Plan


def cert(accepted, baseline, candidate, harm=0.0, probes=("x",)):
    return Certificate(
        accepted,
        Metrics(baseline),
        Metrics(candidate, harm),
        Plan(tuple(Rule(name) for name in probes)),
    )


class TransferAssessmentTests(unittest.TestCase):
    def test_row_success_group_failure_is_leakage_dependent(self):
        row = cert(True, 0.7, 0.4, probes=("subject-proxy",))
        group = cert(False, 0.8, 0.75, harm=0.2, probes=("subject-proxy",))
        result = assess_transfer(row, group)
        self.assertEqual(result.status, "LEAKAGE_DEPENDENT")
        self.assertTrue(result.leakage_dependent)
        self.assertFalse(result.transferable)

    def test_group_safe_success_is_transferable(self):
        row = cert(True, 0.7, 0.5, probes=("light",))
        group = cert(True, 0.8, 0.2, harm=0.0, probes=("light", "temperature"))
        result = assess_transfer(row, group)
        self.assertEqual(result.status, "TRANSFERABLE")
        self.assertTrue(result.transferable)
        self.assertGreater(result.group_gain, 0.0)

    def test_neither_success_is_unresolved(self):
        row = cert(False, 0.7, 0.7)
        group = cert(False, 0.8, 0.8)
        result = assess_transfer(row, group)
        self.assertEqual(result.status, "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
