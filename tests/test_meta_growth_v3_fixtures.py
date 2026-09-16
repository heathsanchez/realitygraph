import unittest

from realitygraph.meta_executor import MetaGrowthRoute, execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase, RepairRuleStatus
from realitygraph.fixtures.meta_growth_v3 import (
    ADD_FINITE_MEMORY_2,
    ADD_FINITE_MEMORY_3,
    ADD_OBSERVABLE,
    FAMILY_C,
    FAMILY_T,
    DEEPEN_STATELESS_COMPOSITION,
    episode_fingerprint,
    frozen_portfolio,
    make_episode,
    make_tie_control,
)


class MetaGrowthV3FixtureTests(unittest.TestCase):
    def test_family_variants_share_fingerprint_but_families_differ(self):
        c_acq = make_episode(FAMILY_C, "acquisition", RepairPhase.ACQUISITION)
        c_cal = make_episode(FAMILY_C, "calibration", RepairPhase.CALIBRATION)
        c_future = make_episode(FAMILY_C, "future", RepairPhase.FUTURE)
        t_acq = make_episode(FAMILY_T, "acquisition", RepairPhase.ACQUISITION)
        t_cal = make_episode(FAMILY_T, "calibration", RepairPhase.CALIBRATION)
        t_future = make_episode(FAMILY_T, "future", RepairPhase.FUTURE)

        c_digests = {episode_fingerprint(bundle).digest for bundle in (c_acq, c_cal, c_future)}
        t_digests = {episode_fingerprint(bundle).digest for bundle in (t_acq, t_cal, t_future)}
        self.assertEqual(len(c_digests), 1)
        self.assertEqual(len(t_digests), 1)
        self.assertNotEqual(next(iter(c_digests)), next(iter(t_digests)))

    def test_surface_carriers_are_disjoint_across_episode_variants(self):
        for family in (FAMILY_C, FAMILY_T):
            bundles = [
                make_episode(family, variant, phase)
                for variant, phase in (
                    ("acquisition", RepairPhase.ACQUISITION),
                    ("calibration", RepairPhase.CALIBRATION),
                    ("future", RepairPhase.FUTURE),
                )
            ]
            carriers = [set(bundle.world.carrier) for bundle in bundles]
            self.assertTrue(carriers[0].isdisjoint(carriers[1]))
            self.assertTrue(carriers[0].isdisjoint(carriers[2]))
            self.assertTrue(carriers[1].isdisjoint(carriers[2]))

    def test_frozen_portfolio_has_four_distinct_repair_families(self):
        portfolio = frozen_portfolio()
        self.assertEqual(
            set(portfolio.strategy_ids),
            {
                DEEPEN_STATELESS_COMPOSITION,
                ADD_OBSERVABLE,
                ADD_FINITE_MEMORY_2,
                ADD_FINITE_MEMORY_3,
            },
        )
        self.assertLess(
            portfolio.get(ADD_FINITE_MEMORY_2).structural_cost,
            portfolio.get(ADD_FINITE_MEMORY_3).structural_cost,
        )

    def test_family_c_cold_winner_is_add_observable(self):
        bundle = make_episode(FAMILY_C, "acquisition", RepairPhase.ACQUISITION)
        result = execute_meta_growth(bundle.state, MetaMemory.empty(), bundle.spec)
        self.assertEqual(result.route, MetaGrowthRoute.COMPILED)
        self.assertEqual(result.selected_strategy_id, ADD_OBSERVABLE)
        attempted = {attempt.strategy_id: attempt for attempt in result.attempts}
        self.assertIn(DEEPEN_STATELESS_COMPOSITION, attempted)
        self.assertFalse(attempted[DEEPEN_STATELESS_COMPOSITION].successful)
        self.assertNotIn(ADD_FINITE_MEMORY_2, attempted)
        self.assertNotIn(ADD_FINITE_MEMORY_3, attempted)

    def test_family_t_cold_winner_is_two_state_memory(self):
        bundle = make_episode(FAMILY_T, "acquisition", RepairPhase.ACQUISITION)
        result = execute_meta_growth(bundle.state, MetaMemory.empty(), bundle.spec)
        self.assertEqual(result.route, MetaGrowthRoute.COMPILED)
        self.assertEqual(result.selected_strategy_id, ADD_FINITE_MEMORY_2)
        attempted = {attempt.strategy_id: attempt for attempt in result.attempts}
        self.assertFalse(attempted[DEEPEN_STATELESS_COMPOSITION].successful)
        self.assertFalse(attempted[ADD_OBSERVABLE].successful)
        self.assertTrue(attempted[ADD_FINITE_MEMORY_2].successful)
        self.assertTrue(attempted[ADD_FINITE_MEMORY_3].successful)
        self.assertLess(
            attempted[ADD_FINITE_MEMORY_2].structural_cost,
            attempted[ADD_FINITE_MEMORY_3].structural_cost,
        )

    def test_acquisition_then_calibration_promotes_family_rule(self):
        memory = MetaMemory.empty()
        acquisition = make_episode(FAMILY_C, "acquisition", RepairPhase.ACQUISITION)
        acquired = execute_meta_growth(acquisition.state, memory, acquisition.spec)
        self.assertEqual(acquired.meta_memory.rules[0].status, RepairRuleStatus.CANDIDATE)

        calibration = make_episode(FAMILY_C, "calibration", RepairPhase.CALIBRATION)
        calibrated = execute_meta_growth(calibration.state, acquired.meta_memory, calibration.spec)
        self.assertEqual(calibrated.meta_memory.rules[0].status, RepairRuleStatus.PROMOTED)
        self.assertEqual(calibrated.meta_memory.rules[0].strategy_id, ADD_OBSERVABLE)

    def test_future_rule_hit_synthesizes_new_capability(self):
        memory = MetaMemory.empty()
        source = make_episode(FAMILY_C, "acquisition", RepairPhase.ACQUISITION)
        source_result = execute_meta_growth(source.state, memory, source.spec)
        calibration = make_episode(FAMILY_C, "calibration", RepairPhase.CALIBRATION)
        calibration_result = execute_meta_growth(
            calibration.state, source_result.meta_memory, calibration.spec
        )
        future = make_episode(FAMILY_C, "future", RepairPhase.FUTURE)
        future_result = execute_meta_growth(
            future.state, calibration_result.meta_memory, future.spec
        )
        self.assertTrue(future_result.rule_hit)
        self.assertEqual(future_result.portfolio_search_calls, 0)
        self.assertEqual(future_result.competitor_strategy_calls, 0)
        self.assertEqual(future_result.selected_strategy_calls, 1)
        self.assertNotEqual(
            source_result.selected_generation.capability.capability_id,
            future_result.selected_generation.capability.capability_id,
        )

    def test_partial_current_language_and_partial_portfolio_fail_closed(self):
        partial_language = make_episode(
            FAMILY_C, "partial", RepairPhase.CONTROL, current_complete=False
        )
        result = execute_meta_growth(partial_language.state, MetaMemory.empty(), partial_language.spec)
        self.assertEqual(result.route, MetaGrowthRoute.UNKNOWN_SEARCH)
        self.assertEqual(result.portfolio_search_calls, 0)

        partial_portfolio = make_episode(
            FAMILY_T, "budget", RepairPhase.CONTROL, portfolio_budget=2
        )
        result = execute_meta_growth(partial_portfolio.state, MetaMemory.empty(), partial_portfolio.spec)
        self.assertEqual(result.route, MetaGrowthRoute.UNKNOWN_SEARCH)
        self.assertEqual(result.object_state.digest, partial_portfolio.state.digest)

    def test_tied_repair_control_preserves_unknown_choice(self):
        bundle = make_tie_control()
        result = execute_meta_growth(bundle.state, MetaMemory.empty(), bundle.spec)
        self.assertEqual(result.route, MetaGrowthRoute.UNKNOWN_CHOICE)
        self.assertIsNone(result.selected_strategy_id)
        self.assertEqual(result.object_state.digest, bundle.state.digest)


if __name__ == "__main__":
    unittest.main()
