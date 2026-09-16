import unittest

from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_state import DevelopmentalState
from realitygraph.grammar import FiniteConstructor, Grammar
from realitygraph.meta_memory import MetaMemory, RepairEpisode, RepairPhase
from realitygraph.meta_snapshot import MetaSnapshot


def state():
    constructor = FiniteConstructor(
        constructor_id="snapshot-base",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "1")),
        complexity=0,
    )
    return DevelopmentalState(
        generation_index=2,
        grammar=Grammar((constructor,)),
        capability_graph=CapabilityGraph(()),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot="snapshot-authority",
        protected_consequence_digest="protected-snapshot",
        provenance_ids=("snapshot-provenance",),
    )


def memory():
    source = RepairEpisode(
        episode_id="source",
        phase=RepairPhase.ACQUISITION,
        obstruction_fingerprint="fingerprint",
        strategy_id="strategy",
        strategy_version="v1",
        portfolio_digest="portfolio",
        authority_snapshot="snapshot-authority",
        verifier_id="snapshot-verifier",
        interface_digest="snapshot-interface",
        selection_cost=1,
        object_evidence_digest="source-evidence",
    )
    calibration = RepairEpisode(
        episode_id="calibration",
        phase=RepairPhase.CALIBRATION,
        obstruction_fingerprint="fingerprint",
        strategy_id="strategy",
        strategy_version="v1",
        portfolio_digest="portfolio",
        authority_snapshot="snapshot-authority",
        verifier_id="snapshot-verifier",
        interface_digest="snapshot-interface",
        selection_cost=1,
        object_evidence_digest="calibration-evidence",
    )
    return MetaMemory.empty().record_success(source).record_success(calibration)


class MetaSnapshotTests(unittest.TestCase):
    def test_meta_snapshot_restart_is_byte_exact(self):
        present_state = state()
        present_memory = memory()
        snapshot = MetaSnapshot.from_present(
            present_state,
            present_memory,
            portfolio_digest="portfolio",
            authority_snapshot="snapshot-authority",
        )
        restored_state, restored_memory = snapshot.restore()
        self.assertEqual(restored_state.to_text(), present_state.to_text())
        self.assertEqual(restored_state.digest, present_state.digest)
        self.assertEqual(restored_memory.text(), present_memory.text())
        self.assertEqual(restored_memory.digest, present_memory.digest)
        self.assertEqual(MetaSnapshot.from_text(snapshot.text()).text(), snapshot.text())

    def test_snapshot_detects_corruption_and_boundary_mismatch(self):
        snapshot = MetaSnapshot.from_present(
            state(), memory(), portfolio_digest="portfolio", authority_snapshot="snapshot-authority"
        )
        corrupted = snapshot.text().replace("snapshot-authority", "wrong-authority", 1)
        with self.assertRaises(ValueError):
            MetaSnapshot.from_text(corrupted)
        with self.assertRaises(ValueError):
            MetaSnapshot.from_present(
                state(), memory(), portfolio_digest="portfolio", authority_snapshot="wrong"
            )

    def test_restore_needs_no_adapter_objects(self):
        snapshot = MetaSnapshot.from_present(
            state(), memory(), portfolio_digest="portfolio", authority_snapshot="snapshot-authority"
        )
        self.assertFalse(hasattr(snapshot, "portfolio"))
        self.assertFalse(hasattr(snapshot, "strategy"))
        restarted_state, restarted_memory = snapshot.restore()
        self.assertEqual(restarted_state.generation_index, 2)
        self.assertEqual(len(restarted_memory.rules), 1)


if __name__ == "__main__":
    unittest.main()
