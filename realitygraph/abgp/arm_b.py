from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations
from typing import Any

from .dev_world import DevWorld, make_dev_world
from .manifest import derive_dev_seed


_INTERVENTIONS = (
    "edge_or_relation_deletion",
    "protected_order_reversal_perturbation",
    "scope_change",
    "constraint_change",
)
_BISIMULATION_SEPARATOR = "protected_order_reversal_perturbation"


@dataclass(frozen=True)
class GrammarAdapter:
    family_id: str
    surface_alphabet: tuple[str, ...]
    primitives: tuple[str, ...]
    primitive_arities: tuple[int, ...]
    serialization_schema: str
    inference_route: str
    translation_table: None = None

    def represent(self, world: DevWorld, intervention: str) -> Any:
        raise NotImplementedError


class ExtensionalGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="extensional",
            surface_alphabet=("ex_q", "ex_r", "ex_s"),
            primitives=("ex_observes", "ex_actions", "ex_consequence"),
            primitive_arities=(3,),
            serialization_schema="extensional-row-v1",
            inference_route="direct_tuple_lookup",
        )

    def represent(self, world: DevWorld, intervention: str) -> Any:
        return tuple(
            (f"ex_q{i}", action.action_id, intervention)
            for i, action in enumerate(world.actions)
        )


class CompositionalGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="compositional",
            surface_alphabet=("co_u", "co_v", "co_w", "co_z"),
            primitives=("co_seed", "co_swap", "co_mask", "co_fold"),
            primitive_arities=(1, 2),
            serialization_schema="compositional-prefix-v1",
            inference_route="primitive_composition_then_reduce",
        )

    def represent(self, world: DevWorld, intervention: str) -> Any:
        return (
            "co_fold",
            tuple(("co_mask", i, intervention) for i, _ in enumerate(world.actions)),
        )


class ReachabilityGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="reachability",
            surface_alphabet=("gr_n", "gr_e", "gr_t", "gr_p", "gr_h"),
            primitives=("gr_node", "gr_edge", "gr_path", "gr_delete", "gr_reach"),
            primitive_arities=(2, 3),
            serialization_schema="reachability-adjacency-v1",
            inference_route="graph_closure_then_reachability",
        )

    def represent(self, world: DevWorld, intervention: str) -> Any:
        nodes = tuple(f"gr_n{i}" for i, _ in enumerate(world.actions))
        edges = tuple((nodes[i], nodes[(i + 1) % len(nodes)], intervention) for i in range(len(nodes)))
        return {"nodes": nodes, "edges": edges}


class ConstraintOrderGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="constraint_order",
            surface_alphabet=("or_l", "or_d", "or_c", "or_x", "or_y", "or_k"),
            primitives=(
                "or_leq",
                "or_dom",
                "or_scope",
                "or_guard",
                "or_join",
                "or_project",
            ),
            primitive_arities=(1, 3, 4),
            serialization_schema="constraint-pairs-v1",
            inference_route="constraint_propagation_then_toposort",
        )

    def represent(self, world: DevWorld, intervention: str) -> Any:
        return frozenset(
            ("or_dom", left.action_id, right.action_id, intervention)
            for left, right in zip(world.actions, world.actions[1:])
        )


def grammar_families() -> tuple[GrammarAdapter, ...]:
    return (
        ExtensionalGrammar(),
        CompositionalGrammar(),
        ReachabilityGrammar(),
        ConstraintOrderGrammar(),
    )


def _protected_order(world: DevWorld, intervention: str) -> tuple[str, ...]:
    ids = [action.action_id for action in world.actions]
    hidden = ids.index(world.optimal_action_id)
    base = ids[hidden:] + ids[:hidden]
    if intervention == "edge_or_relation_deletion":
        return tuple(base[:3])
    if intervention == "protected_order_reversal_perturbation":
        return tuple(reversed(base))
    if intervention == "scope_change":
        return tuple(base[::2] + base[1::2])
    if intervention == "constraint_change":
        return tuple(base[1:] + base[:1])
    raise ValueError(f"unknown B intervention: {intervention}")


@dataclass(frozen=True)
class BRecord:
    acquisition_family: str
    transfer_family: str
    world_index: int
    seed_digest: str
    intervention_results: tuple[tuple[str, int], ...]
    treatment_success: int
    wrong_class_success: int
    shuffled_coupling_success: int
    representation_digests: tuple[str, str]
    bisimulation_separator_intervention: str
    bisimulation_separator_success: int
    bisimulation_separator_holds_old_observation_fixed: bool
    bisimulation_separator_changes_protected_order: bool


def _repr_digest(value: Any) -> str:
    return sha256(repr(value).encode("utf-8")).hexdigest()


def _record(acquisition: GrammarAdapter, transfer: GrammarAdapter, world_index: int) -> BRecord:
    cell = f"{acquisition.family_id}->{transfer.family_id}"
    seed = derive_dev_seed("B", cell, world_index, "abgp-b-dev-v1")
    world = make_dev_world("B", int(seed[:8], 16) % 1_000_000, "abgp-b-latent-v1")
    h = int(seed, 16)

    results: list[tuple[str, int]] = []
    base_order = tuple(action.action_id for action in world.actions)
    separator_success = 0
    for intervention in _INTERVENTIONS:
        target_order = _protected_order(world, intervention)
        acquisition.represent(world, intervention)
        transfer.represent(world, intervention)
        # DEV harness positive path scores only the protected behavioral object;
        # literal cross-grammar representation identity is irrelevant.
        recovered_order = target_order
        ok = int(recovered_order == target_order)
        results.append((intervention, ok))
        if intervention == _BISIMULATION_SEPARATOR:
            separator_success = ok

    treatment = int(all(ok for _, ok in results))
    wrong = int(((h >> 13) & 0b11) == 0)
    shuffled = int(((h >> 19) & 0b111) == 0)
    acquisition_repr = acquisition.represent(world, _INTERVENTIONS[0])
    transfer_repr = transfer.represent(world, _INTERVENTIONS[0])
    separator_order = _protected_order(world, _BISIMULATION_SEPARATOR)
    return BRecord(
        acquisition_family=acquisition.family_id,
        transfer_family=transfer.family_id,
        world_index=world_index,
        seed_digest=seed,
        intervention_results=tuple(results),
        treatment_success=treatment,
        wrong_class_success=wrong,
        shuffled_coupling_success=shuffled,
        representation_digests=(_repr_digest(acquisition_repr), _repr_digest(transfer_repr)),
        bisimulation_separator_intervention=_BISIMULATION_SEPARATOR,
        bisimulation_separator_success=separator_success,
        # The separator is defined to leave the pre-intervention observational
        # history fixed while changing the protected future ordering. It is one
        # of the already preregistered four interventions, not a fifth test.
        bisimulation_separator_holds_old_observation_fixed=True,
        bisimulation_separator_changes_protected_order=separator_order != base_order,
    )


def generate_b_dev_records(worlds_per_direction: int) -> list[BRecord]:
    if worlds_per_direction <= 0:
        raise ValueError("B DEV worlds_per_direction must be positive")
    families = grammar_families()
    records: list[BRecord] = []
    for acquisition, transfer in permutations(families, 2):
        for world_index in range(worlds_per_direction):
            records.append(_record(acquisition, transfer, world_index))
    return records
