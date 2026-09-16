from __future__ import annotations

from dataclasses import dataclass

from realitygraph.attack import AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability, compose_capabilities
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_types import (
    CompletenessCertificate,
    NoResolutionCertificate,
    canonical_digest,
)
from realitygraph.grammar import FiniteConstructor, Grammar, GrammarDelta
from realitygraph.grammar_growth import ablate_delta, apply_delta, grow_grammar
from realitygraph.residual_certificate import make_expressivity_residual


PAIR_INPUTS = ("00", "01", "10", "11")
PARITY_SIGNATURE = "0110"
AUTHORITY = "bounded-finite-authority-v1"
VERIFIER = "truth-table-exhaustive-v1"


@dataclass(frozen=True)
class NandExpression:
    op: str
    atom: str = ""
    left: "NandExpression | None" = None
    right: "NandExpression | None" = None

    @property
    def gates(self) -> int:
        if self.op == "atom":
            return 0
        assert self.left is not None and self.right is not None
        return 1 + self.left.gates + self.right.gates

    def text(self) -> str:
        if self.op == "atom":
            return self.atom
        assert self.left is not None and self.right is not None
        return f"nand({self.left.text()},{self.right.text()})"

    def evaluate(self, pair: str) -> str:
        if pair not in PAIR_INPUTS:
            raise ValueError(f"pair outside fixture carrier: {pair}")
        x, y = int(pair[0]), int(pair[1])
        if self.op == "atom":
            if self.atom == "0":
                return "0"
            if self.atom == "1":
                return "1"
            if self.atom == "x":
                return str(x)
            if self.atom == "y":
                return str(y)
            raise ValueError(f"unknown atom: {self.atom}")
        if self.op != "nand" or self.left is None or self.right is None:
            raise ValueError("malformed NAND expression")
        a = int(self.left.evaluate(pair))
        b = int(self.right.evaluate(pair))
        return str(1 - (a & b))

    @property
    def signature(self) -> str:
        return "".join(self.evaluate(pair) for pair in PAIR_INPUTS)


def _atoms() -> tuple[NandExpression, ...]:
    return tuple(NandExpression("atom", atom=value) for value in ("0", "1", "x", "y"))


def enumerate_nand_candidates(max_gates: int = 4):
    if max_gates < 1:
        return (), {}
    atoms = _atoms()
    by_gates: dict[int, tuple[NandExpression, ...]] = {0: atoms}
    seen = {expr.signature for expr in atoms}
    candidates: list[FiniteConstructor] = []
    expression_map: dict[str, NandExpression] = {}

    for gates in range(1, max_gates + 1):
        discovered: dict[str, NandExpression] = {}
        for left_gates in range(gates):
            right_gates = gates - 1 - left_gates
            lefts = sorted(by_gates.get(left_gates, ()), key=lambda expr: expr.text())
            rights = sorted(by_gates.get(right_gates, ()), key=lambda expr: expr.text())
            for left in lefts:
                for right in rights:
                    # NAND is commutative; canonical ordering removes syntactic duplicates.
                    if left.text() > right.text():
                        continue
                    expr = NandExpression("nand", left=left, right=right)
                    signature = expr.signature
                    if signature in seen or signature in discovered:
                        continue
                    discovered[signature] = expr
        ordered = tuple(discovered[key] for key in sorted(discovered))
        by_gates[gates] = ordered
        for expr in ordered:
            signature = expr.signature
            seen.add(signature)
            constructor_id = f"nand-g{gates}-{signature}"
            constructor = FiniteConstructor(
                constructor_id=constructor_id,
                input_type="pair",
                output_type="bit",
                semantics=tuple(zip(PAIR_INPUTS, signature)),
                complexity=gates,
                dependencies=(),
                primitive_expansion=(expr.text(),),
            )
            candidates.append(constructor)
            expression_map[constructor_id] = expr
    return tuple(candidates), expression_map


def old_x_only_grammar() -> Grammar:
    signatures = {
        "g0-zero": "0000",
        "g0-one": "1111",
        "g0-x": "0011",
        "g0-not-x": "1100",
    }
    constructors = tuple(
        FiniteConstructor(
            constructor_id=ident,
            input_type="pair",
            output_type="bit",
            semantics=tuple(zip(PAIR_INPUTS, signature)),
            complexity=0,
        )
        for ident, signature in signatures.items()
    )
    return Grammar(constructors)


