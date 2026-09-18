from __future__ import annotations

import hashlib
import itertools
import json
import os
from dataclasses import dataclass
from pathlib import Path

from qckn_v2_compounding_falsification import (
    AUTHORITY,
    PAIR_INPUTS,
    VERIFIER,
    acquire_generations,
    build_retained_state,
)
from realitygraph.attack import AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.compiled_present import CompiledPresent
from realitygraph.meta_memory import MetaMemory


LABELS = ("EVEN", "ODD")
SOURCE_SEARCH_CALLS = 13
SOURCE_AUTHORITY_CHECKS = 11


@dataclass(frozen=True)
class LiveGame:
    game_id: str
    surface: tuple[str, ...]
    source_map: tuple[tuple[str, str], ...]
    oracle_rows: tuple[tuple[str, str], ...]
    expected_cold_search: int
    semantic_class: str

    @property
    def oracle(self) -> dict[str, str]:
        return dict(self.oracle_rows)

    @property
    def source_lookup(self) -> dict[str, str]:
        return dict(self.source_map)

    @property
    def expected_signature(self) -> tuple[str, ...]:
        oracle = self.oracle
        return tuple(oracle[value] for value in self.surface)


@dataclass(frozen=True)
class GameOutcome:
    game_id: str
    search_calls: int
    authority_checks: int
    verified_signature: tuple[str, ...]
    route: str


@dataclass(frozen=True)
class ClosureMeasurement:
    outcomes: tuple[GameOutcome, ...]
    unresolved_ids: tuple[str, ...]
    rejected_edges: tuple[tuple[str, str], ...]
    authority_checks: int
    change_counts: tuple[int, ...]

    @property
    def resolved_ids(self) -> tuple[str, ...]:
        return tuple(item.game_id for item in self.outcomes)


@dataclass(frozen=True)
class ArmResult:
    name: str
    source_search_calls: int
    target_search_calls: int
    global_search_calls: int
    authority_checks: int
    outcomes: tuple[GameOutcome, ...]
    closure_change_counts: tuple[int, ...]
    flash_resolved_before_search: tuple[str, ...]
    rejected_edges: tuple[tuple[str, str], ...]

    def outcome(self, game_id: str) -> GameOutcome:
        for outcome in self.outcomes:
            if outcome.game_id == game_id:
                return outcome
        raise KeyError(game_id)

    @property
    def endpoint_digest(self) -> str:
        payload = [
            {
                "game_id": outcome.game_id,
                "signature": list(outcome.verified_signature),
            }
            for outcome in sorted(self.outcomes, key=lambda item: item.game_id)
        ]
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class FlashProbeResult:
    games: tuple[LiveGame, ...]
    arms: tuple[ArmResult, ...]
    gate_results: tuple[tuple[str, bool], ...]
    active_capability_ids: tuple[str, ...]
    compiled_present_digest: str
    restart_exact: bool
    serial_generation_search: tuple[int, int, int]
    serial_generation_authority: tuple[int, int, int]

    def arm(self, name: str) -> ArmResult:
        for arm in self.arms:
            if arm.name == name:
                return arm
        raise KeyError(name)

    @property
    def failed_gates(self) -> tuple[str, ...]:
        return tuple(name for name, passed in self.gate_results if not passed)

    @property
    def passed(self) -> bool:
        return not self.failed_gates

    def metrics(self) -> dict[str, object]:
        isolated = self.arm("ISOLATED")
        flash = self.arm("FLASH")
        raw = self.arm("RAW_SHARED")
        sham = self.arm("SHAM_FLASH")
        ablation = self.arm("ABLATION")
        return {
            "schema": "qckn-v2-flash-closure-v1",
            "passed": self.passed,
            "failed_gates": list(self.failed_gates),
            "live_obligations": 2 + len(self.games),
            "source_obligations": 2,
            "target_obligations": len(self.games),
            "compatible_target_obligations": sum(
                game.semantic_class == "PARITY_LABEL" for game in self.games
            ),
            "semantic_control_obligations": sum(
                game.semantic_class != "PARITY_LABEL" for game in self.games
            ),
            "serial_generation_acquisition_search": {
                "G1": self.serial_generation_search[0],
                "G2": self.serial_generation_search[1],
                "G3": self.serial_generation_search[2],
            },
            "serial_generation_authority_checks": {
                "G1": self.serial_generation_authority[0],
                "G2": self.serial_generation_authority[1],
                "G3": self.serial_generation_authority[2],
            },
            "global_search_calls": {
                arm.name: arm.global_search_calls for arm in self.arms
            },
            "target_search_calls": {
                arm.name: arm.target_search_calls for arm in self.arms
            },
            "authority_checks": {
                arm.name: arm.authority_checks for arm in self.arms
            },
            "flash_search_avoided": (
                isolated.global_search_calls - flash.global_search_calls
            ),
            "flash_resolved_before_search_count": len(
                flash.flash_resolved_before_search
            ),
            "flash_resolved_before_search_ids": list(
                flash.flash_resolved_before_search
            ),
            "flash_closure_change_counts": list(flash.closure_change_counts),
            "flash_fixed_point_rounds": len(flash.closure_change_counts),
            "flash_rejected_edge_count": len(flash.rejected_edges),
            "flash_rejected_edges": [list(edge) for edge in flash.rejected_edges],
            "active_capability_count": len(self.active_capability_ids),
            "active_capability_ids": list(self.active_capability_ids),
            "compiled_present_digest": self.compiled_present_digest,
            "restart_exact": self.restart_exact,
            "endpoint_digest": flash.endpoint_digest,
            "endpoint_digests_equal": len(
                {arm.endpoint_digest for arm in self.arms}
            ) == 1,
            "per_game": {
                game.game_id: {
                    "semantic_class": game.semantic_class,
                    "expected_cold_search": game.expected_cold_search,
                    "search_calls": {
                        arm.name: arm.outcome(game.game_id).search_calls
                        for arm in self.arms
                    },
                    "routes": {
                        arm.name: arm.outcome(game.game_id).route
                        for arm in self.arms
                    },
                }
                for game in self.games
            },
            "control_search_preserved": {
                game.game_id: (
                    flash.outcome(game.game_id).search_calls
                    == game.expected_cold_search
                )
                for game in self.games
                if game.semantic_class != "PARITY_LABEL"
            },
            "raw_shared_matches_isolated": (
                raw.global_search_calls == isolated.global_search_calls
            ),
            "sham_matches_isolated": (
                sham.global_search_calls == isolated.global_search_calls
            ),
            "ablation_matches_isolated": (
                ablation.global_search_calls == isolated.global_search_calls
            ),
            "gate_results": dict(self.gate_results),
        }


