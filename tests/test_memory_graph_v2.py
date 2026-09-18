from __future__ import annotations

import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.memory_graph import (
    MemoryGraphV2,
    MemoryLaw,
    MemoryRevocation,
)
from realitygraph.meta_memory import (
    MetaMemory,
    RepairPhase,
    RepairEpisode,
)


def capability(ident: str, *, deps=()) -> FiniteCapability:
    return FiniteCapability(
        capability_id=ident,
        input_type="X",
        output_type="X",
        semantics=(("0", "0"), ("1", "1")),
        guard_inputs=("0", "1"),
        certificate_id=f"cert:{ident}",
        dependencies=tuple(deps),
        authority_snapshot="authority-v1",
        verifier_id="verifier-v1",
        provenance_ids=(f"prov:{ident}",),
        cost=1,
    )


class MemoryGraphV2Tests(unittest.TestCase):
    def test_empty_round_trip_and_digest_restart(self):
        memory = MemoryGraphV2()
        text = memory.text()
        restarted = MemoryGraphV2.parse(text)
        self.assertEqual(restarted, memory)
        self.assertEqual(restarted.text(), text)
        self.assertEqual(restarted.digest, memory.digest)

    def test_canonical_record_order_is_insertion_independent(self):
        a = MemoryLaw("a", "x")
        b = MemoryLaw("b", "y")
        left = MemoryGraphV2(laws=(b, a))
        right = MemoryGraphV2(laws=(a, b))
        self.assertEqual(left.text(), right.text())
        self.assertEqual(left.digest, right.digest)

    def test_mg1_round_trip_is_exact_for_law_only_memory(self):
        from realitygraph.mg import Law, MG

        mg1 = MG(
            "lean",
            (
                Law("L1", "x=x", "scope-a", "p1"),
                Law("L2", "y=y", "*", "p2"),
            ),
        )
        mg2 = MemoryGraphV2.from_mg1(mg1)
        restored = mg2.to_mg1()
        self.assertEqual(restored.text(), mg1.text())

    def test_whole_memory_mg1_projection_refuses_silent_loss(self):
        memory = MemoryGraphV2(capabilities=(capability("c1"),))
        with self.assertRaises(ValueError):
            memory.to_mg1()
        self.assertEqual(memory.to_mg1(law_only=True).text(), "MG1\n")

    def test_capability_graph_round_trip_preserves_revocation(self):
        c1 = capability("c1")
        c2 = capability("c2", deps=("c1",))
        graph = CapabilityGraph((c1, c2), ("c1",))
        memory = MemoryGraphV2.from_capability_graph(graph)
        restarted = MemoryGraphV2.parse(memory.text())
        restored = restarted.to_capability_graph()
        self.assertEqual(restored, graph)
        self.assertEqual(restored.active_ids(), ())
        self.assertEqual(restarted.active_capabilities, ())

    def test_revocation_memory_blocks_stale_reintroduction_after_merge(self):
        revoke = MemoryGraphV2(
            revocations=(MemoryRevocation("capability", "c1", "audit"),)
        )
        stale = MemoryGraphV2(capabilities=(capability("c1"),))
        merged = revoke.merge(stale)
        self.assertEqual(merged.to_capability_graph().active_ids(), ())

    def test_merge_is_commutative_associative_and_idempotent_when_compatible(self):
        a = MemoryGraphV2(laws=(MemoryLaw("a", "A"),))
        b = MemoryGraphV2(capabilities=(capability("b"),))
        c = MemoryGraphV2(
            revocations=(MemoryRevocation("law", "a"),)
        )

        self.assertEqual(a.merge(b), b.merge(a))
        self.assertEqual(a.merge(a), a)
        self.assertEqual(a.merge(b).merge(c), a.merge(b.merge(c)))

    def test_same_identity_different_payload_is_explicit_conflict(self):
        left = MemoryGraphV2(laws=(MemoryLaw("same", "A"),))
        right = MemoryGraphV2(laws=(MemoryLaw("same", "B"),))
        with self.assertRaises(ValueError):
            left.merge(right)

    def test_promoted_meta_memory_projects_without_fabricating_episodes(self):
        acquisition = RepairEpisode(
            episode_id="e1",
            phase=RepairPhase.ACQUISITION,
            obstruction_fingerprint="obs",
            strategy_id="split",
            strategy_version="v1",
            portfolio_digest="portfolio",
            authority_snapshot="authority",
            verifier_id="verifier",
            interface_digest="interface",
            selection_cost=4,
            object_evidence_digest="evidence-a",
        )
        calibration = RepairEpisode(
            episode_id="e2",
            phase=RepairPhase.CALIBRATION,
            obstruction_fingerprint="obs",
            strategy_id="split",
            strategy_version="v1",
            portfolio_digest="portfolio",
            authority_snapshot="authority",
            verifier_id="verifier",
            interface_digest="interface",
            selection_cost=3,
            object_evidence_digest="evidence-b",
        )
        meta = MetaMemory.empty().record_success(acquisition).record_success(calibration)
        original = meta.promoted_match(
            obstruction_fingerprint="obs",
            portfolio_digest="portfolio",
            authority_snapshot="authority",
            verifier_id="verifier",
            interface_digest="interface",
        )
        self.assertIsNotNone(original)

        memory = MemoryGraphV2.from_meta_memory(meta)
        restarted = MemoryGraphV2.parse(memory.text()).to_meta_memory()
        restored = restarted.promoted_match(
            obstruction_fingerprint="obs",
            portfolio_digest="portfolio",
            authority_snapshot="authority",
            verifier_id="verifier",
            interface_digest="interface",
        )
        self.assertEqual(restored, original)
        self.assertEqual(restarted.episodes, ())


if __name__ == "__main__":
    unittest.main()
