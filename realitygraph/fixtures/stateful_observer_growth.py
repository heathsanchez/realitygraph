from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from realitygraph.attack import AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_types import (
    CompletenessCertificate,
    NoResolutionCertificate,
    canonical_digest,
)
from realitygraph.fixtures.boolean_observer_growth import AUTHORITY, VERIFIER
from realitygraph.grammar import FiniteConstructor, Grammar, GrammarDelta
from realitygraph.grammar_growth import ablate_delta, apply_delta, grow_grammar
from realitygraph.residual_certificate import make_expressivity_residual


TRAIN_HISTORIES = ("00>00", "01>00", "10>00", "11>00")
FUTURE_HISTORIES = ("00>11", "01>11", "10>11", "11>11")
TARGET_SIGNATURE = "0110"


@dataclass(frozen=True)
class TwoStateMooreMachine:
    transitions: tuple[int, int, int, int]
    outputs: tuple[int, int]

    def __post_init__(self) -> None:
        if any(value not in (0, 1) for value in (*self.transitions, *self.outputs)):
            raise ValueError("two-state fixture uses binary transition/output tables")

    @property
    def machine_id(self) -> str:
        t = "".join(str(x) for x in self.transitions)
        o = "".join(str(x) for x in self.outputs)
        return f"fsm-t{t}-o{o}"

    @property
    def complexity(self) -> int:
        # Deterministic finite description cost. The constant base prevents a
        # stateful machine from being treated as a free stateless atom.
        return 1 + sum(self.transitions) + sum(self.outputs)

    def run(self, signals: tuple[int, ...]) -> str:
        state = 0
        for signal in signals:
            state = self.transitions[2 * state + int(signal)]
        return str(self.outputs[state])


def _split_history(history: str) -> tuple[str, str]:
    previous, present = history.split(">", 1)
    return previous, present


def _history_target(g1_capability: FiniteCapability, history: str) -> str:
    previous, _ = _split_history(history)
    return g1_capability.execute(previous)


def _machine_observe(
    machine: TwoStateMooreMachine,
    g1_capability: FiniteCapability,
    history: str,
) -> str:
    previous, present = _split_history(history)
    signals = (
        int(g1_capability.execute(previous)),
        int(g1_capability.execute(present)),
    )
    return machine.run(signals)


def _stateless_history_constructors() -> tuple[FiniteConstructor, ...]:
    rows = []
    # Exhaust all 16 Boolean denotations of the current (x,y) pair. Every
    # training history has the same current pair 00, so each denotation is
    # observationally constant over the histories despite being source-distinct.
    for number in range(16):
        source_signature = format(number, "04b")
        output_at_00 = source_signature[0]
        history_signature = output_at_00 * len(TRAIN_HISTORIES)
        rows.append(
            FiniteConstructor(
                constructor_id=f"g2-stateless-{source_signature}",
                input_type="history",
                output_type="bit",
                semantics=tuple(zip(TRAIN_HISTORIES, history_signature)),
                complexity=0,
                primitive_expansion=(f"current-table:{source_signature}",),
            )
        )
    return tuple(rows)


def enumerate_stateful_candidates(g1_constructor: FiniteConstructor, g1_capability: FiniteCapability):
    best_by_signature: dict[str, tuple[tuple[int, str], FiniteConstructor, TwoStateMooreMachine]] = {}
    for transition_bits in product((0, 1), repeat=4):
        for output_bits in product((0, 1), repeat=2):
            machine = TwoStateMooreMachine(tuple(transition_bits), tuple(output_bits))
            signature = "".join(
                _machine_observe(machine, g1_capability, history)
                for history in TRAIN_HISTORIES
            )
            constructor = FiniteConstructor(
                constructor_id=machine.machine_id,
                input_type="history",
                output_type="bit",
                semantics=tuple(zip(TRAIN_HISTORIES, signature)),
                complexity=machine.complexity,
                dependencies=(g1_constructor.constructor_id,),
                primitive_expansion=(
                    f"two-state-moore:transitions={machine.transitions}:outputs={machine.outputs}",
                ),
            )
            key = (machine.complexity, machine.machine_id)
            old = best_by_signature.get(signature)
            if old is None or key < old[0]:
                best_by_signature[signature] = (key, constructor, machine)
    ordered = sorted(
        (item[1], item[2]) for item in best_by_signature.values()
    , key=lambda pair: (pair[0].complexity, pair[0].constructor_id))
    candidates = tuple(pair[0] for pair in ordered)
    machines = {pair[0].constructor_id: pair[1] for pair in ordered}
    return candidates, machines