def _surface(prefix: str) -> tuple[str, ...]:
    return tuple(f"{prefix}{suffix}" for suffix in ("a", "b", "c", "d"))


def _game(
    game_id: str,
    prefix: str,
    labels: tuple[str, str, str, str],
    expected_cold_search: int,
    semantic_class: str,
) -> LiveGame:
    surface = _surface(prefix)
    return LiveGame(
        game_id=game_id,
        surface=surface,
        source_map=tuple(zip(surface, PAIR_INPUTS)),
        oracle_rows=tuple(zip(surface, labels)),
        expected_cold_search=expected_cold_search,
        semantic_class=semantic_class,
    )


def frozen_games() -> tuple[LiveGame, ...]:
    compatible = tuple(
        _game(
            f"PARITY_TARGET_{index + 1}",
            f"p{index}_",
            ("EVEN", "ODD", "ODD", "EVEN"),
            7,
            "PARITY_LABEL",
        )
        for index in range(6)
    )
    controls = (
        _game(
            "AND_CONTROL",
            "and_",
            ("EVEN", "EVEN", "EVEN", "ODD"),
            2,
            "AND_LABEL",
        ),
        _game(
            "OR_CONTROL",
            "or_",
            ("EVEN", "ODD", "ODD", "ODD"),
            8,
            "OR_LABEL",
        ),
    )
    return (*compatible, *controls)


def _candidate(
    game: LiveGame,
    labels: tuple[str, ...],
    *,
    capability_id: str,
    certificate_id: str,
    provenance_ids: tuple[str, ...],
) -> FiniteCapability:
    return FiniteCapability(
        capability_id=capability_id,
        input_type=f"flash-pair:{game.game_id}",
        output_type="label",
        semantics=tuple(zip(game.surface, labels)),
        guard_inputs=game.surface,
        certificate_id=certificate_id,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=provenance_ids,
        cost=1,
    )


def _cold_search(game: LiveGame, arm_name: str) -> GameOutcome:
    authority_checks = 0
    for search_calls, labels in enumerate(
        itertools.product(LABELS, repeat=len(game.surface)),
        start=1,
    ):
        candidate = _candidate(
            game,
            tuple(labels),
            capability_id=(
                f"{arm_name.lower()}:{game.game_id.lower()}:candidate:{search_calls}"
            ),
            certificate_id=(
                f"candidate:{arm_name.lower()}:{game.game_id.lower()}:{search_calls}"
            ),
            provenance_ids=("complete-flash-target-enumeration-v1",),
        )
        attack = exhaustive_attack(
            candidate,
            game.oracle,
            game.surface,
            budget=len(game.surface),
        )
        authority_checks += attack.checked
        if attack.status is AttackStatus.SURVIVE:
            outcome = GameOutcome(
                game_id=game.game_id,
                search_calls=search_calls,
                authority_checks=authority_checks,
                verified_signature=tuple(
                    candidate.execute(value) for value in game.surface
                ),
                route="COLD_SEARCH",
            )
            if outcome.search_calls != game.expected_cold_search:
                raise AssertionError(
                    f"frozen cold cost drift for {game.game_id}: "
                    f"{outcome.search_calls} != {game.expected_cold_search}"
                )
            return outcome
    raise AssertionError(f"complete candidate universe failed for {game.game_id}")


