import unittest
from dataclasses import dataclass

from realitygraph.repair_strategy import RepairPortfolio


@dataclass(frozen=True)
class StubStrategy:
    strategy_id: str
    structural_cost: int
    strategy_version: str = "v1"

    def applicable(self, fingerprint, object_state, meta_spec):
        return True

    def materialize_generation_spec(self, object_state, meta_spec):
        raise AssertionError("portfolio identity test must not materialize a spec")


class RepairStrategyTests(unittest.TestCase):
    def test_portfolio_digest_is_order_independent(self):
        first = RepairPortfolio((StubStrategy("s1", 1), StubStrategy("s2", 2)))
        reversed_order = RepairPortfolio((StubStrategy("s2", 2), StubStrategy("s1", 1)))
        self.assertEqual(first.digest, reversed_order.digest)
        self.assertEqual(first.strategy_ids, ("s1", "s2"))
        self.assertEqual(reversed_order.strategy_ids, ("s1", "s2"))

    def test_duplicate_strategy_id_is_rejected(self):
        with self.assertRaises(ValueError):
            RepairPortfolio((StubStrategy("same", 1), StubStrategy("same", 2)))

    def test_portfolio_digest_changes_with_version_or_structural_cost(self):
        base = RepairPortfolio((StubStrategy("s1", 1, "v1"),))
        changed_version = RepairPortfolio((StubStrategy("s1", 1, "v2"),))
        changed_cost = RepairPortfolio((StubStrategy("s1", 2, "v1"),))
        self.assertNotEqual(base.digest, changed_version.digest)
        self.assertNotEqual(base.digest, changed_cost.digest)

    def test_invalid_strategy_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            RepairPortfolio((StubStrategy("", 1),))
        with self.assertRaises(ValueError):
            RepairPortfolio((StubStrategy("s1", -1),))
        with self.assertRaises(ValueError):
            RepairPortfolio((StubStrategy("s1", 1, ""),))

    def test_lookup_is_by_explicit_identity_not_position(self):
        portfolio = RepairPortfolio((StubStrategy("later", 9), StubStrategy("earlier", 1)))
        self.assertEqual(portfolio.get("later").structural_cost, 9)
        self.assertEqual(portfolio.get("earlier").structural_cost, 1)
        with self.assertRaises(ValueError):
            portfolio.get("missing")


if __name__ == "__main__":
    unittest.main()
