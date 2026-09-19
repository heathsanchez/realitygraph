from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from realitygraph.flash_contract import (
    CapabilityState,
    DependencyRule,
    FlashEvent,
    FlashEventKind,
    FrontierState,
    IncrementalFlashRuntime,
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def validate_inputs(
    v3: dict[str, Any],
    live: dict[str, Any],
    string_cache: dict[str, Any],
    identity_cache: dict[str, Any],
) -> None:
    if v3.get("schema") != "qckn-real-multidomain-flash-v3":
        raise AssertionError("unexpected real Flash V3 schema")
    if v3.get("verdict") != "PASS" or not all(v3.get("gates", {}).values()):
        raise AssertionError("real Flash V3 is not green")
    if any(row.get("status") != "SETTLED" for row in v3.get("residuals", {}).values()):
        raise AssertionError("declared V3 authority residual reopened")

    summary = live.get("summary", {})
    required_events = {
        "arc3:ft09-vc33-transfer-refutation:v2",
        "collatz:bank-order-redundancy:v1",
        "sair:residual12-portfolio:v1",
    }
    if not required_events <= set(summary.get("event_ids", [])):
        raise AssertionError("required live cross-repo event disappeared")

    if string_cache.get("schema") != "localdef-whnf-context-cache-v1":
        raise AssertionError("unexpected string cache evidence")
    if identity_cache.get("schema") != "localdef-whnf-identity-triple-cache-v1":
        raise AssertionError("unexpected identity cache evidence")
    if not all(string_cache.get("gates", {}).values()):
        raise AssertionError("string cache semantic gate failed")
    if not all(identity_cache.get("gates", {}).values()):
        raise AssertionError("identity cache semantic gate failed")


def classify_lean_capabilities(
    string_cache: dict[str, Any],
    identity_cache: dict[str, Any],
) -> tuple[CapabilityState, CapabilityState, dict[str, Any]]:
    string_rows = string_cache["rows"]
    cold_string = sum(int(r["arms"]["cold"]["elapsed_ms"]) for r in string_rows)
    warm_string = sum(int(r["arms"]["warm"]["elapsed_ms"]) for r in string_rows)

    comparison = identity_cache["comparison"]
    cold_fast = int(comparison["cold_elapsed_ms"])
    warm_fast = int(comparison["fast_elapsed_ms"])
    string_fast_baseline = int(comparison["string_elapsed_ms"])

    string_cap = CapabilityState(
        capability_id="lean:localdef-whnf-string-context-cache:v1",
        semantic_status="VERIFIED",
        economic_status="RESERVE",
        evidence_id="run:35420366767/artifact:10576707760",
        reason=(
            f"semantic reuse verified, but warm wall time {warm_string} ms "
            f"exceeds cold {cold_string} ms"
        ),
    )
    identity_cap = CapabilityState(
        capability_id="lean:localdef-whnf-identity-triple-cache:v1",
        semantic_status="VERIFIED",
        economic_status="RESERVE" if warm_fast >= cold_fast else "ACTIVE",
        evidence_id="run:35421374389/artifact:10576888578",
        reason=(
            f"identity key improves on string key {string_fast_baseline}->{warm_fast} ms, "
            f"but declared incumbent is cold {cold_fast} ms"
        ),
    )
    metrics = {
        "string_cache": {
            "cold_elapsed_ms": cold_string,
            "warm_elapsed_ms": warm_string,
            "ratio_vs_cold": warm_string / cold_string,
        },
        "identity_triple_cache": {
            "cold_elapsed_ms": cold_fast,
            "fast_elapsed_ms": warm_fast,
            "string_elapsed_ms": string_fast_baseline,
            "ratio_vs_cold": warm_fast / cold_fast,
            "improvement_vs_string": 1.0 - warm_fast / string_fast_baseline,
            "fast_hits": int(comparison["fast_hits"]),
            "restart_fast_hits": int(comparison["restart_fast_hits"]),
        },
    }
    return string_cap, identity_cap, metrics


def make_runtime(
    string_cap: CapabilityState,
    identity_cap: CapabilityState,
) -> IncrementalFlashRuntime:
    frontiers = (
        FrontierState(
            "frontier:sair",
            "sair",
            base_search_cost=100,
            search_cost=100,
            route_ids={"route:sair-residual12-reacquire"},
            base_route_ids={"route:sair-residual12-reacquire"},
            reserve_capabilities={"sair:residual12-portfolio:v1"},
        ),
        FrontierState(
            "frontier:arc",
            "arc",
            base_search_cost=80,
            search_cost=80,
            route_ids={"route:arc-ft09-vc33-repeat"},
            base_route_ids={"route:arc-ft09-vc33-repeat"},
        ),
        FrontierState(
            "frontier:lean",
            "lean-kernel",
            base_search_cost=120,
            search_cost=120,
            route_ids={"route:lean-resource-only", "route:lean-cache-next"},
            base_route_ids={"route:lean-resource-only", "route:lean-cache-next"},
        ),
        FrontierState(
            "frontier:collatz",
            "collatz",
            base_search_cost=150,
            search_cost=150,
            route_ids={"route:collatz-bank-order-repeat"},
            base_route_ids={"route:collatz-bank-order-repeat"},
        ),
        FrontierState(
            "frontier:gpu-ir",
            "gpu-ir",
            base_search_cost=60,
            search_cost=60,
            route_ids={"route:gpu-ir-reacquire"},
            base_route_ids={"route:gpu-ir-reacquire"},
        ),
        FrontierState(
            "frontier:flash-platform",
            "realitygraph",
            base_search_cost=40,
            search_cost=40,
            route_ids={"route:flash-platform-next"},
            base_route_ids={"route:flash-platform-next"},
        ),
    )

    caps = (
        CapabilityState(
            "sair:residual12-portfolio:v1",
            "VERIFIED",
            "ACTIVE",
            "live-router:current",
            "real live capability retained by current cross-repo router",
        ),
        string_cap,
        identity_cap,
    )

    rules = (
        # Cross-frontier propagation of the already-qualified four-domain
        # verified-state-compilation meta capability.
        DependencyRule(
            "meta->sair",
            "verified_state_compilation",
            "frontier:sair",
            "reduce_search",
            25,
        ),
        DependencyRule(
            "meta->arc",
            "verified_state_compilation",
            "frontier:arc",
            "reduce_search",
            20,
        ),
        DependencyRule(
            "meta->lean",
            "verified_state_compilation",
            "frontier:lean",
            "reduce_search",
            30,
        ),
        DependencyRule(
            "meta->gpu",
            "verified_state_compilation",
            "frontier:gpu-ir",
            "reduce_search",
            15,
        ),
        # Negative propagation from exact current obstructions.
        DependencyRule(
            "arc-refutation",
            "arc_ft09_vc33_repeat_refuted",
            "frontier:arc",
            "remove_route",
            "route:arc-ft09-vc33-repeat",
        ),
        DependencyRule(
            "arc-obstruction",
            "arc_ft09_vc33_repeat_refuted",
            "frontier:arc",
            "add_obstruction",
            "arc3:ft09-vc33-transfer-refutation:v2",
        ),
        DependencyRule(
            "collatz-refutation",
            "collatz_bank_order_repeat_refuted",
            "frontier:collatz",
            "remove_route",
            "route:collatz-bank-order-repeat",
        ),
        DependencyRule(
            "collatz-obstruction",
            "collatz_bank_order_repeat_refuted",
            "frontier:collatz",
            "add_obstruction",
            "collatz:bank-order-redundancy:v1",
        ),
        # Controlled conformance replay for dormant capability revival using a
        # real capability identity. This is a runtime invariant, not a claim
        # about the historical event that originally activated it.
        DependencyRule(
            "sair-revive",
            "sair_residual12_relevant_again",
            "frontier:sair",
            "activate_capability",
            "sair:residual12-portfolio:v1",
        ),
        # Semantic promotion is distinct from economic promotion. Both localdef
        # caches are currently reserve under measured wall-time preference.
        DependencyRule(
            "lean-string-reserve",
            "lean_string_cache_semantic_verified",
            "frontier:lean",
            "reserve_capability",
            "lean:localdef-whnf-string-context-cache:v1",
        ),
        DependencyRule(
            "lean-identity-reserve",
            "lean_identity_cache_semantic_verified",
            "frontier:lean",
            "activate_capability",
            "lean:localdef-whnf-identity-triple-cache:v1",
        ),
    )
    return IncrementalFlashRuntime(frontiers, rules, caps)


def event(
    event_id: str,
    kind: FlashEventKind,
    domain: str,
    key: str,
    *provenance: str,
) -> FlashEvent:
    return FlashEvent(
        event_id=event_id,
        kind=kind,
        source_domain=domain,
        consequence_key=key,
        authority="qckn-live-developmental-substrate-v2",
        provenance=tuple(provenance),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--v3-result", required=True)
    p.add_argument("--live-cycle", required=True)
    p.add_argument("--string-cache", required=True)
    p.add_argument("--identity-cache", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    v3 = load(Path(args.v3_result))
    live = load(Path(args.live_cycle))
    string_cache = load(Path(args.string_cache))
    identity_cache = load(Path(args.identity_cache))
    validate_inputs(v3, live, string_cache, identity_cache)

    string_cap, identity_cap, promotion_metrics = classify_lean_capabilities(
        string_cache, identity_cache
    )
    runtime = make_runtime(string_cap, identity_cap)

    initial = runtime.snapshot()

    # 1. Cross-frontier propagation.
    meta_event = event(
        "episode:verified-state-compilation",
        FlashEventKind.PROMOTED_CAPABILITY,
        "developmental",
        "verified_state_compilation",
        "real-flash-v3:four-domain-meta-capability",
    )
    meta_delta = runtime.admit(meta_event)
    after_meta = runtime.snapshot()

    # 2. Dormant-capability revival.
    revival_event = event(
        "episode:sair-residual12-relevant-again",
        FlashEventKind.VERIFIED_SEPARATOR,
        "sair",
        "sair_residual12_relevant_again",
        "controlled-replay",
        "live-capability:sair:residual12-portfolio:v1",
    )
    revival_delta = runtime.admit(revival_event)

    # 3. Negative propagation.
    arc_event = event(
        "episode:arc-exact-refutation",
        FlashEventKind.OBSTRUCTION,
        "arc",
        "arc_ft09_vc33_repeat_refuted",
        "arc3:ft09-vc33-transfer-refutation:v2",
    )
    collatz_event = event(
        "episode:collatz-exact-obstruction",
        FlashEventKind.OBSTRUCTION,
        "collatz",
        "collatz_bank_order_repeat_refuted",
        "collatz:bank-order-redundancy:v1",
    )
    arc_delta = runtime.admit(arc_event)
    collatz_delta = runtime.admit(collatz_event)

    # Semantic/economic separation from measured Lean evidence.
    runtime.admit(
        event(
            "episode:lean-string-cache-semantic",
            FlashEventKind.PROMOTED_CAPABILITY,
            "lean-kernel",
            "lean_string_cache_semantic_verified",
            string_cap.evidence_id,
        )
    )
    runtime.admit(
        event(
            "episode:lean-identity-cache-semantic",
            FlashEventKind.PREFERENCE_CHANGE,
            "lean-kernel",
            "lean_identity_cache_semantic_verified",
            identity_cap.evidence_id,
        )
    )
    after_events = runtime.snapshot()

    # Idempotent fixed-point check.
    duplicate_delta = runtime.admit(meta_event)

    # 4/5. Incrementality + revocation.
    pre_revoke = runtime.snapshot()
    revoke_delta = runtime.revoke(
        arc_event.event_id,
        reason="Flash V1 revocation conformance test",
    )
    after_revoke = runtime.snapshot()

    # Re-admit exact warranted obstruction to compile the present again.
    reclose_delta = runtime.admit(arc_event)
    compiled = runtime.snapshot()

    # 6. Restart benefit: persist compiled present and reload without replay.
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "compiled-present.json"
    runtime.save_compiled_present(state_path)
    restarted = IncrementalFlashRuntime.load_compiled_present(
        state_path,
        runtime.rules,
    )
    restarted_snapshot = restarted.snapshot()

    frontiers = compiled["frontiers"]
    restarted_frontiers = restarted_snapshot["frontiers"]

    string_economic_reserve = (
        string_cap.semantic_status == "VERIFIED"
        and string_cap.economic_status == "RESERVE"
    )
    identity_economic_reserve = (
        identity_cap.semantic_status == "VERIFIED"
        and identity_cap.economic_status == "RESERVE"
    )

    gates = {
        "cross_frontier_propagation": (
            set(meta_delta.changed_frontiers)
            == {
                "frontier:sair",
                "frontier:arc",
                "frontier:lean",
                "frontier:gpu-ir",
            }
            and frontiers["frontier:flash-platform"]["search_cost"] == 40
            and frontiers["frontier:collatz"]["search_cost"] == 150
        ),
        "dormant_capability_revival": (
            "sair:residual12-portfolio:v1"
            in frontiers["frontier:sair"]["active_capabilities"]
            and "frontier:sair" in revival_delta.changed_frontiers
        ),
        "negative_propagation": (
            "route:arc-ft09-vc33-repeat"
            not in frontiers["frontier:arc"]["route_ids"]
            and "route:collatz-bank-order-repeat"
            not in frontiers["frontier:collatz"]["route_ids"]
            and "arc3:ft09-vc33-transfer-refutation:v2"
            in frontiers["frontier:arc"]["obstructions"]
            and "collatz:bank-order-redundancy:v1"
            in frontiers["frontier:collatz"]["obstructions"]
        ),
        "incrementality_dependency_cone_only": (
            set(arc_delta.touched_frontiers) == {"frontier:arc"}
            and set(collatz_delta.touched_frontiers) == {"frontier:collatz"}
            and "frontier:flash-platform" not in meta_delta.touched_frontiers
        ),
        "revocation_restores_search": (
            "route:arc-ft09-vc33-repeat"
            in after_revoke["frontiers"]["frontier:arc"]["route_ids"]
            and "route:collatz-bank-order-repeat"
            not in after_revoke["frontiers"]["frontier:collatz"]["route_ids"]
            and set(revoke_delta.touched_frontiers) == {"frontier:arc"}
            and "frontier:arc" in reclose_delta.changed_frontiers
        ),
        "restart_recovers_compiled_present_without_history_replay": (
            restarted.replayed_events_on_restart == 0
            and restarted_frontiers == frontiers
            and restarted_snapshot["active_event_ids"] == compiled["active_event_ids"]
        ),
        "event_admission_is_idempotent_at_fixed_point": (
            duplicate_delta.iterations == 0
            and not duplicate_delta.touched_frontiers
            and not duplicate_delta.changed_frontiers
        ),
        "semantic_and_economic_promotion_separated": (
            string_economic_reserve
            and identity_economic_reserve
            and "lean:localdef-whnf-string-context-cache:v1"
            in frontiers["frontier:lean"]["reserve_capabilities"]
            and "lean:localdef-whnf-identity-triple-cache:v1"
            in frontiers["frontier:lean"]["reserve_capabilities"]
            and "lean:localdef-whnf-identity-triple-cache:v1"
            not in frontiers["frontier:lean"]["active_capabilities"]
        ),
    }

    result = {
        "schema": "qckn-flash-six-invariant-gate-v1",
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "architecture_basis": {
            "typed_event_kinds": [x.value for x in FlashEventKind],
            "implementation_requirements": [
                "cross-frontier propagation",
                "dormant-capability revival",
                "negative propagation",
                "incrementality",
                "revocation",
                "restart benefit",
            ],
        },
        "prospective_episode": {
            "frozen_frontiers": sorted(initial["frontiers"]),
            "frozen_rule_ids": sorted(r.rule_id for r in runtime.rules),
            "meta_delta": {
                "touched": list(meta_delta.touched_frontiers),
                "changed": list(meta_delta.changed_frontiers),
            },
            "revocation_delta": {
                "touched": list(revoke_delta.touched_frontiers),
                "changed": list(revoke_delta.changed_frontiers),
            },
        },
        "promotion_economics": promotion_metrics,
        "capability_states": {
            string_cap.capability_id: {
                "semantic_status": string_cap.semantic_status,
                "economic_status": string_cap.economic_status,
                "reason": string_cap.reason,
            },
            identity_cap.capability_id: {
                "semantic_status": identity_cap.semantic_status,
                "economic_status": identity_cap.economic_status,
                "reason": identity_cap.reason,
            },
        },
        "gates": gates,
        "compiled_present": compiled,
        "restart_snapshot": restarted_snapshot,
        "claim_boundary": (
            "Hard conformance gate for the six Flash V1 implementation requirements using "
            "the current authority-closed V3 graph, current live cross-repo obstruction/"
            "capability identities, and measured Lean cache evidence. Cross-frontier "
            "dependency rules are prospectively frozen in this experiment. The dormant-"
            "capability revival arm is a controlled runtime conformance replay using a real "
            "capability identity, not a claim about its historical discovery sequence. "
            "Scheduler costs in this finite episode are typed test units, not commensurate "
            "measurements across domains. Semantic verification never implies economic "
            "promotion without a declared preference win."
        ),
    }
    (out / "six-invariant-gate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "gates": gates,
                "promotion_economics": promotion_metrics,
                "claim_boundary": result["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    for name, ok in gates.items():
        print(("PASS_" if ok else "FAIL_") + name.upper())
    print(
        "PASS_QCKN_FLASH_SIX_INVARIANT_GATE_V1"
        if result["verdict"] == "PASS"
        else "FAIL_QCKN_FLASH_SIX_INVARIANT_GATE_V1"
    )
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
