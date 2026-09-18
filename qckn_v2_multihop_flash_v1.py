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
from realitygraph.attack import AttackEvidence, AttackStatus, exhaustive_attack
from realitygraph.capability import FiniteCapability, compose_capabilities
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.compiled_present import CompiledPresent
from realitygraph.meta_memory import MetaMemory


LABELS = ("EVEN", "ODD")
TOKENS = ("LOW", "HIGH")
SOURCE_SEARCH_CALLS = 13


@dataclass(frozen=True)
class LiveGame:
    game_id: str
    surface: tuple[str, ...]
    source_map: tuple[tuple[str, str], ...]
    oracle_rows: tuple[tuple[str, str], ...]
    output_type: str
    expected_cold_search: int
    role: str

    @property
    def oracle(self) -> dict[str, str]:
        return dict(self.oracle_rows)

    @property
    def source_lookup(self) -> dict[str, str]:
        return dict(self.source_map)

    @property
    def signature(self) -> tuple[str, ...]:
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
class SecondHopBundle:
    bridge_capability: FiniteCapability
    decoder: FiniteCapability
    dependent: FiniteCapability
    standalone: FiniteCapability
    decoder_search_calls: int
    decoder_authority_checks: int
    bridge_promotion_attack: AttackEvidence
    decoder_promotion_attack: AttackEvidence
    dependent_attack: AttackEvidence
    standalone_attack: AttackEvidence

    @property
    def authority_checks(self) -> int:
        return (
            self.bridge_promotion_attack.checked
            + self.decoder_authority_checks
            + self.dependent_attack.checked
            + self.standalone_attack.checked
        )


@dataclass(frozen=True)
class ArmResult:
    name: str
    source_search_calls: int
    bridge_search_calls: int
    decoder_search_calls: int
    downstream_search_calls: int
    control_search_calls: int
    global_search_calls: int
    authority_checks: int
    outcomes: tuple[GameOutcome, ...]
    closure_change_counts: tuple[int, ...]
    promoted_counts_by_round: tuple[int, ...]
    flash_resolved_ids: tuple[str, ...]
    rejected_edges: tuple[tuple[str, str], ...]
    second_hop_capability_id: str
    second_hop_certificate_id: str
    c2_created_after_bridge: bool
    final_present_digest: str
    restart_exact: bool

    def outcome(self, game_id: str) -> GameOutcome:
        for item in self.outcomes:
            if item.game_id == game_id:
                return item
        raise KeyError(game_id)

    @property
    def endpoint_digest(self) -> str:
        payload = [
            {
                "game_id": item.game_id,
                "signature": list(item.verified_signature),
            }
            for item in sorted(self.outcomes, key=lambda row: row.game_id)
        ]
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class MultiHopProbeResult:
    arms: tuple[ArmResult, ...]
    gate_results: tuple[tuple[str, bool], ...]
    serial_generation_search: tuple[int, int, int]
    serial_generation_authority: tuple[int, int, int]
    source_capability_id: str
    source_certificate_id: str

    def arm(self, name: str) -> ArmResult:
        for arm in self.arms:
            if arm.name == name:
                return arm
        raise KeyError(name)

    @property
    def failed_gates(self) -> tuple[str, ...]:
        return tuple(code for code, passed in self.gate_results if not passed)

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
            "schema": "qckn-v2-multihop-flash-v1",
            "passed": self.passed,
            "failed_gates": list(self.failed_gates),
            "live_obligations": 10,
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
            "source_capability_id": self.source_capability_id,
            "source_certificate_id": self.source_certificate_id,
            "global_search_calls": {
                arm.name: arm.global_search_calls for arm in self.arms
            },
            "bridge_search_calls": {
                arm.name: arm.bridge_search_calls for arm in self.arms
            },
            "decoder_search_calls": {
                arm.name: arm.decoder_search_calls for arm in self.arms
            },
            "downstream_search_calls": {
                arm.name: arm.downstream_search_calls for arm in self.arms
            },
            "control_search_calls": {
                arm.name: arm.control_search_calls for arm in self.arms
            },
            "authority_checks": {
                arm.name: arm.authority_checks for arm in self.arms
            },
            "flash_search_avoided": (
                isolated.global_search_calls - flash.global_search_calls
            ),
            "flash_closure_change_counts": list(flash.closure_change_counts),
            "flash_promoted_counts_by_round": list(flash.promoted_counts_by_round),
            "flash_resolved_ids": list(flash.flash_resolved_ids),
            "flash_rejected_edges": [list(edge) for edge in flash.rejected_edges],
            "second_hop_capability_id": flash.second_hop_capability_id,
            "second_hop_certificate_id": flash.second_hop_certificate_id,
            "c2_created_after_bridge": flash.c2_created_after_bridge,
            "final_present_digest": flash.final_present_digest,
            "restart_exact": flash.restart_exact,
            "endpoint_digests_equal": len(
                {arm.endpoint_digest for arm in self.arms}
            ) == 1,
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
    signature: tuple[str, str, str, str],
    output_type: str,
    expected_cold_search: int,
    role: str,
) -> LiveGame:
    surface = _surface(prefix)
    return LiveGame(
        game_id=game_id,
        surface=surface,
        source_map=tuple(zip(surface, PAIR_INPUTS)),
        oracle_rows=tuple(zip(surface, signature)),
        output_type=output_type,
        expected_cold_search=expected_cold_search,
        role=role,
    )


