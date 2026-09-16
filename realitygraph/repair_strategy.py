from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .developmental_types import canonical_digest


class RepairStrategy(Protocol):
    strategy_id: str
    strategy_version: str
    structural_cost: int

    def applicable(self, fingerprint, object_state, meta_spec) -> bool: ...

    def materialize_generation_spec(self, object_state, meta_spec): ...


@dataclass(frozen=True)
class RepairPortfolio:
    strategies: tuple[RepairStrategy, ...]

    def __post_init__(self) -> None:
        if not self.strategies:
            raise ValueError("repair portfolio requires at least one strategy")
        ids: list[str] = []
        for strategy in self.strategies:
            ident = str(getattr(strategy, "strategy_id", ""))
            version = str(getattr(strategy, "strategy_version", ""))
            cost = int(getattr(strategy, "structural_cost", -1))
            if not ident:
                raise ValueError("repair strategy requires strategy_id")
            if not version:
                raise ValueError("repair strategy requires strategy_version")
            if cost < 0:
                raise ValueError("repair strategy structural_cost must be non-negative")
            ids.append(ident)
        if len(ids) != len(set(ids)):
            raise ValueError("repair strategy IDs must be unique")

    @property
    def strategy_map(self) -> dict[str, RepairStrategy]:
        return {str(strategy.strategy_id): strategy for strategy in self.strategies}

    @property
    def strategy_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.strategy_map))

    def get(self, strategy_id: str) -> RepairStrategy:
        try:
            return self.strategy_map[str(strategy_id)]
        except KeyError as exc:
            raise ValueError(f"unknown repair strategy: {strategy_id}") from exc

    def payload(self) -> dict[str, object]:
        rows = sorted(
            (
                str(strategy.strategy_id),
                str(strategy.strategy_version),
                int(strategy.structural_cost),
            )
            for strategy in self.strategies
        )
        return {
            "strategies": [
                {
                    "strategy_id": ident,
                    "strategy_version": version,
                    "structural_cost": cost,
                }
                for ident, version, cost in rows
            ]
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="repair-portfolio-v3:")
