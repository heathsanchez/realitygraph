import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_snapshot import DevelopmentalSnapshot
from realitygraph.developmental_state import DevelopmentalState
from realitygraph.grammar import FiniteConstructor, Grammar


def seeded_state():
    constructor = FiniteConstructor(
        constructor_id="seed-observer",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "1")),
        complexity=0,
    )
    capability = FiniteCapability(
        capability_id="seed-observer",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "1")),
        guard_inputs=(),
        certificate_id="seed-cert",
        dependencies=(),
        authority_snapshot="authority-v2",
        verifier_id="seed-verifier",
        provenance_ids=("seed",),
        cost=0,
    )
    return DevelopmentalState(
        generation_index=0,
        grammar=Grammar((constructor,)),
        capability_graph=CapabilityGraph((capability,)),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot="authority-v2",
        protected_consequence_digest="protected-v2",
        provenance_ids=("seed",),
    )


class DevelopmentalSnapshotTests(unittest.TestCase):
    def test_snapshot_cold_restart_is_exact_and_adapter_free(self):
        state = seeded_state()
        snapshot = DevelopmentalSnapshot.from_state(state)
        restored = snapshot.restore()
        self.assertEqual(
            snapshot.to_text(),
            DevelopmentalSnapshot.from_state(restored).to_text(),
        )
        self.assertEqual(restored.digest, state.digest)
        self.assertEqual(
            restored.capability_graph.active_ids(),
            state.capability_graph.active_ids(),
        )
        self.assertEqual(
            tuple(c.constructor_id for c in restored.grammar.constructors),
            tuple(c.constructor_id for c in state.grammar.constructors),
        )

    def test_snapshot_detects_corruption(self):
        state = seeded_state()
        snapshot = DevelopmentalSnapshot.from_state(state)
        corrupt = DevelopmentalSnapshot(
            state_text=snapshot.state_text,
            state_digest="wrong",
            grammar_digest=snapshot.grammar_digest,
            active_capability_ids=snapshot.active_capability_ids,
            admitted_delta_ids=snapshot.admitted_delta_ids,
        )
        with self.assertRaises(ValueError):
            corrupt.restore()

    def test_snapshot_text_is_canonical(self):
        snapshot = DevelopmentalSnapshot.from_state(seeded_state())
        rebuilt = DevelopmentalSnapshot.from_text(snapshot.to_text())
        self.assertEqual(rebuilt.to_text(), snapshot.to_text())
        self.assertEqual(rebuilt.digest, snapshot.digest)


if __name__ == "__main__":
    unittest.main()