def frozen_games() -> tuple[LiveGame, ...]:
    bridge = _game(
        "BRIDGE_LABEL",
        "bridge_",
        ("EVEN", "ODD", "ODD", "EVEN"),
        "label",
        7,
        "BRIDGE",
    )
    downstream = tuple(
        _game(
            f"TOKEN_TARGET_{index + 1}",
            f"tok{index}_",
            ("LOW", "HIGH", "HIGH", "LOW"),
            "token",
            7,
            "DOWNSTREAM",
        )
        for index in range(4)
    )
    controls = (
        _game(
            "AND_LABEL_CONTROL",
            "andl_",
            ("EVEN", "EVEN", "EVEN", "ODD"),
            "label",
            2,
            "CONTROL",
        ),
        _game(
            "AND_TOKEN_CONTROL",
            "andt_",
            ("LOW", "LOW", "LOW", "HIGH"),
            "token",
            2,
            "CONTROL",
        ),
        _game(
            "OR_TOKEN_CONTROL",
            "ort_",
            ("LOW", "HIGH", "HIGH", "HIGH"),
            "token",
            8,
            "CONTROL",
        ),
    )
    return (bridge, *downstream, *controls)


def _candidate(
    game: LiveGame,
    values: tuple[str, ...],
    *,
    capability_id: str,
    certificate_id: str,
    provenance_ids: tuple[str, ...],
) -> FiniteCapability:
    return FiniteCapability(
        capability_id=capability_id,
        input_type=f"multihop-pair:{game.game_id}",
        output_type=game.output_type,
        semantics=tuple(zip(game.surface, values)),
        guard_inputs=game.surface,
        certificate_id=certificate_id,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=provenance_ids,
        cost=1,
    )


def _cold_search(game: LiveGame, arm_name: str) -> GameOutcome:
    alphabet = LABELS if game.output_type == "label" else TOKENS
    checks = 0
    for search_calls, values in enumerate(
        itertools.product(alphabet, repeat=len(game.surface)),
        start=1,
    ):
        candidate = _candidate(
            game,
            tuple(values),
            capability_id=(
                f"{arm_name.lower()}:{game.game_id.lower()}:candidate:{search_calls}"
            ),
            certificate_id=(
                f"candidate:{arm_name.lower()}:{game.game_id.lower()}:{search_calls}"
            ),
            provenance_ids=("complete-multihop-target-enumeration-v1",),
        )
        attack = exhaustive_attack(
            candidate,
            game.oracle,
            game.surface,
            budget=len(game.surface),
        )
        checks += attack.checked
        if attack.status is AttackStatus.SURVIVE:
            if search_calls != game.expected_cold_search:
                raise AssertionError(
                    f"frozen cold cost drift for {game.game_id}: "
                    f"{search_calls} != {game.expected_cold_search}"
                )
            return GameOutcome(
                game_id=game.game_id,
                search_calls=search_calls,
                authority_checks=checks,
                verified_signature=tuple(
                    candidate.execute(value) for value in game.surface
                ),
                route="COLD_SEARCH",
            )
    raise AssertionError(f"no candidate survived for {game.game_id}")