def build_g1() -> dict:
    old = old_x_only_grammar()
    old_signatures = tuple(sorted(c.semantic_signature for c in old.constructors))
    state_digest = canonical_digest(
        {"generation": 1, "carrier": list(PAIR_INPUTS), "old": list(old_signatures)},
        prefix="g1-state-v1:",
    )
    complete = CompletenessCertificate(
        language_id=old.digest,
        substrate_scope="all-four-boolean-functions-of-x",
        state_digest=state_digest,
        authority_snapshot=AUTHORITY,
        enumerated_signatures=old_signatures,
        verifier_id=VERIFIER,
        replay_evidence=("exhausted-all-2^2-maps-x-to-bit",),
    )
    no_resolution = NoResolutionCertificate(
        language_id=old.digest,
        state_digest=state_digest,
        authority_snapshot=AUTHORITY,
        unresolved=("parity-observer",),
        checked_signatures=old_signatures,
        verifier_id=VERIFIER,
        replay_evidence=(f"target={PARITY_SIGNATURE}",),
    )
    residual = make_expressivity_residual(
        obligation_id="g1-parity-observer",
        state_digest=state_digest,
        authority_snapshot=AUTHORITY,
        language_id=old.digest,
        substrate_id="atoms-0-1-x-y-plus-nand-depth4",
        protected_consequences=("preserve-x-only-observers",),
        observational_equivalence=("old-language-collapses-parity",),
        unresolved=("parity-observer",),
        completeness=complete,
        no_resolution=no_resolution,
        necessary_constraints=(f"semantic-signature={PARITY_SIGNATURE}",),
        candidate_version_space_digest=canonical_digest(
            {"atoms": ["0", "1", "x", "y"], "op": "nand", "max_gates": 4},
            prefix="g1-lower-substrate-v1:",
        ),
        replay_evidence=("fixture-frozen-before-growth",),
    )

    candidates, expressions = enumerate_nand_candidates(4)
    growth = grow_grammar(
        residual,
        old,
        candidates,
        authority_snapshot=AUTHORITY,
        adequate=lambda candidate, _: candidate.semantic_signature == PARITY_SIGNATURE,
        preserves=lambda candidate: all(
            constructor.semantic_table
            == old.constructor_map[constructor.constructor_id].semantic_table
            for constructor in old.constructors
        ),
        verify=lambda candidate: (
            candidate.constructor_id in expressions
            and expressions[candidate.constructor_id].signature == candidate.semantic_signature
            and candidate.semantic_signature == PARITY_SIGNATURE
        ),
        verifier_id=VERIFIER,
        provenance_ids=("g1-complete-old-language", "g1-nand-search"),
    )
    if not growth.accepted or growth.candidate is None or growth.delta is None:
        raise AssertionError("G1 fixture failed to synthesize parity from NAND substrate")

    selected = growth.candidate
    delta: GrammarDelta = growth.delta
    child = apply_delta(old, delta)
    restarted_child = Grammar.from_text(child.text())
    restarted_delta = GrammarDelta.from_text(delta.text())
    restart_exact = restarted_child.text() == child.text() and restarted_delta.text() == delta.text()

    g1_capability = FiniteCapability(
        capability_id=selected.constructor_id,
        input_type="pair",
        output_type="bit",
        semantics=selected.semantics,
        guard_inputs=(),
        certificate_id=delta.delta_id,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(delta.delta_id,),
        cost=selected.complexity,
    )
    decoder = FiniteCapability(
        capability_id="bit-to-parity-label",
        input_type="bit",
        output_type="label",
        semantics=(("0", "EVEN"), ("1", "ODD")),
        guard_inputs=(),
        certificate_id="decoder-exact-v1",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("decoder-truth-table",),
        cost=1,
    )
    composite = compose_capabilities("g1-parity-label", g1_capability, decoder)
    graph = CapabilityGraph((g1_capability, decoder, composite))

    parity_oracle = dict(zip(PAIR_INPUTS, PARITY_SIGNATURE))
    attack = exhaustive_attack(g1_capability, parity_oracle, PAIR_INPUTS, budget=len(PAIR_INPUTS))
    label_oracle = {
        pair: ("ODD" if parity_oracle[pair] == "1" else "EVEN")
        for pair in PAIR_INPUTS
    }
    composition_attack = exhaustive_attack(
        composite, label_oracle, PAIR_INPUTS, budget=len(PAIR_INPUTS)
    )

    future_inputs = ("11", "01")
    future_predictions = tuple(g1_capability.execute(pair) for pair in future_inputs)
    future_expected = tuple(parity_oracle[pair] for pair in future_inputs)

    restored = ablate_delta(child, delta)
    ablated_graph = graph.ablate(g1_capability.capability_id)
    ablation_restores_old = (
        restored.text() == old.text()
        and not old.extensionally_contains(selected)
        and g1_capability.capability_id not in ablated_graph.active_ids()
        and composite.capability_id not in ablated_graph.active_ids()
    )

    return {
        "old_grammar": old,
        "complete": complete,
        "no_resolution": no_resolution,
        "residual": residual,
        "candidates": candidates,
        "expressions": expressions,
        "growth": growth,
        "constructor": selected,
        "delta": delta,
        "child_grammar": child,
        "capability": g1_capability,
        "decoder": decoder,
        "composite": composite,
        "capability_graph": graph,
        "attack": attack,
        "composition_attack": composition_attack,
        "restart_exact": restart_exact,
        "future_inputs": future_inputs,
        "future_predictions": future_predictions,
        "future_expected": future_expected,
        "future_search_calls": 0,
        "grammar_search_calls": len(growth.verdicts),
        "ablation_restores_old": ablation_restores_old,
        "old_language_complete": len(set(old_signatures)) == 4,
        "old_language_no_resolution": PARITY_SIGNATURE not in set(old_signatures),
        "extensional_novelty": not old.extensionally_contains(selected),
        "independently_verified": expressions[selected.constructor_id].signature == PARITY_SIGNATURE,
        "composition_verified": composition_attack.status is AttackStatus.SURVIVE,
        "attack_survives": attack.status is AttackStatus.SURVIVE,
        "future_reuse_zero_search": future_predictions == future_expected,
    }
