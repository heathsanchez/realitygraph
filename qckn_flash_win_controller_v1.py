from __future__ import annotations

import json
import os
from pathlib import Path

from realitygraph.flash_bus import (
    BridgeCertificate,
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
    TypedCost,
)
from realitygraph.win_controller import (
    FlashWinController,
    SchedulerEffectCertificate,
)
from realitygraph.win_scheduler import GlobalWinScheduler, WinOpportunity


SCHED_AUTH = "qckn-win-scheduler-effect-authority-v1"
SCHED_VERIFIER = "qckn-win-scheduler-effect-verifier-v1"


def live_scheduler() -> GlobalWinScheduler:
    return GlobalWinScheduler(
        (
            WinOpportunity(
                "lean-kernel",
                "lean",
                direct_win=10,
                verification_probability=0.70,
                authority_readiness=1.0,
                destination_bridge_probability=0.25,
                flash_radius=6,
                future_search_removed=20,
                composition_unlocks=2,
                cost=3,
                latency=2,
                deadline_relevance=1.0,
                external_visibility=1.0,
            ),
            WinOpportunity(
                "sair",
                "sair",
                direct_win=8,
                verification_probability=0.65,
                authority_readiness=1.0,
                destination_bridge_probability=0.50,
                flash_radius=8,
                future_search_removed=40,
                composition_unlocks=3,
                cost=3,
                latency=2.5,
                deadline_relevance=0.90,
                external_visibility=1.0,
            ),
            WinOpportunity(
                "arc",
                "arc",
                direct_win=5,
                verification_probability=0.50,
                authority_readiness=0.85,
                destination_bridge_probability=0.30,
                flash_radius=12,
                future_search_removed=50,
                composition_unlocks=4,
                cost=4,
                latency=3,
                deadline_relevance=0.70,
                external_visibility=0.80,
            ),
            WinOpportunity(
                "collatz",
                "collatz",
                direct_win=1,
                verification_probability=0.60,
                authority_readiness=0.95,
                destination_bridge_probability=0.40,
                flash_radius=8,
                future_search_removed=100,
                composition_unlocks=3,
                cost=4,
                latency=3,
                deadline_relevance=0.10,
                external_visibility=0.50,
            ),
        )
    )


def live_bus() -> GlobalFlashBus:
    return GlobalFlashBus(
        domain_contracts=(
            DomainContract(
                "lean",
                "arena-current",
                "arena-semantic-parity",
            ),
            DomainContract(
                "sair",
                "sair-stage2-current",
                "official-judge-replay",
            ),
            DomainContract(
                "arc",
                "arc3-global-flash-v4",
                "arc3-public-structural-check",
            ),
            DomainContract(
                "collatz",
                "collatz-flash-v1",
                "exact-forward-replay",
            ),
        ),
        bridge_contract=DomainContract(
            "bridge",
            "qckn-cross-domain-bridge-v1",
            "independent-bridge-verifier-v1",
        ),
    )


def current_evidence_control() -> dict[str, object]:
    scheduler = live_scheduler()
    bus = live_bus()
    controller = FlashWinController(
        bus=bus,
        scheduler=scheduler,
        scheduler_authority_snapshot=SCHED_AUTH,
        scheduler_verifier_id=SCHED_VERIFIER,
    )
    before = [
        row.opportunity_id
        for row in controller.rank(mode="BATTLE", deadline_pressure=0.80)
    ]

    arc_event = EvidenceEvent(
        event_id="arc-v4-current",
        domain="arc",
        consequence_kind="structural-flash-result",
        consequence_key="no-structural-prune-market-parity",
        authority_snapshot="arc3-global-flash-v4",
        verifier_id="arc3-public-structural-check",
        provenance=(
            "run:35405132123; "
            "market_local=flash_structural; structural_pruned_actions=0"
        ),
        avoided_cost=TypedCost("arc.cross_game_revaluations", 2242),
    )
    collatz_event = EvidenceEvent(
        event_id="collatz-flash-current",
        domain="collatz",
        consequence_kind="bounded-propagation-result",
        consequence_key="no-advantage-over-upfront-guard",
        authority_snapshot="collatz-flash-v1",
        verifier_id="exact-forward-replay",
        provenance=(
            "run:35403074591; "
            "PASS_BOUNDED_PROPAGATION_NO_ADVANTAGE_OVER_UPFRONT_GUARD"
        ),
        avoided_cost=TypedCost("collatz.T_calls", 1292484),
    )

    arc_delta = controller.admit_event(arc_event)
    collatz_delta = controller.admit_event(collatz_event)

    after = [
        row.opportunity_id
        for row in controller.rank(mode="BATTLE", deadline_pressure=0.80)
    ]

    return {
        "before_order": before,
        "after_order": after,
        "arc_affected_domains": list(arc_delta.bus_affected_domains),
        "collatz_affected_domains": list(collatz_delta.bus_affected_domains),
        "cross_domain_edges": len(bus.cross_domain_edges()),
        "scheduler_events": len(scheduler.events),
        "typed_avoided_costs": bus.avoided_costs_by_unit(),
        "ranking_unchanged": before == after,
    }