def _transport_source(
    source: FiniteCapability,
    game: LiveGame,
    *,
    capability_id: str,
    certificate_id: str,
) -> FiniteCapability:
    lookup = game.source_lookup
    values = tuple(source.execute(lookup[value]) for value in game.surface)
    return _candidate(
        game,
        values,
        capability_id=capability_id,
        certificate_id=certificate_id,
        provenance_ids=(source.capability_id, source.certificate_id),
    )


def _promote_bridge_from_verified_candidate(
    candidate: FiniteCapability,
    game: LiveGame,
) -> tuple[FiniteCapability, AttackEvidence]:
    promoted = FiniteCapability(
        capability_id="multihop-bridge-parity-label-v1",
        input_type=candidate.input_type,
        output_type=candidate.output_type,
        semantics=candidate.semantics,
        guard_inputs=candidate.guard_inputs,
        certificate_id="cert:multihop-bridge-label-exhaustive-v1",
        dependencies=(),
        authority_snapshot=candidate.authority_snapshot,
        verifier_id=candidate.verifier_id,
        provenance_ids=tuple(
            dict.fromkeys(
                (
                    *candidate.provenance_ids,
                    candidate.capability_id,
                    candidate.certificate_id,
                )
            )
        ),
        cost=1,
    )
    attack = exhaustive_attack(
        promoted,
        game.oracle,
        game.surface,
        budget=len(game.surface),
    )
    if attack.status is not AttackStatus.SURVIVE:
        raise AssertionError("promoted bridge identity failed independent authority")
    return promoted, attack


def _acquire_decoder() -> tuple[
    FiniteCapability,
    int,
    int,
    AttackEvidence,
]:
    tables = (
        (("EVEN", "LOW"), ("ODD", "LOW")),
        (("EVEN", "HIGH"), ("ODD", "LOW")),
        (("EVEN", "LOW"), ("ODD", "HIGH")),
        (("EVEN", "HIGH"), ("ODD", "HIGH")),
    )
    oracle = {"EVEN": "LOW", "ODD": "HIGH"}
    checks = 0
    for search_calls, table in enumerate(tables, start=1):
        candidate = FiniteCapability(
            capability_id=f"multihop-decoder-candidate-{search_calls}-v1",
            input_type="label",
            output_type="token",
            semantics=table,
            guard_inputs=("EVEN", "ODD"),
            certificate_id=f"candidate:multihop-decoder-{search_calls}-v1",
            dependencies=(),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
            provenance_ids=("complete-multihop-decoder-portfolio-v1",),
            cost=1,
        )
        attack = exhaustive_attack(
            candidate,
            oracle,
            ("EVEN", "ODD"),
            budget=2,
        )
        checks += attack.checked
        if attack.status is AttackStatus.SURVIVE:
            promoted = FiniteCapability(
                capability_id="multihop-label-token-decoder-v1",
                input_type="label",
                output_type="token",
                semantics=candidate.semantics,
                guard_inputs=candidate.guard_inputs,
                certificate_id="cert:multihop-decoder-exhaustive-v1",
                dependencies=(),
                authority_snapshot=AUTHORITY,
                verifier_id=VERIFIER,
                provenance_ids=(
                    "complete-multihop-decoder-portfolio-v1",
                    candidate.capability_id,
                ),
                cost=1,
            )
            promotion_attack = exhaustive_attack(
                promoted,
                oracle,
                ("EVEN", "ODD"),
                budget=2,
            )
            if promotion_attack.status is not AttackStatus.SURVIVE:
                raise AssertionError("promoted decoder identity failed authority")
            checks += promotion_attack.checked
            return promoted, search_calls, checks, promotion_attack
    raise AssertionError("complete decoder portfolio contained no solution")