def _transport(
    source: FiniteCapability,
    game: LiveGame,
    *,
    prefix: str,
) -> FiniteCapability:
    lookup = game.source_lookup
    labels = tuple(source.execute(lookup[value]) for value in game.surface)
    return _candidate(
        game,
        labels,
        capability_id=f"{prefix}:{source.capability_id}:{game.game_id}",
        certificate_id=f"{prefix}:{source.certificate_id}:{game.game_id}",
        provenance_ids=(source.capability_id, source.certificate_id),
    )


def _closure(
    present: CompiledPresent,
    games: tuple[LiveGame, ...],
    *,
    prefix: str,
) -> ClosureMeasurement:
    restarted = present.restart()
    active = tuple(
        restarted.capability_graph.capability_map[capability_id]
        for capability_id in restarted.capability_graph.active_ids()
    )
    unresolved = {game.game_id for game in games}
    game_by_id = {game.game_id: game for game in games}
    tested_edges: set[tuple[str, str]] = set()
    outcomes: dict[str, GameOutcome] = {}
    rejected_edges: list[tuple[str, str]] = []
    authority_checks = 0
    change_counts: list[int] = []

    while True:
        changed = 0
        for game_id in tuple(sorted(unresolved)):
            game = game_by_id[game_id]
            for capability in active:
                edge = (capability.capability_id, game_id)
                if edge in tested_edges:
                    continue
                tested_edges.add(edge)
                if capability.input_type != "pair" or capability.output_type != "label":
                    rejected_edges.append(edge)
                    continue
                transported = _transport(
                    capability,
                    game,
                    prefix=prefix,
                )
                attack = exhaustive_attack(
                    transported,
                    game.oracle,
                    game.surface,
                    budget=len(game.surface),
                )
                authority_checks += attack.checked
                if attack.status is AttackStatus.SURVIVE:
                    outcomes[game_id] = GameOutcome(
                        game_id=game_id,
                        search_calls=0,
                        authority_checks=attack.checked,
                        verified_signature=tuple(
                            transported.execute(value) for value in game.surface
                        ),
                        route="FLASH_RECLOSED",
                    )
                    unresolved.remove(game_id)
                    changed += 1
                    break
                rejected_edges.append(edge)
        change_counts.append(changed)
        if changed == 0:
            break

    return ClosureMeasurement(
        outcomes=tuple(outcomes[key] for key in sorted(outcomes)),
        unresolved_ids=tuple(sorted(unresolved)),
        rejected_edges=tuple(sorted(rejected_edges)),
        authority_checks=authority_checks,
        change_counts=tuple(change_counts),
    )


def _sham_present() -> CompiledPresent:
    sham = FiniteCapability(
        capability_id="flash-sham-parity-label-v1",
        input_type="pair",
        output_type="label",
        semantics=tuple((value, "EVEN") for value in PAIR_INPUTS),
        guard_inputs=PAIR_INPUTS,
        certificate_id="cert:flash-sham-type-compatible-v1",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("flash-sham-control-v1",),
        cost=4,
    )
    return CompiledPresent.compile(
        CapabilityGraph((sham,)),
        MetaMemory.empty(),
    ).restart()


def _empty_present() -> CompiledPresent:
    return CompiledPresent.compile(
        CapabilityGraph(()),
        MetaMemory.empty(),
    ).restart()


def _run_arm(
    name: str,
    games: tuple[LiveGame, ...],
    *,
    present: CompiledPresent | None,
    composition_authority_checks: int,
) -> ArmResult:
    closure = None
    resolved: dict[str, GameOutcome] = {}
    rejected_edges: tuple[tuple[str, str], ...] = ()
    closure_changes: tuple[int, ...] = ()
    authority_checks = SOURCE_AUTHORITY_CHECKS + composition_authority_checks

    if present is not None:
        closure = _closure(present, games, prefix=name.lower())
        resolved.update({item.game_id: item for item in closure.outcomes})
        rejected_edges = closure.rejected_edges
        closure_changes = closure.change_counts
        authority_checks += closure.authority_checks

    outcomes: list[GameOutcome] = []
    for game in games:
        existing = resolved.get(game.game_id)
        if existing is not None:
            outcomes.append(existing)
            continue
        cold = _cold_search(game, name)
        outcomes.append(cold)
        authority_checks += cold.authority_checks

    target_search_calls = sum(item.search_calls for item in outcomes)
    return ArmResult(
        name=name,
        source_search_calls=SOURCE_SEARCH_CALLS,
        target_search_calls=target_search_calls,
        global_search_calls=SOURCE_SEARCH_CALLS + target_search_calls,
        authority_checks=authority_checks,
        outcomes=tuple(outcomes),
        closure_change_counts=closure_changes,
        flash_resolved_before_search=(
            closure.resolved_ids if closure is not None else ()
        ),
        rejected_edges=rejected_edges,
    )