def bridge_fixture() -> tuple[FlashWinController, GlobalWinScheduler, GlobalFlashBus]:
    scheduler = GlobalWinScheduler(
        (
            WinOpportunity(
                "lean-bridge",
                "lean",
                direct_win=2,
                verification_probability=0.95,
                authority_readiness=1.0,
                destination_bridge_probability=0.9,
                flash_radius=5,
                future_search_removed=30,
                composition_unlocks=2,
                cost=1.5,
                latency=0.5,
                deadline_relevance=0.8,
                external_visibility=0.7,
            ),
            WinOpportunity(
                "sair-final",
                "sair",
                direct_win=20,
                verification_probability=0.90,
                authority_readiness=1.0,
                destination_bridge_probability=0.2,
                flash_radius=1,
                future_search_removed=5,
                composition_unlocks=0,
                cost=8,
                latency=16,
                deadline_relevance=1.0,
                external_visibility=1.0,
            ),
            WinOpportunity(
                "sair-duplicate",
                "sair",
                direct_win=3,
                verification_probability=0.8,
                authority_readiness=1.0,
                destination_bridge_probability=0.1,
                flash_radius=1,
                future_search_removed=1,
                composition_unlocks=0,
                cost=3,
                latency=2,
                deadline_relevance=0.5,
                external_visibility=0.6,
            ),
            WinOpportunity(
                "arc-local",
                "arc",
                direct_win=4,
                verification_probability=0.6,
                authority_readiness=0.8,
                destination_bridge_probability=0.2,
                flash_radius=2,
                future_search_removed=3,
                composition_unlocks=0,
                cost=3,
                latency=2,
                deadline_relevance=0.6,
                external_visibility=0.6,
            ),
        )
    )
    bus = live_bus()
    effect_reprice = SchedulerEffectCertificate(
        effect_id="effect:lean-proof-constructor->sair-final",
        bridge_id="bridge:lean-to-sair-proof-constructor",
        destination_domain="sair",
        destination_kind="proof-constructor",
        destination_key="eq-family-v1",
        target_opportunity_id="sair-final",
        scheduler_authority_snapshot=SCHED_AUTH,
        scheduler_verifier_id=SCHED_VERIFIER,
        cost_multiplier=0.25,
        latency_multiplier=0.25,
        flash_radius_realized=4,
        future_search_removed_realized=24,
        composition_unlocks_realized=2,
        provenance=("synthetic-exact-bridge-fixture",),
    )
    effect_cancel = SchedulerEffectCertificate(
        effect_id="effect:lean-proof-constructor->sair-duplicate",
        bridge_id="bridge:lean-to-sair-proof-constructor",
        destination_domain="sair",
        destination_kind="proof-constructor",
        destination_key="eq-family-v1",
        target_opportunity_id="sair-duplicate",
        scheduler_authority_snapshot=SCHED_AUTH,
        scheduler_verifier_id=SCHED_VERIFIER,
        cancel_target=True,
        flash_radius_realized=1,
        future_search_removed_realized=6,
        provenance=("synthetic-exact-bridge-fixture",),
    )
    controller = FlashWinController(
        bus=bus,
        scheduler=scheduler,
        scheduler_authority_snapshot=SCHED_AUTH,
        scheduler_verifier_id=SCHED_VERIFIER,
        effects=(effect_reprice, effect_cancel),
    )
    return controller, scheduler, bus


