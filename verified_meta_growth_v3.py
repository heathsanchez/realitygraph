from __future__ import annotations

import json
import os
from pathlib import Path

from realitygraph.developmental_types import canonical_digest
from realitygraph.fixtures.meta_growth_v3 import (
    ADD_FINITE_MEMORY_2,
    ADD_OBSERVABLE,
    AUTHORITY,
    FAMILY_C,
    FAMILY_T,
    STRATEGY_VERSION,
    VERIFIER,
    episode_fingerprint,
    frozen_portfolio,
    make_episode,
    make_tie_control,
)
from realitygraph.meta_executor import MetaGrowthRoute, execute_meta_growth
from realitygraph.meta_memory import (
    MetaMemory,
    RepairEpisode,
    RepairPhase,
    RepairRuleStatus,
)
from realitygraph.meta_snapshot import MetaSnapshot
from verified_language_growth_closure_v2 import run_qualification as run_v2_qualification


RESULT_PATH = "verified-meta-growth-v3-summary.json"


def _episode_summary(result) -> dict[str, object]:
    selected = result.selected_generation
    capability_id = None
    object_candidate_search_calls = 0
    object_future_grammar_search_calls = None
    attack_status = None
    if selected is not None:
        if selected.capability is not None:
            capability_id = selected.capability.capability_id
        if selected.growth is not None:
            object_candidate_search_calls = len(selected.growth.verdicts)
        if selected.future is not None:
            object_future_grammar_search_calls = selected.future.grammar_search_calls
        if selected.attack is not None:
            attack_status = selected.attack.status.value
    return {
        "route": result.route.value,
        "fingerprint": None if result.fingerprint is None else result.fingerprint.digest,
        "selected_strategy_id": result.selected_strategy_id,
        "selected_strategy_version": result.selected_strategy_version,
        "capability_id": capability_id,
        "rule_hit": result.rule_hit,
        "matched_rule_id": result.matched_rule_id,
        "portfolio_search_calls": result.portfolio_search_calls,
        "competitor_strategy_calls": result.competitor_strategy_calls,
        "selected_strategy_calls": result.selected_strategy_calls,
        "object_candidate_search_calls": object_candidate_search_calls,
        "object_future_grammar_search_calls": object_future_grammar_search_calls,
        "attack_status": attack_status,
        "episode_digest": result.episode_digest,
        "object_state_digest": result.object_state.digest,
        "meta_memory_digest": result.meta_memory.digest,
    }


def _promoted_rules(memory: MetaMemory) -> list[dict[str, object]]:
    return [
        {
            "rule_id": rule.rule_id,
            "fingerprint": rule.obstruction_fingerprint,
            "strategy_id": rule.strategy_id,
            "strategy_version": rule.strategy_version,
            "portfolio_digest": rule.portfolio_digest,
            "authority_snapshot": rule.authority_snapshot,
            "verifier_id": rule.verifier_id,
            "interface_digest": rule.interface_digest,
            "status": rule.status.value,
            "selection_cost": rule.selection_cost,
            "source_episode_digests": list(rule.source_episode_digests),
            "ablation_handle": rule.ablation_handle,
        }
        for rule in sorted(memory.rules, key=lambda item: item.rule_id)
        if rule.status is RepairRuleStatus.PROMOTED
    ]


def _forged_promoted_memory(
    *,
    fingerprint: str,
    strategy_id: str,
    portfolio_digest: str,
    authority_snapshot: str,
    verifier_id: str,
    interface_digest: str,
) -> MetaMemory:
    memory = MetaMemory.empty()
    for suffix, phase in (
        ("source", RepairPhase.ACQUISITION),
        ("calibration", RepairPhase.CALIBRATION),
    ):
        memory = memory.record_success(
            RepairEpisode(
                episode_id=f"forged-{suffix}",
                phase=phase,
                obstruction_fingerprint=fingerprint,
                strategy_id=strategy_id,
                strategy_version=STRATEGY_VERSION,
                portfolio_digest=portfolio_digest,
                authority_snapshot=authority_snapshot,
                verifier_id=verifier_id,
                interface_digest=interface_digest,
                selection_cost=1,
                object_evidence_digest=f"forged-evidence-{suffix}",
            )
        )
    return memory


