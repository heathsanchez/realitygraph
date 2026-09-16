from __future__ import annotations

import unittest

from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.closure import (
    AdmissionEvidence,
    ClosureCertificate,
    FrozenBoundary,
    TerminalRecord,
    audit_closure,
)
from realitygraph.developmental_core import DevelopmentalRoute, route_residual
from realitygraph.developmental_types import (
    CompletenessCertificate,
    DevelopmentalResult,
    NoResolutionCertificate,
    ResultKind,
)
from realitygraph.grammar import FiniteConstructor, Grammar
from realitygraph.grammar_growth import grow_grammar
from realitygraph.residual_certificate import make_expressivity_residual


class DevelopmentalClosureTests(unittest.TestCase):
    def expressivity_fixture(self):
        old = FiniteConstructor("zero", "pair", "bit", (("00", "0"), ("01", "0")), 0)
        grammar = Grammar((old,))
        complete = CompletenessCertificate(
            grammar.digest, "old", "state", "authority", (old.semantic_signature,), "v"
        )
        no_sep = NoResolutionCertificate(
            grammar.digest, "state", "authority", ("separate",),
            (old.semantic_signature,), "v"
        )
        residual = make_expressivity_residual(
            obligation_id="o-expand",
            state_digest="state",
            authority_snapshot="authority",
            language_id=grammar.digest,
            substrate_id="lower",
            protected_consequences=(),
            observational_equivalence=("a~b",),
            unresolved=("separate",),
            completeness=complete,
            no_resolution=no_sep,
            necessary_constraints=("separate",),
            candidate_version_space_digest="space",
            replay_evidence=(),
        )
        result = DevelopmentalResult(
            ResultKind.UNKNOWN_EXPRESSIVITY,
            "o-expand",
            "complete language cannot separate",
            residual.digest,
        )
        return grammar, residual, result

    def test_routes_are_constitutionally_separate(self):
        self.assertEqual(
            route_residual(DevelopmentalResult(ResultKind.UNKNOWN_SEARCH, "s")),
            DevelopmentalRoute.SEARCH,
        )
        self.assertEqual(
            route_residual(DevelopmentalResult(ResultKind.UNKNOWN_CHOICE, "c")),
            DevelopmentalRoute.EVIDENCE,
        )
        self.assertEqual(
            route_residual(DevelopmentalResult(ResultKind.UNKNOWN_IDENTITY, "i")),
            DevelopmentalRoute.SPLIT,
        )
        self.assertEqual(
            route_residual(DevelopmentalResult(ResultKind.AUTHORIZED, "a")),
            DevelopmentalRoute.TERMINAL,
        )
        _, residual, result = self.expressivity_fixture()
        self.assertEqual(
            route_residual(result, residual_certificate=residual),
            DevelopmentalRoute.EXPAND,
        )
        with self.assertRaises(ValueError):
            route_residual(result, residual_certificate=None)

    def capability_graph(self):
        cap = FiniteCapability(
            capability_id="c1",
            input_type="pair",
            output_type="bit",
            semantics=(("00", "0"),),
            guard_inputs=(),
            certificate_id="cert",
            dependencies=(),
            authority_snapshot="authority",
            verifier_id="v",
            provenance_ids=(),
            cost=1,
        )
        return CapabilityGraph((cap,))

    def boundary(self):
        return FrozenBoundary(
            world_manifest_digest="worlds",
            obligation_ids=("a", "b", "c"),
            language_digest="language-final",
            substrate_digest="substrate",
            verifier_digest="verifier",
            protected_consequence_digest="protected",
            resource_envelope="finite-budget-1",
        )

    def terminal_records(self):
        return (
            TerminalRecord("a", ResultKind.AUTHORIZED, "ca", True, "reused"),
            TerminalRecord("b", ResultKind.COMPILED, "cb", True, "grew"),
            TerminalRecord("c", ResultKind.UNKNOWN_CHOICE, "cc", True, "two lawful repairs"),
        )

    def test_closed_bounded_requires_exact_manifest_and_structural_evidence(self):
        grammar, residual, _ = self.expressivity_fixture()
        candidate = FiniteConstructor("new", "pair", "bit", (("00", "0"), ("01", "1")), 1)
        growth = grow_grammar(
            residual,
            grammar,
            (candidate,),
            authority_snapshot="authority",
            adequate=lambda c, r: True,
            preserves=lambda c: True,
            verify=lambda c: True,
            verifier_id="v",
        )
        delta = growth.delta
        evidence = AdmissionEvidence(delta.delta_id, "restart-ok", "ablation-ok")
        cert = audit_closure(
            self.boundary(),
            self.terminal_records(),
            grammar_deltas=(delta,),
            capability_graph=self.capability_graph(),
            admission_evidence=(evidence,),
            replay_digest="replay-exact",
        )
        self.assertEqual(cert.status, "CLOSED_BOUNDED")
        text = cert.text()
        self.assertEqual(ClosureCertificate.from_text(text).text(), text)

        with self.assertRaises(ValueError):
            audit_closure(
                self.boundary(),
                self.terminal_records()[:-1],
                grammar_deltas=(delta,),
                capability_graph=self.capability_graph(),
                admission_evidence=(evidence,),
                replay_digest="replay-exact",
            )
        with self.assertRaises(ValueError):
            audit_closure(
                self.boundary(),
                self.terminal_records(),
                grammar_deltas=(delta,),
                capability_graph=self.capability_graph(),
                admission_evidence=(),
                replay_digest="replay-exact",
            )

    def test_unresolved_expressivity_or_nonreplayable_record_blocks_closure(self):
        records = list(self.terminal_records())
        records[-1] = TerminalRecord(
            "c", ResultKind.UNKNOWN_EXPRESSIVITY, "cx", True, "still needs language"
        )
        with self.assertRaises(ValueError):
            audit_closure(
                self.boundary(), tuple(records), grammar_deltas=(),
                capability_graph=self.capability_graph(), admission_evidence=(),
                replay_digest="r",
            )
        records[-1] = TerminalRecord(
            "c", ResultKind.UNKNOWN_SEARCH, "cs", False, "not replayable"
        )
        with self.assertRaises(ValueError):
            audit_closure(
                self.boundary(), tuple(records), grammar_deltas=(),
                capability_graph=self.capability_graph(), admission_evidence=(),
                replay_digest="r",
            )


if __name__ == "__main__":
    unittest.main()
