from __future__ import annotations

import json

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    FutureQuotient,
    LiveObligation,
    PresentState,
    ProtectedContinuation,
)


AUTHORITY = "flash-authority-v1"
VERIFIER = "flash-verifier-v1"


def capability(cid, input_type, output_type, rows, cert):
    return FiniteCapability(
        capability_id=cid,
        input_type=input_type,
        output_type=output_type,
        semantics=tuple(rows),
        guard_inputs=tuple(key for key, _ in rows),
        certificate_id=cert,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(f"source-{cid}",),
        cost=1,
    )


def make_engine():
    contract = FlashContract(AUTHORITY, VERIFIER)
    obligations = tuple(
        LiveObligation(
            obligation_id=f"o{i}",
            input_type=f"Target{i}",
            source_input_type="X",
            output_type="Z",
            oracle=(("t0", "z0"), ("t1", "z1")),
            transport_to_source=(("t0", "x0"), ("t1", "x1")),
            contract=contract,
            candidate_fingerprints=tuple(f"o{i}-candidate-{j}" for j in range(5)),
            domain=f"domain-{i}",
        )
        for i in range(3)
    )
    return FlashClosure(
        obligations,
        composition_rules=(
            FlashCompositionRule(
                rule_id="compose-f-g",
                first_capability_id="f",
                second_capability_id="g",
                result_capability_id="h",
                oracle=(("x0", "z0"), ("x1", "z1")),
                certificate_id="cert-h",
            ),
        ),
    )


def run_nonlinear():
    f = capability("f", "X", "Y", (("x0", "y0"), ("x1", "y1")), "cert-f")
    g = capability("g", "Y", "Z", (("y0", "z0"), ("y1", "z1")), "cert-g")

    only_f = make_engine()
    only_f.admit_capability(f, oracle=f.semantics)
    f_removed = only_f.total_cancelled_future_search

    only_g = make_engine()
    only_g.admit_capability(g, oracle=g.semantics)
    g_removed = only_g.total_cancelled_future_search

    coupled = make_engine()
    coupled.admit_capability(f, oracle=f.semantics)
    flash = coupled.admit_capability(g, oracle=g.semantics)
    fg_removed = coupled.total_cancelled_future_search
    interaction = fg_removed - f_removed - g_removed

    if not (
        f_removed == 0
        and g_removed == 0
        and fg_removed == 15
        and interaction == 15
        and flash.generated_capabilities == ("h",)
        and flash.flash_radius == 3
        and flash.iterations >= 2
    ):
        raise AssertionError("nonlinear flash interaction did not survive the frozen control")

    revoked = coupled.revoke_capability("f", reason="frozen ablation")
    if revoked.reopened != ("o0", "o1", "o2"):
        raise AssertionError("ablation did not restore dependent unresolved obligations")

    return {
        "f_alone_future_search_removed": f_removed,
        "g_alone_future_search_removed": g_removed,
        "coupled_future_search_removed": fg_removed,
        "interaction_effect": interaction,
        "generated_capabilities": list(flash.generated_capabilities),
        "flash_radius": flash.flash_radius,
        "closure_iterations": flash.iterations,
        "ablation_reopened": list(revoked.reopened),
    }


def run_continuation_ontology():
    quotient = FutureQuotient(
        states=(
            PresentState("a", provenance_ids=("history-a",)),
            PresentState("b", provenance_ids=("history-b",)),
            PresentState("c", provenance_ids=("history-c",)),
        ),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
    )

    first = quotient.admit_continuation(
        ProtectedContinuation(
            continuation_id="future-1",
            outcomes=(("a", "0"), ("b", "0"), ("c", "1")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        )
    )
    after_first = quotient.classes()

    second = quotient.admit_continuation(
        ProtectedContinuation(
            continuation_id="future-2",
            outcomes=(("a", "0"), ("b", "1"), ("c", "1")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        )
    )
    after_separator = quotient.classes()

    revoked = quotient.revoke_continuation(
        "future-2",
        reason="future no longer protected",
    )
    after_revoke = quotient.classes()

    if after_first != (("a", "b"), ("c",)):
        raise AssertionError("different histories failed to merge under identical protected futures")
    if after_separator != (("a",), ("b",), ("c",)):
        raise AssertionError("verified future separator failed to split present ontology")
    if after_revoke != (("a", "b"), ("c",)):
        raise AssertionError("revoked future separator failed to re-merge present ontology")

    return {
        "after_first_future": [list(group) for group in after_first],
        "after_separator": [list(group) for group in after_separator],
        "after_separator_split_classes": [list(group) for group in second.split_classes],
        "after_revoke": [list(group) for group in after_revoke],
        "after_revoke_merged_classes": [list(group) for group in revoked.merged_classes],
        "first_changed_states": list(first.changed_state_ids),
    }


def main():
    evidence = {
        "schema": "qckn-flash-nonlinear-nondual-v1",
        "nonlinear": run_nonlinear(),
        "continuation_relative_ontology": run_continuation_ontology(),
        "claim_boundary": (
            "finite exact demonstration of superadditive flash closure and "
            "continuation-relative present quotienting; not a new truth logic "
            "and not a universal open-ended intelligence theorem"
        ),
    }
    print(json.dumps(evidence, sort_keys=True, indent=2))
    print("PASS_FLASH_NONLINEAR_SUPERADDITIVITY")
    print("PASS_FLASH_CONTINUATION_RELATIVE_ONTOLOGY")
    print("PASS_QCKN_FLASH_NONLINEAR_NONDUAL_V1")


if __name__ == "__main__":
    main()