def _controls(
    *,
    c_promoted_only_memory: MetaMemory,
    c_future_bundle,
    t_future_bundle,
) -> dict[str, bool]:
    # A promoted C rule cannot choose a T repair. T may still be solved cold;
    # the control is specifically that no promoted rule hit occurs.
    wrong_fp = execute_meta_growth(
        t_future_bundle.state,
        c_promoted_only_memory,
        t_future_bundle.spec,
    )

    c_fingerprint = episode_fingerprint(c_future_bundle).digest
    portfolio = frozen_portfolio()

    stale_authority_memory = _forged_promoted_memory(
        fingerprint=c_fingerprint,
        strategy_id=ADD_OBSERVABLE,
        portfolio_digest=portfolio.digest,
        authority_snapshot=f"{AUTHORITY}-stale",
        verifier_id=VERIFIER,
        interface_digest=c_future_bundle.world.interface_digest,
    )
    stale_authority = execute_meta_growth(
        c_future_bundle.state,
        stale_authority_memory,
        c_future_bundle.spec,
    )

    stale_verifier_memory = _forged_promoted_memory(
        fingerprint=c_fingerprint,
        strategy_id=ADD_OBSERVABLE,
        portfolio_digest=portfolio.digest,
        authority_snapshot=AUTHORITY,
        verifier_id=f"{VERIFIER}-stale",
        interface_digest=c_future_bundle.world.interface_digest,
    )
    stale_verifier = execute_meta_growth(
        c_future_bundle.state,
        stale_verifier_memory,
        c_future_bundle.spec,
    )

    sham_memory = _forged_promoted_memory(
        fingerprint=c_fingerprint,
        strategy_id=ADD_OBSERVABLE,
        portfolio_digest="forged-wrong-portfolio-digest",
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=c_future_bundle.world.interface_digest,
    )
    sham = execute_meta_growth(
        c_future_bundle.state,
        sham_memory,
        c_future_bundle.spec,
    )

    incomplete = make_episode(
        FAMILY_C,
        "partial",
        RepairPhase.CONTROL,
        current_complete=False,
    )
    incomplete_result = execute_meta_growth(
        incomplete.state,
        MetaMemory.empty(),
        incomplete.spec,
    )

    partial_portfolio = make_episode(
        FAMILY_T,
        "budget",
        RepairPhase.CONTROL,
        portfolio_budget=2,
    )
    partial_portfolio_result = execute_meta_growth(
        partial_portfolio.state,
        MetaMemory.empty(),
        partial_portfolio.spec,
    )

    tied = make_tie_control()
    tied_result = execute_meta_growth(tied.state, MetaMemory.empty(), tied.spec)

    return {
        "wrong_fingerprint_rejects_rule": (
            not wrong_fp.rule_hit
            and wrong_fp.portfolio_search_calls > 0
            and wrong_fp.selected_strategy_id == ADD_FINITE_MEMORY_2
        ),
        "stale_authority_rule_rejected": (
            not stale_authority.rule_hit
            and stale_authority.portfolio_search_calls > 0
            and stale_authority.selected_strategy_id == ADD_OBSERVABLE
        ),
        "stale_verifier_rule_rejected": (
            not stale_verifier.rule_hit
            and stale_verifier.portfolio_search_calls > 0
            and stale_verifier.selected_strategy_id == ADD_OBSERVABLE
        ),
        "sham_rule_rejected": (
            not sham.rule_hit
            and sham.portfolio_search_calls > 0
            and sham.selected_strategy_id == ADD_OBSERVABLE
        ),
        "incomplete_obstruction_unknown_search": (
            incomplete_result.route is MetaGrowthRoute.UNKNOWN_SEARCH
            and incomplete_result.portfolio_search_calls == 0
            and incomplete_result.object_state.digest == incomplete.state.digest
        ),
        "partial_portfolio_unknown_search": (
            partial_portfolio_result.route is MetaGrowthRoute.UNKNOWN_SEARCH
            and partial_portfolio_result.object_state.digest == partial_portfolio.state.digest
        ),
        "unknown_choice_preserved": (
            tied_result.route is MetaGrowthRoute.UNKNOWN_CHOICE
            and tied_result.selected_strategy_id is None
            and tied_result.object_state.digest == tied.state.digest
        ),
    }


