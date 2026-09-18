from __future__ import annotations

import unittest

from realitygraph.capability_graph import CapabilityGraph
from realitygraph.compiled_present import CompiledPresent
from realitygraph.fixtures.meta_growth_v3 import (
    ADD_OBSERVABLE,
    FAMILY_C,
    make_episode,
)
from realitygraph.meta_executor import execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase, RepairRuleStatus


class CompiledPresentTests(unittest.TestCase):
    def _present(self):
        memory = MetaMemory.empty()

        acquisition = make_episode(
            FAMILY_C, "acquisition", RepairPhase.ACQUISITION
        )
        acquired = execute_meta_growth(
            acquisition.state, memory, acquisition.spec
        )

        calibration = make_episode(
            FAMILY_C, "calibration", RepairPhase.CALIBRATION
        )
        calibrated = execute_meta_growth(
            calibration.state, acquired.meta_memory, calibration.spec
        )

        capability = calibrated.selected_generation.capability
        self.assertIsNotNone(capability)
        graph = CapabilityGraph((capability,))
        present = CompiledPresent.compile(graph, calibrated.meta_memory)
        return present, calibrated.meta_memory

    def test_restart_is_exact_and_history_free(self):
        present, _memory = self._present()
        restarted = present.restart()

        self.assertEqual(restarted.text(), present.text())
        self.assertEqual(restarted.digest, present.digest)
        self.assertEqual(restarted.meta_memory.episodes, ())
        self.assertEqual(
            restarted.capability_graph.active_ids(),
            present.capability_graph.active_ids(),
        )

    def test_future_execution_uses_compiled_rule_without_portfolio_search(self):
        present, _memory = self._present()
        future = make_episode(
            FAMILY_C, "future", RepairPhase.FUTURE
        )
        result = present.restart().execute_future_meta(
            future.state, future.spec
        )

        self.assertTrue(result.rule_hit)
        self.assertEqual(result.selected_strategy_id, ADD_OBSERVABLE)
        self.assertEqual(result.portfolio_search_calls, 0)
        self.assertEqual(result.competitor_strategy_calls, 0)

    def test_rule_revocation_restores_cold_path(self):
        present, memory = self._present()
        rule = next(
            rule for rule in memory.rules
            if rule.status is RepairRuleStatus.PROMOTED
        )

        cold = present.revoke_repair_rule(
            rule.rule_id,
            provenance="unit-ablation",
        )
        future = make_episode(
            FAMILY_C, "future", RepairPhase.FUTURE
        )
        result = cold.restart().execute_future_meta(
            future.state, future.spec
        )

        self.assertFalse(result.rule_hit)
        self.assertGreater(result.portfolio_search_calls, 0)


if __name__ == "__main__":
    unittest.main()
