import unittest
from pathlib import Path

from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_executor import execute_generation
from realitygraph.developmental_state import DevelopmentalState
from realitygraph.developmental_types import canonical_digest
from realitygraph.generation_spec import (
    CandidateEnumeration,
    FutureEvaluation,
    GenerationSpec,
    LanguageEnumeration,
)
from realitygraph.grammar import FiniteConstructor, Grammar


AUTHORITY = "executor-test-authority"
VERIFIER = "executor-test-verifier"


def base_constructor():
    return FiniteConstructor(
        constructor_id="base-zero",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "0")),
        complexity=0,
    )


def novel_constructor():
    return FiniteConstructor(
        constructor_id="novel-identity",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "1")),
        complexity=1,
    )


def seeded_state():
    return DevelopmentalState(
        generation_index=0,
        grammar=Grammar((base_constructor(),)),
        capability_graph=CapabilityGraph(()),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot=AUTHORITY,
        protected_consequence_digest="protected-test",
        provenance_ids=("seed",),
    )


class _PartialCurrent:
    adapter_id = "partial-current"

    def enumerate_current(self, state, spec):
        return LanguageEnumeration(
            constructors=state.grammar.constructors,
            carrier_digest="carrier",
            enumeration_digest="partial-enum",
            replay_evidence=("budget-stop",),
            complete=False,
            search_exhausted=False,
            raw_count=1,
        )


class _CompleteCurrent:
    adapter_id = "complete-current"

    def enumerate_current(self, state, spec):
        return LanguageEnumeration(
            constructors=state.grammar.constructors,
            carrier_digest="carrier",
            enumeration_digest="complete-enum",
            replay_evidence=("exhausted",),
            complete=True,
            search_exhausted=True,
            raw_count=len(state.grammar.constructors),
        )


class _NoCandidates:
    adapter_id = "no-candidates"

    def enumerate_candidates(self, state, residual, spec):
        return CandidateEnumeration((), "none", ("none",), True, 0)


class _OneCandidate:
    adapter_id = "one-candidate"

    def enumerate_candidates(self, state, residual, spec):
        candidate = novel_constructor()
        return CandidateEnumeration(
            (candidate,),
            canonical_digest(candidate.payload(), prefix="candidate-test:"),
            ("one-candidate",),
            True,
            1,
        )


class _Verifier:
    adapter_id = VERIFIER

    def current_resolves(self, state, spec, constructor):
        return constructor.semantic_signature == "01"

    def candidate_adequate(self, state, spec, candidate):
        return candidate.semantic_signature == "01"

    def verify_candidate(self, state, spec, candidate):
        return candidate.semantic_signature == "01"

    def verify_protected(self, state, spec, candidate):
        return True

    def compile_capability(self, state, spec, candidate, delta):
        return FiniteCapability(
            capability_id=candidate.constructor_id,
            input_type=candidate.input_type,
            output_type=candidate.output_type,
            semantics=candidate.semantics,
            guard_inputs=(),
            certificate_id=delta.delta_id,
            dependencies=spec.required_dependency_ids,
            authority_snapshot=spec.authority_snapshot,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id,),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        passed = all(capability.execute(value) == value for value in spec.future_manifest)
        return FutureEvaluation(
            passed=passed,
            evidence_digest=canonical_digest(
                {"future": list(spec.future_manifest), "passed": passed},
                prefix="future-test:",
            ),
            grammar_search_calls=0,
            observations=tuple((value, capability.execute(value)) for value in spec.future_manifest),
        )


class _Attack:
    adapter_id = "attack-test"

    def challenges(self, state, spec, capability):
        return ("0", "1")

    def oracle(self, state, spec, challenge):
        return challenge


def make_spec(current, lower):
    return GenerationSpec(
        generation_id="generic-probe",
        obligation_id="identity-bit",
        input_type="bit",
        output_type="bit",
        current_language_adapter=current,
        lower_substrate_adapter=lower,
        verifier_adapter=_Verifier(),
        attack_adapter=_Attack(),
        acquisition_manifest=("seed",),
        growth_manifest=("identity-bit",),
        future_manifest=("0", "1"),
        resource_envelope=(("candidate_budget", 10), ("attack_budget", 2)),
        authority_snapshot=AUTHORITY,
        protected_consequences=("keep-base",),
        required_dependency_ids=(),
    )


class DevelopmentalExecutorTests(unittest.TestCase):
    def test_partial_current_language_routes_unknown_search_without_growth(self):
        state = seeded_state()
        result = execute_generation(state, make_spec(_PartialCurrent(), _NoCandidates()))
        self.assertEqual(result.trace.route, "UNKNOWN_SEARCH")
        self.assertEqual(result.state.digest, state.digest)
        self.assertIsNone(result.trace.admitted_delta_id)
        self.assertIsNone(result.capability)

    def test_complete_unresolved_language_can_license_growth(self):
        state = seeded_state()
        result = execute_generation(state, make_spec(_CompleteCurrent(), _OneCandidate()))
        self.assertEqual(result.trace.route, "COMPILED")
        self.assertTrue(result.trace.completeness_digest)
        self.assertTrue(result.trace.no_resolution_digest)
        self.assertTrue(result.trace.residual_digest)
        self.assertTrue(result.trace.admitted_delta_id)
        self.assertIsNotNone(result.capability)
        self.assertEqual(result.capability.capability_id, "novel-identity")
        self.assertEqual(result.future.grammar_search_calls, 0)
        self.assertEqual(result.state.generation_index, 1)

    def test_executor_source_has_no_fixture_import_or_generation_dispatch(self):
        source = Path("realitygraph/developmental_executor.py").read_text()
        self.assertNotIn("realitygraph.fixtures", source)
        for forbidden in ("G1", "G2", "G3", "generation_id ==", "constructor_id =="):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
