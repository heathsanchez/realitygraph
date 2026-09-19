from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .flash_bus import (
    BridgeCertificate,
    BusDelta,
    CrossDomainEdge,
    EvidenceEvent,
    GlobalFlashBus,
)
from .win_scheduler import (
    GlobalWinScheduler,
    SchedulerDelta,
    VerifiedWinEvent,
)


@dataclass(frozen=True)
class SchedulerEffectCertificate:
    effect_id: str
    bridge_id: str
    destination_domain: str
    destination_kind: str
    destination_key: str
    target_opportunity_id: str
    scheduler_authority_snapshot: str
    scheduler_verifier_id: str
    cancel_target: bool = False
    cost_multiplier: float = 1.0
    latency_multiplier: float = 1.0
    flash_radius_realized: int = 0
    future_search_removed_realized: float = 0.0
    composition_unlocks_realized: float = 0.0
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(
            (
                self.effect_id,
                self.bridge_id,
                self.destination_domain,
                self.destination_kind,
                self.destination_key,
                self.target_opportunity_id,
                self.scheduler_authority_snapshot,
                self.scheduler_verifier_id,
            )
        ):
            raise ValueError("scheduler effect certificate requires exact identity")
        if not 0 < float(self.cost_multiplier) <= 1.0:
            raise ValueError("cost multiplier must lie in (0,1]")
        if not 0 < float(self.latency_multiplier) <= 1.0:
            raise ValueError("latency multiplier must lie in (0,1]")
        if self.flash_radius_realized < 0:
            raise ValueError("flash radius must be nonnegative")
        if self.future_search_removed_realized < 0:
            raise ValueError("future search removal must be nonnegative")
        if self.composition_unlocks_realized < 0:
            raise ValueError("composition unlocks must be nonnegative")
        if len(self.provenance) != len(set(self.provenance)):
            raise ValueError("effect provenance must be unique")


@dataclass(frozen=True)
class ControllerDelta:
    source_event_id: str
    bus_affected_domains: tuple[str, ...]
    bus_edges: tuple[CrossDomainEdge, ...]
    scheduler_deltas: tuple[SchedulerDelta, ...]
    applied_effect_ids: tuple[str, ...]


