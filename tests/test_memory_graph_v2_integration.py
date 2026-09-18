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
from realitygraph.memory_graph import MemoryGraphV2, MemoryRevocation
from realitygraph.meta_executor import execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase, RepairRuleStatus


class MemoryGraphV2MetaGrowthIntegrationTests(unittest.TestCase):
    def _qualified_present(self):
        memory = MetaMemory.empty()

        c_acq_bundle = make_episode(
            FAMILY_C, "acquisition", RepairPhase.ACQUISITION
        )
        c_acq = execute_meta_growth(
            c_acq_bundle.state, memory, c_acq_bundle.spec
        )
        memory = c_acq.meta_memory

        t_acq_bundle = make_episode(
            FAMILY_T, "acquisition", RepairPhase.ACQUISITION
        )
        t_acq = execute_meta_growth(
            t_acq_bundle.state, memory, t_acq_bundle.spec
        )
        memory = t_acq.meta_memory

        c_cal_bundle = make_episode(
            FAMILY_C, "calibration", RepairPhase.CALIBRATION
        )
        c_cal = execute_meta_growth(
            c_cal_bundle.state, memory, c_cal_bundle.spec
        )
        memory = c_cal.meta_memory

        t_cal_bundle = make_episode(
            FAMILY_T, "calibration", RepairPhase.CALIBRATION
        )
        t_cal = execute_meta_growth(
            t_cal_bundle.state, memory, t_cal_bundle.spec
        )
        promoted_memory = t_cal.meta_memory

        promoted = tuple(
            rule for rule in promoted_memory.rules
            if rule.status is RepairRuleStatus.PROMOTED
        )
        self.assertEqual(len(promoted), 2)

        c_capability = c_cal.selected_generation.capability
        t_capability = t_cal.selected_generation.capability
        self.assertIsNotNone(c_capability)
        self.assertIsNotNone(t_capability)
        object_graph = CapabilityGraph((c_capability, t_capability))

        combined = MemoryGraphV2.from_capability_graph(object_graph).merge(
            MemoryGraphV2.from_meta_memory(promoted_memory)
        )
        return combined, object_graph, promoted_memory

    def test_combined_mg2_restart_preserves_object_and_meta_active_views(self):
        combined, object_graph, promoted_memory = self._qualified_present()

        restarted = MemoryGraphV2.parse(combined.text())
        self.assertEqual(restarted.text(), combined.text())
        self.assertEqual(restarted.digest, combined.digest)

        restored_graph = restarted.to_capability_graph()
        restored_meta = restarted.to_meta_memory()

        self.assertEqual(
            restored_graph.active_ids(),
            object_graph.active_ids(),
        )
        self.assertEqual(
            {rule.rule_id for rule in restored_meta.rules},
            {
                rule.rule_id
                for rule in promoted_memory.rules
                if rule.status is RepairRuleStatus.PROMOTED
            },
        )
        self.assertEqual(restored_meta.episodes, ())

    def test_restarted_mg2_preserves_untouched_future_zero_search_routes(self):
        combined, _object_graph, _promoted_memory = self._qualified_present()
        restarted_meta = MemoryGraphV2.parse(combined.text()).to_meta_memory()

        c_future_bundle = make_episode(
            FAMILY_C, "future", RepairPhase.FUTURE
        )
        c_future = execute_meta_growth(
            c_future_bundle.state, restarted_meta, c_future_bundle.spec
        )
        t_future_bundle = make_episode(
            FAMILY_T, "future", RepairPhase.FUTURE
        )
        t_future = execute_meta_growth(
            t_future_bundle.state, restarted_meta, t_future_bundle.spec
        )

        self.assertTrue(c_future.rule_hit)
        self.assertTrue(t_future.rule_hit)
        self.assertEqual(c_future.selected_strategy_id, ADD_OBSERVABLE)
        self.assertEqual(t_future.selected_strategy_id, ADD_FINITE_MEMORY_2)
        self.assertEqual(c_future.portfolio_search_calls, 0)
        self.assertEqual(t_future.portfolio_search_calls, 0)
        self.assertEqual(c_future.competitor_strategy_calls, 0)
        self.assertEqual(t_future.competitor_strategy_calls, 0)
        self.assertEqual(
            c_future.selected_generation.future.grammar_search_calls,
            0,
        )
        self.assertEqual(
            t_future.selected_generation.future.grammar_search_calls,
            0,
        )

    def test_mg2_rule_revocation_restores_cold_search(self):
        combined, _object_graph, promoted_memory = self._qualified_present()

        c_rule = next(
            rule for rule in promoted_memory.rules
            if rule.status is RepairRuleStatus.PROMOTED
            and rule.strategy_id == ADD_OBSERVABLE
        )
        t_rule = next(
            rule for rule in promoted_memory.rules
            if rule.status is RepairRuleStatus.PROMOTED
            and rule.strategy_id == ADD_FINITE_MEMORY_2
        )

        for family, rule in (
            (FAMILY_C, c_rule),
            (FAMILY_T, t_rule),
        ):
            revoked = combined.merge(
                MemoryGraphV2(
                    revocations=(
                        MemoryRevocation(
                            "repair_rule",
                            rule.rule_id,
                            "integration-ablation",
                        ),
                    )
                )
            )
            restarted_meta = MemoryGraphV2.parse(
                revoked.text()
            ).to_meta_memory()
            future_bundle = make_episode(
                family, "future", RepairPhase.FUTURE
            )
            future = execute_meta_growth(
                future_bundle.state,
                restarted_meta,
                future_bundle.spec,
            )
            self.assertFalse(future.rule_hit)
            self.assertGreater(future.portfolio_search_calls, 0)

    def test_mg2_capability_revocation_preserves_dependency_ablation_semantics(self):
        combined, object_graph, _promoted_memory = self._qualified_present()
        target = object_graph.active_ids()[0]

        revoked = combined.merge(
            MemoryGraphV2(
                revocations=(
                    MemoryRevocation(
                        "capability",
                        target,
                        "integration-ablation",
                    ),
                )
            )
        )
        restored = MemoryGraphV2.parse(revoked.text()).to_capability_graph()

        self.assertEqual(
            restored.active_ids(),
            object_graph.ablate(target).active_ids(),
        )


if __name__ == "__main__":
    unittest.main()
