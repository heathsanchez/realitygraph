"""Execute finite cell interventions against a supplied protected evaluator.

Unlike the historical planted G fixtures, flip labels are derived by evaluating
both the unmodified and modified object. Relevance is audited over the supplied
finite intervention alphabet. Exhaustiveness outside that alphabet is not claimed.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Iterable, Mapping, Sequence
from .dev_world import DevWorld

Evaluator = Callable[[DevWorld], Sequence[str]]


def legacy_world_order(world: DevWorld) -> tuple[str, ...]:
    """Read the existing world's protected-action truth without inventing semantics.

    The legacy world stores this label independently of all comparative cells.
    Consequently its cells cannot justify its pre-assigned relevance annotations.
    """
    ids = tuple(action.action_id for action in world.actions)
    start = ids.index(world.optimal_action_id)
    return ids[start:] + ids[:start]


def evaluate_corruption(world: DevWorld, evaluator: Evaluator,
                        replacements: Mapping[str, int]) -> dict[str, Any]:
    cells = {c.cell_id for c in world.comparative_cells}
    if not set(replacements) <= cells or any(type(v) is not int for v in replacements.values()):
        raise ValueError('corruption must specify existing cell IDs and integer values')
    changed = replace(world, comparative_cells=tuple(
        replace(cell, value=replacements[cell.cell_id]) if cell.cell_id in replacements else cell
        for cell in world.comparative_cells))
    before, after = tuple(evaluator(world)), tuple(evaluator(changed))
    return {'before': before, 'after': after, 'flip': int(before != after),
            'replacement_values': dict(replacements), 'evaluator_calls': 2}


def audit_relevance(world: DevWorld, evaluator: Evaluator,
                    admissible_values: Iterable[int]) -> dict[str, Any]:
    values = tuple(admissible_values)
    if not values or len(set(values)) != len(values) or any(type(v) is not int for v in values):
        raise ValueError('need a finite distinct integer intervention alphabet')
    base = tuple(evaluator(world))
    calls, actual, witnesses = 1, [], {}
    for cell in world.comparative_cells:
        alternatives = []
        for value in values:
            if value == cell.value:
                continue
            changed = replace(world, comparative_cells=tuple(
                replace(c, value=value) if c.cell_id == cell.cell_id else c for c in world.comparative_cells))
            after = tuple(evaluator(changed))
            calls += 1
            if after != base:
                alternatives.append({'replacement': value, 'before': base, 'after': after})
        if alternatives:
            actual.append(cell.cell_id)
            witnesses[cell.cell_id] = alternatives
    declared = [c.cell_id for c in world.comparative_cells if c.action_relevant]
    return {'world_index': world.world_index, 'actual_relevant_cell_ids': actual,
            'declared_relevant_cell_ids': declared,
            'declared_relevance_matches': set(actual) == set(declared),
            'eligible_matched_corruption_design': bool(actual) and len(actual) < len(world.comparative_cells),
            'evaluations': calls, 'admissible_values': values, 'separating_witnesses': witnesses,
            'scope': 'complete single-cell interventions over specified finite alphabet'}