def run_qualification(*, write_result: bool = True) -> dict[str, object]:
    memory = MetaMemory.empty()

    c_acquisition_bundle = make_episode(
        FAMILY_C, "acquisition", RepairPhase.ACQUISITION
    )
    c_acquisition = execute_meta_growth(
        c_acquisition_bundle.state, memory, c_acquisition_bundle.spec
    )
    memory = c_acquisition.meta_memory

    t_acquisition_bundle = make_episode(
        FAMILY_T, "acquisition", RepairPhase.ACQUISITION
    )
    t_acquisition = execute_meta_growth(
        t_acquisition_bundle.state, memory, t_acquisition_bundle.spec
    )
    memory = t_acquisition.meta_memory

    candidate_only = (
        len(memory.rules) == 2
        and all(rule.status is RepairRuleStatus.CANDIDATE for rule in memory.rules)
    )

    c_calibration_bundle = make_episode(
        FAMILY_C, "calibration", RepairPhase.CALIBRATION
    )
    c_calibration = execute_meta_growth(
        c_calibration_bundle.state, memory, c_calibration_bundle.spec
    )
    memory = c_calibration.meta_memory
    c_promoted_only_memory = memory

    t_calibration_bundle = make_episode(
        FAMILY_T, "calibration", RepairPhase.CALIBRATION
    )
    t_calibration = execute_meta_growth(
        t_calibration_bundle.state, memory, t_calibration_bundle.spec
    )
    promoted_memory = t_calibration.meta_memory

    promoted = [
        rule for rule in promoted_memory.rules
        if rule.status is RepairRuleStatus.PROMOTED
    ]

    portfolio = frozen_portfolio()
    snapshot = MetaSnapshot.from_present(
        t_calibration.object_state,
        promoted_memory,
        portfolio_digest=portfolio.digest,
        authority_snapshot=AUTHORITY,
    )
    restarted_snapshot = MetaSnapshot.from_text(snapshot.text())
    restarted_object_state, restarted_memory = restarted_snapshot.restore()
    snapshot_exact = (
        restarted_object_state.digest == t_calibration.object_state.digest
        and restarted_object_state.to_text() == t_calibration.object_state.to_text()
        and restarted_memory.digest == promoted_memory.digest
        and restarted_memory.text() == promoted_memory.text()
        and restarted_snapshot.text() == snapshot.text()
    )

    c_future_bundle = make_episode(FAMILY_C, "future", RepairPhase.FUTURE)
    c_future = execute_meta_growth(
        c_future_bundle.state, restarted_memory, c_future_bundle.spec
    )

    t_future_bundle = make_episode(FAMILY_T, "future", RepairPhase.FUTURE)
    t_future = execute_meta_growth(
        t_future_bundle.state, restarted_memory, t_future_bundle.spec
    )

    c_rule = next(
        rule for rule in promoted
        if rule.strategy_id == ADD_OBSERVABLE
    )
    t_rule = next(
        rule for rule in promoted
        if rule.strategy_id == ADD_FINITE_MEMORY_2
    )

    c_ablated_memory = restarted_memory.revoke(c_rule.rule_id)
    c_ablated = execute_meta_growth(
        c_future_bundle.state,
        c_ablated_memory,
        c_future_bundle.spec,
    )
    t_ablated_memory = restarted_memory.revoke(t_rule.rule_id)
    t_ablated = execute_meta_growth(
        t_future_bundle.state,
        t_ablated_memory,
        t_future_bundle.spec,
    )

    controls = _controls(
        c_promoted_only_memory=c_promoted_only_memory,
        c_future_bundle=c_future_bundle,
        t_future_bundle=t_future_bundle,
    )

    inherited_v2 = run_v2_qualification(write_result=False)

    c_acq_fp = episode_fingerprint(c_acquisition_bundle).digest
    c_cal_fp = episode_fingerprint(c_calibration_bundle).digest
    c_future_fp = episode_fingerprint(c_future_bundle).digest
    t_acq_fp = episode_fingerprint(t_acquisition_bundle).digest
    t_cal_fp = episode_fingerprint(t_calibration_bundle).digest
    t_future_fp = episode_fingerprint(t_future_bundle).digest

    c_source_capability = c_acquisition.selected_generation.capability
    t_source_capability = t_acquisition.selected_generation.capability
    c_future_capability = c_future.selected_generation.capability
    t_future_capability = t_future.selected_generation.capability

    gates = {
        "acquisition_rules_candidate_only": candidate_only,
        "acquisition_distinct_repair_classes": (
            c_acquisition.selected_strategy_id == ADD_OBSERVABLE
            and t_acquisition.selected_strategy_id == ADD_FINITE_MEMORY_2
        ),
        "calibration_promotes_both_rules": (
            len(promoted) == 2
            and all(len(rule.source_episode_digests) >= 2 for rule in promoted)
        ),
        "two_distinct_promoted_repair_rules": (
            {rule.strategy_id for rule in promoted}
            == {ADD_OBSERVABLE, ADD_FINITE_MEMORY_2}
        ),
        "family_c_observation_rule": c_rule.strategy_id == ADD_OBSERVABLE,
        "family_t_memory_rule": t_rule.strategy_id == ADD_FINITE_MEMORY_2,
        "family_c_fingerprint_transfers": c_acq_fp == c_cal_fp == c_future_fp,
        "family_t_fingerprint_transfers": t_acq_fp == t_cal_fp == t_future_fp,
        "cross_family_fingerprint_separates": c_acq_fp != t_acq_fp,
        "future_c_rule_hit": c_future.rule_hit,
        "future_t_rule_hit": t_future.rule_hit,
        "future_c_zero_portfolio_search": c_future.portfolio_search_calls == 0,
        "future_t_zero_portfolio_search": t_future.portfolio_search_calls == 0,
        "future_c_zero_competitor_calls": c_future.competitor_strategy_calls == 0,
        "future_t_zero_competitor_calls": t_future.competitor_strategy_calls == 0,
        "future_c_new_verified_capability": (
            c_source_capability is not None
            and c_future_capability is not None
            and c_source_capability.capability_id != c_future_capability.capability_id
            and c_future.attack is not None
            and c_future.attack.status.value == "SURVIVE"
            and c_future.selected_generation.future is not None
            and c_future.selected_generation.future.passed
        ),
        "future_t_new_verified_capability": (
            t_source_capability is not None
            and t_future_capability is not None
            and t_source_capability.capability_id != t_future_capability.capability_id
            and t_future.attack is not None
            and t_future.attack.status.value == "SURVIVE"
            and t_future.selected_generation.future is not None
            and t_future.selected_generation.future.passed
        ),
        "future_object_zero_grammar_search": (
            c_future.selected_generation.future.grammar_search_calls == 0
            and t_future.selected_generation.future.grammar_search_calls == 0
        ),
        "exact_meta_snapshot_restart": snapshot_exact,
        "rule_ablation_restores_cold_search": (
            not c_ablated.rule_hit
            and c_ablated.portfolio_search_calls > 0
            and c_ablated.selected_strategy_id == ADD_OBSERVABLE
            and not t_ablated.rule_hit
            and t_ablated.portfolio_search_calls > 0
            and t_ablated.selected_strategy_id == ADD_FINITE_MEMORY_2
        ),
        **controls,
        "inherited_v2_green": (
            inherited_v2["passed"] is True
            and inherited_v2["verdict"] == "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2"
        ),
    }

    preclosure_passed = all(gates.values())
    closure_payload = {
        "status": "CLOSED_BOUNDED_META_GROWTH_V3" if preclosure_passed else "PARTIAL_BOUNDED_META_GROWTH_V3",
        "portfolio_digest": portfolio.digest,
        "acquisition_episode_digests": [
            c_acquisition.episode_digest,
            t_acquisition.episode_digest,
        ],
        "calibration_episode_digests": [
            c_calibration.episode_digest,
            t_calibration.episode_digest,
        ],
        "promoted_rule_ids": sorted(rule.rule_id for rule in promoted),
        "promoted_strategy_ids": sorted(rule.strategy_id for rule in promoted),
        "future_evidence": {
            "c": c_future.selected_generation.trace.digest,
            "t": t_future.selected_generation.trace.digest,
        },
        "future_portfolio_calls": {
            "c": c_future.portfolio_search_calls,
            "t": t_future.portfolio_search_calls,
        },
        "ablation_portfolio_calls": {
            "c": c_ablated.portfolio_search_calls,
            "t": t_ablated.portfolio_search_calls,
        },
        "controls": controls,
        "meta_snapshot_digest": snapshot.digest,
        "meta_memory_digest": restarted_memory.digest,
        "inherited_v2_certificate": inherited_v2["closure"]["certificate_digest"],
        "claims": {
            "open_ended_meta_growth": False,
            "arbitrary_substrate_invention": False,
            "unbounded_self_development": False,
            "universal_obstruction_classification": False,
        },
    }
    closure_digest = canonical_digest(
        closure_payload,
        prefix="verified-meta-growth-closure-v3:",
    )
    gates["closed_bounded_meta_growth"] = (
        closure_payload["status"] == "CLOSED_BOUNDED_META_GROWTH_V3"
        and bool(closure_digest)
    )
    passed = all(gates.values())
    verdict = (
        "PASS_VERIFIED_META_GROWTH_V3"
        if passed
        else "PARTIAL_VERIFIED_META_GROWTH_V3"
    )

    summary = {
        "version": "verified-meta-growth-v3",
        "verdict": verdict,
        "passed": passed,
        "gates": gates,
        "acquisition": {
            "c": _episode_summary(c_acquisition),
            "t": _episode_summary(t_acquisition),
        },
        "calibration": {
            "c": _episode_summary(c_calibration),
            "t": _episode_summary(t_calibration),
        },
        "promoted_rules": _promoted_rules(promoted_memory),
        "future": {
            "c": _episode_summary(c_future),
            "t": _episode_summary(t_future),
        },
        "ablations": {
            "c": _episode_summary(c_ablated),
            "t": _episode_summary(t_ablated),
        },
        "controls": controls,
        "snapshot": {
            "digest": snapshot.digest,
            "exact": snapshot_exact,
            "before_object_digest": t_calibration.object_state.digest,
            "after_object_digest": restarted_object_state.digest,
            "before_memory_digest": promoted_memory.digest,
            "after_memory_digest": restarted_memory.digest,
        },
        "inherited_v2": {
            "passed": inherited_v2["passed"],
            "verdict": inherited_v2["verdict"],
            "closure_status": inherited_v2["closure"]["status"],
            "certificate_digest": inherited_v2["closure"]["certificate_digest"],
        },
        "closure": {
            "status": closure_payload["status"],
            "certificate_digest": closure_digest,
            "payload": closure_payload,
        },
        "claims": {
            "bounded_verified_meta_growth": passed,
            "open_ended_meta_growth": False,
            "arbitrary_substrate_invention": False,
            "unbounded_self_development": False,
            "universal_obstruction_classification": False,
        },
    }

    if write_result:
        path = Path(os.environ.get("REALITYGRAPH_META_GROWTH_RESULT", RESULT_PATH))
        path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary


