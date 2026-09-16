import unittest
from dataclasses import dataclass
from pathlib import Path

from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_state import DevelopmentalState
from realitygraph.developmental_types import canonical_digest
from realitygraph.generation_spec import CandidateEnumeration, FutureEvaluation, GenerationSpec, LanguageEnumeration
from realitygraph.grammar import FiniteConstructor, Grammar
from realitygraph.meta_executor import MetaGrowthRoute, MetaGrowthSpec, execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairEpisode, RepairPhase
from realitygraph.obstruction_fingerprint import canonicalize_obstruction
from realitygraph.repair_strategy import RepairPortfolio

AUTH = "meta-test-authority"
VERIFIER = "meta-test-verifier"


def base_constructor():
    return FiniteConstructor(
        constructor_id="base-zero",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "0")),
        complexity=0,
    )


def seeded_state():
    return DevelopmentalState(
        generation_index=0,
        grammar=Grammar((base_constructor(),)),
        capability_graph=CapabilityGraph(()),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot=AUTH,
        protected_consequence_digest="protected-meta-test",
        provenance_ids=("seed-meta-test",),
    )


class CurrentAdapter:
    adapter_id = "meta-current"

    def __init__(self, complete=True):
        self.complete = complete

    def enumerate_current(self, state, spec):
        return LanguageEnumeration(
            constructors=state.grammar.constructors,
            carrier_digest="carrier-meta",
            enumeration_digest="current-complete" if self.complete else "current-partial",
            replay_evidence=("enumerated-current",),
            complete=self.complete,
            search_exhausted=self.complete,
            raw_count=len(state.grammar.constructors),
        )


class NoCandidateAdapter:
    adapter_id = "no-candidates-placeholder"

    def enumerate_candidates(self, state, residual, spec):
        return CandidateEnumeration((), "none", ("none",), True, 0)


class CandidateAdapter:
    def __init__(self, adapter_id, signature, complexity=1):
        self.adapter_id = adapter_id
        self.signature = signature
        self.complexity = complexity

    def enumerate_candidates(self, state, residual, spec):
        candidate = FiniteConstructor(
            constructor_id=f"candidate-{self.adapter_id}",
            input_type="bit",
            output_type="bit",
            semantics=(("0", self.signature[0]), ("1", self.signature[1])),
            complexity=self.complexity,
        )
        return CandidateEnumeration(
            (candidate,),
            canonical_digest(candidate.payload(), prefix="meta-test-candidate:"),
            ("one-candidate",),
            True,
            1,
        )


class Verifier:
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
            input_type="bit",
            output_type="bit",
            semantics=candidate.semantics,
            guard_inputs=(),
            certificate_id=delta.delta_id,
            dependencies=(),
            authority_snapshot=AUTH,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id,),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        passed = all(capability.execute(x) == x for x in spec.future_manifest)
        return FutureEvaluation(
            passed,
            canonical_digest({"future": list(spec.future_manifest), "passed": passed}, prefix="meta-test-future:"),
            0,
            tuple((x, capability.execute(x)) for x in spec.future_manifest),
        )


class Attack:
    adapter_id = "meta-test-attack"

    def challenges(self, state, spec, capability):
        return ("0", "1")

    def oracle(self, state, spec, challenge):
        return challenge


class FingerprintBuilder:
    builder_id = "meta-test-fingerprint-builder"

    def build(self, state, spec, current):
        return canonicalize_obstruction(
            input_type=spec.input_type,
            output_type=spec.output_type,
            current_partition=(("a", "b"), ("c", "d")),
            consequence_partition=(("a", "c"), ("b", "d")),
            current_language_semantic_count=len(current.semantic_signatures),
            authority_snapshot=spec.authority_snapshot,
            verifier_id=spec.verifier_adapter.adapter_id,
        )


@dataclass(frozen=True)
class Strategy:
    strategy_id: str
    structural_cost: int
    signature: str
    complexity: int = 1
    strategy_version: str = "v1"
    applicable_value: bool = True

    def applicable(self, fingerprint, object_state, meta_spec):
        return self.applicable_value

    def materialize_generation_spec(self, object_state, meta_spec):
        return GenerationSpec(
            generation_id=f"object-{meta_spec.episode_id}-{self.strategy_id}",
            obligation_id=meta_spec.object_template.obligation_id,
            input_type="bit",
            output_type="bit",
            current_language_adapter=meta_spec.object_template.current_language_adapter,
            lower_substrate_adapter=CandidateAdapter(
                f"lower-{meta_spec.episode_id}-{self.strategy_id}",
                self.signature,
                self.complexity,
            ),
            verifier_adapter=meta_spec.object_template.verifier_adapter,
            attack_adapter=meta_spec.object_template.attack_adapter,
            acquisition_manifest=meta_spec.object_template.acquisition_manifest,
            growth_manifest=(self.strategy_id,),
            future_manifest=meta_spec.object_template.future_manifest,
            resource_envelope=(("candidate_budget", 1), ("attack_budget", 2)),
            authority_snapshot=AUTH,
            protected_consequences=("keep-base",),
        )


def object_template(*, complete=True):
    return GenerationSpec(
        generation_id="template",
        obligation_id="identity-bit",
        input_type="bit",
        output_type="bit",
        current_language_adapter=CurrentAdapter(complete),
        lower_substrate_adapter=NoCandidateAdapter(),
        verifier_adapter=Verifier(),
        attack_adapter=Attack(),
        acquisition_manifest=("a", "b", "c", "d"),
        growth_manifest=("identity-bit",),
        future_manifest=("0", "1"),
        resource_envelope=(("candidate_budget", 1), ("attack_budget", 2)),
        authority_snapshot=AUTH,
        protected_consequences=("keep-base",),
    )


