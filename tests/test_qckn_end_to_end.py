from __future__ import annotations

import unittest

from realitygraph.capability_graph import CapabilityGraph
from realitygraph.fixtures.meta_growth_v3 import (
    ADD_FINITE_MEMORY_2,
    ADD_OBSERVABLE,
    FAMILY_C,
    FAMILY_T,
    make_episode,
)
from realitygraph.ledger import Ledger
from realitygraph.meta_executor import execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase, RepairRuleStatus


class QCKNEndToEndTests(unittest.TestCase):
    def _causal_present(self):
        memory = MetaMemory.empty()

        c_acq = make_episode(FAMILY_C, "acquisition", RepairPhase.ACQUISITION)
        c_acquired = execute_meta_growth(c_acq.state, memory, c_acq.spec)
        memory = c_acquired.meta_memory

        t_acq = make_episode(FAMILY_T, "acquisition", RepairPhase.ACQUISITION)
        t_acquired = execute_meta_growth(t_acq.state, memory, t_acq.spec)
        memory = t_acquired.meta_memory

        c_cal = make_episode(FAMILY_C, "calibration", RepairPhase.CALIBRATION)
        c_calibrated = execute_meta_growth(c_cal.state, memory, c_cal.spec)
        memory = c_calibrated.meta_memory

        t_cal = make_episode(FAMILY_T, "calibration", RepairPhase.CALIBRATION)
        t_calibrated = execute_meta_growth(t_cal.state, memory, t_cal.spec)
        promoted = t_calibrated.meta_memory

        c_cap = c_calibrated.selected_generation.capability
        t_cap = t_calibrated.selected_generation.capability
        self.assertIsNotNone(c_cap)
        self.assertIsNotNone(t_cap)

        graph = CapabilityGraph((c_cap, t_cap))
        rules = tuple(
            rule for rule in promoted.rules
            if rule.status is RepairRuleStatus.PROMOTED
        )
        self.assertEqual(len(rules), 2)

        ledger = Ledger()
        for capability in sorted(graph.capabilities, key=lambda item: item.capability_id):
            ledger.append_promote_capability(capability, "qckn-e2e")
        for rule in sorted(rules, key=lambda item: item.rule_id):
            ledger.append_promote_repair_rule(rule, "qckn-e2e")

        return ledger, rules

    def test_causal_present_restarts_and_reuses_both_repairs_without_search(self):
        ledger, _rules = self._causal_present()
        present = ledger.materialize_compiled_present().restart()

        for family, expected in (
            (FAMILY_C, ADD_OBSERVABLE),
            (FAMILY_T, ADD_FINITE_MEMORY_2),
        ):
            future = make_episode(family, "future", RepairPhase.FUTURE)
            result = present.execute_future_meta(future.state, future.spec)
            self.assertTrue(result.rule_hit)
            self.assertEqual(result.selected_strategy_id, expected)
            self.assertEqual(result.portfolio_search_calls, 0)
            self.assertEqual(result.competitor_strategy_calls, 0)
            self.assertEqual(
                result.selected_generation.future.grammar_search_calls,
                0,
            )

    def test_causal_revocation_restores_search_after_restart(self):
        ledger, rules = self._causal_present()
        c_rule = next(rule for rule in rules if rule.strategy_id == ADD_OBSERVABLE)

        ablated = Ledger(ledger.events.values())
        ablated.append_revoke_repair_rule(
            c_rule.rule_id,
            "qckn-e2e",
            reason="ablation",
        )
        present = ablated.materialize_compiled_present().restart()

        future = make_episode(FAMILY_C, "future", RepairPhase.FUTURE)
        result = present.execute_future_meta(future.state, future.spec)
        self.assertFalse(result.rule_hit)
        self.assertGreater(result.portfolio_search_calls, 0)


if __name__ == "__main__":
    unittest.main()
