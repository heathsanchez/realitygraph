import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    CapabilityAdmissionEvent,
    CapabilityRevocationEvent,
    FlashClosure,
    FlashContract,
    FlashEventRuntime,
    FlashObstruction,
    LiveObligation,
    ObstructionAdmissionEvent,
    ObstructionRevocationEvent,
)


AUTHORITY = "authority-v1"
VERIFIER = "verifier-v1"
CONTRACT = FlashContract(AUTHORITY, VERIFIER)


def capability():
    return FiniteCapability(
        capability_id="cap",
        input_type="X",
        output_type="Y",
        semantics=(("x", "y"),),
        guard_inputs=("x",),
        certificate_id="cert",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("source",),
        cost=1,
    )


def obligation():
    return LiveObligation(
        obligation_id="o",
        input_type="X",
        source_input_type="X",
        output_type="Y",
        oracle=(("x", "y"),),
        transport_to_source=(("x", "x"),),
        contract=CONTRACT,
        candidate_fingerprints=("good", "bad"),
    )


class FlashEventRuntimeTests(unittest.TestCase):
    def test_verified_event_is_idempotent_and_closes_graph(self):
        closure = FlashClosure((obligation(),))
        runtime = FlashEventRuntime(closure)
        event = CapabilityAdmissionEvent(
            event_id="event-1",
            capability=capability(),
            oracle=(("x", "y"),),
            origin="lean",
        )
        first = runtime.apply(event)
        second = runtime.apply(event)

        self.assertEqual(first, second)
        self.assertEqual(closure.discharged_obligation_ids(), ("o",))
        self.assertEqual(runtime.event_ids(), ("event-1",))
        self.assertEqual(closure.event_count, 1)

    def test_same_event_id_with_different_payload_is_rejected(self):
        closure = FlashClosure((obligation(),))
        runtime = FlashEventRuntime(closure)
        runtime.apply(
            CapabilityAdmissionEvent(
                event_id="event-1",
                capability=capability(),
                oracle=(("x", "y"),),
            )
        )
        other = FiniteCapability(
            **{**capability().__dict__, "cost": 2}
        )
        with self.assertRaisesRegex(ValueError, "event identity conflict"):
            runtime.apply(
                CapabilityAdmissionEvent(
                    event_id="event-1",
                    capability=other,
                    oracle=(("x", "y"),),
                )
            )

    def test_positive_and_negative_memory_share_same_event_boundary(self):
        row = obligation()
        closure = FlashClosure((row,))
        runtime = FlashEventRuntime(closure)

        obs = FlashObstruction(
            obstruction_id="obs",
            input_type="X",
            output_type="Y",
            contract=CONTRACT,
            candidate_fingerprint="bad",
            separating_input="x",
            expected_output="y",
            actual_output="wrong",
        )
        runtime.apply(ObstructionAdmissionEvent("obs-add", obs))
        self.assertEqual(row.pruned_fingerprints, {"bad"})

        runtime.apply(
            ObstructionRevocationEvent(
                event_id="obs-revoke",
                obstruction_id="obs",
                reason="authority superseded",
            )
        )
        self.assertEqual(row.pruned_fingerprints, set())

        runtime.apply(
            CapabilityAdmissionEvent(
                event_id="cap-add",
                capability=capability(),
                oracle=(("x", "y"),),
            )
        )
        self.assertEqual(closure.discharged_obligation_ids(), ("o",))

        runtime.apply(
            CapabilityRevocationEvent(
                event_id="cap-revoke",
                capability_id="cap",
                reason="ablation",
            )
        )
        self.assertEqual(closure.open_obligation_ids(), ("o",))


if __name__ == "__main__":
    unittest.main()
