from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Iterable


@dataclass(frozen=True)
class WinOpportunity:
    opportunity_id: str
    domain: str
    direct_win: float
    verification_probability: float
    authority_readiness: float
    destination_bridge_probability: float
    flash_radius: float
    future_search_removed: float
    composition_unlocks: float
    cost: float
    latency: float
    maintenance_cost: float = 0.0
    deadline_relevance: float = 1.0
    external_visibility: float = 1.0
    status: str = "OPEN"
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.opportunity_id or not self.domain:
            raise ValueError("opportunity requires identity and domain")
        for name, value in (
            ("verification_probability", self.verification_probability),
            ("authority_readiness", self.authority_readiness),
            ("destination_bridge_probability", self.destination_bridge_probability),
            ("deadline_relevance", self.deadline_relevance),
            ("external_visibility", self.external_visibility),
        ):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must lie in [0,1]")
        if self.cost <= 0 or self.latency <= 0:
            raise ValueError("cost and latency must be positive")
        if self.maintenance_cost < 0:
            raise ValueError("maintenance cost must be nonnegative")
        if self.status not in {"OPEN", "CANCELLED", "RESOLVED", "BLOCKED"}:
            raise ValueError("unsupported opportunity status")
        if len(self.provenance) != len(set(self.provenance)):
            raise ValueError("opportunity provenance must be unique")

    @property
    def local_admission_probability(self) -> float:
        return (
            self.verification_probability
            * self.authority_readiness
        )

    @property
    def global_admission_probability(self) -> float:
        return (
            self.local_admission_probability
            * self.destination_bridge_probability
        )


@dataclass(frozen=True)
class WinScore:
    opportunity_id: str
    mode: str
    score: float
    expected_direct_value: float
    expected_global_value: float
    denominator: float


@dataclass(frozen=True)
class VerifiedWinEvent:
    event_id: str
    source_opportunity_id: str
    verified: bool
    direct_win_realized: float = 0.0
    flash_radius_realized: int = 0
    future_search_removed_realized: float = 0.0
    composition_unlocks_realized: float = 0.0
    cancel_opportunities: tuple[str, ...] = ()
    cost_multipliers: tuple[tuple[str, float], ...] = ()
    latency_multipliers: tuple[tuple[str, float], ...] = ()
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.event_id or not self.source_opportunity_id:
            raise ValueError("event requires identity and source")
        if self.direct_win_realized < 0:
            raise ValueError("realized direct win must be nonnegative")
        if self.flash_radius_realized < 0:
            raise ValueError("flash radius must be nonnegative")
        if self.future_search_removed_realized < 0:
            raise ValueError("search removal must be nonnegative")
        if self.composition_unlocks_realized < 0:
            raise ValueError("composition unlocks must be nonnegative")
        for _, multiplier in (*self.cost_multipliers, *self.latency_multipliers):
            if not 0 < float(multiplier) <= 1.0:
                raise ValueError("event multipliers must lie in (0,1]")
        if len(self.cancel_opportunities) != len(set(self.cancel_opportunities)):
            raise ValueError("event cancellation targets must be unique")


@dataclass(frozen=True)
class SchedulerDelta:
    event_id: str
    verified: bool
    cancelled: tuple[str, ...]
    repriced: tuple[str, ...]
    changed_opportunities: tuple[str, ...]
    flash_radius: int


