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
    TemporalFlashDelta,
)


AUTHORITY="authority-v1"
VERIFIER="verifier-v1"


def make():
    contract=FlashContract(AUTHORITY,VERIFIER)
    quotient=FutureQuotient(
        states=(PresentState("a"),PresentState("b")),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
    )
    quotient.admit_continuation(ProtectedContinuation(
        continuation_id="baseline-future",
        outcomes=(("a","same"),("b","same")),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
    ))
    obligation=LiveObligation(
        obligation_id="o",
        input_type="X",
        source_input_type="X",
        output_type="Y",
        oracle=(("x","y"),),
        transport_to_source=(("x","x"),),
        contract=contract,
        candidate_fingerprints=("cold-1","cold-2","cold-3"),
    )
    closure=FlashClosure(
        (obligation,),
        future_quotient=quotient,
    )
    runtime=FlashEventRuntime(
        closure,
        future_quotient=quotient,
    )
    cap=FiniteCapability(
        capability_id="merged-route",
        input_type="X",
        output_type="Y",
        semantics=(("x","y"),),
        guard_inputs=("x",),
        certificate_id="cert",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("source",),
        cost=1,
    )
    return quotient,obligation,closure,runtime,cap


class FlashTemporalCouplingTests(unittest.TestCase):
    def test_future_separator_reopens_present_capability_and_revocation_reuses_it(self):
        quotient,obligation,closure,runtime,cap=make()

        admitted=runtime.apply(CapabilityAdmissionEvent(
            event_id="cap-add",
            capability=cap,
            oracle=(("x","y"),),
            future_equivalences=(("a","b"),),
        ))
        self.assertEqual(closure.discharged_obligation_ids(),("o",))
        self.assertEqual(obligation.solved_by,"merged-route")
        self.assertEqual(admitted.discharged,("o",))

        split=runtime.apply(ContinuationAdmissionEvent(
            event_id="future-split",
            continuation=ProtectedContinuation(
                continuation_id="separator",
                outcomes=(("a","0"),("b","1")),
                authority_snapshot=AUTHORITY,
                verifier_id=VERIFIER,
            ),
        ))
        self.assertIsInstance(split,TemporalFlashDelta)
        self.assertEqual(quotient.classes(),(("a",),("b",)))
        self.assertEqual(split.quotient.split_classes,(("a","b"),))
        self.assertEqual(split.flash.reopened,("o",))
        self.assertEqual(closure.open_obligation_ids(),("o",))
        self.assertEqual(obligation.remaining_search(),3)

        merged=runtime.apply(ContinuationRevocationEvent(
            event_id="future-revoke",
            continuation_id="separator",
            reason="future obligation removed",
        ))
        self.assertIsInstance(merged,TemporalFlashDelta)
        self.assertEqual(quotient.classes(),(("a","b"),))
        self.assertEqual(merged.quotient.merged_classes,(("a","b"),))
        self.assertEqual(merged.flash.discharged,("o",))
        self.assertEqual(closure.discharged_obligation_ids(),("o",))
        self.assertEqual(obligation.solved_by,"merged-route")
        self.assertEqual(obligation.searched_fingerprints,[])
        self.assertEqual(len(closure.capabilities),1)

    def test_unrelated_future_split_does_not_invalidate_capability(self):
        contract=FlashContract(AUTHORITY,VERIFIER)
        quotient=FutureQuotient(
            states=(PresentState("a"),PresentState("b"),PresentState("c")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        )
        quotient.admit_continuation(ProtectedContinuation(
            continuation_id="base",
            outcomes=(("a","same"),("b","same"),("c","other")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        ))
        obligation=LiveObligation(
            obligation_id="o",
            input_type="X",
            source_input_type="X",
            output_type="Y",
            oracle=(("x","y"),),
            transport_to_source=(("x","x"),),
            contract=contract,
        )
        closure=FlashClosure((obligation,),future_quotient=quotient)
        runtime=FlashEventRuntime(closure,future_quotient=quotient)
        cap=FiniteCapability(
            capability_id="ab-route",
            input_type="X",output_type="Y",
            semantics=(("x","y"),),guard_inputs=("x",),
            certificate_id="cert",dependencies=(),
            authority_snapshot=AUTHORITY,verifier_id=VERIFIER,
            provenance_ids=(),cost=1,
        )
        runtime.apply(CapabilityAdmissionEvent(
            event_id="cap",
            capability=cap,
            oracle=(("x","y"),),
            future_equivalences=(("a","b"),),
        ))
        delta=runtime.apply(ContinuationAdmissionEvent(
            event_id="future-c-split",
            continuation=ProtectedContinuation(
                continuation_id="c-only",
                outcomes=(("a","0"),("b","0"),("c","1")),
                authority_snapshot=AUTHORITY,
                verifier_id=VERIFIER,
            ),
        ))
        self.assertEqual(delta.flash.reopened,())
        self.assertEqual(closure.discharged_obligation_ids(),("o",))


if __name__=="__main__":
    unittest.main()
