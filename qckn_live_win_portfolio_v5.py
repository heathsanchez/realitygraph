from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import qckn_live_win_portfolio_v4 as v4
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
from realitygraph.win_scheduler import GlobalWinScheduler


SCHEDULER_AUTHORITY = "qckn-live-win-portfolio-v5"
SCHEDULER_VERIFIER = "event-driven-portfolio-gate-v1"
BRIDGE_VERIFIER = "real-flash-v2-scheduler-projection-v1"

RESIDUAL_TO_OPPORTUNITY = {
    residual_id: opportunity_id
    for opportunity_id, (residual_id, _domain, _cost)
    in v4.SETTLED_PROTOCOL_OPPORTUNITIES.items()
}
RESIDUAL_TO_COST = {
    residual_id: float(cost)
    for _opportunity_id, (residual_id, _domain, cost)
    in v4.SETTLED_PROTOCOL_OPPORTUNITIES.items()
}
RESIDUAL_TO_DOMAIN = {
    residual_id: domain
    for _opportunity_id, (residual_id, domain, _cost)
    in v4.SETTLED_PROTOCOL_OPPORTUNITIES.items()
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric_map(row: dict[str, Any]) -> dict[str, Any]:
    metrics = row.get("metrics", [])
    if isinstance(metrics, dict):
        return metrics
    return {str(k): v for k, v in metrics}


def _evidence_for_domain(real: dict[str, Any], domain: str) -> dict[str, Any]:
    evidence = real["snapshot"]["evidence"]
    rows = [row for row in evidence.values() if row["domain"] == domain]
    if not rows:
        raise AssertionError(f"no authority evidence for {domain}")
    # Prefer evidence carrying the verified-state compilation pattern.
    rows.sort(
        key=lambda row: (
            "verified_state_compilation" not in row.get("pattern_ids", []),
            row["evidence_id"],
        )
    )
    return rows[0]


def _contracts(
    real: dict[str, Any],
    result_digest: str,
) -> tuple[tuple[DomainContract, ...], DomainContract]:
    supported = set(
        real["cross_domain_result"]["genuine_meta_flash"]["supporting_domains"]
    )
    required = {"sair", "arc", "gpu-ir", "lean-kernel"}
    if supported != required:
        raise AssertionError(f"unexpected supporting domains: {sorted(supported)}")

    rows = [
        DomainContract(
            "realitygraph",
            f"real-flash-v2:{result_digest}",
            "real-multidomain-v2-gates",
        )
    ]
    for domain in sorted(required | {"gpu-hardware"}):
        rows.append(
            DomainContract(
                domain,
                f"real-flash-v2-supported:{domain}",
                f"destination-authority:{domain}",
            )
        )
    return (
        tuple(rows),
        DomainContract(
            "bridge",
            f"real-flash-v2:{result_digest}",
            BRIDGE_VERIFIER,
        ),
    )


def _bridge_and_effect_rows(
    real: dict[str, Any],
    result_digest: str,
) -> tuple[tuple[BridgeCertificate, ...], tuple[SchedulerEffectCertificate, ...]]:
    genuine = real["cross_domain_result"]["genuine_meta_flash"]
    settled = set(genuine["settled_protocol_residuals"])
    required = set(RESIDUAL_TO_OPPORTUNITY)
    if settled != required:
        raise AssertionError(f"settled residual set changed: {sorted(settled)}")

    supporting_ids = tuple(sorted(genuine["supporting_evidence_ids"]))
    evidence_by_domain = {
        row["domain"]: row["evidence_id"]
        for row in real["snapshot"]["evidence"].values()
        if row["evidence_id"] in supporting_ids
    }

    bridges: list[BridgeCertificate] = []
    effects: list[SchedulerEffectCertificate] = []
    for residual_id in sorted(required):
        domain = RESIDUAL_TO_DOMAIN[residual_id]
        opportunity_id = RESIDUAL_TO_OPPORTUNITY[residual_id]
        cost = RESIDUAL_TO_COST[residual_id]
        source_evidence_id = evidence_by_domain.get(domain)
        if source_evidence_id is None:
            raise AssertionError(
                f"missing supporting evidence for settled domain {domain}"
            )
        bridge_id = f"real-v2:{domain}:verified-state-compilation"
        destination_key = residual_id
        bridges.append(
            BridgeCertificate(
                bridge_id=bridge_id,
                source_domain="realitygraph",
                source_kind="compiled-meta-capability",
                source_key="verified_state_compilation",
                destination_domain=domain,
                destination_kind="settled-protocol-residual",
                destination_key=destination_key,
                bridge_authority_snapshot=f"real-flash-v2:{result_digest}",
                bridge_verifier_id=BRIDGE_VERIFIER,
                certificate_id=(
                    f"real-v2-support:{source_evidence_id}:{result_digest[:12]}"
                ),
            )
        )
        effects.append(
            SchedulerEffectCertificate(
                effect_id=f"effect:{bridge_id}",
                bridge_id=bridge_id,
                destination_domain=domain,
                destination_kind="settled-protocol-residual",
                destination_key=destination_key,
                target_opportunity_id=opportunity_id,
                scheduler_authority_snapshot=SCHEDULER_AUTHORITY,
                scheduler_verifier_id=SCHEDULER_VERIFIER,
                cancel_target=True,
                flash_radius_realized=1,
                future_search_removed_realized=cost,
                composition_unlocks_realized=0.25,
                provenance=(
                    source_evidence_id,
                    residual_id,
                    result_digest,
                ),
            )
        )
    return tuple(bridges), tuple(effects)


def _rank(
    controller: FlashWinController,
    *,
    mode: str,
    pressure: float,
) -> list[str]:
    return [
        row.opportunity_id
        for row in controller.rank(
            mode=mode,
            deadline_pressure=pressure,
        )
    ]


def _bad_authority_rejected_without_mutation(
    controller: FlashWinController,
    result_digest: str,
) -> bool:
    before = controller.snapshot()
    bad = EvidenceEvent(
        event_id="negative-control:bad-meta-authority",
        domain="realitygraph",
        consequence_kind="compiled-meta-capability",
        consequence_key="verified_state_compilation",
        authority_snapshot="wrong-authority",
        verifier_id="real-multidomain-v2-gates",
        provenance="negative-control",
    )
    try:
        controller.admit_event(
            bad,
            source_opportunity_id="flash-meta-qualification",
        )
    except ValueError:
        return controller.snapshot() == before
    return False


def _wrong_bridge_has_no_scheduler_effect(
    real: dict[str, Any],
    result_digest: str,
    profile: str,
) -> bool:
    domain_contracts, bridge_contract = _contracts(real, result_digest)
    scheduler = GlobalWinScheduler(v4.portfolio(profile))
    bus = GlobalFlashBus(
        domain_contracts=domain_contracts,
        bridge_contract=bridge_contract,
    )
    controller = FlashWinController(
        bus=bus,
        scheduler=scheduler,
        scheduler_authority_snapshot=SCHEDULER_AUTHORITY,
        scheduler_verifier_id=SCHEDULER_VERIFIER,
    )
    event = EvidenceEvent(
        event_id="negative-control:real-meta-event",
        domain="realitygraph",
        consequence_kind="compiled-meta-capability",
        consequence_key="verified_state_compilation",
        authority_snapshot=f"real-flash-v2:{result_digest}",
        verifier_id="real-multidomain-v2-gates",
        provenance="negative-control",
    )
    controller.admit_event(
        event,
        source_opportunity_id="flash-meta-qualification",
    )
    before = scheduler.metrics()
    wrong = BridgeCertificate(
        bridge_id="negative-control:wrong-key",
        source_domain="realitygraph",
        source_kind="compiled-meta-capability",
        source_key="different-capability",
        destination_domain="arc",
        destination_kind="settled-protocol-residual",
        destination_key="res:arc:should-reuse-verified-state",
        bridge_authority_snapshot=f"real-flash-v2:{result_digest}",
        bridge_verifier_id=BRIDGE_VERIFIER,
        certificate_id="negative-control:wrong-key",
    )
    deltas = controller.admit_bridge(wrong)
    after = scheduler.metrics()
    return deltas == () and before == after


def _add_typed_local_evidence(
    controller: FlashWinController,
    real: dict[str, Any],
) -> dict[str, float]:
    lean_saved = float(
        real["cross_domain_result"]["lean_authority"]["saved_verifier_calls"]
    )
    gpu_row = _evidence_for_domain(real, "gpu-ir")
    gpu_metrics = _metric_map(gpu_row)
    gpu_saved = float(gpu_metrics["cold_search"]) - float(
        gpu_metrics["warm_search"]
    )

    # These are local measurements with different units. They are admitted to
    # the bus for accounting/provenance, but have no bridge and therefore cannot
    # mutate another domain's scheduler state.
    for event in (
        EvidenceEvent(
            event_id="local:lean-restart-savings",
            domain="lean-kernel",
            consequence_kind="measured-local-savings",
            consequence_key="restartable-negative-reuse",
            authority_snapshot="real-flash-v2-supported:lean-kernel",
            verifier_id="destination-authority:lean-kernel",
            provenance=(
                real["cross_domain_result"]["lean_authority"].get(
                    "artifact_digest",
                    "real-multidomain-v2",
                )
            ),
            avoided_cost=TypedCost("lean.verifier_calls", lean_saved),
        ),
        EvidenceEvent(
            event_id="local:gpu-ir-search-savings",
            domain="gpu-ir",
            consequence_kind="measured-local-savings",
            consequence_key="verified-developmental-optimization",
            authority_snapshot="real-flash-v2-supported:gpu-ir",
            verifier_id="destination-authority:gpu-ir",
            provenance=gpu_row["source_ref"],
            avoided_cost=TypedCost("gpu-ir.search_candidates", gpu_saved),
        ),
    ):
        delta = controller.admit_event(event)
        if delta.scheduler_deltas or delta.applied_effect_ids:
            raise AssertionError("local typed measurement mutated global scheduler")

    return controller.bus.avoided_costs_by_unit()


def run_profile(
    profile: str,
    real: dict[str, Any],
    result_digest: str,
) -> dict[str, Any]:
    scheduler = GlobalWinScheduler(v4.portfolio(profile))
    domain_contracts, bridge_contract = _contracts(real, result_digest)
    bus = GlobalFlashBus(
        domain_contracts=domain_contracts,
        bridge_contract=bridge_contract,
    )
    bridges, effects = _bridge_and_effect_rows(real, result_digest)
    controller = FlashWinController(
        bus=bus,
        scheduler=scheduler,
        scheduler_authority_snapshot=SCHEDULER_AUTHORITY,
        scheduler_verifier_id=SCHEDULER_VERIFIER,
        effects=effects,
    )

    for bridge in bridges:
        if controller.admit_bridge(bridge):
            raise AssertionError("bridge materialized before source event existed")

    battle_before = _rank(controller, mode="BATTLE", pressure=0.80)
    discovery_before = _rank(controller, mode="DISCOVERY", pressure=0.0)

    real_event = EvidenceEvent(
        event_id=f"real-meta:{result_digest[:20]}",
        domain="realitygraph",
        consequence_kind="compiled-meta-capability",
        consequence_key="verified_state_compilation",
        authority_snapshot=f"real-flash-v2:{result_digest}",
        verifier_id="real-multidomain-v2-gates",
        provenance=result_digest,
        avoided_cost=TypedCost("protocol_search_units", 500.0),
    )
    delta = controller.admit_event(
        real_event,
        source_opportunity_id="flash-meta-qualification",
    )

    battle_after = _rank(controller, mode="BATTLE", pressure=0.80)
    discovery_after = _rank(controller, mode="DISCOVERY", pressure=0.0)
    typed_costs = _add_typed_local_evidence(controller, real)

    scalar_rejected = False
    try:
        controller.bus.scalar_avoided_cost()
    except ValueError:
        scalar_rejected = True

    snapshot = controller.snapshot()
    scheduler_metrics = snapshot["scheduler"]
    open_ids = set(scheduler_metrics["open"])
    authority_ids = {
        *v4.SETTLED_PROTOCOL_OPPORTUNITIES.keys(),
        "gpu-hardware-authority",
    }
    open_authority = sorted(open_ids & authority_ids)

    expected_cancelled = set(v4.SETTLED_PROTOCOL_OPPORTUNITIES)
    actual_cancelled = set(scheduler_metrics["cancelled"])

    gates = {
        "four_real_cross_domain_edges_materialized": (
            len(delta.bus_edges) == 4
            and len(controller.bus.cross_domain_edges()) == 4
        ),
        "four_scheduler_effects_applied": (
            len(delta.applied_effect_ids) == 4
            and len(controller.applied_effect_ids) == 4
        ),
        "real_settled_protocol_work_cancelled": (
            actual_cancelled == expected_cancelled
        ),
        "measured_protocol_search_removed_is_500": (
            abs(
                float(scheduler_metrics["total_future_search_removed"])
                - 500.0
            )
            < 1e-9
        ),
        "gpu_hardware_is_only_open_authority_acquisition": (
            open_authority == ["gpu-hardware-authority"]
        ),
        "lean_direct_remains_battle_first": (
            battle_after[0] == "lean-kernel"
        ),
        "portfolio_reclosed_after_global_event": (
            battle_before != battle_after
            and not (expected_cancelled & set(battle_after))
        ),
        "local_measurements_do_not_mutate_foreign_scheduler_state": (
            typed_costs.get("lean.verifier_calls") == 8.0
            and typed_costs.get("gpu-ir.search_candidates") == 96.0
        ),
        "heterogeneous_costs_cannot_be_silently_scalarized": scalar_rejected,
        "wrong_bridge_has_no_scheduler_effect": (
            _wrong_bridge_has_no_scheduler_effect(
                real,
                result_digest,
                profile,
            )
        ),
    }

    return {
        "profile": profile,
        "battle_before": battle_before,
        "battle_after": battle_after,
        "discovery_before": discovery_before,
        "discovery_after": discovery_after,
        "controller_delta": {
            "source_event_id": delta.source_event_id,
            "affected_domains": list(delta.bus_affected_domains),
            "edge_count": len(delta.bus_edges),
            "scheduler_delta_count": len(delta.scheduler_deltas),
            "applied_effect_ids": list(delta.applied_effect_ids),
        },
        "typed_avoided_costs": typed_costs,
        "open_authority_opportunities": open_authority,
        "controller_snapshot": snapshot,
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-result", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    real_path = Path(args.real_result)
    real = _load(real_path)
    result_digest = _digest(real_path)

    if real.get("verdict") != "PASS" or not all(real.get("gates", {}).values()):
        raise AssertionError("real multidomain V2 prerequisite is not green")

    bad_control = _bad_authority_rejected_without_mutation(
        FlashWinController(
            bus=GlobalFlashBus(
                domain_contracts=_contracts(real, result_digest)[0],
                bridge_contract=_contracts(real, result_digest)[1],
            ),
            scheduler=GlobalWinScheduler(v4.portfolio("neutral")),
            scheduler_authority_snapshot=SCHEDULER_AUTHORITY,
            scheduler_verifier_id=SCHEDULER_VERIFIER,
        ),
        result_digest,
    )

    profiles = {
        profile: run_profile(profile, real, result_digest)
        for profile in v4.PROFILES
    }
    all_gates = {
        f"{profile}:{gate}": passed
        for profile, row in profiles.items()
        for gate, passed in row["gates"].items()
    }
    all_gates["global:bad_authority_rejected_without_mutation"] = bad_control

    result = {
        "schema": "qckn-live-win-portfolio-v5",
        "passed": all(all_gates.values()),
        "real_result_sha256": result_digest,
        "supporting_domains": real["cross_domain_result"][
            "genuine_meta_flash"
        ]["supporting_domains"],
        "open_real_residuals": real["cross_domain_result"]["still_unresolved"],
        "profiles": profiles,
        "gates": all_gates,
        "claim_boundary": (
            "This gate joins the real four-domain Flash closure to the frozen "
            "authority-gated bus, bridge, controller and win scheduler. The "
            "500-unit protocol-search cancellation comes from the real V2 graph. "
            "Lean verifier calls and GPU-IR search candidates remain separately "
            "typed and are never added without a conversion contract. Ranking "
            "probabilities and direct-win magnitudes remain operator priors."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "passed": result["passed"],
                "supporting_domains": result["supporting_domains"],
                "open_real_residuals": result["open_real_residuals"],
                "profiles": {
                    profile: {
                        "battle_before": row["battle_before"],
                        "battle_after": row["battle_after"],
                        "discovery_after": row["discovery_after"],
                        "typed_avoided_costs": row["typed_avoided_costs"],
                        "open_authority": row[
                            "open_authority_opportunities"
                        ],
                        "edge_count": row["controller_delta"]["edge_count"],
                        "applied_effect_count": len(
                            row["controller_delta"]["applied_effect_ids"]
                        ),
                        "gates": row["gates"],
                    }
                    for profile, row in profiles.items()
                },
                "claim_boundary": result["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(
        "PASS_QCKN_LIVE_WIN_PORTFOLIO_V5"
        if result["passed"]
        else "FAIL_QCKN_LIVE_WIN_PORTFOLIO_V5"
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
