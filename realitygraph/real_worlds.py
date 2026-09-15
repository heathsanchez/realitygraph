from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Callable

from .lab import opaque_scope


@dataclass(frozen=True)
class MechanismFamily:
    report_name: str
    category: str
    mechanism: str
    scope: str
    hypotheses: tuple[int, ...]
    actions: tuple[int, ...]
    predict: Callable[[int, int], int]


def _digits(value: int, base: int, width: int) -> tuple[int, ...]:
    out = []
    for _ in range(width):
        out.append(value % base)
        value //= base
    return tuple(out)


def affine_response(name: str, category: str, prime: int) -> MechanismFamily:
    def predict(h: int, x: int) -> int:
        a, b = divmod(h, prime)
        return (a * x + b) % prime

    return MechanismFamily(
        name, category, "affine-response",
        opaque_scope(f"real:affine:{name}:p={prime}"),
        tuple(range(prime * prime)), tuple(range(prime)), predict,
    )


def polynomial_response(
    name: str, category: str, prime: int, degree: int
) -> MechanismFamily:
    count = prime ** (degree + 1)

    def predict(h: int, x: int) -> int:
        coeffs = _digits(h, prime, degree + 1)
        y = 0
        power = 1
        for c in coeffs:
            y = (y + c * power) % prime
            power = (power * x) % prime
        return y

    return MechanismFamily(
        name, category, f"polynomial-{degree}",
        opaque_scope(f"real:poly:{name}:p={prime}:d={degree}"),
        tuple(range(count)), tuple(range(prime)), predict,
    )


def linear_mixer(
    name: str, category: str, prime: int, width: int
) -> MechanismFamily:
    count = prime ** width

    def predict(h: int, action: int) -> int:
        weights = _digits(h, prime, width)
        signal = _digits(action, prime, width)
        return sum(a * b for a, b in zip(weights, signal)) % prime

    return MechanismFamily(
        name, category, f"linear-mixer-{width}",
        opaque_scope(f"real:mixer:{name}:p={prime}:w={width}"),
        tuple(range(count)), tuple(range(count)), predict,
    )


def threshold_detector(
    name: str, category: str, levels: int
) -> MechanismFamily:
    def predict(threshold: int, level: int) -> int:
        return int(level >= threshold)

    return MechanismFamily(
        name, category, "threshold",
        opaque_scope(f"real:threshold:{name}:n={levels}"),
        tuple(range(levels + 1)), tuple(range(levels)), predict,
    )


def interval_detector(
    name: str, category: str, levels: int
) -> MechanismFamily:
    intervals = [(lo, hi) for lo in range(levels) for hi in range(lo, levels)]

    def predict(h: int, level: int) -> int:
        lo, hi = intervals[h]
        return int(lo <= level <= hi)

    return MechanismFamily(
        name, category, "interval-window",
        opaque_scope(f"real:interval:{name}:n={levels}"),
        tuple(range(len(intervals))), tuple(range(levels)), predict,
    )


def cyclic_shift(
    name: str, category: str, symbols: int
) -> MechanismFamily:
    def predict(shift: int, symbol: int) -> int:
        return (symbol + shift) % symbols

    return MechanismFamily(
        name, category, "cyclic-shift",
        opaque_scope(f"real:shift:{name}:n={symbols}"),
        tuple(range(symbols)), tuple(range(symbols)), predict,
    )


def affine_symbol_map(
    name: str, category: str, prime: int
) -> MechanismFamily:
    # Over a prime alphabet every nonzero multiplier is invertible.
    hypotheses = tuple(range((prime - 1) * prime))

    def predict(h: int, symbol: int) -> int:
        a0, b = divmod(h, prime)
        a = a0 + 1
        return (a * symbol + b) % prime

    return MechanismFamily(
        name, category, "affine-symbol-map",
        opaque_scope(f"real:affine-symbol:{name}:p={prime}"),
        hypotheses, tuple(range(prime)), predict,
    )


def channel_rotation(
    name: str, category: str, width: int
) -> MechanismFamily:
    one_hot = tuple(1 << i for i in range(width))
    mask = (1 << width) - 1

    def predict(shift: int, bits: int) -> int:
        return ((bits << shift) | (bits >> (width - shift))) & mask if shift else bits

    return MechanismFamily(
        name, category, "channel-rotation",
        opaque_scope(f"real:rotation:{name}:w={width}"),
        tuple(range(width)), one_hot, predict,
    )


def lane_permutation(
    name: str, category: str, width: int
) -> MechanismFamily:
    perms = tuple(permutations(range(width)))
    actions = tuple(1 << i for i in range(width))

    def predict(h: int, bits: int) -> int:
        perm = perms[h]
        out = 0
        for src in range(width):
            if bits & (1 << src):
                out |= 1 << perm[src]
        return out

    return MechanismFamily(
        name, category, "lane-permutation",
        opaque_scope(f"real:perm:{name}:w={width}"),
        tuple(range(len(perms))), actions, predict,
    )


