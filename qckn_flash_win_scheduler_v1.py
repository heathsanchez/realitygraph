from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from realitygraph.win_scheduler import (
    GlobalWinScheduler,
    VerifiedWinEvent,
    WinOpportunity,
)


BUDGET = 10.0
DEADLINE_PRESSURE = 0.75


@dataclass(frozen=True)
class RunResult:
    policy: str
    direct_win: float
    spent: float
    steps: tuple[str, ...]
    events: tuple[str, ...]
    metrics: dict[str, object]


def fixture() -> tuple[WinOpportunity, ...]:
    return (
        WinOpportunity(
            "fast-score",
            "lean-kernel",
            direct_win=6.0,
            verification_probability=0.85,
            authority_readiness=0.95,
            destination_bridge_probability=0.10,
            flash_radius=1.0,
            future_search_removed=2.0,
            composition_unlocks=0.0,
            cost=2.0,
            latency=1.0,
            deadline_relevance=1.0,
            external_visibility=1.0,
        ),
        WinOpportunity(
            "bridge-lemma",
            "formal-reasoning",
            direct_win=2.0,
            verification_probability=0.95,
            authority_readiness=0.95,
            destination_bridge_probability=0.90,
            flash_radius=6.0,
            future_search_removed=30.0,
            composition_unlocks=2.0,
            cost=1.5,
            latency=0.5,
            maintenance_cost=0.2,
            deadline_relevance=0.80,
            external_visibility=0.70,
        ),
        WinOpportunity(
            "final-boss",
            "lean-kernel",
            direct_win=20.0,
            verification_probability=0.90,
            authority_readiness=0.95,
            destination_bridge_probability=0.10,
            flash_radius=1.0,
            future_search_removed=5.0,
            composition_unlocks=0.0,
            cost=8.0,
            latency=16.0,
            deadline_relevance=1.0,
            external_visibility=1.0,
        ),
        WinOpportunity(
            "kernel-guard",
            "lean-kernel",
            direct_win=8.0,
            verification_probability=0.95,
            authority_readiness=1.0,
            destination_bridge_probability=0.20,
            flash_radius=2.0,
            future_search_removed=8.0,
            composition_unlocks=1.0,
            cost=4.0,
            latency=2.0,
            deadline_relevance=0.95,
            external_visibility=1.0,
        ),
        WinOpportunity(
            "duplicate-a",
            "arc",
            direct_win=3.0,
            verification_probability=0.80,
            authority_readiness=0.80,
            destination_bridge_probability=0.25,
            flash_radius=1.0,
            future_search_removed=1.0,
            composition_unlocks=0.0,
            cost=3.0,
            latency=2.0,
            deadline_relevance=0.50,
            external_visibility=0.60,
        ),
        WinOpportunity(
            "duplicate-b",
            "arc",
            direct_win=3.0,
            verification_probability=0.80,
            authority_readiness=0.80,
            destination_bridge_probability=0.25,
            flash_radius=1.0,
            future_search_removed=1.0,
            composition_unlocks=0.0,
            cost=3.0,
            latency=2.0,
            deadline_relevance=0.50,
            external_visibility=0.60,
        ),
        WinOpportunity(
            "speculative-global",
            "cross-domain",
            direct_win=3.0,
            verification_probability=0.70,
            authority_readiness=0.25,
            destination_bridge_probability=0.10,
            flash_radius=30.0,
            future_search_removed=200.0,
            composition_unlocks=5.0,
            cost=1.0,
            latency=1.0,
            deadline_relevance=0.40,
            external_visibility=0.70,
        ),
        WinOpportunity(
            "flash-infrastructure",
            "realitygraph",
            direct_win=0.5,
            verification_probability=0.95,
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=15.0,
            future_search_removed=100.0,
            composition_unlocks=3.0,
            cost=3.0,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=0.30,
            external_visibility=0.30,
        ),
    )