def run_probe() -> FlashProbeResult:
    games = frozen_games()
    bundle = acquire_generations()
    retained = build_retained_state(bundle)
    restarted = retained.present.restart()
    serial_search = tuple(
        item.acquisition_search_calls for item in bundle.measurements
    )
    serial_authority = tuple(
        item.authority_checks for item in bundle.measurements
    )

    arms = (
        _run_arm(
            "ISOLATED",
            games,
            present=None,
            composition_authority_checks=0,
        ),
        _run_arm(
            "RAW_SHARED",
            games,
            present=None,
            composition_authority_checks=0,
        ),
        _run_arm(
            "FLASH",
            games,
            present=restarted,
            composition_authority_checks=serial_authority[2],
        ),
        _run_arm(
            "SHAM_FLASH",
            games,
            present=_sham_present(),
            composition_authority_checks=0,
        ),
        _run_arm(
            "ABLATION",
            games,
            present=_empty_present(),
            composition_authority_checks=serial_authority[2],
        ),
    )
    by_name = {arm.name: arm for arm in arms}
    isolated = by_name["ISOLATED"]
    flash = by_name["FLASH"]
    raw = by_name["RAW_SHARED"]
    sham = by_name["SHAM_FLASH"]
    ablation = by_name["ABLATION"]
    compatible_ids = {
        game.game_id for game in games if game.semantic_class == "PARITY_LABEL"
    }
    control_ids = {
        game.game_id for game in games if game.semantic_class != "PARITY_LABEL"
    }
    endpoints_equal = len({arm.endpoint_digest for arm in arms}) == 1

    gates = (
        ("TEN_LIVE_OBLIGATIONS", 2 + len(games) == 10),
        ("SERIAL_SOURCE_COSTS_PRESERVED", serial_search == (10, 3, 0)),
        ("ISOLATED_GLOBAL_SEARCH_65", isolated.global_search_calls == 65),
        ("FLASH_GLOBAL_SEARCH_23", flash.global_search_calls == 23),
        (
            "FLASH_AVOIDS_42_SEARCH_CALLS",
            isolated.global_search_calls - flash.global_search_calls == 42,
        ),
        (
            "SIX_GAMES_RECLOSED_BEFORE_SEARCH",
            set(flash.flash_resolved_before_search) == compatible_ids
            and len(flash.flash_resolved_before_search) == 6,
        ),
        (
            "FLASH_REACHES_FIXED_POINT_6_THEN_0",
            flash.closure_change_counts == (6, 0),
        ),
        (
            "SEMANTIC_CONTROLS_REJECT_PROPAGATION",
            all(
                flash.outcome(game_id).search_calls
                == next(
                    game.expected_cold_search
                    for game in games
                    if game.game_id == game_id
                )
                for game_id in control_ids
            )
            and len(
                [
                    edge for edge in flash.rejected_edges
                    if edge[1] in control_ids
                ]
            )
            == 2,
        ),
        ("RAW_SHARED_STAYS_COLD", raw.global_search_calls == 65),
        ("SHAM_FLASH_STAYS_COLD", sham.global_search_calls == 65),
        ("ABLATION_RESTORES_ISOLATED", ablation.global_search_calls == 65),
        ("ALL_ENDPOINTS_IDENTICAL_AND_VERIFIED", endpoints_equal),
        (
            "FLASH_PRESENT_RESTART_EXACT",
            retained.restart_exact
            and restarted.text() == retained.present.text()
            and restarted.digest == retained.present.digest,
        ),
        (
            "SOURCE_ACTIVE_PRESENT_REMINIMISED",
            restarted.capability_graph.active_ids()
            == (bundle.standalone.capability_id,),
        ),
    )

    return FlashProbeResult(
        games=games,
        arms=arms,
        gate_results=gates,
        active_capability_ids=restarted.capability_graph.active_ids(),
        compiled_present_digest=restarted.digest,
        restart_exact=retained.restart_exact,
        serial_generation_search=serial_search,
        serial_generation_authority=serial_authority,
    )


def main() -> int:
    result = run_probe()
    serialized = json.dumps(
        result.metrics(),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output_path = os.environ.get("QCKN_FLASH_RESULT_PATH")
    if output_path:
        Path(output_path).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