def _build_second_hop(
    bridge_capability: FiniteCapability,
    bridge_promotion_attack: AttackEvidence,
    bridge_game: LiveGame,
) -> SecondHopBundle:
    decoder, decoder_search, decoder_checks, decoder_promotion_attack = (
        _acquire_decoder()
    )
    dependent = compose_capabilities(
        "multihop-dependent-pair-token-v1",
        bridge_capability,
        decoder,
    )
    token_oracle = {
        value: ("LOW" if label == "EVEN" else "HIGH")
        for value, label in bridge_game.oracle.items()
    }
    dependent_attack = exhaustive_attack(
        dependent,
        token_oracle,
        bridge_game.surface,
        budget=len(bridge_game.surface),
    )
    if dependent_attack.status is not AttackStatus.SURVIVE:
        raise AssertionError("dependent second-hop composition failed authority")
    standalone = FiniteCapability(
        capability_id="multihop-standalone-pair-token-v1",
        input_type=dependent.input_type,
        output_type=dependent.output_type,
        semantics=dependent.semantics,
        guard_inputs=dependent.guard_inputs,
        certificate_id="cert:multihop-standalone-pair-token-v1",
        dependencies=(),
        authority_snapshot=dependent.authority_snapshot,
        verifier_id=dependent.verifier_id,
        provenance_ids=tuple(
            dict.fromkeys(
                (
                    bridge_capability.capability_id,
                    decoder.capability_id,
                    dependent.capability_id,
                    bridge_capability.certificate_id,
                    decoder.certificate_id,
                    dependent.certificate_id,
                )
            )
        ),
        cost=dependent.cost,
    )
    standalone_attack = exhaustive_attack(
        standalone,
        token_oracle,
        bridge_game.surface,
        budget=len(bridge_game.surface),
    )
    if standalone_attack.status is not AttackStatus.SURVIVE:
        raise AssertionError("standalone second-hop identity failed authority")
    return SecondHopBundle(
        bridge_capability=bridge_capability,
        decoder=decoder,
        dependent=dependent,
        standalone=standalone,
        decoder_search_calls=decoder_search,
        decoder_authority_checks=decoder_checks,
        bridge_promotion_attack=bridge_promotion_attack,
        decoder_promotion_attack=decoder_promotion_attack,
        dependent_attack=dependent_attack,
        standalone_attack=standalone_attack,
    )