def late_bridge_control() -> dict[str, object]:
    controller, scheduler, bus = bridge_fixture()

    before = scheduler.score(
        "sair-final",
        mode="BATTLE",
        deadline_pressure=0.8,
    )
    event = EvidenceEvent(
        event_id="lean-proof-constructor-event",
        domain="lean",
        consequence_kind="verified-proof-constructor",
        consequence_key="lean-eq-family-v1",
        authority_snapshot="arena-current",
        verifier_id="arena-semantic-parity",
        provenance="synthetic-exact-bridge-fixture",
    )

    local_delta = controller.admit_event(
        event,
        source_opportunity_id="lean-bridge",
        direct_win_realized=2.0,
    )
    middle = scheduler.score(
        "sair-final",
        mode="BATTLE",
        deadline_pressure=0.8,
    )

    wrong_bridge = BridgeCertificate(
        bridge_id="bridge:wrong",
        source_domain="lean",
        source_kind="verified-proof-constructor",
        source_key="different-key",
        destination_domain="sair",
        destination_kind="proof-constructor",
        destination_key="eq-family-v1",
        bridge_authority_snapshot="qckn-cross-domain-bridge-v1",
        bridge_verifier_id="independent-bridge-verifier-v1",
        certificate_id="bridge-cert:wrong",
    )
    wrong_delta = controller.admit_bridge(wrong_bridge)
    after_wrong = scheduler.score(
        "sair-final",
        mode="BATTLE",
        deadline_pressure=0.8,
    )

    bridge = BridgeCertificate(
        bridge_id="bridge:lean-to-sair-proof-constructor",
        source_domain="lean",
        source_kind="verified-proof-constructor",
        source_key="lean-eq-family-v1",
        destination_domain="sair",
        destination_kind="proof-constructor",
        destination_key="eq-family-v1",
        bridge_authority_snapshot="qckn-cross-domain-bridge-v1",
        bridge_verifier_id="independent-bridge-verifier-v1",
        certificate_id="bridge-cert:lean-to-sair-v1",
    )
    bridge_deltas = controller.admit_bridge(bridge)
    after = scheduler.score(
        "sair-final",
        mode="BATTLE",
        deadline_pressure=0.8,
    )
    ranking = [
        row.opportunity_id
        for row in controller.rank(mode="BATTLE", deadline_pressure=0.8)
    ]

    return {
        "before_score": before.score,
        "middle_score": middle.score,
        "after_wrong_score": after_wrong.score,
        "after_bridge_score": after.score,
        "local_affected_domains": list(local_delta.bus_affected_domains),
        "wrong_bridge_delta_count": len(wrong_delta),
        "bridge_delta_count": len(bridge_deltas),
        "bus_edges": [
            {
                "source": edge.source_event_id,
                "destination_domain": edge.destination_domain,
                "destination_kind": edge.destination_kind,
                "destination_key": edge.destination_key,
                "bridge_id": edge.bridge_id,
            }
            for edge in bus.cross_domain_edges()
        ],
        "cancelled": scheduler.metrics()["cancelled"],
        "applied_effects": sorted(controller.applied_effect_ids),
        "ranking_after_bridge": ranking,
        "score_unchanged_before_bridge": (
            before.score == middle.score == after_wrong.score
        ),
        "score_increased_after_bridge": after.score > before.score,
        "duplicate_cancelled": "sair-duplicate" in scheduler.metrics()["cancelled"],
        "unrelated_arc_still_open": "arc-local" in scheduler.metrics()["open"],
    }


