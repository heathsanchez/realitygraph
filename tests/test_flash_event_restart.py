import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    CapabilityAdmissionEvent,
    FlashClosure,
    FlashContract,
    FlashEventRuntime,
    LiveObligation,
)


def fixture():
    contract = FlashContract("authority-v1", "verifier-v1")
    obligation = LiveObligation(
        obligation_id="o",
        input_type="X",
        source_input_type="X",
        output_type="Y",
        oracle=(("x", "y"),),
        transport_to_source=(("x", "x"),),
        contract=contract,
    )
    cap = FiniteCapability(
        capability_id="cap",
        input_type="X",
        output_type="Y",
        semantics=(("x", "y"),),
        guard_inputs=("x",),
        certificate_id="cert",
        dependencies=(),
        authority_snapshot="authority-v1",
        verifier_id="verifier-v1",
        provenance_ids=("source",),
        cost=1,
    )
    event = CapabilityAdmissionEvent(
        event_id="event-1",
        capability=cap,
        oracle=(("x", "y"),),
        origin="lean",
    )
    return obligation, event


class FlashEventRestartTests(unittest.TestCase):
    def test_event_manifest_is_canonical_and_restart_preserves_idempotence(self):
        obligation, event = fixture()
        closure = FlashClosure((obligation,))
        runtime = FlashEventRuntime(closure)
        runtime.apply(event)

        text = runtime.event_manifest_text()
        self.assertEqual(text, runtime.event_manifest_text())

        restarted = FlashEventRuntime.from_event_manifest(closure, text)
        before = closure.event_count
        replay = restarted.apply(event)

        self.assertEqual(closure.event_count, before)
        self.assertEqual(replay.iterations, 0)
        self.assertEqual(replay.changed_obligations, ())
        self.assertEqual(restarted.event_ids(), ("event-1",))
        self.assertEqual(restarted.event_manifest_text(), text)

    def test_restart_still_rejects_same_id_with_changed_payload(self):
        obligation, event = fixture()
        closure = FlashClosure((obligation,))
        runtime = FlashEventRuntime(closure)
        runtime.apply(event)
        restarted = FlashEventRuntime.from_event_manifest(
            closure,
            runtime.event_manifest_text(),
        )

        changed_cap = FiniteCapability(
            **{**event.capability.__dict__, "cost": 2}
        )
        changed = CapabilityAdmissionEvent(
            event_id="event-1",
            capability=changed_cap,
            oracle=event.oracle,
            origin=event.origin,
        )
        with self.assertRaisesRegex(ValueError, "event identity conflict"):
            restarted.apply(changed)

    def test_noncanonical_manifest_is_rejected(self):
        obligation, event = fixture()
        closure = FlashClosure((obligation,))
        runtime = FlashEventRuntime(closure)
        runtime.apply(event)
        text = runtime.event_manifest_text()
        tampered = text.replace(",", ", ", 1)
        with self.assertRaises(ValueError):
            FlashEventRuntime.from_event_manifest(closure, tampered)


if __name__ == "__main__":
    unittest.main()
