from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .lab import opaque_scope


@dataclass(frozen=True)
class FiniteFamily:
    report_name: str
    scope: str
    hypotheses: tuple[int, ...]
    actions: tuple[int, ...]
    predict: Callable[[int, int], int]


def lookup_bits(bits: int = 12) -> FiniteFamily:
    def predict(hypothesis: int, action: int) -> int:
        return (hypothesis >> action) & 1

    return FiniteFamily(
        f"opaque lookup/{bits}",
        opaque_scope(f"binary-lookup-table:v1:bits={bits}"),
        tuple(range(1 << bits)),
        tuple(range(bits)),
        predict,
    )


def affine_binary(dimension: int = 7) -> FiniteFamily:
    def predict(hypothesis: int, action: int) -> int:
        bias = hypothesis & 1
        weights = hypothesis >> 1
        return ((weights & action).bit_count() & 1) ^ bias

    return FiniteFamily(
        f"binary affine/{dimension}",
        opaque_scope(f"gf2-affine:v1:dimension={dimension}"),
        tuple(range(1 << (dimension + 1))),
        tuple(range(1 << dimension)),
        predict,
    )


def affine_mod(prime: int = 17) -> FiniteFamily:
    def predict(hypothesis: int, action: int) -> int:
        a, b = divmod(hypothesis, prime)
        return (a * action + b) % prime

    return FiniteFamily(
        f"modular affine/{prime}",
        opaque_scope(f"prime-affine:v1:p={prime}"),
        tuple(range(prime * prime)),
        tuple(range(prime)),
        predict,
    )


def eca8() -> FiniteFamily:
    width = 8

    def predict(rule: int, row: int) -> int:
        out = 0
        for i in range(width):
            left = (row >> ((i - 1) % width)) & 1
            center = (row >> i) & 1
            right = (row >> ((i + 1) % width)) & 1
            neighborhood = (left << 2) | (center << 1) | right
            out |= ((rule >> neighborhood) & 1) << i
        return out

    return FiniteFamily(
        "cyclic local dynamics/8",
        opaque_scope("eca:v1:width=8:radius=1:binary"),
        tuple(range(256)),
        tuple(range(256)),
        predict,
    )


def quadratic_mod(prime: int = 7) -> FiniteFamily:
    def predict(hypothesis: int, action: int) -> int:
        c = hypothesis % prime
        q = hypothesis // prime
        b = q % prime
        a = q // prime
        return (a * action * action + b * action + c) % prime

    return FiniteFamily(
        f"modular quadratic/{prime}",
        opaque_scope(f"prime-quadratic:v1:p={prime}"),
        tuple(range(prime ** 3)),
        tuple(range(prime)),
        predict,
    )
