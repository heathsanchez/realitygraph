from __future__ import annotations

import unittest

from realitygraph.attack import AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability, compose_capabilities
from realitygraph.capability_graph import CapabilityGraph


class CapabilityAlgebraTests(unittest.TestCase):
    def cap(self, ident, input_type, output_type, table, *, deps=(), guard=()):
        return FiniteCapability(
            capability_id=ident,
            input_type=input_type,
            output_type=output_type,
            semantics=tuple(table),
            guard_inputs=tuple(guard),
            certificate_id=f"cert-{ident}",
            dependencies=tuple(deps),
            authority_snapshot="authority-frozen",
            verifier_id="finite-semantic-v1",
            provenance_ids=(f"prov-{ident}",),
            cost=1,
        )

    def test_composition_is_typed_and_evaluated_explicitly(self):
        first = self.cap("first", "pair", "bit", (("00", "0"), ("01", "1")))
        second = self.cap("second", "bit", "label", (("0", "N"), ("1", "Y")))
        composite = compose_capabilities("composed", first, second)
        self.assertEqual(composite.input_type, "pair")
        self.assertEqual(composite.output_type, "label")
        self.assertEqual(composite.execute("00"), "N")
        self.assertEqual(composite.execute("01"), "Y")
        self.assertEqual(set(composite.dependencies), {"first", "second"})

        wrong = self.cap("wrong", "number", "label", (("0", "N"),))
        with self.assertRaises(ValueError):
            compose_capabilities("bad", first, wrong)

    def test_composition_requires_bridge_for_authority_or_verifier_mismatch(self):
        first = self.cap("first", "pair", "bit", (("00", "0"),))
        second = FiniteCapability(
            capability_id="second",
            input_type="bit",
            output_type="label",
            semantics=(("0", "N"),),
            guard_inputs=(),
            certificate_id="cert-second",
            dependencies=(),
            authority_snapshot="different-authority",
            verifier_id="other-verifier",
            provenance_ids=(),
            cost=1,
        )
        with self.assertRaises(ValueError):
            compose_capabilities("bad", first, second)
        bridged = compose_capabilities(
            "bridged", first, second, bridge_verifier=lambda a, b: True
        )
        self.assertEqual(bridged.execute("00"), "N")

    def test_dependency_graph_rejects_cycles_and_ablation_is_transitive(self):
        g1 = self.cap("g1", "a", "b", (("x", "y"),))
        g2 = self.cap("g2", "b", "c", (("y", "z"),), deps=("g1",))
        g3 = self.cap("g3", "c", "d", (("z", "w"),), deps=("g2",))
        graph = CapabilityGraph((g1, g2, g3))
        self.assertEqual(set(graph.active_ids()), {"g1", "g2", "g3"})

        after_g1 = graph.ablate("g1")
        self.assertEqual(after_g1.active_ids(), ())
        after_g2 = graph.ablate("g2")
        self.assertEqual(set(after_g2.active_ids()), {"g1"})

        c1 = self.cap("c1", "a", "b", (("x", "y"),), deps=("c2",))
        c2 = self.cap("c2", "b", "c", (("y", "z"),), deps=("c1",))
        with self.assertRaises(ValueError):
            CapabilityGraph((c1, c2))

    def test_graph_rejects_initial_missing_dependency(self):
        orphan = self.cap("orphan", "a", "b", (("x", "y"),), deps=("missing",))
        with self.assertRaises(ValueError):
            CapabilityGraph((orphan,))

    def test_exhaustive_attack_survives_only_complete_matching_challenge_set(self):
        capability = self.cap(
            "truth",
            "pair",
            "bit",
            (("00", "0"), ("01", "1"), ("10", "1"), ("11", "0")),
        )
        oracle = {"00": "0", "01": "1", "10": "1", "11": "0"}
        survived = exhaustive_attack(
            capability, oracle, ("00", "01", "10", "11"), budget=4
        )
        self.assertEqual(survived.status, AttackStatus.SURVIVE)
        self.assertEqual(survived.checked, 4)

        partial = exhaustive_attack(
            capability, oracle, ("00", "01", "10", "11"), budget=3
        )
        self.assertEqual(partial.status, AttackStatus.UNKNOWN_ATTACK)

        bad_oracle = dict(oracle)
        bad_oracle["10"] = "0"
        refuted = exhaustive_attack(
            capability, bad_oracle, ("00", "01", "10", "11"), budget=4
        )
        self.assertEqual(refuted.status, AttackStatus.REVOKE)
        self.assertEqual(refuted.counterexample, ("10", "1", "0"))


if __name__ == "__main__":
    unittest.main()
