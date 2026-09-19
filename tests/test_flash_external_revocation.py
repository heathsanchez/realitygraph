import unittest

from realitygraph.flash import (
    CapabilityRevocationEvent,
    ExternalEventEnvelope,
    ObstructionRevocationEvent,
)


class ExternalRevocationEnvelopeTests(unittest.TestCase):
    def test_capability_revocation_round_trip(self):
        evidence=b"revocation-evidence"
        envelope=ExternalEventEnvelope.capability_revocation(
            event_id="revoke-cap-1",
            repository="repo/name",
            commit="0123456789abcdef0123456789abcdef01234567",
            authority_snapshot="authority-v2",
            verifier_id="verifier-v2",
            source_evidence=evidence,
            capability_id="cap-1",
            reason="superseded by stronger authority",
        )
        rebuilt=ExternalEventEnvelope.from_text(envelope.to_text())
        rebuilt.verify_source_bytes(evidence)
        event=rebuilt.to_runtime_event()
        self.assertIsInstance(event,CapabilityRevocationEvent)
        self.assertEqual(event.capability_id,"cap-1")
        self.assertEqual(event.reason,"superseded by stronger authority")

    def test_obstruction_revocation_round_trip(self):
        evidence=b"revocation-evidence"
        envelope=ExternalEventEnvelope.obstruction_revocation(
            event_id="revoke-obs-1",
            repository="repo/name",
            commit="0123456789abcdef0123456789abcdef01234567",
            authority_snapshot="authority-v2",
            verifier_id="verifier-v2",
            source_evidence=evidence,
            obstruction_id="obs-1",
            reason="destination contract changed",
        )
        rebuilt=ExternalEventEnvelope.from_text(envelope.to_text())
        event=rebuilt.to_runtime_event()
        self.assertIsInstance(event,ObstructionRevocationEvent)
        self.assertEqual(event.obstruction_id,"obs-1")

    def test_empty_revocation_reason_is_rejected(self):
        with self.assertRaises(ValueError):
            ExternalEventEnvelope.capability_revocation(
                event_id="r",
                repository="repo/name",
                commit="0123456789abcdef0123456789abcdef01234567",
                authority_snapshot="a",
                verifier_id="v",
                source_evidence=b"e",
                capability_id="c",
                reason="",
            )


if __name__=="__main__":
    unittest.main()
