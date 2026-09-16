import unittest

from realitygraph.developmental_state import DevelopmentalState, TerminalRecord


class DevelopmentalStateTests(unittest.TestCase):
    def test_state_round_trip_is_byte_exact(self):
        state = DevelopmentalState.empty(
            authority_snapshot="authority-v2",
            protected_consequence_digest="protected-v2",
        )
        rebuilt = DevelopmentalState.from_text(state.to_text())
        self.assertEqual(rebuilt.to_text(), state.to_text())
        self.assertEqual(rebuilt.digest, state.digest)
        self.assertEqual(rebuilt.capability_graph.active_ids(), ())
        self.assertEqual(rebuilt.grammar.constructors, ())

    def test_with_generation_returns_new_state(self):
        state = DevelopmentalState.empty(
            authority_snapshot="authority-v2",
            protected_consequence_digest="protected-v2",
        )
        next_state = state.with_generation(
            grammar=state.grammar,
            capability_graph=state.capability_graph,
            admitted_delta=None,
            terminal_record=TerminalRecord(
                generation_id="probe",
                obligation_id="o",
                route="UNKNOWN_SEARCH",
                evidence_digest="e",
            ),
            provenance_ids=("p",),
        )
        self.assertEqual(state.generation_index, 0)
        self.assertEqual(next_state.generation_index, 1)
        self.assertNotEqual(state.digest, next_state.digest)
        self.assertEqual(state.terminal_records, ())
        self.assertEqual(len(next_state.terminal_records), 1)

    def test_noncanonical_state_text_is_rejected(self):
        state = DevelopmentalState.empty("authority-v2", "protected-v2")
        text = state.to_text().replace(",", ", ", 1)
        with self.assertRaises(ValueError):
            DevelopmentalState.from_text(text)


if __name__ == "__main__":
    unittest.main()
