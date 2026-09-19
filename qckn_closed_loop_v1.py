from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import qckn_live_win_portfolio_v4 as v4
from realitygraph.flash_bus import (
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
    TypedCost,
)
from realitygraph.win_controller import FlashWinController
from realitygraph.win_scheduler import GlobalWinScheduler


LEAN_REPO = "heathsanchez/lean-kernel-arena"
LEAN_REF = "a449228f46dcef2bb30a8de73d84a4f4d3f8a3d5"
LEAN_EXPERIMENT = "lean-seven-unknown-resource-sweep-v1"
LEAN_EVIDENCE = "genesis/evidence/seven-unknown-resource-sweep-v1.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def consensus_top(portfolio: dict[str, Any]) -> str:
    profiles = portfolio.get("profiles", {})
    tops = {
        name: row["battle_after"][0]
        for name, row in profiles.items()
    }
    if not tops or len(set(tops.values())) != 1:
        raise AssertionError(f"no consensus next target: {tops}")
    return next(iter(tops.values()))


def select(portfolio_path: Path, out_path: Path) -> dict[str, Any]:
    portfolio = load_json(portfolio_path)
    if portfolio.get("passed") is not True:
        raise AssertionError("V5 portfolio prerequisite is not green")
    top = consensus_top(portfolio)
    if top != "lean-kernel":
        raise AssertionError(
            f"closed-loop executable registry has no mapping for selected target {top}"
        )

    launch = {
        "schema": "qckn-closed-loop-launch-v1",
        "selected_opportunity": top,
        "selection_basis": {
            "portfolio_schema": portfolio.get("schema"),
            "consensus_profiles": sorted(portfolio["profiles"]),
            "all_profiles_battle_first": top,
        },
        "experiment": {
            "experiment_id": LEAN_EXPERIMENT,
            "repository": LEAN_REPO,
            "ref": LEAN_REF,
            "evidence_path": LEAN_EVIDENCE,
            "authority": "current-public-arena-corpus",
            "claim_boundary": (
                "Diagnostic resource-envelope sweep only; no kernel semantics "
                "change and no Arena promotion is implied by launch."
            ),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(launch, indent=2, sort_keys=True) + "\n")
    print("CLOSED_LOOP_SELECTED=" + top)
    print("CLOSED_LOOP_EXPERIMENT=" + LEAN_EXPERIMENT)
    return launch


def validate_lean_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence.get("schema") != "lean-seven-unknown-resource-sweep-v1":
        raise AssertionError("unexpected Lean evidence schema")
    gates = evidence.get("gates", {})
    if not gates or not all(gates.values()):
        raise AssertionError(f"Lean experiment gates failed: {gates}")
    results = evidence.get("results", [])
    if len(results) != 7:
        raise AssertionError("Lean experiment did not cover exactly seven residuals")
    if not all(
        row.get("attempts")
        and row["attempts"][0].get("status") == "UNKNOWN"
        for row in results
    ):
        raise AssertionError("Lean baseline no longer reproduces the seven UNKNOWNs")

    latent = evidence.get("latent_wrong_rejects", [])
    open_rows = evidence.get("still_open", [])
    if evidence.get("closed_count") != 0:
        raise AssertionError("resource sweep unexpectedly closed a residual")
    if len(latent) != 2 or len(open_rows) != 5:
        raise AssertionError(
            "expected two latent wrong rejects and five persistent UNKNOWNs"
        )
    if not all(
        row["first_reject"].get("reason") == "rigid-head-mismatch"
        for row in latent
    ):
        raise AssertionError("latent wrong separator changed")

    return {
        "closed_count": int(evidence["closed_count"]),
        "persistent_unknown_count": int(evidence["still_open_count"]),
        "latent_wrong_reject_count": int(evidence["latent_wrong_reject_count"]),
        "persistent_unknowns": list(open_rows),
        "latent_wrong_rejects": [
            {
                "name": row["name"],
                "config": row["first_reject"]["config"],
                "budget": row["first_reject"]["budget"],
                "reason": row["first_reject"]["reason"],
                "steps": row["first_reject"]["steps"],
            }
            for row in latent
        ],
    }


def local_residual_queue(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    latent_by_family: dict[str, int] = {}
    for row in evidence.get("latent_wrong_rejects", []):
        name = row["name"]
        family = (
            "deep-list"
            if "magma-list-deep" in name
            else "pair-countermodel"
            if "magma-list-pair" in name
            else "host-stack"
            if name in {"init-prelude.ndjson", "perf/grind-ring-5.ndjson"}
            else "fueled-chain"
        )
        latent_by_family[family] = latent_by_family.get(family, 0) + 1

    open_by_family: dict[str, int] = {}
    for name in evidence.get("still_open", []):
        family = (
            "deep-list"
            if "magma-list-deep" in name
            else "pair-countermodel"
            if "magma-list-pair" in name
            else "host-stack"
            if name in {"init-prelude.ndjson", "perf/grind-ring-5.ndjson"}
            else "fueled-chain"
        )
        open_by_family[family] = open_by_family.get(family, 0) + 1

    families = sorted(set(latent_by_family) | set(open_by_family))
    rows = []
    for family in families:
        wrong = latent_by_family.get(family, 0)
        still_open = open_by_family.get(family, 0)
        kind = (
            "semantic-correctness-obstruction"
            if wrong
            else "persistent-resource-frontier"
        )
        rows.append(
            {
                "residual_id": f"lean:{family}",
                "family": family,
                "kind": kind,
                "latent_wrong_rejects": wrong,
                "persistent_unknowns": still_open,
                "priority_key": [int(wrong > 0), wrong, still_open],
            }
        )
    rows.sort(
        key=lambda row: (
            row["priority_key"][0],
            row["priority_key"][1],
            row["priority_key"][2],
            row["residual_id"],
        ),
        reverse=True,
    )
    return rows


def post_flash_portfolio(profile: str) -> tuple[Any, ...]:
    settled = set(v4.SETTLED_PROTOCOL_OPPORTUNITIES)
    return tuple(
        row
        for row in v4.portfolio(profile)
        if row.opportunity_id not in settled
        and row.opportunity_id != "flash-meta-qualification"
    )


def rerank_without_foreign_mutation(
    portfolio_result: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for profile in sorted(portfolio_result["profiles"]):
        scheduler = GlobalWinScheduler(post_flash_portfolio(profile))
        bus = GlobalFlashBus(
            domain_contracts=(
                DomainContract(
                    "lean-kernel",
                    f"{LEAN_EXPERIMENT}:{LEAN_REF}",
                    "lean-resource-sweep-gates-v1",
                ),
                DomainContract(
                    "realitygraph",
                    "qckn-live-win-portfolio-v6",
                    "closed-loop-controller-v1",
                ),
            ),
            bridge_contract=DomainContract(
                "bridge",
                "qckn-live-win-portfolio-v6",
                "closed-loop-bridge-verifier-v1",
            ),
        )
        controller = FlashWinController(
            bus=bus,
            scheduler=scheduler,
            scheduler_authority_snapshot="qckn-live-win-portfolio-v6",
            scheduler_verifier_id="closed-loop-scheduler-verifier-v1",
        )
        before = [
            row.opportunity_id
            for row in controller.rank(mode="BATTLE", deadline_pressure=0.80)
        ]

        event = EvidenceEvent(
            event_id=f"{LEAN_EXPERIMENT}:{profile}",
            domain="lean-kernel",
            consequence_kind="diagnostic-obstruction",
            consequence_key="resource-scaling-does-not-close-seven-unknowns",
            authority_snapshot=f"{LEAN_EXPERIMENT}:{LEAN_REF}",
            verifier_id="lean-resource-sweep-gates-v1",
            provenance=(
                "selected-by-qckn-live-win-portfolio-v5;"
                f"closed={evidence['closed_count']};"
                f"latent-wrong={evidence['latent_wrong_reject_count']};"
                f"open={evidence['still_open_count']}"
            ),
            avoided_cost=TypedCost(
                "lean.invalid_resource_only_strategy_families",
                1.0,
            ),
        )
        delta = controller.admit_event(event)
        after = [
            row.opportunity_id
            for row in controller.rank(mode="BATTLE", deadline_pressure=0.80)
        ]
        profiles[profile] = {
            "battle_before": before,
            "battle_after": after,
            "event_affected_domains": list(delta.bus_affected_domains),
            "cross_domain_edges": len(delta.bus_edges),
            "scheduler_deltas": len(delta.scheduler_deltas),
            "typed_avoided_costs": bus.avoided_costs_by_unit(),
            "ranking_unchanged": before == after,
        }
    return profiles


def ingest(
    portfolio_path: Path,
    launch_path: Path,
    evidence_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    portfolio = load_json(portfolio_path)
    launch = load_json(launch_path)
    evidence = load_json(evidence_path)

    if portfolio.get("passed") is not True:
        raise AssertionError("portfolio prerequisite is not green")
    if launch.get("selected_opportunity") != "lean-kernel":
        raise AssertionError("launch no longer maps to Lean")
    if launch["experiment"]["ref"] != LEAN_REF:
        raise AssertionError("Lean launch ref drifted")

    evidence_summary = validate_lean_evidence(evidence)
    queue = local_residual_queue(evidence)
    if not queue or queue[0]["family"] != "deep-list":
        raise AssertionError(f"unexpected next local residual queue: {queue}")

    profiles = rerank_without_foreign_mutation(portfolio, evidence)

    gates = {
        "selected_experiment_matches_market_winner": (
            consensus_top(portfolio) == launch["selected_opportunity"]
        ),
        "experiment_authority_green": all(evidence["gates"].values()),
        "resource_scaling_closed_zero_of_seven": evidence["closed_count"] == 0,
        "two_latent_wrong_rejects_typed": (
            evidence["latent_wrong_reject_count"] == 2
        ),
        "five_resource_unknowns_remain": evidence["still_open_count"] == 5,
        "next_local_residual_is_semantic_deep_list": (
            queue[0]["family"] == "deep-list"
            and queue[0]["kind"] == "semantic-correctness-obstruction"
            and queue[0]["latent_wrong_rejects"] == 2
        ),
        "local_obstruction_does_not_mutate_foreign_market": all(
            row["cross_domain_edges"] == 0
            and row["scheduler_deltas"] == 0
            and row["ranking_unchanged"]
            for row in profiles.values()
        ),
        "lean_remains_global_battle_first": all(
            row["battle_after"][0] == "lean-kernel"
            for row in profiles.values()
        ),
    }

    result = {
        "schema": "qckn-closed-loop-v1",
        "passed": all(gates.values()),
        "launch": launch,
        "evidence_summary": evidence_summary,
        "local_residual_queue": queue,
        "next_global_opportunity": "lean-kernel",
        "next_local_experiment_class": "deep-list-semantic-repair",
        "market_after_evidence": profiles,
        "gates": gates,
        "claim_boundary": (
            "The selected Lean experiment is an exact diagnostic resource sweep. "
            "It closed no public UNKNOWNs and therefore records no direct Arena win. "
            "It did expose two expected-ACCEPT deep-list cases that become REJECT "
            "under a larger resource envelope, promoting a semantic-correctness "
            "obstruction locally. No bridge certificate exists for this event, so "
            "foreign portfolio state is unchanged."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    print("CLOSED_LOOP_INGESTED=" + LEAN_EXPERIMENT)
    print("CLOSED_LOOP_NEXT_GLOBAL=lean-kernel")
    print("CLOSED_LOOP_NEXT_LOCAL=deep-list-semantic-repair")
    print(
        "PASS_QCKN_CLOSED_LOOP_V1"
        if result["passed"]
        else "FAIL_QCKN_CLOSED_LOOP_V1"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_select = sub.add_parser("select")
    p_select.add_argument("--portfolio-result", required=True)
    p_select.add_argument("--out", required=True)

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--portfolio-result", required=True)
    p_ingest.add_argument("--launch", required=True)
    p_ingest.add_argument("--evidence", required=True)
    p_ingest.add_argument("--out", required=True)

    args = parser.parse_args()
    if args.command == "select":
        select(Path(args.portfolio_result), Path(args.out))
        return 0

    result = ingest(
        Path(args.portfolio_result),
        Path(args.launch),
        Path(args.evidence),
        Path(args.out),
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
