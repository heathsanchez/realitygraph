from __future__ import annotations

import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.fixtures.meta_growth_v3 import (
    ADD_OBSERVABLE,
    FAMILY_C,
    make_episode,
)
from realitygraph.ledger import Ledger
from realitygraph.meta_executor import execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase, RepairRuleStatus


class CausalCompiledPresentTests(unittest.TestCase):
    def _qualified_family_c(self):
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
            calibration.state,
            acquired.meta_memory,
            calibration.spec,
        )

        capability = calibrated.selected_generation.capability
        self.assertIsNotNone(capability)
        rule = next(
            rule for rule in calibrated.meta_memory.rules
            if rule.status is RepairRuleStatus.PROMOTED
        )
        return capability, rule

    def test_causal_history_compiles_to_future_reusable_present(self):
        capability, rule = self._qualified_family_c()
        ledger = Ledger()

        cap_event = ledger.append_promote_capability(
            capability,
            "authority",
        )
        ledger.append_promote_repair_rule(
            rule,
            "authority",
            parents=(cap_event.id,),
        )

        present = ledger.materialize_compiled_present().restart()
        self.assertIn(
            capability.capability_id,
            present.capability_graph.active_ids(),
        )
        self.assertEqual(
            {item.rule_id for item in present.meta_memory.rules},
            {rule.rule_id},
        )
        self.assertEqual(present.meta_memory.episodes, ())

        future = make_episode(
            FAMILY_C, "future", RepairPhase.FUTURE
        )
        result = present.execute_future_meta(
            future.state, future.spec
        )
        self.assertTrue(result.rule_hit)
        self.assertEqual(result.selected_strategy_id, ADD_OBSERVABLE)
        self.assertEqual(result.portfolio_search_calls, 0)

    def test_causal_rule_revocation_compiles_to_cold_path(self):
        capability, rule = self._qualified_family_c()
        ledger = Ledger()

        cap_event = ledger.append_promote_capability(
            capability,
            "authority",
        )
        rule_event = ledger.append_promote_repair_rule(
            rule,
            "authority",
            parents=(cap_event.id,),
        )
        ledger.append_revoke_repair_rule(
            rule.rule_id,
            "authority",
            reason="ablation",
            parents=(rule_event.id,),
        )

        present = ledger.materialize_compiled_present().restart()
        self.assertEqual(present.meta_memory.rules, ())

        future = make_episode(
            FAMILY_C, "future", RepairPhase.FUTURE
        )
        result = present.execute_future_meta(
            future.state, future.spec
        )
        self.assertFalse(result.rule_hit)
        self.assertGreater(result.portfolio_search_calls, 0)

    def test_causal_capability_revocation_preserves_record_but_disables_active_view(self):
        capability, _rule = self._qualified_family_c()
        ledger = Ledger()

        cap_event = ledger.append_promote_capability(
            capability,
            "authority",
        )
        ledger.append_revoke_capability(
            capability.capability_id,
            "authority",
            reason="ablation",
            parents=(cap_event.id,),
        )

        present = ledger.materialize_compiled_present().restart()
        self.assertEqual(present.capability_graph.active_ids(), ())
        self.assertEqual(
            {item.capability_id for item in present.memory.capabilities},
            {capability.capability_id},
        )

    def test_concurrent_same_identity_payload_conflict_is_not_silently_compressed(self):
        base = FiniteCapability(
            capability_id="same",
            input_type="X",
            output_type="X",
            semantics=(("0", "0"),),
            guard_inputs=("0",),
            certificate_id="cert-a",
            dependencies=(),
            authority_snapshot="authority",
            verifier_id="verifier",
            provenance_ids=("p-a",),
            cost=1,
        )
        other = FiniteCapability(
            capability_id="same",
            input_type="X",
            output_type="X",
            semantics=(("0", "1"),),
            guard_inputs=("0",),
            certificate_id="cert-b",
            dependencies=(),
            authority_snapshot="authority",
            verifier_id="verifier",
            provenance_ids=("p-b",),
            cost=1,
        )

        left = Ledger()
        right = Ledger()
        left.append_promote_capability(base, "left", parents=())
        right.append_promote_capability(other, "right", parents=())

        with self.assertRaisesRegex(ValueError, "causal identity conflict"):
            left.merge(right).materialize_compiled_present()

    def test_mixed_concurrent_revocation_is_refused_instead_of_overcollapsed(self):
        capability, _rule = self._qualified_family_c()

        left = Ledger()
        promoted_left = left.append_promote_capability(
            capability,
            "left",
            parents=(),
        )
        left.append_revoke_capability(
            capability.capability_id,
            "left",
            parents=(promoted_left.id,),
        )

        right = Ledger()
        right.append_promote_capability(
            capability,
            "right",
            parents=(),
        )

        with self.assertRaisesRegex(ValueError, "mixed causal revocation"):
            left.merge(right).materialize_compiled_present()


if __name__ == "__main__":
    unittest.main()
