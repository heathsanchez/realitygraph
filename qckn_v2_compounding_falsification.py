from __future__ import annotations

import hashlib
import itertools
import json
import os
from dataclasses import dataclass
from pathlib import Path

from realitygraph.attack import AttackEvidence, AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability, compose_capabilities
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.compiled_present import CompiledPresent
from realitygraph.fixtures.boolean_observer_growth import (
    AUTHORITY,
    PAIR_INPUTS,
    VERIFIER,
    build_g1,
)
from realitygraph.ledger import Ledger
from realitygraph.meta_memory import MetaMemory


DECODER_ORACLE = {"0": "EVEN", "1": "ODD"}
DECODER_TABLES = (
    (("0", "EVEN"), ("1", "EVEN")),
    (("0", "ODD"), ("1", "EVEN")),
    (("0", "EVEN"), ("1", "ODD")),
    (("0", "ODD"), ("1", "ODD")),
)
SOURCE_LABEL_ORACLE = {
    "00": "EVEN",
    "01": "ODD",
    "10": "ODD",
    "11": "EVEN",
}
TARGET_INPUTS = ("aa", "ab", "ba", "bb")
TARGET_TO_SOURCE = {"aa": "00", "ab": "01", "ba": "10", "bb": "11"}
TARGET_LABEL_ORACLE = {
    "aa": "EVEN",
    "ab": "ODD",
    "ba": "ODD",
    "bb": "EVEN",
}