def truth_table_controller(
    name: str, category: str, inputs: int
) -> MechanismFamily:
    rows = 1 << inputs
    count = 1 << rows

    def predict(table: int, row: int) -> int:
        return (table >> row) & 1

    return MechanismFamily(
        name, category, f"truth-table-{inputs}",
        opaque_scope(f"real:truth:{name}:inputs={inputs}"),
        tuple(range(count)), tuple(range(rows)), predict,
    )


def parity_feedback(
    name: str, category: str, width: int
) -> MechanismFamily:
    count = 1 << width

    def predict(mask: int, state: int) -> int:
        return (mask & state).bit_count() & 1

    return MechanismFamily(
        name, category, "parity-feedback",
        opaque_scope(f"real:parity:{name}:w={width}"),
        tuple(range(count)), tuple(range(count)), predict,
    )


def binary_lookup(
    name: str, category: str, states: int
) -> MechanismFamily:
    count = 1 << states

    def predict(table: int, state: int) -> int:
        return (table >> state) & 1

    return MechanismFamily(
        name, category, "binary-lookup",
        opaque_scope(f"real:lookup2:{name}:states={states}"),
        tuple(range(count)), tuple(range(states)), predict,
    )


def ternary_lookup(
    name: str, category: str, states: int
) -> MechanismFamily:
    count = 3 ** states

    def predict(table: int, state: int) -> int:
        return _digits(table, 3, states)[state]

    return MechanismFamily(
        name, category, "ternary-lookup",
        opaque_scope(f"real:lookup3:{name}:states={states}"),
        tuple(range(count)), tuple(range(states)), predict,
    )


def real_world_suite() -> tuple[MechanismFamily, ...]:
    """Mechanism-grounded finite worlds spanning real engineering tasks.

    These are exact parameterized mechanisms, not claims of empirical data.
    Hidden parameters are chosen after freeze by the benchmark seed.
    """
    return (
        # sensing / calibration
        affine_response("thermometer gain-offset", "sensing", 11),
        affine_response("ADC gain-offset", "sensing", 13),
        affine_response("clock drift correction", "timing", 17),
        affine_response("flow-meter calibration", "sensing", 19),
        polynomial_response("pressure transducer curve", "sensing", 5, 2),
        polynomial_response("battery gauge curve", "energy", 7, 2),
        polynomial_response("lens correction curve", "imaging", 11, 2),
        polynomial_response("motor torque curve", "control", 5, 3),

        # linear signal/control mechanisms
        linear_mixer("two-channel audio mix", "signal", 5, 2),
        linear_mixer("three-axis sensor fusion", "sensing", 3, 3),
        linear_mixer("two-input actuator mix", "control", 7, 2),
        linear_mixer("three-tap FIR response", "signal", 5, 3),

        # alarms / operating envelopes
        threshold_detector("thermostat trip", "control", 12),
        threshold_detector("over-current relay", "energy", 16),
        threshold_detector("pressure relief alarm", "safety", 20),
        threshold_detector("RPM limiter", "control", 24),
        interval_detector("comfort temperature band", "control", 8),
        interval_detector("safe pressure band", "safety", 9),
        interval_detector("valid battery voltage band", "energy", 10),
        interval_detector("acceptable vibration band", "maintenance", 12),

        # phase / coding / symbol transforms
        cyclic_shift("rotary encoder phase", "timing", 12),
        cyclic_shift("TDMA scheduler phase", "networking", 16),
        cyclic_shift("alphabet shift channel", "communications", 26),
        cyclic_shift("antenna phase index", "signal", 32),
        affine_symbol_map("small telemetry scrambler", "communications", 7),
        affine_symbol_map("packet symbol remap", "networking", 11),
        affine_symbol_map("finite field interleaver map", "coding", 17),

        # wiring / routing / permutations
        channel_rotation("LED ring phase wiring", "hardware", 8),
        channel_rotation("serializer lane rotation", "hardware", 12),
        channel_rotation("cyclic bus offset", "hardware", 16),
        lane_permutation("four-lane cable wiring", "hardware", 4),
        lane_permutation("five-channel sensor wiring", "sensing", 5),
        lane_permutation("six-lane serializer wiring", "hardware", 6),

        # logic / finite controllers
        truth_table_controller("two-input relay logic", "control", 2),
        truth_table_controller("three-input safety interlock", "safety", 3),
        binary_lookup("six-state valve controller", "control", 6),
        binary_lookup("eight-state protocol flag", "networking", 8),
        binary_lookup("ten-state fault decoder", "maintenance", 10),
        ternary_lookup("four-state traffic controller", "control", 4),
        ternary_lookup("five-state device mode map", "hardware", 5),
        ternary_lookup("six-state protocol response", "networking", 6),

        # feedback / parity / error detection
        parity_feedback("five-tap LFSR feedback", "coding", 5),
        parity_feedback("six-line parity checker", "coding", 6),
        parity_feedback("seven-bit syndrome mask", "coding", 7),
        parity_feedback("eight-bit packet parity mask", "networking", 8),
    )