def build_g2(g1: dict) -> dict:
    g1_constructor: FiniteConstructor = g1["constructor"]
    g1_capability: FiniteCapability = g1["capability"]

    stateless = _stateless_history_constructors()
    # G2 starts from the already-earned G1 grammar plus a separately declared,
    # exhaustively characterized stateless present-observer class.
    parent = Grammar((*g1["child_grammar"].constructors, *stateless))
    source_denotations = tuple(format(number, "04b") for number in range(16))
    effective_history_signatures = tuple(
        sorted({constructor.semantic_signature for constructor in stateless})
    )
    state_digest = canonical_digest(
        {
            "generation": 2,
            "training_histories": list(TRAIN_HISTORIES),
            "g1": g1_constructor.constructor_id,
            "stateless_source_denotations": list(source_denotations),
        },
        prefix="g2-state-v1:",
    )
    complete = CompletenessCertificate(
        language_id=parent.digest,
        substrate_scope="all-16-stateless-current-pair-denotations",
        state_digest=state_digest,
        authority_snapshot=AUTHORITY,
        enumerated_signatures=source_denotations,
        verifier_id=VERIFIER,
        replay_evidence=("exhausted-all-2^4-current-pair-boolean-maps",),
    )
    no_resolution = NoResolutionCertificate(
        language_id=parent.digest,
        state_digest=state_digest,
        authority_snapshot=AUTHORITY,
        unresolved=("remember-previous-g1",),
        checked_signatures=effective_history_signatures,
        verifier_id=VERIFIER,
        replay_evidence=(
            "all-training-histories-share-current-pair=00",
            f"required-history-signature={TARGET_SIGNATURE}",
        ),
    )
    residual = make_expressivity_residual(
        obligation_id="g2-stateful-history-observer",
        state_digest=state_digest,
        authority_snapshot=AUTHORITY,
        language_id=parent.digest,
        substrate_id="generic-two-state-moore-over-earned-g1-signal",
        protected_consequences=("preserve-g1-parity-observer",),
        observational_equivalence=("same-present-different-prior-g1",),
        unresolved=("remember-previous-g1",),
        completeness=complete,
        no_resolution=no_resolution,
        necessary_constraints=(f"history-signature={TARGET_SIGNATURE}",),
        candidate_version_space_digest=canonical_digest(
            {
                "states": 2,
                "binary_inputs": True,
                "transition_tables": 16,
                "output_tables": 4,
                "input_signal": g1_constructor.constructor_id,
            },
            prefix="g2-lower-substrate-v1:",
        ),
        replay_evidence=("g2-fixture-frozen-before-machine-search",),
    )

    candidates, machines = enumerate_stateful_candidates(g1_constructor, g1_capability)
    growth = grow_grammar(
        residual,
        parent,
        candidates,
        authority_snapshot=AUTHORITY,
        adequate=lambda candidate, _: candidate.semantic_signature == TARGET_SIGNATURE,
        preserves=lambda candidate: g1_constructor.constructor_id in parent.constructor_map,
        verify=lambda candidate: (
            candidate.constructor_id in machines
            and "".join(
                _machine_observe(machines[candidate.constructor_id], g1_capability, history)
                for history in TRAIN_HISTORIES
            )
            == candidate.semantic_signature
            == TARGET_SIGNATURE
        ),
        verifier_id=VERIFIER,
        provenance_ids=("g2-complete-stateless-language", g1["delta"].delta_id),
    )
    if not growth.accepted or growth.candidate is None or growth.delta is None:
        raise AssertionError("G2 fixture failed to synthesize a stateful separator")

    selected = growth.candidate
    delta: GrammarDelta = growth.delta
    child = apply_delta(parent, delta)
    restarted_child = Grammar.from_text(child.text())
    restarted_delta = GrammarDelta.from_text(delta.text())
    restart_exact = restarted_child.text() == child.text() and restarted_delta.text() == delta.text()
    machine = machines[selected.constructor_id]

    all_histories = (*TRAIN_HISTORIES, *FUTURE_HISTORIES)
    compiled_semantics = tuple(
        (history, _machine_observe(machine, g1_capability, history))
        for history in all_histories
    )
    g2_capability = FiniteCapability(
        capability_id=selected.constructor_id,
        input_type="history",
        output_type="bit",
        semantics=compiled_semantics,
        guard_inputs=(),
        certificate_id=f"{delta.delta_id}:complete-history-scope",
        dependencies=(g1_capability.capability_id,),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(delta.delta_id, g1["delta"].delta_id),
        cost=selected.complexity,
    )
    graph = CapabilityGraph((g1_capability, g2_capability))
    oracle = {
        history: _history_target(g1_capability, history)
        for history in all_histories
    }
    attack = exhaustive_attack(
        g2_capability, oracle, all_histories, budget=len(all_histories)
    )

    future_predictions = tuple(g2_capability.execute(history) for history in FUTURE_HISTORIES)
    future_expected = tuple(oracle[history] for history in FUTURE_HISTORIES)
    g1_ablated_graph = graph.ablate(g1_capability.capability_id)
    g2_ablated_graph = graph.ablate(g2_capability.capability_id)
    restored_parent = ablate_delta(child, delta)

    return {
        "parent_grammar": parent,
        "complete": complete,
        "no_resolution": no_resolution,
        "residual": residual,
        "candidates": candidates,
        "machines": machines,
        "growth": growth,
        "constructor": selected,
        "delta": delta,
        "child_grammar": child,
        "capability": g2_capability,
        "capability_graph": graph,
        "machine": machine,
        "attack": attack,
        "restart_exact": restart_exact,
        "future_predictions": future_predictions,
        "future_expected": future_expected,
        "future_search_calls": 0,
        "grammar_search_calls": len(growth.verdicts),
        "stateless_language_complete": len(source_denotations) == 16,
        "stateless_no_resolution": TARGET_SIGNATURE not in set(effective_history_signatures),
        "stateful_novelty": not parent.extensionally_contains(selected),
        "depends_on_g1": g1_constructor.constructor_id in selected.dependencies,
        "future_reuse_zero_search": future_predictions == future_expected,
        "attack_survives": attack.status is AttackStatus.SURVIVE,
        "g1_ablation_invalidates_g2": (
            g1_capability.capability_id not in g1_ablated_graph.active_ids()
            and g2_capability.capability_id not in g1_ablated_graph.active_ids()
        ),
        "g2_only_ablation_preserves_g1": (
            g1_capability.capability_id in g2_ablated_graph.active_ids()
            and g2_capability.capability_id not in g2_ablated_graph.active_ids()
            and g1_constructor.constructor_id in restored_parent.constructor_map
        ),
    }