class GlobalWinScheduler:
    """Opportunity-cost scheduler above QCKN Flash.

    Speculation may contribute to a local direct-win estimate. Lateral/global
    value is discounted by both authority readiness and destination-bridge
    probability, implementing the empirical law learned from ARC Global Flash:
    verified consequences may propagate globally; speculative priors may not.
    """

    MODES = {"BATTLE", "DISCOVERY"}

    def __init__(self, opportunities: Iterable[WinOpportunity]) -> None:
        rows = tuple(opportunities)
        ids = [row.opportunity_id for row in rows]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("scheduler requires unique opportunities")
        self.opportunities = {row.opportunity_id: row for row in rows}
        self.event_ids: set[str] = set()
        self.events: list[VerifiedWinEvent] = []
        self.total_direct_win = 0.0
        self.total_future_search_removed = 0.0
        self.total_flash_radius = 0
        self.total_composition_unlocks = 0.0
        self.cancelled_work_cost = 0.0

    @staticmethod
    def _benefit_weights(mode: str, deadline_pressure: float) -> tuple[float, float, float, float]:
        if mode == "BATTLE":
            # Direct scoreboard gain dominates. Flash/search terms still matter
            # because they can create room for more wins inside the deadline.
            return (
                8.0 + 6.0 * deadline_pressure,
                1.4 - 0.4 * deadline_pressure,
                1.6 - 0.5 * deadline_pressure,
                1.2 - 0.2 * deadline_pressure,
            )
        if mode == "DISCOVERY":
            return (
                2.0 + 1.0 * deadline_pressure,
                4.0,
                4.5,
                3.5,
            )
        raise ValueError("unsupported scheduler mode")

    @staticmethod
    def _cost_denominator(row: WinOpportunity, mode: str, deadline_pressure: float) -> float:
        if mode == "BATTLE":
            latency_weight = 1.5 + 2.5 * deadline_pressure
            maintenance_weight = 1.0
        else:
            latency_weight = 0.8 + 0.5 * deadline_pressure
            maintenance_weight = 1.4
        return (
            float(row.cost)
            + latency_weight * float(row.latency)
            + maintenance_weight * float(row.maintenance_cost)
        )

    def score(
        self,
        opportunity_id: str,
        *,
        mode: str,
        deadline_pressure: float = 0.0,
    ) -> WinScore:
        mode = str(mode).upper()
        if mode not in self.MODES:
            raise ValueError("unsupported scheduler mode")
        if not 0.0 <= deadline_pressure <= 1.0:
            raise ValueError("deadline pressure must lie in [0,1]")
        row = self.opportunities[opportunity_id]
        if row.status != "OPEN":
            return WinScore(
                opportunity_id,
                mode,
                float("-inf"),
                0.0,
                0.0,
                float("inf"),
            )

        direct_weight, flash_weight, search_weight, composition_weight = (
            self._benefit_weights(mode, deadline_pressure)
        )

        expected_direct = (
            row.local_admission_probability
            * row.direct_win
            * row.external_visibility
            * row.deadline_relevance
        )
        expected_global = row.global_admission_probability * (
            flash_weight * math.log1p(row.flash_radius)
            + search_weight * math.log1p(row.future_search_removed)
            + composition_weight * math.log1p(row.composition_unlocks)
        )
        numerator = direct_weight * expected_direct + expected_global
        denominator = self._cost_denominator(
            row,
            mode,
            deadline_pressure,
        )
        return WinScore(
            row.opportunity_id,
            mode,
            numerator / denominator,
            expected_direct,
            expected_global,
            denominator,
        )

    def rank(
        self,
        *,
        mode: str,
        deadline_pressure: float = 0.0,
    ) -> tuple[WinScore, ...]:
        rows = [
            self.score(
                opportunity_id,
                mode=mode,
                deadline_pressure=deadline_pressure,
            )
            for opportunity_id, opportunity in self.opportunities.items()
            if opportunity.status == "OPEN"
        ]
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.score,
                    -row.expected_direct_value,
                    row.denominator,
                    row.opportunity_id,
                ),
            )
        )

    def choose_next(
        self,
        *,
        mode: str,
        deadline_pressure: float = 0.0,
        remaining_budget: float | None = None,
    ) -> WinScore | None:
        for row in self.rank(
            mode=mode,
            deadline_pressure=deadline_pressure,
        ):
            opportunity = self.opportunities[row.opportunity_id]
            if remaining_budget is None or opportunity.cost <= remaining_budget:
                return row
        return None

    def resolve_without_event(self, opportunity_id: str) -> None:
        row = self.opportunities[opportunity_id]
        if row.status != "OPEN":
            raise ValueError("only open opportunities can resolve")
        self.opportunities[opportunity_id] = replace(row, status="RESOLVED")

    def admit_event(self, event: VerifiedWinEvent) -> SchedulerDelta:
        if event.event_id in self.event_ids:
            raise ValueError("duplicate event identity")
        source = self.opportunities.get(event.source_opportunity_id)
        if source is None:
            raise ValueError("event source is not a live opportunity")
        if source.status not in {"OPEN", "RESOLVED"}:
            raise ValueError("event source is not admissible")

        # A failed/unverified event may resolve its own experiment, but it is not
        # allowed to mutate any other opportunity.
        if not event.verified:
            if event.cancel_opportunities or event.cost_multipliers or event.latency_multipliers:
                raise ValueError("unverified event cannot mutate shared portfolio")
            if source.status == "OPEN":
                self.opportunities[source.opportunity_id] = replace(
                    source,
                    status="RESOLVED",
                )
            self.event_ids.add(event.event_id)
            self.events.append(event)
            return SchedulerDelta(
                event.event_id,
                False,
                (),
                (),
                (source.opportunity_id,),
                0,
            )

        self.event_ids.add(event.event_id)
        self.events.append(event)

        if source.status == "OPEN":
            self.opportunities[source.opportunity_id] = replace(
                source,
                status="RESOLVED",
            )

        changed = {source.opportunity_id}
        cancelled: list[str] = []
        repriced: set[str] = set()

        for opportunity_id in event.cancel_opportunities:
            row = self.opportunities.get(opportunity_id)
            if row is None:
                raise ValueError(f"unknown cancellation target: {opportunity_id}")
            if row.status != "OPEN":
                continue
            self.cancelled_work_cost += row.cost
            self.opportunities[opportunity_id] = replace(
                row,
                status="CANCELLED",
            )
            cancelled.append(opportunity_id)
            changed.add(opportunity_id)

        for opportunity_id, multiplier in event.cost_multipliers:
            row = self.opportunities.get(opportunity_id)
            if row is None:
                raise ValueError(f"unknown repricing target: {opportunity_id}")
            if row.status != "OPEN":
                continue
            self.opportunities[opportunity_id] = replace(
                row,
                cost=max(1e-9, row.cost * float(multiplier)),
            )
            repriced.add(opportunity_id)
            changed.add(opportunity_id)

        for opportunity_id, multiplier in event.latency_multipliers:
            row = self.opportunities.get(opportunity_id)
            if row is None:
                raise ValueError(f"unknown latency target: {opportunity_id}")
            if row.status != "OPEN":
                continue
            self.opportunities[opportunity_id] = replace(
                row,
                latency=max(1e-9, row.latency * float(multiplier)),
            )
            repriced.add(opportunity_id)
            changed.add(opportunity_id)

        self.total_direct_win += event.direct_win_realized
        self.total_future_search_removed += event.future_search_removed_realized
        self.total_flash_radius += event.flash_radius_realized
        self.total_composition_unlocks += event.composition_unlocks_realized

        return SchedulerDelta(
            event.event_id,
            True,
            tuple(sorted(cancelled)),
            tuple(sorted(repriced)),
            tuple(sorted(changed)),
            event.flash_radius_realized,
        )

    def metrics(self) -> dict[str, object]:
        return {
            "schema": "qckn-flash-win-scheduler-v1",
            "total_direct_win": self.total_direct_win,
            "total_future_search_removed": self.total_future_search_removed,
            "total_flash_radius": self.total_flash_radius,
            "total_composition_unlocks": self.total_composition_unlocks,
            "cancelled_work_cost": self.cancelled_work_cost,
            "open": sorted(
                row.opportunity_id
                for row in self.opportunities.values()
                if row.status == "OPEN"
            ),
            "cancelled": sorted(
                row.opportunity_id
                for row in self.opportunities.values()
                if row.status == "CANCELLED"
            ),
            "resolved": sorted(
                row.opportunity_id
                for row in self.opportunities.values()
                if row.status == "RESOLVED"
            ),
            "events": [
                {
                    "event_id": event.event_id,
                    "source": event.source_opportunity_id,
                    "verified": event.verified,
                    "direct_win_realized": event.direct_win_realized,
                    "flash_radius_realized": event.flash_radius_realized,
                    "future_search_removed_realized": event.future_search_removed_realized,
                    "composition_unlocks_realized": event.composition_unlocks_realized,
                }
                for event in self.events
            ],
        }
