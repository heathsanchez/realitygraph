from __future__ import annotations

import itertools
import json
import os
from dataclasses import dataclass
from pathlib import Path

from realitygraph.attack import AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    FlashObstruction,
    LiveObligation,
)


AUTHORITY = "bounded-finite-authority-v1"
VERIFIER = "truth-table-exhaustive-v1"
CONTRACT = FlashContract(AUTHORITY, VERIFIER)

PAIR_INPUTS = ("00", "01", "10", "11")
BIT_INPUTS = ("0", "1")
PARITY = (("00", "0"), ("01", "1"), ("10", "1"), ("11", "0"))
DECODER = (("0", "EVEN"), ("1", "ODD"))
PAIR_LABEL = (
    ("00", "EVEN"),
    ("01", "ODD"),
    ("10", "ODD"),
    ("11", "EVEN"),
)


@dataclass(frozen=True)
class WorkerSpec:
    obligation_id: str
    source_tables: tuple[tuple[tuple[str, str], ...], ...]

    @property
    def cold_search_cost(self) -> int:
        return next(
            index
            for index, table in enumerate(self.source_tables, start=1)
            if table in (PARITY, DECODER, PAIR_LABEL)
        )


@dataclass(frozen=True)
class SimulationResult:
    search_calls: int
    authority_checks: int
    rounds: int
    engine: FlashClosure


def all_tables(inputs: tuple[str, ...], outputs: tuple[str, ...]):
    return tuple(
        tuple(zip(inputs, values))
        for values in itertools.product(outputs, repeat=len(inputs))
    )


def positioned_portfolio(
    universe: tuple[tuple[tuple[str, str], ...], ...],
    correct: tuple[tuple[str, str], ...],
    position: int,
) -> tuple[tuple[tuple[str, str], ...], ...]:
    wrong = [table for table in universe if table != correct]
    if not 1 <= position <= len(universe):
        raise ValueError("invalid frozen search position")
    rows = wrong[: position - 1] + [correct] + wrong[position - 1 :]
    return tuple(rows)


def target_surface(prefix: str) -> tuple[str, ...]:
    return tuple(f"{prefix}{index}" for index in range(4))


def relabel_oracle(
    target_inputs: tuple[str, ...],
    source_oracle: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (target, source_oracle[index][1])
        for index, target in enumerate(target_inputs)
    )


