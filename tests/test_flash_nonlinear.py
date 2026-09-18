import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    LiveObligation,
)


AUTHORITY = "flash-authority-v1"
VERIFIER = "flash-verifier-v1"
CONTRACT = FlashContract(AUTHORITY, VERIFIER)


def cap_f():
    return FiniteCapability(
        capability_id="f",
        input_type="X",
        output_type="Y",
        semantics=(("x0", "y0"), ("x1", "y1")),
        guard_inputs=("x0", "x1"),
        certificate_id="cert-f",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("source-f",),
        cost=1,
    )


def cap_g():
    return FiniteCapability(
        capability_id="g",
        input_type="Y",
        output_type="Z",
        semantics=(("y0", "z0"), ("y1", "z1")),
        guard_inputs=("y0", "y1"),
        certificate_id="cert-g",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("source-g",),
        cost=1,
    )


def obligations():
    rows = []
    for i in range(3):
        rows.append(
            LiveObligation(
                obligation_id=f"o{i}",
                input_type=f"Target{i}",
                source_input_type="X",
                output_type="Z",
                oracle=(("t0", "z0"), ("t1", "z1")),
                transport_to_source=(("t0", "x0"), ("t1", "x1")),
                contract=CONTRACT,
                candidate_fingerprints=tuple(f"o{i}-candidate-{j}" for j in range(5)),
                domain=f"domain-{i}",
            )
        )
    return tuple(rows)


def engine():
    return FlashClosure(
        obligations(),
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


class FlashNonlinearTests(unittest.TestCase):
    def test_composition_has_positive_interaction_effect(self):
        only_f = engine()
        delta_f = only_f.admit_capability(
            cap_f(),
            oracle=(("x0", "y0"), ("x1", "y1")),
        )
        self.assertEqual(delta_f.discharged, ())
        self.assertEqual(only_f.total_cancelled_future_search, 0)

        only_g = engine()
        delta_g = only_g.admit_capability(
            cap_g(),
            oracle=(("y0", "z0"), ("y1", "z1")),
        )
        self.assertEqual(delta_g.discharged, ())
        self.assertEqual(only_g.total_cancelled_future_search, 0)

        coupled = engine()
        coupled.admit_capability(
            cap_f(),
            oracle=(("x0", "y0"), ("x1", "y1")),
        )
        delta_fg = coupled.admit_capability(
            cap_g(),
            oracle=(("y0", "z0"), ("y1", "z1")),
        )

        self.assertEqual(delta_fg.generated_capabilities, ("h",))
        self.assertEqual(delta_fg.discharged, ("o0", "o1", "o2"))
        self.assertEqual(delta_fg.flash_radius, 3)
        self.assertGreaterEqual(delta_fg.iterations, 2)
        self.assertEqual(coupled.total_cancelled_future_search, 15)

        interaction_effect = (
            coupled.total_cancelled_future_search
            - only_f.total_cancelled_future_search
            - only_g.total_cancelled_future_search
        )
        self.assertEqual(interaction_effect, 15)
        self.assertGreater(interaction_effect, 0)

    def test_revoking_one_support_reopens_all_dependents_in_same_flash(self):
        coupled = engine()
        coupled.admit_capability(
            cap_f(),
            oracle=(("x0", "y0"), ("x1", "y1")),
        )
        coupled.admit_capability(
            cap_g(),
            oracle=(("y0", "z0"), ("y1", "z1")),
        )
        delta = coupled.revoke_capability("f", reason="counterfactual ablation")

        self.assertEqual(delta.reopened, ("o0", "o1", "o2"))
        self.assertEqual(delta.flash_radius, 3)
        self.assertEqual(coupled.open_obligation_ids(), ("o0", "o1", "o2"))
        self.assertNotIn("h", coupled.active_capability_ids())


if __name__ == "__main__":
    unittest.main()
