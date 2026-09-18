import unittest

from realitygraph.flash import (
    FlashClosure,
    FlashContract,
    FlashObstruction,
    LiveObligation,
)


class FlashObstructionRevocationTests(unittest.TestCase):
    def test_revoking_obstruction_restores_only_exactly_pruned_candidates(self):
        contract = FlashContract("authority-v1", "verifier-v1")
        other_contract = FlashContract("authority-v2", "verifier-v1")

        exact = LiveObligation(
            obligation_id="exact",
            input_type="X",
            source_input_type="X",
            output_type="Y",
            oracle=(("x", "y"),),
            transport_to_source=(("x", "x"),),
            contract=contract,
            candidate_fingerprints=("good", "bad"),
        )
        other = LiveObligation(
            obligation_id="other",
            input_type="X",
            source_input_type="X",
            output_type="Y",
            oracle=(("x", "y"),),
            transport_to_source=(("x", "x"),),
            contract=other_contract,
            candidate_fingerprints=("good", "bad"),
        )
        flash = FlashClosure((exact, other))

        admitted = flash.admit_obstruction(
            FlashObstruction(
                obstruction_id="obs-bad",
                input_type="X",
                output_type="Y",
                contract=contract,
                candidate_fingerprint="bad",
                separating_input="x",
                expected_output="y",
                actual_output="not-y",
            )
        )
        self.assertEqual(exact.pruned_fingerprints, {"bad"})
        self.assertEqual(other.pruned_fingerprints, set())
        self.assertEqual(admitted.pruned_candidate_occurrences, 1)
        self.assertEqual(exact.remaining_search(), 1)

        revoked = flash.revoke_obstruction(
            "obs-bad",
            reason="authority superseded",
        )
        self.assertEqual(exact.pruned_fingerprints, set())
        self.assertEqual(other.pruned_fingerprints, set())
        self.assertEqual(exact.remaining_search(), 2)
        self.assertEqual(revoked.restored_candidate_occurrences, 1)
        self.assertEqual(revoked.changed_obligations, ("exact",))

    def test_revoked_obstruction_no_longer_reapplies_on_later_closure(self):
        contract = FlashContract("authority-v1", "verifier-v1")
        obligation = LiveObligation(
            obligation_id="o",
            input_type="X",
            source_input_type="X",
            output_type="Y",
            oracle=(("x", "y"),),
            transport_to_source=(("x", "x"),),
            contract=contract,
            candidate_fingerprints=("bad",),
        )
        flash = FlashClosure((obligation,))
        flash.admit_obstruction(
            FlashObstruction(
                obstruction_id="obs",
                input_type="X",
                output_type="Y",
                contract=contract,
                candidate_fingerprint="bad",
                separating_input="x",
                expected_output="y",
                actual_output="wrong",
            )
        )
        flash.revoke_obstruction("obs", reason="control")
        flash.close()
        self.assertEqual(obligation.pruned_fingerprints, set())


if __name__ == "__main__":
    unittest.main()
