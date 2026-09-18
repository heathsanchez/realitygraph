import unittest

from realitygraph.flash import (
    FutureQuotient,
    ProtectedContinuation,
    PresentState,
)


class FutureQuotientTests(unittest.TestCase):
    def test_future_continuations_define_present_identity(self):
        quotient = FutureQuotient(
            states=(
                PresentState("a", provenance_ids=("history-a",)),
                PresentState("b", provenance_ids=("history-b",)),
                PresentState("c", provenance_ids=("history-c",)),
            ),
            authority_snapshot="authority-v1",
            verifier_id="verifier-v1",
        )

        first = quotient.admit_continuation(
            ProtectedContinuation(
                continuation_id="future-1",
                outcomes=(("a", "0"), ("b", "0"), ("c", "1")),
                authority_snapshot="authority-v1",
                verifier_id="verifier-v1",
            )
        )
        self.assertEqual(quotient.classes(), (("a", "b"), ("c",)))
        self.assertEqual(first.split_classes, ())
        self.assertEqual(first.merged_classes, ())
        self.assertEqual(first.changed_state_ids, ("a", "b", "c"))

        second = quotient.admit_continuation(
            ProtectedContinuation(
                continuation_id="future-2",
                outcomes=(("a", "0"), ("b", "1"), ("c", "1")),
                authority_snapshot="authority-v1",
                verifier_id="verifier-v1",
            )
        )
        self.assertEqual(quotient.classes(), (("a",), ("b",), ("c",)))
        self.assertEqual(second.split_classes, (("a", "b"),))
        self.assertEqual(second.changed_state_ids, ("a", "b"))

        revoked = quotient.revoke_continuation("future-2", reason="future no longer protected")
        self.assertEqual(quotient.classes(), (("a", "b"), ("c",)))
        self.assertEqual(revoked.merged_classes, (("a", "b"),))
        self.assertEqual(revoked.changed_state_ids, ("a", "b"))

    def test_history_never_separates_states_without_future_consequence(self):
        quotient = FutureQuotient(
            states=(
                PresentState("left", provenance_ids=("very-different-history",)),
                PresentState("right", provenance_ids=("another-history",)),
            ),
            authority_snapshot="authority-v1",
            verifier_id="verifier-v1",
        )
        quotient.admit_continuation(
            ProtectedContinuation(
                continuation_id="same-future",
                outcomes=(("left", "same"), ("right", "same")),
                authority_snapshot="authority-v1",
                verifier_id="verifier-v1",
            )
        )
        self.assertTrue(quotient.equivalent("left", "right"))
        self.assertEqual(quotient.classes(), (("left", "right"),))

    def test_unverified_future_cannot_change_present_ontology(self):
        quotient = FutureQuotient(
            states=(PresentState("a"), PresentState("b")),
            authority_snapshot="authority-v1",
            verifier_id="verifier-v1",
        )
        with self.assertRaisesRegex(ValueError, "authority/verifier mismatch"):
            quotient.admit_continuation(
                ProtectedContinuation(
                    continuation_id="foreign",
                    outcomes=(("a", "0"), ("b", "1")),
                    authority_snapshot="other-authority",
                    verifier_id="verifier-v1",
                )
            )
        self.assertEqual(quotient.classes(), (("a", "b"),))


if __name__ == "__main__":
    unittest.main()