def outcome(opportunity_id: str) -> VerifiedWinEvent:
    if opportunity_id == "fast-score":
        return VerifiedWinEvent(
            "event:fast-score",
            opportunity_id,
            True,
            direct_win_realized=6.0,
        )
    if opportunity_id == "bridge-lemma":
        return VerifiedWinEvent(
            "event:bridge-lemma",
            opportunity_id,
            True,
            direct_win_realized=2.0,
            flash_radius_realized=5,
            future_search_removed_realized=30.0,
            composition_unlocks_realized=2.0,
            cancel_opportunities=("duplicate-a", "duplicate-b"),
            cost_multipliers=(
                ("final-boss", 0.25),
                ("kernel-guard", 0.50),
            ),
            latency_multipliers=(
                ("final-boss", 0.25),
                ("kernel-guard", 0.50),
            ),
            provenance=("verified-bridge",),
        )
    if opportunity_id == "final-boss":
        return VerifiedWinEvent(
            "event:final-boss",
            opportunity_id,
            True,
            direct_win_realized=20.0,
        )
    if opportunity_id == "kernel-guard":
        return VerifiedWinEvent(
            "event:kernel-guard",
            opportunity_id,
            True,
            direct_win_realized=8.0,
            flash_radius_realized=2,
            future_search_removed_realized=8.0,
            composition_unlocks_realized=1.0,
        )
    if opportunity_id in {"duplicate-a", "duplicate-b"}:
        return VerifiedWinEvent(
            f"event:{opportunity_id}",
            opportunity_id,
            True,
            direct_win_realized=3.0,
        )
    if opportunity_id == "speculative-global":
        return VerifiedWinEvent(
            "event:speculative-global-failed",
            opportunity_id,
            False,
        )
    if opportunity_id == "flash-infrastructure":
        return VerifiedWinEvent(
            "event:flash-infrastructure",
            opportunity_id,
            True,
            direct_win_realized=0.5,
            flash_radius_realized=15,
            future_search_removed_realized=100.0,
            composition_unlocks_realized=3.0,
        )
    raise KeyError(opportunity_id)


def run_policy(policy: str) -> RunResult:
    scheduler = GlobalWinScheduler(fixture())
    budget = float(BUDGET)
    spent = 0.0
    steps: list[str] = []
    events: list[str] = []

    while True:
        affordable = [
            row
            for row in scheduler.opportunities.values()
            if row.status == "OPEN" and row.cost <= budget
        ]
        if not affordable:
            break

        if policy == "WIN_SCHEDULER":
            selected = scheduler.choose_next(
                mode="BATTLE",
                deadline_pressure=DEADLINE_PRESSURE,
                remaining_budget=budget,
            )
            if selected is None:
                break
            opportunity = scheduler.opportunities[selected.opportunity_id]
        elif policy == "DIRECT_GREEDY":
            opportunity = sorted(
                affordable,
                key=lambda row: (
                    -(
                        row.local_admission_probability
                        * row.direct_win
                        * row.external_visibility
                        * row.deadline_relevance
                        / row.cost
                    ),
                    row.opportunity_id,
                ),
            )[0]
        elif policy == "ROUND_ROBIN":
            opportunity = sorted(affordable, key=lambda row: row.opportunity_id)[0]
        else:
            raise ValueError("unknown policy")

        current_cost = opportunity.cost
        budget -= current_cost
        spent += current_cost
        steps.append(opportunity.opportunity_id)

        event = outcome(opportunity.opportunity_id)
        scheduler.admit_event(event)
        events.append(event.event_id)

    return RunResult(
        policy=policy,
        direct_win=scheduler.total_direct_win,
        spent=spent,
        steps=tuple(steps),
        events=tuple(events),
        metrics=scheduler.metrics(),
    )


def ranking_controls() -> dict[str, object]:
    scheduler = GlobalWinScheduler(fixture())
    battle = scheduler.rank(
        mode="BATTLE",
        deadline_pressure=DEADLINE_PRESSURE,
    )
    discovery = scheduler.rank(
        mode="DISCOVERY",
        deadline_pressure=0.0,
    )
    battle_ids = [row.opportunity_id for row in battle]
    discovery_ids = [row.opportunity_id for row in discovery]

    speculative = next(
        row for row in battle
        if row.opportunity_id == "speculative-global"
    )
    bridge = next(
        row for row in battle
        if row.opportunity_id == "bridge-lemma"
    )

    before_final = scheduler.score(
        "final-boss",
        mode="BATTLE",
        deadline_pressure=DEADLINE_PRESSURE,
    )
    delta = scheduler.admit_event(outcome("bridge-lemma"))
    after_final = scheduler.score(
        "final-boss",
        mode="BATTLE",
        deadline_pressure=DEADLINE_PRESSURE,
    )

    return {
        "battle_order": battle_ids,
        "discovery_order": discovery_ids,
        "speculative_global_below_verified_bridge": (
            speculative.score < bridge.score
        ),
        "discovery_prefers_flash_infrastructure": (
            discovery_ids[0] == "flash-infrastructure"
        ),
        "bridge_reprices_final_boss_up": (
            after_final.score > before_final.score
        ),
        "bridge_cancelled_duplicates": list(delta.cancelled),
        "bridge_repriced": list(delta.repriced),
        "final_boss_score_before": before_final.score,
        "final_boss_score_after": after_final.score,
    }