def main() -> None:
    summary = run_qualification(write_result=True)
    print("REALITYGRAPH / VERIFIED META-GROWTH V3")
    print("--------------------------------------")
    for family in ("c", "t"):
        acquisition = summary["acquisition"][family]
        future = summary["future"][family]
        print(
            family.upper(),
            "acquire", acquisition["selected_strategy_id"],
            "portfolio", acquisition["portfolio_search_calls"],
            "capability", acquisition["capability_id"],
        )
        print(
            family.upper(),
            "future", future["selected_strategy_id"],
            "rule_hit", int(bool(future["rule_hit"])),
            "portfolio", future["portfolio_search_calls"],
            "competitors", future["competitor_strategy_calls"],
            "capability", future["capability_id"],
        )
    print("PROMOTED")
    for rule in summary["promoted_rules"]:
        print(rule["rule_id"], "->", rule["strategy_id"])
    for name, value in summary["gates"].items():
        print(f"gate_{name}={int(bool(value))}")
    print(
        "CLOSURE",
        summary["closure"]["status"],
        "certificate",
        summary["closure"]["certificate_digest"],
    )
    print("VERDICT")
    print(summary["verdict"])
    if not summary["passed"]:
        raise AssertionError("one or more verified meta-growth V3 gates failed")


if __name__ == "__main__":
    main()