def _sham_source_present() -> CompiledPresent:
    sham = FiniteCapability(
        capability_id="multihop-sham-source-v1",
        input_type="pair",
        output_type="label",
        semantics=tuple((value, "EVEN") for value in PAIR_INPUTS),
        guard_inputs=PAIR_INPUTS,
        certificate_id="cert:multihop-sham-v1",
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=("multihop-sham-control-v1",),
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


def _run_nonflash_arm(
    name: str,
    games: tuple[LiveGame, ...],
    source_authority_checks: int,
) -> ArmResult:
    bridge = next(game for game in games if game.role == "BRIDGE")
    bridge_outcome = _cold_search(bridge, name)
    cold_bridge_candidate = _candidate(
        bridge,
        bridge_outcome.verified_signature,
        capability_id=f"{name.lower()}:bridge-verified-v1",
        certificate_id=f"cert:{name.lower()}:bridge-verified-v1",
        provenance_ids=("cold-bridge-search-v1",),
    )
    bridge_capability, bridge_promotion_attack = (
        _promote_bridge_from_verified_candidate(
            cold_bridge_candidate,
            bridge,
        )
    )
    second_hop = _build_second_hop(
        bridge_capability,
        bridge_promotion_attack,
        bridge,
    )

    outcomes: list[GameOutcome] = [bridge_outcome]
    for game in games:
        if game.game_id == bridge.game_id:
            continue
        outcomes.append(_cold_search(game, name))

    downstream_search = sum(
        item.search_calls
        for item in outcomes
        if next(game.role for game in games if game.game_id == item.game_id)
        == "DOWNSTREAM"
    )
    control_search = sum(
        item.search_calls
        for item in outcomes
        if next(game.role for game in games if game.game_id == item.game_id)
        == "CONTROL"
    )
    authority_checks = (
        source_authority_checks
        + sum(item.authority_checks for item in outcomes)
        + second_hop.authority_checks
    )
    total_search = (
        SOURCE_SEARCH_CALLS
        + bridge_outcome.search_calls
        + second_hop.decoder_search_calls
        + downstream_search
        + control_search
    )
    return ArmResult(
        name=name,
        source_search_calls=SOURCE_SEARCH_CALLS,
        bridge_search_calls=bridge_outcome.search_calls,
        decoder_search_calls=second_hop.decoder_search_calls,
        downstream_search_calls=downstream_search,
        control_search_calls=control_search,
        global_search_calls=total_search,
        authority_checks=authority_checks,
        outcomes=tuple(outcomes),
        closure_change_counts=(),
        promoted_counts_by_round=(),
        flash_resolved_ids=(),
        rejected_edges=(),
        second_hop_capability_id=second_hop.standalone.capability_id,
        second_hop_certificate_id=second_hop.standalone.certificate_id,
        c2_created_after_bridge=True,
        final_present_digest="",
        restart_exact=True,
    )


def _try_capability_on_game(
    capability: FiniteCapability,
    game: LiveGame,
    *,
    prefix: str,
) -> tuple[FiniteCapability | None, AttackEvidence | None]:
    if capability.output_type != game.output_type:
        return None, None
    if capability.input_type not in {"pair", "multihop-pair:BRIDGE_LABEL"}:
        return None, None

    # Source Pair capability and second-hop bridge Pair capability share the
    # same ordered four-state abstract carrier; transport is only by the
    # frozen literal isomorphism.
    lookup = game.source_lookup
    source_rows = capability.semantic_table
    source_order = tuple(source_rows)
    if len(source_order) != len(PAIR_INPUTS):
        return None, None
    canonical_to_value = dict(zip(PAIR_INPUTS, source_order))
    values = tuple(
        capability.execute(canonical_to_value[lookup[value]])
        for value in game.surface
    )
    transported = _candidate(
        game,
        values,
        capability_id=f"{prefix}:{capability.capability_id}:{game.game_id}",
        certificate_id=f"{prefix}:{capability.certificate_id}:{game.game_id}",
        provenance_ids=(capability.capability_id, capability.certificate_id),
    )
    attack = exhaustive_attack(
        transported,
        game.oracle,
        game.surface,
        budget=len(game.surface),
    )
    return transported, attack


def _run_flash_arm(
    name: str,
    games: tuple[LiveGame, ...],
    initial_present: CompiledPresent,
    source_authority_checks: int,
    *,
    allow_cascade: bool,
) -> ArmResult:
    bridge = next(game for game in games if game.role == "BRIDGE")
    unresolved = {game.game_id for game in games}
    game_by_id = {game.game_id: game for game in games}
    outcomes: dict[str, GameOutcome] = {}
    rejected_edges: list[tuple[str, str]] = []
    tested_edges: set[tuple[str, str]] = set()
    change_counts: list[int] = []
    promoted_counts: list[int] = []
    authority_checks = source_authority_checks
    decoder_search_calls = 0
    second_hop: SecondHopBundle | None = None
    present = initial_present.restart()
    restart_exact = (
        present.text() == initial_present.text()
        and present.digest == initial_present.digest
    )
    bridge_resolved_round: int | None = None
    c2_created_round: int | None = None

    round_index = 0
    while True:
        round_index += 1
        changed = 0
        promoted = 0
        active_graph = present.capability_graph
        active = tuple(
            active_graph.capability_map[capability_id]
            for capability_id in active_graph.active_ids()
        )

        for game_id in tuple(sorted(unresolved)):
            game = game_by_id[game_id]
            for capability in active:
                edge = (capability.capability_id, game_id)
                if edge in tested_edges:
                    continue
                tested_edges.add(edge)
                transported, attack = _try_capability_on_game(
                    capability,
                    game,
                    prefix=f"{name.lower()}:r{round_index}",
                )
                if transported is None or attack is None:
                    continue
                authority_checks += attack.checked
                if attack.status is AttackStatus.SURVIVE:
                    outcomes[game_id] = GameOutcome(
                        game_id=game_id,
                        search_calls=0,
                        authority_checks=attack.checked,
                        verified_signature=tuple(
                            transported.execute(value) for value in game.surface
                        ),
                        route=f"FLASH_WAVE_{round_index}",
                    )
                    unresolved.remove(game_id)
                    changed += 1

                    if (
                        allow_cascade
                        and game.role == "BRIDGE"
                        and second_hop is None
                    ):
                        bridge_resolved_round = round_index
                        bridge_capability, bridge_promotion_attack = (
                            _promote_bridge_from_verified_candidate(
                                transported,
                                bridge,
                            )
                        )
                        authority_checks += bridge_promotion_attack.checked
                        second_hop = _build_second_hop(
                            bridge_capability,
                            bridge_promotion_attack,
                            bridge,
                        )
                        # bridge promotion check was already counted explicitly
                        # above; the bundle total includes it, so count only the
                        # remaining second-hop checks here.
                        authority_checks += (
                            second_hop.authority_checks
                            - bridge_promotion_attack.checked
                        )
                        decoder_search_calls += second_hop.decoder_search_calls
                        existing = tuple(
                            active_graph.capability_map[cid]
                            for cid in active_graph.active_ids()
                        )
                        present = CompiledPresent.compile(
                            CapabilityGraph(
                                (*existing, second_hop.standalone)
                            ),
                            MetaMemory.empty(),
                        ).restart()
                        c2_created_round = round_index
                        promoted += 1
                    break
                rejected_edges.append(edge)

        change_counts.append(changed)
        promoted_counts.append(promoted)
        if changed == 0 and promoted == 0:
            break

    # Anything not discharged by closure pays its frozen cold search.
    for game_id in tuple(sorted(unresolved)):
        game = game_by_id[game_id]
        cold = _cold_search(game, name)
        outcomes[game_id] = cold
        authority_checks += cold.authority_checks

    # If the bridge did not trigger the shared cascade, build its local
    # second-hop capability only after its cold resolution, so all arms end at
    # the same verified local endpoint but no other game can use it.
    if second_hop is None:
        bridge_outcome = outcomes[bridge.game_id]
        local_bridge = _candidate(
            bridge,
            bridge_outcome.verified_signature,
            capability_id=f"{name.lower()}:local-bridge-v1",
            certificate_id=f"cert:{name.lower()}:local-bridge-v1",
            provenance_ids=("local-cold-bridge-v1",),
        )
        promoted_bridge, bridge_attack = _promote_bridge_from_verified_candidate(
            local_bridge,
            bridge,
        )
        authority_checks += bridge_attack.checked
        second_hop = _build_second_hop(
            promoted_bridge,
            bridge_attack,
            bridge,
        )
        authority_checks += second_hop.authority_checks - bridge_attack.checked
        decoder_search_calls += second_hop.decoder_search_calls
        c2_created_round = (
            (bridge_resolved_round or len(change_counts)) + 1
        )

    ordered_outcomes = tuple(
        outcomes[game.game_id] for game in games
    )
    bridge_search = outcomes[bridge.game_id].search_calls
    downstream_search = sum(
        outcomes[game.game_id].search_calls
        for game in games
        if game.role == "DOWNSTREAM"
    )
    control_search = sum(
        outcomes[game.game_id].search_calls
        for game in games
        if game.role == "CONTROL"
    )
    total_search = (
        SOURCE_SEARCH_CALLS
        + bridge_search
        + decoder_search_calls
        + downstream_search
        + control_search
    )

    final_restarted = present.restart()
    restart_exact = restart_exact and (
        final_restarted.text() == present.text()
        and final_restarted.digest == present.digest
    )

    return ArmResult(
        name=name,
        source_search_calls=SOURCE_SEARCH_CALLS,
        bridge_search_calls=bridge_search,
        decoder_search_calls=decoder_search_calls,
        downstream_search_calls=downstream_search,
        control_search_calls=control_search,
        global_search_calls=total_search,
        authority_checks=authority_checks,
        outcomes=ordered_outcomes,
        closure_change_counts=tuple(change_counts),
        promoted_counts_by_round=tuple(promoted_counts),
        flash_resolved_ids=tuple(
            item.game_id
            for item in ordered_outcomes
            if item.route.startswith("FLASH_WAVE_")
        ),
        rejected_edges=tuple(sorted(rejected_edges)),
        second_hop_capability_id=second_hop.standalone.capability_id,
        second_hop_certificate_id=second_hop.standalone.certificate_id,
        c2_created_after_bridge=(
            bridge_resolved_round is not None
            and c2_created_round is not None
            and c2_created_round >= bridge_resolved_round
        ),
        final_present_digest=final_restarted.digest,
        restart_exact=restart_exact,
    )


def run_probe() -> MultiHopProbeResult:
    games = frozen_games()
    bundle = acquire_generations()
    retained = build_retained_state(bundle)
    serial_search = tuple(
        item.acquisition_search_calls for item in bundle.measurements
    )
    serial_authority = tuple(
        item.authority_checks for item in bundle.measurements
    )
    source_authority_checks = sum(serial_authority)

    isolated = _run_nonflash_arm(
        "ISOLATED",
        games,
        source_authority_checks,
    )
    raw = _run_nonflash_arm(
        "RAW_SHARED",
        games,
        source_authority_checks,
    )
    flash = _run_flash_arm(
        "FLASH",
        games,
        retained.present.restart(),
        source_authority_checks,
        allow_cascade=True,
    )
    sham = _run_flash_arm(
        "SHAM_FLASH",
        games,
        _sham_source_present(),
        source_authority_checks,
        allow_cascade=False,
    )
    ablation = _run_flash_arm(
        "ABLATION",
        games,
        _empty_present(),
        source_authority_checks,
        allow_cascade=False,
    )
    arms = (isolated, raw, flash, sham, ablation)

    downstream_ids = {
        game.game_id for game in games if game.role == "DOWNSTREAM"
    }
    control_ids = {
        game.game_id for game in games if game.role == "CONTROL"
    }
    endpoints_equal = len({arm.endpoint_digest for arm in arms}) == 1

    gates = (
        ("TEN_LIVE_OBLIGATIONS", 2 + len(games) == 10),
        ("SERIAL_SOURCE_COSTS_PRESERVED", serial_search == (10, 3, 0)),
        ("ISOLATED_GLOBAL_SEARCH_63", isolated.global_search_calls == 63),
        ("FLASH_GLOBAL_SEARCH_28", flash.global_search_calls == 28),
        (
            "FLASH_AVOIDS_35_SEARCH_CALLS",
            isolated.global_search_calls - flash.global_search_calls == 35,
        ),
        (
            "FLASH_CASCADE_1_4_0",
            flash.closure_change_counts == (1, 4, 0),
        ),
        (
            "ONE_SECOND_HOP_PROMOTION",
            flash.promoted_counts_by_round == (1, 0, 0),
        ),
        (
            "C2_CREATED_ONLY_AFTER_BRIDGE",
            flash.c2_created_after_bridge,
        ),
        (
            "DECODER_SEARCH_EXACTLY_3",
            all(arm.decoder_search_calls == 3 for arm in arms),
        ),
        (
            "FOUR_DOWNSTREAM_ZERO_SEARCH_AFTER_C2",
            all(
                flash.outcome(game_id).search_calls == 0
                and flash.outcome(game_id).route == "FLASH_WAVE_2"
                for game_id in downstream_ids
            ),
        ),
        (
            "SEMANTIC_CONTROLS_STAY_COLD",
            all(
                flash.outcome(game_id).search_calls
                == next(
                    game.expected_cold_search
                    for game in games
                    if game.game_id == game_id
                )
                for game_id in control_ids
            ),
        ),
        ("RAW_SHARED_STAYS_ISOLATED", raw.global_search_calls == 63),
        ("SHAM_FLASH_STAYS_ISOLATED", sham.global_search_calls == 63),
        ("ABLATION_RESTORES_ISOLATED", ablation.global_search_calls == 63),
        ("ALL_ENDPOINTS_IDENTICAL_AND_VERIFIED", endpoints_equal),
        ("FLASH_RESTART_EXACT", flash.restart_exact),
        (
            "SECOND_HOP_HAS_NEW_CERTIFICATE",
            flash.second_hop_certificate_id
            == "cert:multihop-standalone-pair-token-v1",
        ),
    )

    return MultiHopProbeResult(
        arms=arms,
        gate_results=gates,
        serial_generation_search=serial_search,
        serial_generation_authority=serial_authority,
        source_capability_id=bundle.standalone.capability_id,
        source_certificate_id=bundle.standalone.certificate_id,
    )


def main() -> int:
    result = run_probe()
    serialized = json.dumps(
        result.metrics(),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output_path = os.environ.get("QCKN_MULTIHOP_RESULT_PATH")
    if output_path:
        Path(output_path).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
