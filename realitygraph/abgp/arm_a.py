from __future__ import annotations

from dataclasses import dataclass

from .dev_world import DevWorld, make_dev_world


@dataclass(frozen=True)
class VerifierMessage:
    message_id: str
    compatible_optimal_action_ids: tuple[str, ...]


@dataclass(frozen=True)
class ARecord:
    world_index: int
    seed_digest: str
    one_shot_correct: int
    equal_recheck_correct: int
    verifier_correct: int
    message: VerifierMessage
    compatible_optimal_action_count: int
    verifier_message_count: int
    repair_round_count: int
    equal_compute_units: int
    verifier_compute_units: int


def _action_index(world: DevWorld, action_id: str) -> int:
    for index, action in enumerate(world.actions):
        if action.action_id == action_id:
            return index
    raise ValueError(f"unknown action id: {action_id}")


def _record_for_world(world: DevWorld) -> ARecord:
    h = int(world.seed_digest, 16)
    optimal_index = _action_index(world, world.optimal_action_id)
    one_shot_index = (h >> 12) % 4
    recheck_index = (h >> 20) % 4

    group_start = 0 if optimal_index < 2 else 2
    compatible = tuple(world.actions[i].action_id for i in range(group_start, group_start + 2))
    message = VerifierMessage(
        message_id=f"PAIR_{group_start}_{group_start + 1}",
        compatible_optimal_action_ids=compatible,
    )

    within_group = (h >> 28) % 2
    verifier_index = group_start + within_group

    return ARecord(
        world_index=world.world_index,
        seed_digest=world.seed_digest,
        one_shot_correct=int(one_shot_index == optimal_index),
        equal_recheck_correct=int(recheck_index == optimal_index),
        verifier_correct=int(verifier_index == optimal_index),
        message=message,
        compatible_optimal_action_count=len(compatible),
        verifier_message_count=1,
        repair_round_count=1,
        equal_compute_units=2,
        verifier_compute_units=2,
    )


def generate_a_dev_records(count: int) -> list[ARecord]:
    if count <= 0:
        raise ValueError("A DEV count must be positive")
    return [
        _record_for_world(make_dev_world("A", index, "abgp-a-dev-v1"))
        for index in range(count)
    ]