def identity_transport(inputs: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((value, value) for value in inputs)


def surface_transport(
    target_inputs: tuple[str, ...],
    source_inputs: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(zip(target_inputs, source_inputs))


def fingerprints(
    tables: tuple[tuple[tuple[str, str], ...], ...],
    *,
    input_type: str,
    output_type: str,
) -> tuple[str, ...]:
    return tuple(
        FlashClosure.candidate_fingerprint(
            table,
            input_type=input_type,
            output_type=output_type,
            contract=CONTRACT,
        )
        for table in tables
    )


def build_positive_fixture() -> tuple[FlashClosure, dict[str, WorkerSpec]]:
    bit_maps = all_tables(PAIR_INPUTS, ("0", "1"))
    decoder_maps = all_tables(BIT_INPUTS, ("EVEN", "ODD"))
    label_maps = all_tables(PAIR_INPUTS, ("EVEN", "ODD"))

    parity_source = positioned_portfolio(bit_maps, PARITY, 7)
    decoder_source = positioned_portfolio(decoder_maps, DECODER, 3)
    parity_target = positioned_portfolio(bit_maps, PARITY, 13)
    decoder_target = positioned_portfolio(decoder_maps, DECODER, 4)
    label_positions = (11, 12, 13, 14, 15, 16)

    obligations: list[LiveObligation] = [
        LiveObligation(
            "00-source-decoder",
            "bit",
            "bit",
            "label",
            DECODER,
            identity_transport(BIT_INPUTS),
            CONTRACT,
            fingerprints(decoder_source, input_type="bit", output_type="label"),
            domain="source",
        ),
        LiveObligation(
            "01-source-parity",
            "pair",
            "pair",
            "bit",
            PARITY,
            identity_transport(PAIR_INPUTS),
            CONTRACT,
            fingerprints(parity_source, input_type="pair", output_type="bit"),
            domain="source",
        ),
    ]
    workers = {
        "00-source-decoder": WorkerSpec("00-source-decoder", decoder_source),
        "01-source-parity": WorkerSpec("01-source-parity", parity_source),
    }

    decoder_surface = ("d0", "d1")
    obligations.append(
        LiveObligation(
            "10-target-decoder",
            "decoder-surface",
            "bit",
            "label",
            tuple(zip(decoder_surface, ("EVEN", "ODD"))),
            surface_transport(decoder_surface, BIT_INPUTS),
            CONTRACT,
            fingerprints(decoder_target, input_type="bit", output_type="label"),
            domain="target",
        )
    )
    workers["10-target-decoder"] = WorkerSpec(
        "10-target-decoder",
        decoder_target,
    )

    parity_surface = target_surface("p")
    obligations.append(
        LiveObligation(
            "11-target-parity",
            "parity-surface",
            "pair",
            "bit",
            relabel_oracle(parity_surface, PARITY),
            surface_transport(parity_surface, PAIR_INPUTS),
            CONTRACT,
            fingerprints(parity_target, input_type="pair", output_type="bit"),
            domain="target",
        )
    )
    workers["11-target-parity"] = WorkerSpec(
        "11-target-parity",
        parity_target,
    )

    for index, position in enumerate(label_positions, start=1):
        obligation_id = f"2{index}-target-label"
        target_inputs = target_surface(f"g{index}-")
        portfolio = positioned_portfolio(label_maps, PAIR_LABEL, position)
        obligations.append(
            LiveObligation(
                obligation_id,
                f"label-surface-{index}",
                "pair",
                "label",
                relabel_oracle(target_inputs, PAIR_LABEL),
                surface_transport(target_inputs, PAIR_INPUTS),
                CONTRACT,
                fingerprints(portfolio, input_type="pair", output_type="label"),
                domain=f"game-{index}",
            )
        )
        workers[obligation_id] = WorkerSpec(obligation_id, portfolio)

    rule = FlashCompositionRule(
        "parity-plus-decoder",
        "flash-parity-v1",
        "flash-decoder-v1",
        "flash-pair-label-v1",
        PAIR_LABEL,
        "cert:flash-pair-label-exhaustive-v1",
    )
    return FlashClosure(obligations, composition_rules=(rule,)), workers


def canonical_oracle(obligation: LiveObligation) -> tuple[tuple[str, str], ...]:
    rows = []
    inverse = {
        source: target
        for target, source in obligation.transport_to_source
    }
    for source in sorted(inverse):
        target = inverse[source]
        rows.append((source, obligation.oracle_map[target]))
    return tuple(rows)


def candidate_capability(
    obligation: LiveObligation,
    table: tuple[tuple[str, str], ...],
    candidate_index: int,
) -> FiniteCapability:
    return FiniteCapability(
        capability_id=(
            f"candidate:{obligation.obligation_id}:{candidate_index}"
        ),
        input_type=obligation.source_input_type,
        output_type=obligation.output_type,
        semantics=table,
        guard_inputs=tuple(key for key, _ in table),
        certificate_id=(
            f"candidate-cert:{obligation.obligation_id}:{candidate_index}"
        ),
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(obligation.obligation_id,),
        cost=1,
    )


def promoted_capability(
    obligation_id: str,
    table: tuple[tuple[str, str], ...],
) -> FiniteCapability:
    if obligation_id == "00-source-decoder":
        capability_id = "flash-decoder-v1"
        certificate_id = "cert:flash-decoder-exhaustive-v1"
        input_type, output_type = "bit", "label"
    elif obligation_id == "01-source-parity":
        capability_id = "flash-parity-v1"
        certificate_id = "cert:flash-parity-exhaustive-v1"
        input_type, output_type = "pair", "bit"
    else:
        raise ValueError("positive fixture only promotes canonical source workers")
    return FiniteCapability(
        capability_id=capability_id,
        input_type=input_type,
        output_type=output_type,
        semantics=table,
        guard_inputs=tuple(key for key, _ in table),
        certificate_id=certificate_id,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(obligation_id,),
        cost=1,
    )


def run_positive_flash() -> SimulationResult:
    engine, workers = build_positive_fixture()
    search_calls = 0
    authority_checks = 0
    rounds = 0
    worker_order = tuple(sorted(workers))

    while engine.open_obligation_ids():
        rounds += 1
        if rounds > 32:
            raise RuntimeError("positive flash fixture did not close")
        for obligation_id in worker_order:
            obligation = engine.obligations[obligation_id]
            if obligation.status != "OPEN":
                continue
            spec = workers[obligation_id]
            attempted = set(obligation.searched_fingerprints)
            candidate_index = next(
                (
                    index
                    for index, fingerprint in enumerate(
                        obligation.candidate_fingerprints
                    )
                    if fingerprint not in attempted
                    and fingerprint not in obligation.pruned_fingerprints
                ),
                None,
            )
            if candidate_index is None:
                raise RuntimeError(
                    f"frozen search exhausted without result: {obligation_id}"
                )
            fingerprint = obligation.candidate_fingerprints[candidate_index]
            table = spec.source_tables[candidate_index]
            engine.note_search_attempt(obligation_id, fingerprint)
            search_calls += 1

            candidate = candidate_capability(
                obligation,
                table,
                candidate_index + 1,
            )
            oracle = canonical_oracle(obligation)
            attack = exhaustive_attack(
                candidate,
                dict(oracle),
                tuple(key for key, _ in oracle),
                budget=len(oracle),
            )
            authority_checks += attack.checked
            if attack.status is not AttackStatus.SURVIVE:
                continue

            if obligation_id not in (
                "00-source-decoder",
                "01-source-parity",
            ):
                raise RuntimeError(
                    "target worker solved before intended flash event"
                )
            promoted = promoted_capability(obligation_id, table)
            engine.admit_capability(
                promoted,
                oracle=oracle,
                origin=f"worker:{obligation_id}",
            )

    return SimulationResult(
        search_calls=search_calls,
        authority_checks=authority_checks,
        rounds=rounds,
        engine=engine,
    )


def independent_positive_cost() -> tuple[int, int]:
    _engine, workers = build_positive_fixture()
    return (
        sum(worker.cold_search_cost for worker in workers.values()),
        max(worker.cold_search_cost for worker in workers.values()),
    )


def build_negative_fixture() -> tuple[
    FlashClosure,
    dict[str, WorkerSpec],
    tuple[tuple[tuple[str, str], ...], ...],
]:
    universe = all_tables(PAIR_INPUTS, ("EVEN", "ODD"))
    wrong = tuple(table for table in universe if table != PAIR_LABEL)[:3]
    portfolio = (*wrong, PAIR_LABEL)
    obligations = []
    workers = {}
    for index in range(4):
        obligation_id = f"negative-{index + 1}"
        target_inputs = target_surface(f"n{index + 1}-")
        obligations.append(
            LiveObligation(
                obligation_id,
                f"negative-surface-{index + 1}",
                "pair",
                "label",
                relabel_oracle(target_inputs, PAIR_LABEL),
                surface_transport(target_inputs, PAIR_INPUTS),
                CONTRACT,
                fingerprints(
                    portfolio,
                    input_type="pair",
                    output_type="label",
                ),
                domain="negative-control",
            )
        )
        workers[obligation_id] = WorkerSpec(
            obligation_id,
            tuple(portfolio),
        )
    return FlashClosure(obligations), workers, tuple(portfolio)


def first_separation(
    candidate: tuple[tuple[str, str], ...],
    oracle: tuple[tuple[str, str], ...],
) -> tuple[str, str, str]:
    expected = dict(oracle)
    for key, actual in candidate:
        if expected[key] != actual:
            return key, expected[key], actual
    raise ValueError("candidate does not separate from oracle")


def run_negative_flash() -> SimulationResult:
    engine, workers, _portfolio = build_negative_fixture()
    search_calls = 0
    authority_checks = 0
    rounds = 0
    worker_order = tuple(sorted(workers))

    while engine.open_obligation_ids():
        rounds += 1
        if rounds > 8:
            raise RuntimeError("negative flash fixture did not close")
        for obligation_id in worker_order:
            obligation = engine.obligations[obligation_id]
            if obligation.status != "OPEN":
                continue
            spec = workers[obligation_id]
            attempted = set(obligation.searched_fingerprints)
            candidate_index = next(
                (
                    index
                    for index, fingerprint in enumerate(
                        obligation.candidate_fingerprints
                    )
                    if fingerprint not in attempted
                    and fingerprint not in obligation.pruned_fingerprints
                ),
                None,
            )
            if candidate_index is None:
                raise RuntimeError("negative fixture search exhausted")
            fingerprint = obligation.candidate_fingerprints[candidate_index]
            table = spec.source_tables[candidate_index]
            engine.note_search_attempt(obligation_id, fingerprint)
            search_calls += 1

            candidate = candidate_capability(
                obligation,
                table,
                candidate_index + 1,
            )
            oracle = canonical_oracle(obligation)
            attack = exhaustive_attack(
                candidate,
                dict(oracle),
                tuple(key for key, _ in oracle),
                budget=len(oracle),
            )
            authority_checks += attack.checked
            if attack.status is AttackStatus.SURVIVE:
                promoted = FiniteCapability(
                    capability_id="negative-pair-label-v1",
                    input_type="pair",
                    output_type="label",
                    semantics=table,
                    guard_inputs=tuple(key for key, _ in table),
                    certificate_id="cert:negative-pair-label-exhaustive-v1",
                    dependencies=(),
                    authority_snapshot=AUTHORITY,
                    verifier_id=VERIFIER,
                    provenance_ids=(obligation_id,),
                    cost=1,
                )
                engine.admit_capability(
                    promoted,
                    oracle=PAIR_LABEL,
                    origin=f"worker:{obligation_id}",
                )
                continue

            source, expected, actual = first_separation(table, PAIR_LABEL)
            obstruction = FlashObstruction(
                obstruction_id=(
                    f"obs:{fingerprint[:20]}:{source}"
                ),
                input_type="pair",
                output_type="label",
                contract=CONTRACT,
                candidate_fingerprint=fingerprint,
                separating_input=source,
                expected_output=expected,
                actual_output=actual,
                provenance=f"worker:{obligation_id}",
            )
            engine.admit_obstruction(obstruction)

    return SimulationResult(
        search_calls=search_calls,
        authority_checks=authority_checks,
        rounds=rounds,
        engine=engine,
    )


def sham_rejection_control() -> bool:
    engine, _workers = build_positive_fixture()
    wrong = FiniteCapability(
        capability_id="sham-parity-v1",
        input_type="pair",
        output_type="bit",
        semantics=tuple((key, "0") for key in PAIR_INPUTS),
        guard_inputs=PAIR_INPUTS,
        certificate_id="sham:type-compatible",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("sham-control",),
        cost=1,
    )
    before = engine.metrics()
    try:
        engine.admit_capability(wrong, oracle=PARITY, origin="sham")
    except ValueError:
        after = engine.metrics()
        return (
            before["open_obligations"] == after["open_obligations"]
            and before["active_capability_ids"] == after["active_capability_ids"]
            and before["ledger_event_count"] == after["ledger_event_count"]
        )
    return False


def revocation_control(result: SimulationResult) -> dict[str, object]:
    engine = result.engine
    before = set(engine.discharged_obligation_ids())
    delta = engine.revoke_capability(
        "flash-parity-v1",
        reason="matched causal revocation control",
    )
    after = set(engine.discharged_obligation_ids())
    reopened = set(delta.reopened)
    expected_reopened = {
        "01-source-parity",
        "11-target-parity",
        *{f"2{index}-target-label" for index in range(1, 7)},
    }
    return {
        "before_discharged": sorted(before),
        "after_discharged": sorted(after),
        "reopened": sorted(reopened),
        "expected_reopened": sorted(expected_reopened),
        "exact_reopen": reopened == expected_reopened,
        "decoder_targets_preserved": {
            "00-source-decoder",
            "10-target-decoder",
        }.issubset(after),
        "active_after_revocation": list(engine.active_capability_ids()),
        "flash_radius": delta.flash_radius,
    }


def order_invariance_control() -> bool:
    left, _ = build_positive_fixture()
    right, _ = build_positive_fixture()

    parity = FiniteCapability(
        capability_id="flash-parity-v1",
        input_type="pair",
        output_type="bit",
        semantics=PARITY,
        guard_inputs=PAIR_INPUTS,
        certificate_id="cert:flash-parity-exhaustive-v1",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("order-control",),
        cost=1,
    )
    decoder = FiniteCapability(
        capability_id="flash-decoder-v1",
        input_type="bit",
        output_type="label",
        semantics=DECODER,
        guard_inputs=BIT_INPUTS,
        certificate_id="cert:flash-decoder-exhaustive-v1",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("order-control",),
        cost=1,
    )

    left.admit_capability(parity, oracle=PARITY, origin="order-control")
    left.admit_capability(decoder, oracle=DECODER, origin="order-control")

    right.admit_capability(decoder, oracle=DECODER, origin="order-control")
    right.admit_capability(parity, oracle=PARITY, origin="order-control")

    return (
        left.discharged_obligation_ids() == right.discharged_obligation_ids()
        and left.active_capability_ids() == right.active_capability_ids()
        and left.compiled_present().digest == right.compiled_present().digest
    )


def run_probe() -> dict[str, object]:
    independent_search, independent_rounds = independent_positive_cost()
    positive = run_positive_flash()
    positive_metrics = positive.engine.metrics()

    negative = run_negative_flash()
    negative_independent_search = 4 * 4
    negative_metrics = negative.engine.metrics()

    sham_ok = sham_rejection_control()
    order_ok = order_invariance_control()

    # Capture positive fixed-point evidence before the deliberate revocation.
    positive_fixed_digest = positive.engine.compiled_present().digest
    positive_active = positive.engine.active_capability_ids()
    positive_discharged = positive.engine.discharged_obligation_ids()
    positive_flash_events = list(positive.engine.flash_events)
    positive_cancelled = positive.engine.total_cancelled_future_search

    revocation = revocation_control(positive)

    gates = {
        "ALL_POSITIVE_OBLIGATIONS_CLOSE": len(positive_discharged) == 10,
        "FLASH_SEARCH_BEATS_INDEPENDENT": (
            positive.search_calls < independent_search
        ),
        "FLASH_WALL_ROUNDS_BEAT_INDEPENDENT": (
            positive.rounds < independent_rounds
        ),
        "COMPOSITION_FLASHES_TO_SIX_GAMES": any(
            event["event_id"] == "flash-parity-v1"
            and len(event["discharged"]) >= 8
            and "flash-pair-label-v1" in event["generated_capabilities"]
            for event in positive_flash_events
        ),
        "CANCELLED_FUTURE_SEARCH_POSITIVE": positive_cancelled > 0,
        "FAILURE_CAPITAL_BEATS_INDEPENDENT": (
            negative.search_calls < negative_independent_search
        ),
        "NEGATIVE_FIXTURE_CLOSES_IN_ONE_ROUND": negative.rounds == 1,
        "SHAM_CANNOT_MUTATE_GRAPH": sham_ok,
        "ORDER_INVARIANT_COMPILED_PRESENT": order_ok,
        "REVOCATION_REOPENS_EXACT_CAUSAL_DEPENDENTS": bool(
            revocation["exact_reopen"]
        ),
        "REVOCATION_PRESERVES_UNRELATED": bool(
            revocation["decoder_targets_preserved"]
        ),
    }
    passed = all(gates.values())

    return {
        "schema": "qckn-flash-closure-v1",
        "passed": passed,
        "gates": gates,
        "positive": {
            "independent_search_calls": independent_search,
            "flash_search_calls": positive.search_calls,
            "search_calls_avoided": independent_search - positive.search_calls,
            "independent_wall_rounds": independent_rounds,
            "flash_wall_rounds": positive.rounds,
            "wall_rounds_avoided": independent_rounds - positive.rounds,
            "search_reduction_fraction": (
                (independent_search - positive.search_calls)
                / independent_search
            ),
            "authority_checks": positive.authority_checks,
            "cancelled_future_search": positive_cancelled,
            "fixed_point_discharged": list(positive_discharged),
            "fixed_point_active_capabilities": list(positive_active),
            "fixed_point_compiled_present_digest": positive_fixed_digest,
            "flash_events": positive_flash_events,
            "metrics_before_revocation": positive_metrics,
        },
        "negative_capital": {
            "independent_search_calls": negative_independent_search,
            "flash_search_calls": negative.search_calls,
            "search_calls_avoided": (
                negative_independent_search - negative.search_calls
            ),
            "flash_wall_rounds": negative.rounds,
            "authority_checks": negative.authority_checks,
            "obstruction_count": len(negative.engine.obstructions),
            "pruned_candidate_occurrences": (
                negative.engine.total_pruned_occurrences
            ),
            "flash_events": list(negative.engine.flash_events),
            "metrics": negative_metrics,
        },
        "revocation": revocation,
        "controls": {
            "sham_rejected_without_mutation": sham_ok,
            "admission_order_compiled_state_invariant": order_ok,
        },
    }


def main() -> int:
    result = run_probe()
    serialized = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output = os.environ.get("QCKN_FLASH_RESULT_PATH")
    if output:
        Path(output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