def authority_rejection_control() -> bool:
    controller, scheduler, _bus = bridge_fixture()
    before = scheduler.metrics()
    bad = EvidenceEvent(
        event_id="bad-authority",
        domain="lean",
        consequence_kind="verified-proof-constructor",
        consequence_key="lean-eq-family-v1",
        authority_snapshot="wrong-authority",
        verifier_id="arena-semantic-parity",
        provenance="negative-control",
    )
    try:
        controller.admit_event(
            bad,
            source_opportunity_id="lean-bridge",
        )
    except ValueError:
        after = scheduler.metrics()
        return (
            before["open"] == after["open"]
            and before["events"] == after["events"]
            and before["cancelled"] == after["cancelled"]
        )
    return False


def effect_authority_rejection_control() -> bool:
    scheduler = live_scheduler()
    bus = live_bus()
    controller = FlashWinController(
        bus=bus,
        scheduler=scheduler,
        scheduler_authority_snapshot=SCHED_AUTH,
        scheduler_verifier_id=SCHED_VERIFIER,
    )
    before = scheduler.metrics()
    bad = SchedulerEffectCertificate(
        effect_id="bad-effect",
        bridge_id="bridge:x",
        destination_domain="sair",
        destination_kind="x",
        destination_key="y",
        target_opportunity_id="sair",
        scheduler_authority_snapshot="wrong",
        scheduler_verifier_id=SCHED_VERIFIER,
    )
    try:
        controller.admit_effect_certificate(bad)
    except ValueError:
        return before == scheduler.metrics()
    return False


def run_probe() -> dict[str, object]:
    current = current_evidence_control()
    late = late_bridge_control()
    authority_ok = authority_rejection_control()
    effect_authority_ok = effect_authority_rejection_control()

    gates = {
        "CURRENT_EVIDENCE_STAYS_LOCAL_WITHOUT_BRIDGE": (
            current["cross_domain_edges"] == 0
            and current["scheduler_events"] == 0
            and current["ranking_unchanged"]
            and current["arc_affected_domains"] == ["arc"]
            and current["collatz_affected_domains"] == ["collatz"]
        ),
        "WRONG_KEY_BRIDGE_HAS_NO_EFFECT": (
            late["wrong_bridge_delta_count"] == 0
            and late["score_unchanged_before_bridge"]
        ),
        "EXACT_LATE_BRIDGE_REPRICES_DESTINATION": (
            late["bridge_delta_count"] == 1
            and late["score_increased_after_bridge"]
            and late["after_bridge_score"] > 4 * late["before_score"] - 1e-9
        ),
        "EXACT_LATE_BRIDGE_CANCELS_DUPLICATE": late["duplicate_cancelled"],
        "EXACT_LATE_BRIDGE_PRESERVES_UNRELATED": late["unrelated_arc_still_open"],
        "DOMAIN_AUTHORITY_MISMATCH_CANNOT_MUTATE": authority_ok,
        "SCHEDULER_EFFECT_AUTHORITY_MISMATCH_CANNOT_MUTATE": effect_authority_ok,
        "TYPED_COSTS_REMAIN_SEPARATE": (
            set(current["typed_avoided_costs"])
            == {"arc.cross_game_revaluations", "collatz.T_calls"}
        ),
    }

    return {
        "schema": "qckn-flash-win-controller-v1",
        "passed": all(gates.values()),
        "gates": gates,
        "current_evidence_control": current,
        "late_bridge_control": late,
        "authority_controls": {
            "domain_authority_rejected_without_mutation": authority_ok,
            "scheduler_effect_authority_rejected_without_mutation": (
                effect_authority_ok
            ),
        },
        "claim_boundary": (
            "Current ARC V4 and Collatz Flash evidence are real run-derived "
            "metadata controls, but the Lean->SAIR bridge is an exact finite "
            "synthetic bridge fixture. The result qualifies the authority-gated "
            "coupling semantics, not the existence of a real Lean->SAIR bridge."
        ),
    }


def main() -> int:
    result = run_probe()
    serialized = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output = os.environ.get("QCKN_FLASH_WIN_CONTROLLER_RESULT_PATH")
    if output:
        Path(output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
