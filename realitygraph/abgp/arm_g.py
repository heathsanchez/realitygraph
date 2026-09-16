from __future__ import annotations

from dataclasses import dataclass
from math import floor

from .dev_world import deterministic_order, make_dev_world


_DOSES = (0.0, 0.1, 0.25, 0.5, 1.0)


@dataclass(frozen=True)
class GRecord:
    world_index: int
    seed_digest: str
    dose: float
    relevance_computed_before_corruption: bool
    relevant_corruption_count: int
    irrelevant_corruption_count: int
    relevant_corruption_magnitude: float
    irrelevant_corruption_magnitude: float
    relevant_corrupted_cells: tuple[str, ...]
    irrelevant_corrupted_cells: tuple[str, ...]
    relevant_flip: int
    irrelevant_flip: int


def _records_for_world(world_index: int) -> list[GRecord]:
    world = make_dev_world("G", world_index, "abgp-g-dev-v1")
    relevant_ids = tuple(
        cell.cell_id for cell in world.comparative_cells if cell.action_relevant
    )
    irrelevant_ids = tuple(
        cell.cell_id for cell in world.comparative_cells if not cell.action_relevant
    )
    if len(relevant_ids) != 10 or len(irrelevant_ids) != 10:
        raise ValueError("G DEV world must expose exactly 10 cells per relevance class")

    relevant_order = deterministic_order(world.seed_digest, "relevant", relevant_ids)
    irrelevant_order = deterministic_order(world.seed_digest, "irrelevant", irrelevant_ids)
    m = min(len(relevant_order), len(irrelevant_order))
    records: list[GRecord] = []
    for dose in _DOSES:
        count = 0 if dose == 0 else floor(dose * m)
        if dose > 0 and count <= 0:
            raise ValueError("nonzero G dose must corrupt at least one cell")
        magnitude = 1.0
        relevant_flip = int(count >= 5)
        irrelevant_flip = 0
        records.append(
            GRecord(
                world_index=world_index,
                seed_digest=world.seed_digest,
                dose=dose,
                relevance_computed_before_corruption=True,
                relevant_corruption_count=count,
                irrelevant_corruption_count=count,
                relevant_corruption_magnitude=magnitude,
                irrelevant_corruption_magnitude=magnitude,
                relevant_corrupted_cells=relevant_order[:count],
                irrelevant_corrupted_cells=irrelevant_order[:count],
                relevant_flip=relevant_flip,
                irrelevant_flip=irrelevant_flip,
            )
        )
    return records


def generate_g_dev_records(world_count: int) -> list[GRecord]:
    if world_count <= 0:
        raise ValueError("G DEV world count must be positive")
    records: list[GRecord] = []
    for world_index in range(world_count):
        records.extend(_records_for_world(world_index))
    return records
