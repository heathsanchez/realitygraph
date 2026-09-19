import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    AcquisitionProposal,
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    LiveObligation,
)


AUTHORITY="authority-v1"
VERIFIER="verifier-v1"
CONTRACT=FlashContract(AUTHORITY,VERIFIER)


def cap(cid,input_type,output_type,rows,cost=1):
    return FiniteCapability(
        capability_id=cid,
        input_type=input_type,
        output_type=output_type,
        semantics=tuple(rows),
        guard_inputs=tuple(k for k,_ in rows),
        certificate_id=f"cert:{cid}",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(),
        cost=cost,
    )


def obligation(oid,source_type,output_type,oracle,transport,n):
    return LiveObligation(
        obligation_id=oid,
        input_type=f"T-{oid}",
        source_input_type=source_type,
        output_type=output_type,
        oracle=tuple(oracle),
        transport_to_source=tuple(transport),
        contract=CONTRACT,
        candidate_fingerprints=tuple(f"{oid}-{i}" for i in range(n)),
    )


class FlashCounterfactualMarketTests(unittest.TestCase):
    def test_compositional_option_value_beats_direct_local_win(self):
        obs=tuple(
            obligation(
                f"global-{i}",
                "X","Z",
                (("t0","z0"),("t1","z1")),
                (("t0","x0"),("t1","x1")),
                5,
            )
            for i in range(3)
        ) + (
            obligation(
                "local","L","W",
                (("t","w"),),
                (("t","l"),),
                2,
            ),
        )
        closure=FlashClosure(
            obs,
            composition_rules=(
                FlashCompositionRule(
                    rule_id="f-then-g",
                    first_capability_id="f",
                    second_capability_id="g",
                    result_capability_id="h",
                    oracle=(("x0","z0"),("x1","z1")),
                    certificate_id="cert:h",
                ),
            ),
        )
        f=cap("f","X","Y",(("x0","y0"),("x1","y1")))
        closure.admit_capability(
            f,
            oracle=(("x0","y0"),("x1","y1")),
        )

        # g directly solves zero current obligations. Its value exists only
        # through f ∘ g => h and the fixed-point consequences of h.
        g=cap("g","Y","Z",(("y0","z0"),("y1","z1")))
        local=cap("local-cap","L","W",(("l","w"),))

        ranked=closure.rank_acquisition_proposals((
            AcquisitionProposal(
                proposal_id="compose-global",
                capability=g,
                verification_cost=2,
            ),
            AcquisitionProposal(
                proposal_id="direct-local",
                capability=local,
                verification_cost=1,
            ),
        ))

        self.assertEqual(ranked[0].proposal_id,"compose-global")
        self.assertEqual(ranked[0].direct_obligations_solved,())
        self.assertEqual(
            ranked[0].obligations_solved,
            ("global-0","global-1","global-2"),
        )
        self.assertEqual(ranked[0].predicted_generated_capabilities,("h",))
        self.assertEqual(ranked[0].future_search_removed,15)
        self.assertEqual(ranked[0].value,7.5)

        self.assertEqual(ranked[1].proposal_id,"direct-local")
        self.assertEqual(ranked[1].future_search_removed,2)
        self.assertEqual(ranked[1].value,2.0)

        # Counterfactual scoring must not leak speculative state.
        self.assertEqual(closure.active_capability_ids(),("f",))
        self.assertEqual(
            closure.open_obligation_ids(),
            ("global-0","global-1","global-2","local"),
        )
        self.assertNotIn("g",closure.capabilities)
        self.assertNotIn("h",closure.capabilities)


if __name__=="__main__":
    unittest.main()
