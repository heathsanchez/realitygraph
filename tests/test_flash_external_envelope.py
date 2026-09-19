import unittest

from realitygraph.flash import (
    CapabilityAdmissionEvent,
    ExternalEventEnvelope,
    FlashContract,
    FlashObstruction,
    ObstructionAdmissionEvent,
)


class ExternalEventEnvelopeTests(unittest.TestCase):
    def test_canonical_round_trip_and_source_evidence_binding(self):
        source = b"verified-source-evidence"
        envelope = ExternalEventEnvelope.capability(
            event_id="lean:direct-var:v1",
            repository="metalogiclabs/mathgraph-lean-kernel",
            commit="74dc5ddb4584e1254f5687615e5b02795b8dc6f3",
            authority_snapshot="lean-kernel-arena@510fbfead6f02bed1a0179d01729a6ddf5bfd06d",
            verifier_id="arena409-native-ablation-callgrind-v1",
            source_evidence=source,
            capability={
                "capability_id": "lean:direct-var:v1",
                "input_type": "lean-eval-var",
                "output_type": "lean-value",
                "semantics": [["var", "env-slot-value"]],
                "guard_inputs": ["var"],
                "certificate_id": "run:35380841937+35380563756",
                "dependencies": [],
                "authority_snapshot": "lean-kernel-arena@510fbfead6f02bed1a0179d01729a6ddf5bfd06d",
                "verifier_id": "arena409-native-ablation-callgrind-v1",
                "provenance_ids": ["run:35380841937", "run:35380563756"],
                "cost": 0,
            },
            oracle=[["var", "env-slot-value"]],
            origin="lean",
        )
        text = envelope.to_text()
        rebuilt = ExternalEventEnvelope.from_text(text)
        self.assertEqual(rebuilt.to_text(), text)
        rebuilt.verify_source_bytes(source)
        self.assertIsInstance(rebuilt.to_runtime_event(), CapabilityAdmissionEvent)

    def test_payload_tampering_is_rejected(self):
        source = b"evidence"
        envelope = ExternalEventEnvelope.obstruction(
            event_id="arc:refute:v1",
            repository="heathsanchez/Minimal-Sufficient-Interface",
            commit="86e540b2bb9a0fbb91805d3735333048d05c2a92",
            authority_snapshot="arc3-vc33-pinned-v2",
            verifier_id="destination-exact-v1",
            source_evidence=source,
            obstruction={
                "obstruction_id": "arc:refute:v1",
                "input_type": "cross-game-transfer",
                "output_type": "destination-validity",
                "contract": {
                    "authority_snapshot": "arc3-vc33-pinned-v2",
                    "verifier_id": "destination-exact-v1",
                },
                "candidate_fingerprint": "candidate-1",
                "separating_input": "ft09->vc33",
                "expected_output": "verified",
                "actual_output": "refuted",
                "provenance": "run:35404864326",
            },
        )
        text = envelope.to_text()
        tampered = text.replace('"actual_output":"refuted"', '"actual_output":"verified-ish"')
        with self.assertRaisesRegex(ValueError, "payload digest"):
            ExternalEventEnvelope.from_text(tampered)

    def test_source_evidence_mismatch_is_rejected(self):
        envelope = ExternalEventEnvelope.obstruction(
            event_id="o",
            repository="repo/name",
            commit="0123456789abcdef0123456789abcdef01234567",
            authority_snapshot="a",
            verifier_id="v",
            source_evidence=b"right",
            obstruction={
                "obstruction_id": "o",
                "input_type": "X",
                "output_type": "Y",
                "contract": {"authority_snapshot": "a", "verifier_id": "v"},
                "candidate_fingerprint": "bad",
                "separating_input": "x",
                "expected_output": "yes",
                "actual_output": "no",
                "provenance": "",
            },
        )
        with self.assertRaisesRegex(ValueError, "source evidence digest"):
            envelope.verify_source_bytes(b"wrong")

    def test_obstruction_converts_to_runtime_event(self):
        envelope = ExternalEventEnvelope.obstruction(
            event_id="o",
            repository="repo/name",
            commit="0123456789abcdef0123456789abcdef01234567",
            authority_snapshot="a",
            verifier_id="v",
            source_evidence=b"evidence",
            obstruction={
                "obstruction_id": "o",
                "input_type": "X",
                "output_type": "Y",
                "contract": {"authority_snapshot": "a", "verifier_id": "v"},
                "candidate_fingerprint": "bad",
                "separating_input": "x",
                "expected_output": "yes",
                "actual_output": "no",
                "provenance": "",
            },
        )
        event = envelope.to_runtime_event()
        self.assertIsInstance(event, ObstructionAdmissionEvent)
        self.assertIsInstance(event.obstruction, FlashObstruction)
        self.assertEqual(event.obstruction.contract, FlashContract("a", "v"))


if __name__ == "__main__":
    unittest.main()