class FlashWinController:
    """Authority-gated coupling from evidence bus to win scheduler.

    A local domain event is allowed to resolve its own scheduler opportunity
    once its domain authority admits it. Cross-domain mutation requires both:
      1. an exact GlobalFlashBus bridge edge; and
      2. an independently admitted scheduler-effect certificate matching that
         edge's destination kind/key and target opportunity domain.

    This deliberately prevents speculative proposal priors from changing
    another domain's allocation.
    """

    def __init__(
        self,
        *,
        bus: GlobalFlashBus,
        scheduler: GlobalWinScheduler,
        scheduler_authority_snapshot: str,
        scheduler_verifier_id: str,
        effects: Iterable[SchedulerEffectCertificate] = (),
    ) -> None:
        if not scheduler_authority_snapshot or not scheduler_verifier_id:
            raise ValueError("controller requires scheduler authority and verifier")
        self.bus = bus
        self.scheduler = scheduler
        self.scheduler_authority_snapshot = str(scheduler_authority_snapshot)
        self.scheduler_verifier_id = str(scheduler_verifier_id)
        self.effects: dict[str, SchedulerEffectCertificate] = {}
        self.applied_effect_ids: set[str] = set()
        self.event_to_opportunity: dict[str, str] = {}
        self.event_direct_win: dict[str, float] = {}
        for effect in effects:
            self.admit_effect_certificate(effect)

    def admit_effect_certificate(
        self,
        effect: SchedulerEffectCertificate,
    ) -> None:
        if (
            effect.scheduler_authority_snapshot
            != self.scheduler_authority_snapshot
            or effect.scheduler_verifier_id != self.scheduler_verifier_id
        ):
            raise ValueError("scheduler effect authority/verifier mismatch")
        target = self.scheduler.opportunities.get(effect.target_opportunity_id)
        if target is None:
            raise ValueError("scheduler effect targets unknown opportunity")
        if target.domain != effect.destination_domain:
            raise ValueError("scheduler effect destination domain mismatch")
        old = self.effects.get(effect.effect_id)
        if old is not None and old != effect:
            raise ValueError("scheduler effect identity conflict")
        self.effects[effect.effect_id] = effect

    def _effects_for_edge(
        self,
        edge: CrossDomainEdge,
    ) -> tuple[SchedulerEffectCertificate, ...]:
        rows = [
            effect
            for effect in self.effects.values()
            if (
                effect.effect_id not in self.applied_effect_ids
                and effect.bridge_id == edge.bridge_id
                and effect.destination_domain == edge.destination_domain
                and effect.destination_kind == edge.destination_kind
                and effect.destination_key == edge.destination_key
            )
        ]
        return tuple(sorted(rows, key=lambda row: row.effect_id))

    def _apply_scheduler_effects(
        self,
        *,
        source_event_id: str,
        edges: tuple[CrossDomainEdge, ...],
        event_id_suffix: str,
        direct_win_realized: float = 0.0,
        resolve_source: bool = True,
    ) -> tuple[tuple[SchedulerDelta, ...], tuple[str, ...]]:
        source_opportunity_id = self.event_to_opportunity.get(source_event_id)
        matched: list[SchedulerEffectCertificate] = []
        for edge in edges:
            matched.extend(self._effects_for_edge(edge))
        matched = sorted(
            {effect.effect_id: effect for effect in matched}.values(),
            key=lambda row: row.effect_id,
        )

        # No scheduler mutation is possible without a mapped source opportunity.
        if source_opportunity_id is None:
            return (), ()

        cancel_targets = tuple(
            sorted(
                {
                    effect.target_opportunity_id
                    for effect in matched
                    if effect.cancel_target
                }
            )
        )
        cost_multipliers: dict[str, float] = {}
        latency_multipliers: dict[str, float] = {}
        for effect in matched:
            if effect.cancel_target:
                continue
            cost_multipliers[effect.target_opportunity_id] = (
                cost_multipliers.get(effect.target_opportunity_id, 1.0)
                * effect.cost_multiplier
            )
            latency_multipliers[effect.target_opportunity_id] = (
                latency_multipliers.get(effect.target_opportunity_id, 1.0)
                * effect.latency_multiplier
            )

        should_emit = bool(matched) or resolve_source or direct_win_realized > 0
        if not should_emit:
            return (), ()

        scheduler_event = VerifiedWinEvent(
            event_id=f"scheduler:{source_event_id}:{event_id_suffix}",
            source_opportunity_id=source_opportunity_id,
            verified=True,
            direct_win_realized=float(direct_win_realized),
            flash_radius_realized=sum(
                effect.flash_radius_realized for effect in matched
            ),
            future_search_removed_realized=sum(
                effect.future_search_removed_realized for effect in matched
            ),
            composition_unlocks_realized=sum(
                effect.composition_unlocks_realized for effect in matched
            ),
            cancel_opportunities=cancel_targets,
            cost_multipliers=tuple(sorted(cost_multipliers.items())),
            latency_multipliers=tuple(sorted(latency_multipliers.items())),
            provenance=tuple(
                sorted(
                    {
                        item
                        for effect in matched
                        for item in effect.provenance
                    }
                )
            ),
        )
        delta = self.scheduler.admit_event(scheduler_event)
        for effect in matched:
            self.applied_effect_ids.add(effect.effect_id)
        return (delta,), tuple(effect.effect_id for effect in matched)

    def admit_event(
        self,
        event: EvidenceEvent,
        *,
        source_opportunity_id: str | None = None,
        direct_win_realized: float = 0.0,
    ) -> ControllerDelta:
        if source_opportunity_id is not None:
            opportunity = self.scheduler.opportunities.get(source_opportunity_id)
            if opportunity is None:
                raise ValueError("event maps to unknown source opportunity")
            if opportunity.domain != event.domain:
                raise ValueError("event source opportunity domain mismatch")
            old = self.event_to_opportunity.get(event.event_id)
            if old is not None and old != source_opportunity_id:
                raise ValueError("event-to-opportunity identity conflict")
            self.event_to_opportunity[event.event_id] = source_opportunity_id
            self.event_direct_win[event.event_id] = float(direct_win_realized)

        bus_delta = self.bus.admit_event(event)
        scheduler_deltas, effects = self._apply_scheduler_effects(
            source_event_id=event.event_id,
            edges=bus_delta.cross_domain_edges,
            event_id_suffix="event",
            direct_win_realized=direct_win_realized,
            resolve_source=(source_opportunity_id is not None),
        )
        return ControllerDelta(
            event.event_id,
            bus_delta.affected_domains,
            bus_delta.cross_domain_edges,
            scheduler_deltas,
            effects,
        )

    def admit_bridge(
        self,
        bridge: BridgeCertificate,
    ) -> tuple[ControllerDelta, ...]:
        created = self.bus.admit_bridge(bridge)
        by_event: dict[str, list[CrossDomainEdge]] = {}
        for edge in created:
            by_event.setdefault(edge.source_event_id, []).append(edge)

        results: list[ControllerDelta] = []
        for source_event_id in sorted(by_event):
            edges = tuple(sorted(by_event[source_event_id]))
            scheduler_deltas, effects = self._apply_scheduler_effects(
                source_event_id=source_event_id,
                edges=edges,
                event_id_suffix=f"bridge:{bridge.bridge_id}",
                direct_win_realized=0.0,
                resolve_source=False,
            )
            affected = {
                self.bus.events[source_event_id].domain,
                *(edge.destination_domain for edge in edges),
            }
            results.append(
                ControllerDelta(
                    source_event_id,
                    tuple(sorted(affected)),
                    edges,
                    scheduler_deltas,
                    effects,
                )
            )
        return tuple(results)

    def rank(
        self,
        *,
        mode: str,
        deadline_pressure: float = 0.0,
    ):
        return self.scheduler.rank(
            mode=mode,
            deadline_pressure=deadline_pressure,
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "schema": "qckn-flash-win-controller-v1",
            "bus_edges": [
                {
                    "source_event_id": edge.source_event_id,
                    "source_domain": edge.source_domain,
                    "destination_domain": edge.destination_domain,
                    "destination_kind": edge.destination_kind,
                    "destination_key": edge.destination_key,
                    "bridge_id": edge.bridge_id,
                    "certificate_id": edge.certificate_id,
                }
                for edge in self.bus.cross_domain_edges()
            ],
            "applied_effect_ids": sorted(self.applied_effect_ids),
            "scheduler": self.scheduler.metrics(),
        }
