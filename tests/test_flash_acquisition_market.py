import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    AcquisitionProposal,
    CapabilityAdmissionEvent,
    FlashClosure,
    FlashContract,
    FlashEventRuntime,
    FutureQuotient,
    LiveObligation,
    PresentState,
    ProtectedContinuation,
)


AUTHORITY="authority-v1"
VERIFIER="verifier-v1"
CONTRACT=FlashContract(AUTHORITY,VERIFIER)


def cap(cid, rows):
    return FiniteCapability(
        capability_id=cid,
        input_type="X",
        output_type="Y",
        semantics=tuple(rows),
        guard_inputs=tuple(k for k,_ in rows),
        certificate_id=f"untrusted:{cid}",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(),
        cost=0,
    )


def obligation(oid, oracle, candidates):
    return LiveObligation(
        obligation_id=oid,
        input_type="T",
        source_input_type="X",
        output_type="Y",
        oracle=tuple(oracle),
        transport_to_source=tuple((t,x) for t,x,_y in candidates["transport"]),
        contract=CONTRACT,
        candidate_fingerprints=tuple(candidates["fingerprints"]),
        domain=candidates.get("domain",""),
    )


class FlashAcquisitionMarketTests(unittest.TestCase):
    def test_global_future_search_eliminated_per_cost_beats_local_cheapest(self):
        shared_transport=(("t0","x0","y0"),("t1","x1","y1"))
        obs=(
            obligation("wide-1",(("t0","y0"),("t1","y1")),{
                "transport":shared_transport,
                "fingerprints":tuple(f"a{i}" for i in range(5)),
                "domain":"A",
            }),
            obligation("wide-2",(("t0","y0"),("t1","y1")),{
                "transport":shared_transport,
                "fingerprints":tuple(f"b{i}" for i in range(5)),
                "domain":"B",
            }),
            obligation("wide-3",(("t0","y0"),("t1","y1")),{
                "transport":shared_transport,
                "fingerprints":tuple(f"c{i}" for i in range(5)),
                "domain":"C",
            }),
            obligation("local",(("t0","local"),),{
                "transport":(("t0","z","local"),),
                "fingerprints":("l0","l1"),
                "domain":"local",
            }),
        )
        closure=FlashClosure(obs)

        proposals=(
            AcquisitionProposal(
                proposal_id="cheap-local",
                capability=cap("cheap-local-cap",(("z","local"),)),
                verification_cost=1,
            ),
            AcquisitionProposal(
                proposal_id="expensive-global",
                capability=cap("global-cap",(("x0","y0"),("x1","y1"))),
                verification_cost=3,
            ),
        )
        ranked=closure.rank_acquisition_proposals(proposals)

        self.assertEqual(ranked[0].proposal_id,"expensive-global")
        self.assertEqual(ranked[0].obligations_solved,("wide-1","wide-2","wide-3"))
        self.assertEqual(ranked[0].future_search_removed,15)
        self.assertEqual(ranked[0].verification_cost,3)
        self.assertEqual(ranked[0].value,5.0)

        self.assertEqual(ranked[1].proposal_id,"cheap-local")
        self.assertEqual(ranked[1].future_search_removed,2)
        self.assertEqual(ranked[1].value,2.0)

        # Ranking is speculative only: nothing mutates before authority.
        self.assertEqual(closure.open_obligation_ids(),("local","wide-1","wide-2","wide-3"))
        self.assertEqual(closure.active_capability_ids(),())

    def test_future_guard_changes_market_without_mutating_memory(self):
        quotient=FutureQuotient(
            states=(PresentState("a"),PresentState("b")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        )
        quotient.admit_continuation(ProtectedContinuation(
            continuation_id="same",
            outcomes=(("a","0"),("b","0")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        ))
        obs=(obligation("o",(("t","y"),),{
            "transport":(("t","x","y"),),
            "fingerprints":("c1","c2","c3","c4"),
        }),)
        closure=FlashClosure(obs,future_quotient=quotient)

        proposal=AcquisitionProposal(
            proposal_id="merge-dependent",
            capability=cap("c",(("x","y"),)),
            verification_cost=1,
            future_equivalences=(("a","b"),),
        )
        self.assertEqual(
            closure.rank_acquisition_proposals((proposal,))[0].future_search_removed,
            4,
        )

        quotient.admit_continuation(ProtectedContinuation(
            continuation_id="split",
            outcomes=(("a","0"),("b","1")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        ))
        score=closure.rank_acquisition_proposals((proposal,))[0]
        self.assertEqual(score.future_search_removed,0)
        self.assertEqual(score.value,0.0)
        self.assertEqual(closure.active_capability_ids(),())

    def test_verified_winner_realizes_predicted_search_elimination(self):
        transport=(("t0","x0","y0"),("t1","x1","y1"))
        obs=tuple(
            obligation(f"o{i}",(("t0","y0"),("t1","y1")),{
                "transport":transport,
                "fingerprints":tuple(f"{i}-{j}" for j in range(4)),
            })
            for i in range(3)
        )
        closure=FlashClosure(obs)
        runtime=FlashEventRuntime(closure)
        candidate=cap("winner",(("x0","y0"),("x1","y1")))
        proposal=AcquisitionProposal(
            proposal_id="p",
            capability=candidate,
            verification_cost=2,
        )
        score=closure.rank_acquisition_proposals((proposal,))[0]
        self.assertEqual(score.future_search_removed,12)

        delta=runtime.apply(CapabilityAdmissionEvent(
            event_id="verified-winner",
            capability=candidate,
            oracle=(("x0","y0"),("x1","y1")),
            origin="independent-authority",
        ))
        self.assertEqual(delta.discharged,("o0","o1","o2"))
        self.assertEqual(
            sum(closure.obligations[o].cancelled_remaining_search for o in delta.discharged),
            12,
        )


if __name__=="__main__":
    unittest.main()