class CompoundingObstruction(RuntimeError):
    def __init__(
        self,
        code: str,
        detail: str,
        separating_input: str | None = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.separating_input = separating_input
        suffix = f" at {separating_input}" if separating_input is not None else ""
        super().__init__(f"{code}{suffix}: {detail}")


@dataclass(frozen=True)
class GenerationMeasurement:
    generation: str
    capability_id: str
    acquisition_search_calls: int
    authority_checks: int


@dataclass(frozen=True)
class GenerationBundle:
    measurements: tuple[GenerationMeasurement, ...]
    parity: FiniteCapability
    decoder: FiniteCapability
    dependent: FiniteCapability
    standalone: FiniteCapability
    attacks: tuple[AttackEvidence, ...]


@dataclass(frozen=True)
class RetentionDecision:
    active_before_count: int
    active_after_count: int
    active_ids: tuple[str, ...]
    reserve_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    deleted_from_active_ids: tuple[str, ...]
    deletion_evidence: tuple[str, ...]

    def require_removal(self, capability_id: str) -> None:
        if capability_id in self.reserve_ids:
            raise CompoundingObstruction(
                "RecoveryUnavailable",
                f"declared future recovery requires reserve capability {capability_id}",
            )


@dataclass(frozen=True)
class RetainedState:
    bundle: GenerationBundle
    ledger: Ledger
    decision: RetentionDecision
    present: CompiledPresent
    source_replay_before: tuple[tuple[str, str], ...]
    source_replay_after: tuple[tuple[str, str], ...]
    source_replay_digest: str
    restart_exact: bool


@dataclass(frozen=True)
class ArmMeasurement:
    name: str
    search_calls: int
    authority_checks: int
    verified_semantics: tuple[tuple[str, str], ...]
    authority_snapshot: str
    verifier_id: str
    used_compiled_capability: bool


@dataclass(frozen=True)
class ProbeResult:
    generations: GenerationBundle
    retained: RetainedState
    reserve_control: RetainedState
    arms: tuple[ArmMeasurement, ...]
    gate_results: tuple[tuple[str, bool], ...]

    def arm(self, name: str) -> ArmMeasurement:
        for measurement in self.arms:
            if measurement.name == name:
                return measurement
        raise KeyError(name)

    @property
    def failed_gates(self) -> tuple[str, ...]:
        return tuple(code for code, passed in self.gate_results if not passed)

    @property
    def passed(self) -> bool:
        return not self.failed_gates

    def metrics(self) -> dict[str, object]:
        generations = {
            item.generation: item for item in self.generations.measurements
        }
        arms = {item.name: item for item in self.arms}
        active_before_cost = sum(
            capability.cost
            for capability in (
                self.generations.parity,
                self.generations.decoder,
                self.generations.standalone,
            )
        )
        active_after_cost = self.generations.standalone.cost
        restarted = self.retained.present.restart()
        return {
            "schema": "qckn-v2-compounding-falsification-v1",
            "passed": self.passed,
            "failed_gates": list(self.failed_gates),
            "generation_acquisition_search": {
                name: generations[name].acquisition_search_calls
                for name in ("G1", "G2", "G3")
            },
            "generation_authority_checks": {
                name: generations[name].authority_checks
                for name in ("G1", "G2", "G3")
            },
            "target_search_calls": {
                name: arms[name].search_calls
                for name in (
                    "COLD",
                    "WARM",
                    "RAW_HISTORY",
                    "SHAM",
                    "ANCESTOR_ABLATION",
                )
            },
            "target_authority_checks": {
                name: arms[name].authority_checks
                for name in (
                    "COLD",
                    "WARM",
                    "RAW_HISTORY",
                    "SHAM",
                    "ANCESTOR_ABLATION",
                )
            },
            "active_capabilities": {
                "before": self.retained.decision.active_before_count,
                "after": self.retained.decision.active_after_count,
            },
            "active_declared_cost": {
                "before": active_before_cost,
                "after": active_after_cost,
            },
            "active_ids": list(self.retained.decision.active_ids),
            "deleted_from_active_ids": list(
                self.retained.decision.deleted_from_active_ids
            ),
            "reserve_item_count": len(self.retained.decision.reserve_ids),
            "reserve_negative_control_count": len(
                self.reserve_control.decision.reserve_ids
            ),
            "reserve_negative_control_ids": list(
                self.reserve_control.decision.reserve_ids
            ),
            "provenance_pointer_count": len(
                self.retained.decision.provenance_ids
            ),
            "provenance_ids": list(self.retained.decision.provenance_ids),
            "deletion_evidence": list(
                self.retained.decision.deletion_evidence
            ),
            "compiled_present_bytes": len(
                self.retained.present.text().encode("utf-8")
            ),
            "restart_text_equal": restarted.text() == self.retained.present.text(),
            "restart_digest_equal": restarted.digest == self.retained.present.digest,
            "restart_digest": restarted.digest,
            "protected_replay_digest": self.retained.source_replay_digest,
            "ledger_event_count": len(self.retained.ledger.events),
            "ledger_digest": self.retained.ledger.digest(),
            "authority_snapshot": AUTHORITY,
            "verifier_id": VERIFIER,
            "dependent_capability_id": self.generations.dependent.capability_id,
            "standalone_capability_id": self.generations.standalone.capability_id,
            "standalone_certificate_id": self.generations.standalone.certificate_id,
            "ablation_restores_cold": (
                arms["ANCESTOR_ABLATION"].search_calls
                == arms["COLD"].search_calls
            ),
            "gate_results": {
                code: passed for code, passed in self.gate_results
            },
        }


def _decoder_candidate(index: int, table: tuple[tuple[str, str], ...]) -> FiniteCapability:
    return FiniteCapability(
        capability_id=f"g2-decoder-candidate-{index}-v2",
        input_type="bit",
        output_type="label",
        semantics=table,
        guard_inputs=("0", "1"),
        certificate_id=f"candidate:g2-decoder-{index}-v2",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("g2-complete-decoder-portfolio-v2",),
        cost=1,
    )


def _acquire_decoder() -> tuple[FiniteCapability, int, int, tuple[AttackEvidence, ...]]:
    attacks: list[AttackEvidence] = []
    for search_calls, table in enumerate(DECODER_TABLES, start=1):
        candidate = _decoder_candidate(search_calls, table)
        attack = exhaustive_attack(
            candidate,
            DECODER_ORACLE,
            ("0", "1"),
            budget=2,
        )
        attacks.append(attack)
        if attack.status is AttackStatus.SURVIVE:
            decoder = FiniteCapability(
                capability_id="g2-parity-label-decoder-v2",
                input_type=candidate.input_type,
                output_type=candidate.output_type,
                semantics=candidate.semantics,
                guard_inputs=candidate.guard_inputs,
                certificate_id="cert:g2-decoder-exhaustive-v2",
                dependencies=(),
                authority_snapshot=candidate.authority_snapshot,
                verifier_id=candidate.verifier_id,
                provenance_ids=(
                    "g2-complete-decoder-portfolio-v2",
                    candidate.capability_id,
                ),
                cost=candidate.cost,
            )
            promotion_attack = exhaustive_attack(
                decoder,
                DECODER_ORACLE,
                ("0", "1"),
                budget=2,
            )
            if promotion_attack.status is not AttackStatus.SURVIVE:
                raise CompoundingObstruction(
                    "G2_PROMOTION_AUTHORITY_FAILED",
                    "promoted decoder identity did not survive independent authority",
                )
            attacks.append(promotion_attack)
            return decoder, search_calls, sum(item.checked for item in attacks), tuple(attacks)
    raise CompoundingObstruction(
        "G2_SEARCH_EXHAUSTED",
        "complete decoder portfolio contains no surviving capability",
    )


def acquire_generations() -> GenerationBundle:
    g1 = build_g1()
    parity = g1["capability"]
    g1_attack = g1["attack"]
    g1_search_calls = int(g1["grammar_search_calls"])
    if g1_attack.status is not AttackStatus.SURVIVE:
        raise CompoundingObstruction(
            "G1_AUTHORITY_FAILED",
            "frozen parity acquisition did not survive its complete authority",
        )

    decoder, g2_search_calls, g2_checks, g2_attacks = _acquire_decoder()
    dependent = compose_capabilities(
        "g3-dependent-parity-label-v2",
        parity,
        decoder,
    )
    dependent_attack = exhaustive_attack(
        dependent,
        SOURCE_LABEL_ORACLE,
        PAIR_INPUTS,
        budget=len(PAIR_INPUTS),
    )
    if dependent_attack.status is not AttackStatus.SURVIVE:
        separating = (
            dependent_attack.counterexample[0]
            if dependent_attack.counterexample is not None
            else None
        )
        raise CompoundingObstruction(
            "COMPOSITION_AUTHORITY_FAILED",
            "dependency-bearing composition changed a protected consequence",
            separating,
        )

    standalone = FiniteCapability(
        capability_id="g3-standalone-parity-label-v2",
        input_type=dependent.input_type,
        output_type=dependent.output_type,
        semantics=dependent.semantics,
        guard_inputs=dependent.guard_inputs,
        certificate_id="cert:g3-standalone-exhaustive-v2",
        dependencies=(),
        authority_snapshot=dependent.authority_snapshot,
        verifier_id=dependent.verifier_id,
        provenance_ids=tuple(
            dict.fromkeys(
                (
                    parity.capability_id,
                    decoder.capability_id,
                    dependent.capability_id,
                    parity.certificate_id,
                    decoder.certificate_id,
                    dependent.certificate_id,
                )
            )
        ),
        cost=dependent.cost,
    )
    standalone_attack = exhaustive_attack(
        standalone,
        SOURCE_LABEL_ORACLE,
        PAIR_INPUTS,
        budget=len(PAIR_INPUTS),
    )
    if standalone_attack.status is not AttackStatus.SURVIVE:
        separating = (
            standalone_attack.counterexample[0]
            if standalone_attack.counterexample is not None
            else None
        )
        raise CompoundingObstruction(
            "RECERTIFICATION_FAILED",
            "standalone materialization did not survive independent authority",
            separating,
        )

    measurements = (
        GenerationMeasurement(
            "G1",
            parity.capability_id,
            g1_search_calls,
            g1_attack.checked,
        ),
        GenerationMeasurement(
            "G2",
            decoder.capability_id,
            g2_search_calls,
            g2_checks,
        ),
        GenerationMeasurement(
            "G3",
            standalone.capability_id,
            0,
            dependent_attack.checked + standalone_attack.checked,
        ),
    )
    return GenerationBundle(
        measurements,
        parity,
        decoder,
        dependent,
        standalone,
        (g1_attack, *g2_attacks, dependent_attack, standalone_attack),
    )


def _replay(capability: FiniteCapability) -> tuple[tuple[str, str], ...]:
    return tuple((value, capability.execute(value)) for value in PAIR_INPUTS)


def _replay_digest(rows: tuple[tuple[str, str], ...]) -> str:
    raw = json.dumps(rows, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def build_retained_state(
    bundle: GenerationBundle,
    require_decoder_recovery: bool = False,
) -> RetainedState:
    ledger = Ledger()
    parity_event = ledger.append_promote_capability(
        bundle.parity,
        "bounded-finite-authority-v1",
        parents=(),
    )
    decoder_event = ledger.append_promote_capability(
        bundle.decoder,
        "bounded-finite-authority-v1",
        parents=(),
    )
    ledger.append_promote_capability(
        bundle.standalone,
        "bounded-finite-authority-v1",
        parents=(parity_event.id, decoder_event.id),
    )

    pre_contraction = CapabilityGraph(
        (bundle.parity, bundle.decoder, bundle.standalone)
    )
    post_contraction = CapabilityGraph((bundle.standalone,))
    before = _replay(bundle.dependent)
    present = CompiledPresent.compile(
        post_contraction,
        MetaMemory.empty(),
    )
    restarted = present.restart()
    standalone = restarted.capability_graph.capability_map[
        bundle.standalone.capability_id
    ]
    after = _replay(standalone)
    if before != after:
        mismatch = next(
            source
            for (source, expected), (_, actual) in zip(before, after)
            if expected != actual
        )
        raise CompoundingObstruction(
            "REMINIMISATION_SEPARATION",
            "contracted compiled present changed a protected consequence",
            mismatch,
        )

    reserve_ids = (
        (bundle.decoder.capability_id,)
        if require_decoder_recovery
        else ()
    )
    provenance_ids = tuple(
        dict.fromkeys(
            (
                bundle.parity.capability_id,
                bundle.decoder.capability_id,
                bundle.dependent.capability_id,
                bundle.standalone.capability_id,
                bundle.parity.certificate_id,
                bundle.decoder.certificate_id,
                bundle.dependent.certificate_id,
                bundle.standalone.certificate_id,
            )
        )
    )
    digest = _replay_digest(after)
    active_before_ids = pre_contraction.active_ids()
    active_after_ids = restarted.capability_graph.active_ids()
    decision = RetentionDecision(
        active_before_count=len(active_before_ids),
        active_after_count=len(active_after_ids),
        active_ids=active_after_ids,
        reserve_ids=reserve_ids,
        provenance_ids=provenance_ids,
        deleted_from_active_ids=tuple(
            capability_id
            for capability_id in active_before_ids
            if capability_id not in set(active_after_ids)
        ),
        deletion_evidence=(
            f"protected-replay:{digest}",
            f"standalone-certificate:{bundle.standalone.certificate_id}",
            "source-replay-exact",
        ),
    )
    return RetainedState(
        bundle=bundle,
        ledger=ledger,
        decision=decision,
        present=restarted,
        source_replay_before=before,
        source_replay_after=after,
        source_replay_digest=digest,
        restart_exact=(
            restarted.text() == present.text()
            and restarted.digest == present.digest
        ),
    )


def _target_candidate(
    capability_id: str,
    labels: tuple[str, ...],
    *,
    certificate_id: str,
    provenance_ids: tuple[str, ...],
) -> FiniteCapability:
    return FiniteCapability(
        capability_id=capability_id,
        input_type="pair-prime",
        output_type="label",
        semantics=tuple(zip(TARGET_INPUTS, labels)),
        guard_inputs=TARGET_INPUTS,
        certificate_id=certificate_id,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=provenance_ids,
        cost=1,
    )


def _cold_target(name: str, prior_authority_checks: int = 0) -> ArmMeasurement:
    authority_checks = prior_authority_checks
    for search_calls, labels in enumerate(
        itertools.product(("EVEN", "ODD"), repeat=len(TARGET_INPUTS)),
        start=1,
    ):
        candidate = _target_candidate(
            f"{name.lower()}-target-candidate-{search_calls}-v2",
            labels,
            certificate_id=f"candidate:{name.lower()}-{search_calls}-v2",
            provenance_ids=("complete-target-map-enumeration-v2",),
        )
        attack = exhaustive_attack(
            candidate,
            TARGET_LABEL_ORACLE,
            TARGET_INPUTS,
            budget=len(TARGET_INPUTS),
        )
        authority_checks += attack.checked
        if attack.status is AttackStatus.SURVIVE:
            return ArmMeasurement(
                name=name,
                search_calls=search_calls,
                authority_checks=authority_checks,
                verified_semantics=candidate.semantics,
                authority_snapshot=candidate.authority_snapshot,
                verifier_id=candidate.verifier_id,
                used_compiled_capability=False,
            )
    raise CompoundingObstruction(
        "TARGET_SEARCH_EXHAUSTED",
        "complete target candidate space contains no surviving capability",
    )


def _transport_to_target(source: FiniteCapability) -> FiniteCapability:
    labels = tuple(source.execute(TARGET_TO_SOURCE[value]) for value in TARGET_INPUTS)
    return _target_candidate(
        f"transport:{source.capability_id}",
        labels,
        certificate_id=f"transport:{source.certificate_id}",
        provenance_ids=(source.capability_id, source.certificate_id),
    )


def run_target_arm(
    name: str,
    *,
    present: CompiledPresent | None = None,
    raw_history: str = "",
) -> ArmMeasurement:
    allowed = {"COLD", "WARM", "RAW_HISTORY", "SHAM", "ANCESTOR_ABLATION"}
    if name not in allowed:
        raise ValueError(f"unknown target arm: {name}")
    if name == "RAW_HISTORY" and not raw_history:
        raise ValueError("RAW_HISTORY requires causal evidence")

    prior_authority_checks = 0
    if present is not None:
        restarted = present.restart()
        active = restarted.capability_graph
        for capability_id in active.active_ids():
            capability = active.capability_map[capability_id]
            if capability.input_type != "pair" or capability.output_type != "label":
                continue
            transported = _transport_to_target(capability)
            attack = exhaustive_attack(
                transported,
                TARGET_LABEL_ORACLE,
                TARGET_INPUTS,
                budget=len(TARGET_INPUTS),
            )
            prior_authority_checks += attack.checked
            trusted_boundary = (
                capability.capability_id == "g3-standalone-parity-label-v2"
                and capability.certificate_id == "cert:g3-standalone-exhaustive-v2"
                and capability.authority_snapshot == AUTHORITY
                and capability.verifier_id == VERIFIER
            )
            if attack.status is AttackStatus.SURVIVE and trusted_boundary:
                return ArmMeasurement(
                    name=name,
                    search_calls=0,
                    authority_checks=prior_authority_checks,
                    verified_semantics=transported.semantics,
                    authority_snapshot=transported.authority_snapshot,
                    verifier_id=transported.verifier_id,
                    used_compiled_capability=True,
                )

    return _cold_target(name, prior_authority_checks)


def _sham_present(cost: int) -> CompiledPresent:
    sham = FiniteCapability(
        capability_id="sham-parity-label-v2",
        input_type="pair",
        output_type="label",
        semantics=tuple((value, "EVEN") for value in PAIR_INPUTS),
        guard_inputs=PAIR_INPUTS,
        certificate_id="cert:sham-type-compatible-v2",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("matched-size-sham-control-v2",),
        cost=cost,
    )
    return CompiledPresent.compile(CapabilityGraph((sham,)), MetaMemory.empty()).restart()


def _reserve_removal_is_refused(state: RetainedState) -> bool:
    try:
        state.decision.require_removal(state.bundle.decoder.capability_id)
    except CompoundingObstruction as obstruction:
        return obstruction.code == "RecoveryUnavailable"
    return False


def run_probe() -> ProbeResult:
    generations = acquire_generations()
    retained = build_retained_state(generations)
    reserve_control = build_retained_state(
        generations,
        require_decoder_recovery=True,
    )
    empty_present = CompiledPresent.compile(CapabilityGraph(()), MetaMemory.empty()).restart()
    arms = (
        run_target_arm("COLD"),
        run_target_arm("WARM", present=retained.present.restart()),
        run_target_arm("RAW_HISTORY", raw_history=retained.ledger.jsonl()),
        run_target_arm(
            "SHAM",
            present=_sham_present(generations.standalone.cost),
        ),
        run_target_arm("ANCESTOR_ABLATION", present=empty_present),
    )
    by_name = {arm.name: arm for arm in arms}
    cold = by_name["COLD"]
    warm = by_name["WARM"]
    raw = by_name["RAW_HISTORY"]
    sham = by_name["SHAM"]
    ablation = by_name["ANCESTOR_ABLATION"]
    costs = tuple(item.acquisition_search_calls for item in generations.measurements)
    decoder_authorized = any(
        attack.capability_id == generations.decoder.capability_id
        and attack.status is AttackStatus.SURVIVE
        for attack in generations.attacks
    )
    authority_gate = (
        generations.attacks[0].status is AttackStatus.SURVIVE
        and decoder_authorized
        and generations.attacks[-2].status is AttackStatus.SURVIVE
        and generations.attacks[-1].status is AttackStatus.SURVIVE
    )
    gate_results = (
        ("G1_SEARCH_10", costs[0] == 10),
        ("G2_SEARCH_3", costs[1] == 3),
        ("G3_SEARCH_0", costs[2] == 0),
        ("DECLARED_AUTHORITIES_SURVIVE", authority_gate),
        (
            "ACTIVE_3_TO_1",
            retained.decision.active_before_count == 3
            and retained.decision.active_after_count == 1,
        ),
        (
            "PROTECTED_REPLAY_UNCHANGED",
            retained.source_replay_before == retained.source_replay_after,
        ),
        (
            "RESTART_EXACT_AND_HISTORY_FREE",
            retained.restart_exact
            and len(retained.present.memory.capabilities) == 1,
        ),
        ("WARM_BEATS_COLD", warm.search_calls < cold.search_calls),
        (
            "WARM_COLD_ENDPOINT_EQUAL",
            warm.verified_semantics == cold.verified_semantics
            and warm.authority_snapshot == cold.authority_snapshot
            and warm.verifier_id == cold.verifier_id,
        ),
        (
            "RAW_HISTORY_AND_SHAM_NO_SHORTCUT",
            raw.search_calls == cold.search_calls
            and sham.search_calls == cold.search_calls
            and not raw.used_compiled_capability
            and not sham.used_compiled_capability,
        ),
        ("ABLATION_RESTORES_COLD", ablation.search_calls == cold.search_calls),
        ("RESERVE_PREVENTS_DELETION", _reserve_removal_is_refused(reserve_control)),
    )
    return ProbeResult(generations, retained, reserve_control, arms, gate_results)


def main() -> int:
    result = run_probe()
    serialized = json.dumps(
        result.metrics(),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output_path = os.environ.get("QCKN_V2_RESULT_PATH")
    if output_path:
        Path(output_path).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
