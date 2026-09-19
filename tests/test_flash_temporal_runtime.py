import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    CapabilityAdmissionEvent,
    ContinuationAdmissionEvent,
    ContinuationRevocationEvent,
    FlashClosure,
    FlashContract,
    FlashEventRuntime,
    FutureQuotient,
    LiveObligation,
    PresentState,
    ProtectedContinuation,
)


class FlashTemporalRuntimeTests(unittest.TestCase):
    def fixture(self):
        contract=FlashContract("authority-v1","verifier-v1")
        obligation=LiveObligation(
            obligation_id="o",
            input_type="X",
            source_input_type="X",
            output_type="Y",
            oracle=(("x","y"),),
            transport_to_source=(("x","x"),),
            contract=contract,
        )
        closure=FlashClosure((obligation,))
        quotient=FutureQuotient(
            states=(PresentState("a"),PresentState("b")),
            authority_snapshot="authority-v1",
            verifier_id="verifier-v1",
        )
        runtime=FlashEventRuntime(closure,future_quotient=quotient)
        return runtime,closure,quotient

    def test_past_capability_and_future_separator_share_one_event_stream(self):
        runtime,closure,quotient=self.fixture()

        future=ContinuationAdmissionEvent(
            event_id="future-add",
            continuation=ProtectedContinuation(
                continuation_id="future-1",
                outcomes=(("a","0"),("b","1")),
                authority_snapshot="authority-v1",
                verifier_id="verifier-v1",
            ),
        )
        qdelta=runtime.apply(future)
        self.assertEqual(quotient.classes(),(("a",),("b",)))
        self.assertEqual(qdelta.changed_state_ids,("a","b"))

        cap=FiniteCapability(
            capability_id="cap",
            input_type="X",
            output_type="Y",
            semantics=(("x","y"),),
            guard_inputs=("x",),
            certificate_id="cert",
            dependencies=(),
            authority_snapshot="authority-v1",
            verifier_id="verifier-v1",
            provenance_ids=("source",),
            cost=1,
        )
        runtime.apply(CapabilityAdmissionEvent(
            event_id="past-capability",
            capability=cap,
            oracle=(("x","y"),),
        ))
        self.assertEqual(closure.discharged_obligation_ids(),("o",))
        self.assertEqual(runtime.event_ids(),("future-add","past-capability"))

        merged=runtime.apply(ContinuationRevocationEvent(
            event_id="future-revoke",
            continuation_id="future-1",
            reason="future obligation removed",
        ))
        self.assertEqual(quotient.classes(),(("a","b"),))
        self.assertEqual(merged.merged_classes,(("a","b"),))
        self.assertEqual(
            runtime.event_ids(),
            ("future-add","future-revoke","past-capability"),
        )

    def test_temporal_events_survive_manifest_restart_idempotently(self):
        runtime,closure,quotient=self.fixture()
        event=ContinuationAdmissionEvent(
            event_id="future-add",
            continuation=ProtectedContinuation(
                continuation_id="future-1",
                outcomes=(("a","0"),("b","1")),
                authority_snapshot="authority-v1",
                verifier_id="verifier-v1",
            ),
        )
        runtime.apply(event)
        text=runtime.event_manifest_text()

        restarted=FlashEventRuntime.from_event_manifest(
            closure,
            text,
            future_quotient=quotient,
        )
        replay=restarted.apply(event)
        self.assertEqual(replay.changed_state_ids,())
        self.assertEqual(quotient.classes(),(("a",),("b",)))
        self.assertEqual(restarted.event_manifest_text(),text)


if __name__=="__main__":
    unittest.main()
