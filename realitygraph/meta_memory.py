from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum

from .developmental_types import canonical_digest, canonical_json


class RepairPhase(str, Enum):
    ACQUISITION = "ACQUISITION"
    CALIBRATION = "CALIBRATION"
    FUTURE = "FUTURE"
    CONTROL = "CONTROL"


class RepairRuleStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    PROMOTED = "PROMOTED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class RepairEpisode:
    episode_id: str
    phase: RepairPhase
    obstruction_fingerprint: str
    strategy_id: str
    strategy_version: str
    portfolio_digest: str
    authority_snapshot: str
    verifier_id: str
    interface_digest: str
    selection_cost: int
    object_evidence_digest: str

    def __post_init__(self) -> None:
        required = (
            self.episode_id,
            self.obstruction_fingerprint,
            self.strategy_id,
            self.strategy_version,
            self.portfolio_digest,
            self.authority_snapshot,
            self.verifier_id,
            self.interface_digest,
            self.object_evidence_digest,
        )
        if any(not value for value in required):
            raise ValueError("repair episode requires complete boundary and evidence identity")
        if self.selection_cost < 0:
            raise ValueError("repair episode selection cost must be non-negative")

    def payload(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "phase": self.phase.value,
            "obstruction_fingerprint": self.obstruction_fingerprint,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "portfolio_digest": self.portfolio_digest,
            "authority_snapshot": self.authority_snapshot,
            "verifier_id": self.verifier_id,
            "interface_digest": self.interface_digest,
            "selection_cost": self.selection_cost,
            "object_evidence_digest": self.object_evidence_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="repair-episode-v3:")

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "RepairEpisode":
        return cls(
            episode_id=str(payload["episode_id"]),
            phase=RepairPhase(str(payload["phase"])),
            obstruction_fingerprint=str(payload["obstruction_fingerprint"]),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            portfolio_digest=str(payload["portfolio_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
            verifier_id=str(payload["verifier_id"]),
            interface_digest=str(payload["interface_digest"]),
            selection_cost=int(payload["selection_cost"]),
            object_evidence_digest=str(payload["object_evidence_digest"]),
        )


@dataclass(frozen=True)
class RepairRule:
    rule_id: str
    obstruction_fingerprint: str
    strategy_id: str
    strategy_version: str
    portfolio_digest: str
    authority_snapshot: str
    verifier_id: str
    interface_digest: str
    source_episode_digests: tuple[str, ...]
    source_episode_phases: tuple[str, ...]
    status: RepairRuleStatus
    selection_cost: int
    ablation_handle: str

    def __post_init__(self) -> None:
        required = (
            self.rule_id,
            self.obstruction_fingerprint,
            self.strategy_id,
            self.strategy_version,
            self.portfolio_digest,
            self.authority_snapshot,
            self.verifier_id,
            self.interface_digest,
            self.ablation_handle,
        )
        if any(not value for value in required):
            raise ValueError("repair rule requires complete identity")
        if not self.source_episode_digests:
            raise ValueError("repair rule requires evidence lineage")
        if len(self.source_episode_digests) != len(self.source_episode_phases):
            raise ValueError("repair rule evidence phases must align with episode digests")
        if len(self.source_episode_digests) != len(set(self.source_episode_digests)):
            raise ValueError("repair rule episode digests must be unique")
        if self.selection_cost < 0:
            raise ValueError("repair rule selection cost must be non-negative")

    @property
    def boundary_key(self) -> tuple[str, ...]:
        return (
            self.obstruction_fingerprint,
            self.strategy_id,
            self.strategy_version,
            self.portfolio_digest,
            self.authority_snapshot,
            self.verifier_id,
            self.interface_digest,
        )

    def payload(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "obstruction_fingerprint": self.obstruction_fingerprint,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "portfolio_digest": self.portfolio_digest,
            "authority_snapshot": self.authority_snapshot,
            "verifier_id": self.verifier_id,
            "interface_digest": self.interface_digest,
            "source_episode_digests": list(self.source_episode_digests),
            "source_episode_phases": list(self.source_episode_phases),
            "status": self.status.value,
            "selection_cost": self.selection_cost,
            "ablation_handle": self.ablation_handle,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "RepairRule":
        return cls(
            rule_id=str(payload["rule_id"]),
            obstruction_fingerprint=str(payload["obstruction_fingerprint"]),
            strategy_id=str(payload["strategy_id"]),
            strategy_version=str(payload["strategy_version"]),
            portfolio_digest=str(payload["portfolio_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
            verifier_id=str(payload["verifier_id"]),
            interface_digest=str(payload["interface_digest"]),
            source_episode_digests=tuple(str(x) for x in payload["source_episode_digests"]),
            source_episode_phases=tuple(str(x) for x in payload["source_episode_phases"]),
            status=RepairRuleStatus(str(payload["status"])),
            selection_cost=int(payload["selection_cost"]),
            ablation_handle=str(payload["ablation_handle"]),
        )


@dataclass(frozen=True)
class MetaMemory:
    rules: tuple[RepairRule, ...] = ()
    episodes: tuple[RepairEpisode, ...] = ()

    def __post_init__(self) -> None:
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("repair rule IDs must be unique")
        episode_digests = [episode.digest for episode in self.episodes]
        if len(episode_digests) != len(set(episode_digests)):
            raise ValueError("repair episodes must be unique")

    @classmethod
    def empty(cls) -> "MetaMemory":
        return cls()

    @staticmethod
    def _episode_boundary(episode: RepairEpisode) -> tuple[str, ...]:
        return (
            episode.obstruction_fingerprint,
            episode.strategy_id,
            episode.strategy_version,
            episode.portfolio_digest,
            episode.authority_snapshot,
            episode.verifier_id,
            episode.interface_digest,
        )

    @staticmethod
    def _rule_id(episode: RepairEpisode) -> str:
        return "repair-rule-" + canonical_digest(
            {
                "fingerprint": episode.obstruction_fingerprint,
                "strategy_id": episode.strategy_id,
                "strategy_version": episode.strategy_version,
                "portfolio": episode.portfolio_digest,
                "authority": episode.authority_snapshot,
                "verifier": episode.verifier_id,
                "interface": episode.interface_digest,
            },
            prefix="repair-rule-v3:",
        )[:20]

    @staticmethod
    def _ablation_handle(rule_id: str) -> str:
        return canonical_digest({"rule_id": rule_id}, prefix="repair-rule-ablation-v3:")[:20]

    def record_success(self, episode: RepairEpisode) -> "MetaMemory":
        if any(existing.digest == episode.digest for existing in self.episodes):
            return self
        boundary = self._episode_boundary(episode)
        matching = [rule for rule in self.rules if rule.boundary_key == boundary]
        others = [rule for rule in self.rules if rule.boundary_key != boundary]
        if len(matching) > 1:
            raise ValueError("multiple repair rules share exact boundary identity")

        if matching:
            prior = matching[0]
            if prior.status is RepairRuleStatus.REVOKED:
                updated = prior
            else:
                pairs = list(zip(prior.source_episode_digests, prior.source_episode_phases))
                pairs.append((episode.digest, episode.phase.value))
                pairs = sorted(set(pairs))
                digests = tuple(pair[0] for pair in pairs)
                phases = tuple(pair[1] for pair in pairs)
                phase_set = set(phases)
                status = (
                    RepairRuleStatus.PROMOTED
                    if RepairPhase.ACQUISITION.value in phase_set
                    and RepairPhase.CALIBRATION.value in phase_set
                    and len(digests) >= 2
                    else RepairRuleStatus.CANDIDATE
                )
                updated = replace(
                    prior,
                    source_episode_digests=digests,
                    source_episode_phases=phases,
                    status=status,
                    selection_cost=min(prior.selection_cost, episode.selection_cost),
                )
        else:
            rule_id = self._rule_id(episode)
            updated = RepairRule(
                rule_id=rule_id,
                obstruction_fingerprint=episode.obstruction_fingerprint,
                strategy_id=episode.strategy_id,
                strategy_version=episode.strategy_version,
                portfolio_digest=episode.portfolio_digest,
                authority_snapshot=episode.authority_snapshot,
                verifier_id=episode.verifier_id,
                interface_digest=episode.interface_digest,
                source_episode_digests=(episode.digest,),
                source_episode_phases=(episode.phase.value,),
                status=RepairRuleStatus.CANDIDATE,
                selection_cost=episode.selection_cost,
                ablation_handle=self._ablation_handle(rule_id),
            )

        return MetaMemory(
            rules=tuple(sorted((*others, updated), key=lambda rule: rule.rule_id)),
            episodes=tuple(sorted((*self.episodes, episode), key=lambda item: item.digest)),
        )

    def promoted_match(
        self,
        *,
        obstruction_fingerprint: str,
        portfolio_digest: str,
        authority_snapshot: str,
        verifier_id: str,
        interface_digest: str,
    ) -> RepairRule | None:
        matches = [
            rule for rule in self.rules
            if rule.status is RepairRuleStatus.PROMOTED
            and rule.obstruction_fingerprint == obstruction_fingerprint
            and rule.portfolio_digest == portfolio_digest
            and rule.authority_snapshot == authority_snapshot
            and rule.verifier_id == verifier_id
            and rule.interface_digest == interface_digest
        ]
        if len(matches) > 1:
            raise ValueError("multiple promoted repair rules match exact obstruction boundary")
        return matches[0] if matches else None

    def revoke(self, rule_id: str) -> "MetaMemory":
        if rule_id not in {rule.rule_id for rule in self.rules}:
            raise ValueError(f"unknown repair rule: {rule_id}")
        rules = tuple(
            replace(rule, status=RepairRuleStatus.REVOKED)
            if rule.rule_id == rule_id else rule
            for rule in self.rules
        )
        return MetaMemory(rules=rules, episodes=self.episodes)

    def payload(self) -> dict[str, object]:
        return {
            "rules": [rule.payload() for rule in sorted(self.rules, key=lambda item: item.rule_id)],
            "episodes": [
                episode.payload()
                for episode in sorted(self.episodes, key=lambda item: item.digest)
            ],
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="meta-memory-v3:")

    def text(self) -> str:
        return canonical_json({"version": "meta-memory-v3", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "MetaMemory":
        payload = json.loads(text)
        if payload.pop("version", None) != "meta-memory-v3":
            raise ValueError("unsupported meta memory version")
        memory = cls(
            rules=tuple(RepairRule.from_payload(row) for row in payload["rules"]),
            episodes=tuple(RepairEpisode.from_payload(row) for row in payload["episodes"]),
        )
        if memory.text() != text:
            raise ValueError("non-canonical meta memory")
        return memory
