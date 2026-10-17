from __future__ import annotations

import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    CapabilityAdmissionEvent,
    CapabilityRevocationEvent,
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    FlashEventRuntime,
    LiveObligation,
)

A = "audit-omega-1"
V = "audit-v1"


def cap(name: str, input_type: str, output_type: str, semantics, cost: int) -> FiniteCapability:
    return FiniteCapability(
        capability_id=name,
        input_type=input_type,
        output_type=output_type,
        semantics=tuple(semantics),
        guard_inputs=tuple(x for x, _ in semantics),
        certificate_id="cert-" + name,
        dependencies=(),
        authority_snapshot=A,
        verifier_id=V,
        provenance_ids=("pinned-native-v2",),
        cost=cost,
    )


def fixture():
    first = cap("f", "X", "Y", (("x0", "y0"), ("x1", "y1")), 2)
    second = cap("g", "Y", "Z", (("y0", "z0"), ("y1", "z1")), 2)
    expensive = cap("alt", "X", "Z", (("x0", "z0"), ("x1", "z1")), 9)
    obligation = LiveObligation(
        obligation_id="o", input_type="Task", source_input_type="X",
        output_type="Z", oracle=(("t0", "z0"), ("t1", "z1")),
        transport_to_source=(("t0", "x0"), ("t1", "x1")),
        contract=FlashContract(A, V),
        candidate_fingerprints=("bad", "good"),
    )
    rule = FlashCompositionRule(
        rule_id="f-then-g", first_capability_id="f",
        second_capability_id="g", result_capability_id="h",
        oracle=(("x0", "z0"), ("x1", "z1")), certificate_id="cert-h",
    )
    closure = FlashClosure((obligation,), composition_rules=(rule,))
    return closure, FlashEventRuntime(closure), first, second, expensive


class PreferenceRepairTests(unittest.TestCase):
    def test_new_verified_cheaper_composition_reselects_without_reopening(self):
        closure, runtime, f, g, alt = fixture()
        runtime.apply(CapabilityAdmissionEvent("alt", alt, alt.semantics))
        o = closure.obligations["o"]
        self.assertEqual(o.solved_by, "alt")
        before_reopen = o.reopen_count
        before_cancel = o.cancelled_remaining_search
        runtime.apply(CapabilityAdmissionEvent("f", f, f.semantics))
        runtime.apply(CapabilityAdmissionEvent("g", g, g.semantics))
        self.assertEqual(o.status, "DISCHARGED")
        self.assertEqual(o.solved_by, "h")
        self.assertEqual(o.support_ids, ("h", "f", "g"))
        self.assertEqual(o.reopen_count, before_reopen)
        self.assertEqual(o.cancelled_remaining_search, before_cancel)
        self.assertTrue(o.worker_cancelled)
        self.assertEqual(closure.compiled_present().restart().capability_graph.active_ids(), ("alt", "f", "g", "h"))
        stable = closure.close()
        self.assertEqual(stable.changed_obligations, ())
        self.assertEqual(stable.iterations, 1)

    def test_disabling_chosen_source_uses_independent_live_support(self):
        closure, runtime, f, g, alt = fixture()
        for name, capability in (("f", f), ("g", g), ("alt", alt)):
            runtime.apply(CapabilityAdmissionEvent(name, capability, capability.semantics))
        self.assertEqual(closure.obligations["o"].solved_by, "h")
        runtime.apply(CapabilityRevocationEvent("remove-f", "f", "source authority revoked"))
        self.assertEqual(closure.obligations["o"].status, "DISCHARGED")
        self.assertEqual(closure.obligations["o"].solved_by, "alt")
        runtime.apply(CapabilityRevocationEvent("remove-alt", "alt", "alternative withdrawn"))
        self.assertEqual(closure.obligations["o"].status, "OPEN")


if __name__ == "__main__":
    unittest.main()