def sham_control() -> bool:
    scheduler = GlobalWinScheduler(fixture())
    before = scheduler.metrics()
    try:
        scheduler.admit_event(
            VerifiedWinEvent(
                "event:sham",
                "speculative-global",
                False,
                cancel_opportunities=("final-boss",),
            )
        )
    except ValueError:
        after = scheduler.metrics()
        return (
            before["open"] == after["open"]
            and before["cancelled"] == after["cancelled"]
            and before["total_direct_win"] == after["total_direct_win"]
        )
    return False


def run_probe() -> dict[str, object]:
    win = run_policy("WIN_SCHEDULER")
    direct = run_policy("DIRECT_GREEDY")
    round_robin = run_policy("ROUND_ROBIN")
    controls = ranking_controls()
    sham_ok = sham_control()

    gates = {
        "WIN_SCHEDULER_BEATS_DIRECT_GREEDY": (
            win.direct_win > direct.direct_win
        ),
        "WIN_SCHEDULER_BEATS_ROUND_ROBIN": (
            win.direct_win > round_robin.direct_win
        ),
        "WIN_SCHEDULER_STAYS_WITHIN_BUDGET": win.spent <= BUDGET,
        "VERIFIED_BRIDGE_REPRICES_FINAL_BOSS": bool(
            controls["bridge_reprices_final_boss_up"]
        ),
        "VERIFIED_BRIDGE_CANCELS_DUPLICATE_WORK": (
            controls["bridge_cancelled_duplicates"]
            == ["duplicate-a", "duplicate-b"]
        ),
        "SPECULATIVE_GLOBAL_PRIOR_IS_AUTHORITY_DISCOUNTED": bool(
            controls["speculative_global_below_verified_bridge"]
        ),
        "DISCOVERY_MODE_PREFERS_HIGH_FLASH_VALUE": bool(
            controls["discovery_prefers_flash_infrastructure"]
        ),
        "SHAM_CANNOT_MUTATE_PORTFOLIO": sham_ok,
        "COMPOUNDING_ROUTE_USED": (
            "bridge-lemma" in win.steps
            and "final-boss" in win.steps
            and win.steps.index("bridge-lemma") < win.steps.index("final-boss")
        ),
        "DUPLICATE_WORK_NOT_PAID_AFTER_FLASH": (
            "duplicate-a" not in win.steps
            and "duplicate-b" not in win.steps
        ),
    }

    return {
        "schema": "qckn-flash-win-scheduler-v1",
        "passed": all(gates.values()),
        "budget": BUDGET,
        "deadline_pressure": DEADLINE_PRESSURE,
        "gates": gates,
        "win_scheduler": {
            "direct_win": win.direct_win,
            "spent": win.spent,
            "steps": list(win.steps),
            "events": list(win.events),
            "metrics": win.metrics,
        },
        "direct_greedy": {
            "direct_win": direct.direct_win,
            "spent": direct.spent,
            "steps": list(direct.steps),
            "events": list(direct.events),
            "metrics": direct.metrics,
        },
        "round_robin": {
            "direct_win": round_robin.direct_win,
            "spent": round_robin.spent,
            "steps": list(round_robin.steps),
            "events": list(round_robin.events),
            "metrics": round_robin.metrics,
        },
        "controls": {
            **controls,
            "sham_rejected_without_mutation": sham_ok,
        },
    }


def main() -> int:
    result = run_probe()
    serialized = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output = os.environ.get("QCKN_WIN_SCHEDULER_RESULT_PATH")
    if output:
        Path(output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