def meta_spec(portfolio, *, phase=RepairPhase.ACQUISITION, complete=True, budget=None):
    return MetaGrowthSpec(
        episode_id=f"episode-{phase.value.lower()}",
        phase=phase,
        object_template=object_template(complete=complete),
        fingerprint_builder=FingerprintBuilder(),
        portfolio=portfolio,
        authority_snapshot=AUTH,
        verifier_id=VERIFIER,
        interface_digest="bit-to-bit-meta-test",
        portfolio_budget=len(portfolio.strategies) if budget is None else budget,
    )


def promoted_memory(spec, strategy):
    fp = FingerprintBuilder().build(seeded_state(), spec.object_template,
        spec.object_template.current_language_adapter.enumerate_current(seeded_state(), spec.object_template))
    memory = MetaMemory.empty()
    for ident, phase in (("source", RepairPhase.ACQUISITION), ("cal", RepairPhase.CALIBRATION)):
        memory = memory.record_success(RepairEpisode(
            episode_id=ident,
            phase=phase,
            obstruction_fingerprint=fp.digest,
            strategy_id=strategy.strategy_id,
            strategy_version=strategy.strategy_version,
            portfolio_digest=spec.portfolio.digest,
            authority_snapshot=AUTH,
            verifier_id=VERIFIER,
            interface_digest=spec.interface_digest,
            selection_cost=strategy.structural_cost,
            object_evidence_digest=f"evidence-{ident}",
        ))
    return memory


class MetaExecutorTests(unittest.TestCase):
    def test_cold_path_evaluates_full_applicable_portfolio_from_same_parent(self):
        failing = Strategy("fail", 1, "00")
        winning = Strategy("win", 2, "01")
        portfolio = RepairPortfolio((winning, failing))
        state = seeded_state()
        result = execute_meta_growth(state, MetaMemory.empty(), meta_spec(portfolio))
        self.assertEqual(result.route, MetaGrowthRoute.COMPILED)
        self.assertEqual(result.selected_strategy_id, "win")
        self.assertEqual(result.portfolio_search_calls, 2)
        self.assertEqual(result.competitor_strategy_calls, 1)
        self.assertEqual(set(result.strategy_parent_digests), {state.digest})
        self.assertEqual(result.object_state.generation_index, 1)

    def test_promoted_rule_hit_skips_competitors(self):
        winning = Strategy("win", 2, "01")
        competitor = Strategy("competitor", 1, "00")
        portfolio = RepairPortfolio((winning, competitor))
        spec = meta_spec(portfolio, phase=RepairPhase.FUTURE)
        memory = promoted_memory(spec, winning)
        result = execute_meta_growth(seeded_state(), memory, spec)
        self.assertEqual(result.route, MetaGrowthRoute.COMPILED)
        self.assertTrue(result.rule_hit)
        self.assertEqual(result.selected_strategy_id, "win")
        self.assertEqual(result.portfolio_search_calls, 0)
        self.assertEqual(result.competitor_strategy_calls, 0)
        self.assertEqual(result.selected_strategy_calls, 1)

    def test_partial_current_language_routes_unknown_search_without_strategy_calls(self):
        portfolio = RepairPortfolio((Strategy("win", 1, "01"),))
        result = execute_meta_growth(
            seeded_state(), MetaMemory.empty(), meta_spec(portfolio, complete=False)
        )
        self.assertEqual(result.route, MetaGrowthRoute.UNKNOWN_SEARCH)
        self.assertEqual(result.portfolio_search_calls, 0)
        self.assertEqual(result.selected_strategy_calls, 0)

    def test_partial_portfolio_budget_cannot_select_even_if_checked_strategy_succeeds(self):
        portfolio = RepairPortfolio((Strategy("a", 1, "01"), Strategy("b", 2, "00")))
        result = execute_meta_growth(
            seeded_state(), MetaMemory.empty(), meta_spec(portfolio, budget=1)
        )
        self.assertEqual(result.route, MetaGrowthRoute.UNKNOWN_SEARCH)
        self.assertEqual(result.object_state.digest, seeded_state().digest)

    def test_equal_ranked_successes_stay_unknown_choice(self):
        portfolio = RepairPortfolio((
            Strategy("alpha", 1, "01", complexity=1),
            Strategy("beta", 1, "01", complexity=1),
        ))
        result = execute_meta_growth(seeded_state(), MetaMemory.empty(), meta_spec(portfolio))
        self.assertEqual(result.route, MetaGrowthRoute.UNKNOWN_CHOICE)
        self.assertIsNone(result.selected_strategy_id)
        self.assertEqual(result.object_state.digest, seeded_state().digest)

    def test_complete_portfolio_with_no_success_is_named_meta_obstruction(self):
        portfolio = RepairPortfolio((Strategy("a", 1, "00"), Strategy("b", 2, "11")))
        result = execute_meta_growth(seeded_state(), MetaMemory.empty(), meta_spec(portfolio))
        self.assertEqual(result.route, MetaGrowthRoute.NAMED_META_OBSTRUCTION)
        self.assertEqual(result.object_state.digest, seeded_state().digest)

    def test_source_has_no_fixture_or_strategy_name_dispatch(self):
        source = Path("realitygraph/meta_executor.py").read_text()
        self.assertNotIn("realitygraph.fixtures", source)
        for forbidden in (
            "Family C", "Family T", "add_observable ==", "add_finite_memory_2 ==",
            'strategy_id == "', "strategy.strategy_id ==",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
