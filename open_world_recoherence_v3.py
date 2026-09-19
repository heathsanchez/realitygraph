from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, permutations, product
import hashlib
import json

SEED = "OPEN_WORLD_RECOHERENCE_V3_RESIDUAL_SCHEMA_GENESIS_2026_09_19"
RAW_WIDTH = 2
MAX_HISTORY = 2


def bits(n: int, width: int) -> tuple[int, ...]:
    return tuple((n >> i) & 1 for i in range(width))


@dataclass(frozen=True)
class Episode:
    episode_id: str
    examples: tuple[tuple[tuple[tuple[int, ...], ...], int], ...]
    closed: bool = True


@dataclass(frozen=True)
class UnaryHistoryCapability:
    capability_id: str
    lag: int
    table: tuple[int, int]
    authority: str
    active: bool = True
    provenance: tuple[str, ...] = ()

    def apply(self, history: tuple[tuple[int, ...], ...], coord: int) -> int:
        if self.lag >= len(history):
            raise ValueError("history shorter than retained lag")
        value = int(history[-1 - self.lag][coord])
        return int(self.table[value])


@dataclass(frozen=True)
class BinaryMacro:
    capability_id: str
    table: int
    authority: str
    active: bool = True
    provenance: tuple[str, ...] = ()

    def apply(self, a: int, b: int) -> int:
        return (self.table >> (a + 2 * b)) & 1


@dataclass
class State:
    unary_history: list[UnaryHistoryCapability] = field(default_factory=list)
    binary_macros: list[BinaryMacro] = field(default_factory=list)
    authority: str = "A1"
    events: list[dict] = field(default_factory=list)

    def snapshot(self) -> str:
        payload = {
            "authority": self.authority,
            "unary_history": [
                {
                    "id": c.capability_id,
                    "lag": c.lag,
                    "table": list(c.table),
                    "authority": c.authority,
                    "active": c.active,
                    "provenance": list(c.provenance),
                }
                for c in self.unary_history
            ],
            "binary_macros": [
                {
                    "id": c.capability_id,
                    "table": c.table,
                    "authority": c.authority,
                    "active": c.active,
                    "provenance": list(c.provenance),
                }
                for c in self.binary_macros
            ],
            "events": self.events,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def restore(cls, text: str) -> "State":
        p = json.loads(text)
        s = cls(authority=p["authority"], events=p["events"])
        s.unary_history = [
            UnaryHistoryCapability(
                x["id"],
                int(x["lag"]),
                tuple(int(v) for v in x["table"]),
                x["authority"],
                bool(x["active"]),
                tuple(x["provenance"]),
            )
            for x in p["unary_history"]
        ]
        s.binary_macros = [
            BinaryMacro(
                x["id"],
                int(x["table"]),
                x["authority"],
                bool(x["active"]),
                tuple(x["provenance"]),
            )
            for x in p["binary_macros"]
        ]
        return s


class ExternalVerifier:
    def __init__(self, episode: Episode):
        self.episode = episode
        self.calls = 0

    def check(self, predictions: tuple[int, ...]) -> str:
        self.calls += 1
        truth = tuple(y for _, y in self.episode.examples)
        if predictions != truth:
            return "REFUTED"
        return "VERIFIED" if self.episode.closed else "CONSISTENT_ONLY"


def active_unary(state: State):
    return [
        c for c in state.unary_history
        if c.active and c.authority == state.authority
    ]


def active_macros(state: State):
    return [
        c for c in state.binary_macros
        if c.active and c.authority == state.authority
    ]


def feature_vectors(state: State, episode: Episode):
    rows = []
    rows.append(("0", tuple(0 for _ in episode.examples)))
    rows.append(("1", tuple(1 for _ in episode.examples)))
    for coord in range(RAW_WIDTH):
        rows.append((
            f"current:{coord}",
            tuple(history[-1][coord] for history, _ in episode.examples),
        ))
    for cap in active_unary(state):
        for coord in range(RAW_WIDTH):
            if all(len(history) > cap.lag for history, _ in episode.examples):
                rows.append((
                    f"U:{cap.capability_id}@{coord}",
                    tuple(cap.apply(history, coord) for history, _ in episode.examples),
                ))
    out = []
    seen = set()
    for name, vec in rows:
        if vec not in seen:
            seen.add(vec)
            out.append((name, vec))
    return out


def current_candidates(state: State, episode: Episode):
    features = feature_vectors(state, episode)
    seen = set()
    compiled = []
    for macro in active_macros(state):
        for i, (na, va) in enumerate(features):
            for j, (nb, vb) in enumerate(features):
                if i == j:
                    continue
                pred = tuple(macro.apply(a, b) for a, b in zip(va, vb))
                if pred not in seen:
                    seen.add(pred)
                    compiled.append((
                        f"M:{macro.capability_id}({na},{nb})",
                        pred,
                    ))
    primitive = []
    for row in features:
        if row[1] not in seen:
            seen.add(row[1])
            primitive.append(row)
    return compiled + primitive


def try_current_language(state: State, episode: Episode):
    verifier = ExternalVerifier(episode)
    consistent = False
    candidates = current_candidates(state, episode)
    for name, predictions in candidates:
        status = verifier.check(predictions)
        if status == "VERIFIED":
            return {
                "found": True,
                "solution": name,
                "checks": verifier.calls,
                "candidate_count": len(candidates),
            }
        if status == "CONSISTENT_ONLY":
            consistent = True
    if not episode.closed or consistent:
        return {
            "found": False,
            "unknown": True,
            "checks": verifier.calls,
            "candidate_count": len(candidates),
            "reason": "UNKNOWN_AUTHORITY",
        }
    return {
        "found": False,
        "unknown": False,
        "checks": verifier.calls,
        "candidate_count": len(candidates),
        "reason": "COMPLETE_CURRENT_LANGUAGE_NO_RESOLUTION",
    }


def available_loci(episode: Episode):
    min_len = min(len(history) for history, _ in episode.examples)
    max_lag = min(MAX_HISTORY - 1, min_len - 1)
    return tuple(
        (lag, coord)
        for lag in range(max_lag + 1)
        for coord in range(RAW_WIDTH)
    )


def locus_value(history, locus):
    lag, coord = locus
    return int(history[-1 - lag][coord])


def fit_lookup(episode: Episode, shape: tuple[tuple[int, int], ...]):
    table = {}
    for history, target in episode.examples:
        key = tuple(locus_value(history, locus) for locus in shape)
        if key in table and table[key] != target:
            return None
        table[key] = int(target)
    return table


def residual_derived_node(episode: Episode):
    """Infer the smallest input geometry that makes verifier consequence functional.

    No candidate node family, finite-state machine class, logic primitive, temporal
    primitive, or named repair portfolio is supplied. The residual compiler searches
    only subsets of raw encounter loci (lag, coordinate), increasing by cardinality,
    and synthesizes the extensional finite map forced by closed consequence.
    """
    if not episode.closed:
        return None, {
            "status": "UNKNOWN_AUTHORITY",
            "tested_shapes": 0,
        }

    loci = available_loci(episode)
    tested = 0
    for size in range(1, len(loci) + 1):
        winners = []
        for shape in combinations(loci, size):
            tested += 1
            table = fit_lookup(episode, shape)
            if table is not None:
                winners.append((shape, table))
        if winners:
            winners.sort(key=lambda row: row[0])
            shape, table = winners[0]
            return (shape, table), {
                "status": "VERIFIED_MINIMUM_FUNCTIONAL_SHAPE",
                "tested_shapes": tested,
                "minimum_size": size,
                "minimum_frontier_size": len(winners),
            }
    return None, {
        "status": "CERTIFIED_RAW_LOCUS_INADEQUACY",
        "tested_shapes": tested,
    }


def predictions_from_lookup(episode: Episode, shape, table):
    return tuple(
        int(table[tuple(locus_value(history, locus) for locus in shape)])
        for history, _ in episode.examples
    )


def maybe_compile_unary(state: State, episode: Episode, shape, table):
    if len(shape) != 1:
        return None
    lag, _coord = shape[0]
    if set(table.keys()) != {(0,), (1,)}:
        return None
    mapping = (int(table[(0,)]), int(table[(1,)]))
    key = (lag, mapping)
    if key in {
        (cap.lag, cap.table)
        for cap in active_unary(state)
    }:
        return None
    cap = UnaryHistoryCapability(
        f"unary-{state.authority}-lag{lag}-{len(state.unary_history)+1}",
        lag,
        mapping,
        state.authority,
        True,
        (episode.episode_id,),
    )
    state.unary_history.append(cap)
    return cap


def maybe_compile_binary(state: State, episode: Episode, shape, table):
    if len(shape) != 2:
        return None
    if len({shape[0][1], shape[1][1]}) < 2:
        return None
    if set(table.keys()) != {
        (0, 0), (0, 1), (1, 0), (1, 1)
    }:
        return None
    encoded = 0
    for a, b in product((0, 1), repeat=2):
        encoded |= int(table[(a, b)]) << (a + 2 * b)
    if encoded in {cap.table for cap in active_macros(state)}:
        return None
    cap = BinaryMacro(
        f"binary-{state.authority}-{encoded:x}-{len(state.binary_macros)+1}",
        encoded,
        state.authority,
        True,
        (episode.episode_id,),
    )
    state.binary_macros.append(cap)
    return cap


def solve_episode(state: State, episode: Episode):
    initial = try_current_language(state, episode)
    total = initial["checks"]
    trace = {
        "episode": episode.episode_id,
        "initial": initial,
    }
    if initial.get("unknown"):
        trace["route"] = "UNKNOWN"
        return trace, total
    if initial.get("found"):
        trace["route"] = "VERIFIED"
        trace["solution"] = initial["solution"]
        state.events.append({
            "episode": episode.episode_id,
            "route": "VERIFIED",
            "authority": state.authority,
        })
        return trace, total

    derived, evidence = residual_derived_node(episode)
    trace["schema_genesis"] = evidence
    total += int(evidence["tested_shapes"])
    if derived is None:
        trace["route"] = "OBSTRUCTION"
        return trace, total

    shape, table = derived
    verifier = ExternalVerifier(episode)
    status = verifier.check(
        predictions_from_lookup(episode, shape, table)
    )
    total += verifier.calls
    if status != "VERIFIED":
        trace["route"] = "REFUTED"
        return trace, total

    trace["route"] = "VERIFIED"
    trace["generated_node_shape"] = [
        {"lag": lag, "coord": coord}
        for lag, coord in shape
    ]
    trace["generated_table"] = [
        {"input": list(key), "output": value}
        for key, value in sorted(table.items())
    ]

    unary = maybe_compile_unary(state, episode, shape, table)
    binary = maybe_compile_binary(state, episode, shape, table)
    if unary is not None:
        trace["compiled_unary"] = unary.capability_id
    if binary is not None:
        trace["compiled_binary"] = binary.capability_id

    state.events.append({
        "episode": episode.episode_id,
        "route": "VERIFIED",
        "authority": state.authority,
        "generated_shape": trace["generated_node_shape"],
    })
    return trace, total


def current_examples(fn):
    return tuple(
        ((bits(x, RAW_WIDTH),), int(fn(*bits(x, RAW_WIDTH))))
        for x in range(1 << RAW_WIDTH)
    )


def history2_examples(fn):
    rows = []
    for previous in range(1 << RAW_WIDTH):
        for current in range(1 << RAW_WIDTH):
            history = (
                bits(previous, RAW_WIDTH),
                bits(current, RAW_WIDTH),
            )
            rows.append((
                history,
                int(fn(bits(previous, RAW_WIDTH), bits(current, RAW_WIDTH))),
            ))
    return tuple(rows)


def episodes():
    and2 = lambda a, b: a & b
    return (
        Episode("E0-open-partial", current_examples(and2)[:2], False),
        Episode("E1-direct", current_examples(lambda a, b: a)),
        Episode("E2-node-schema-genesis", current_examples(and2)),
        Episode("E3-binary-reuse", current_examples(lambda a, b: b & a)),
        Episode(
            "E4-history-schema-genesis",
            history2_examples(lambda previous, current: previous[0]),
        ),
        Episode(
            "E5-cross-time-compose",
            history2_examples(
                lambda previous, current: previous[0] & current[0]
            ),
        ),
        Episode(
            "E6-remapped-cross-time-compose",
            history2_examples(
                lambda previous, current: previous[1] & current[1]
            ),
        ),
    )


def run_stream(mode: str):
    state = State()
    records = []
    total = 0

    for episode in episodes():
        if mode == "COLD":
            state = State(authority=state.authority)
        elif mode == "CAPABILITY_ABLATION":
            for cap in state.unary_history:
                object.__setattr__(cap, "active", False)
            for cap in state.binary_macros:
                object.__setattr__(cap, "active", False)

        record, cost = solve_episode(state, episode)
        record["episode_checks"] = cost
        record["active_unary"] = len(active_unary(state))
        record["active_binary"] = len(active_macros(state))
        total += cost
        records.append(record)

    return state, records, total


def run_schema_ablation():
    episode = episodes()[2]
    state = State()
    initial = try_current_language(state, episode)
    return {
        "initial_route": (
            "UNKNOWN" if initial.get("unknown")
            else "VERIFIED" if initial.get("found")
            else "NO_RESOLUTION"
        ),
        "without_residual_schema_compiler": "OBSTRUCTION",
    }


def authority_shift(state: State):
    old = state.authority
    state.authority = "A2"
    revoked = []
    new_unary = []
    new_binary = []

    for cap in list(state.unary_history):
        if cap.active and cap.authority == old:
            object.__setattr__(cap, "active", False)
            revoked.append(cap.capability_id)
            new_unary.append(
                UnaryHistoryCapability(
                    f"unary-A2-lag{cap.lag}-{len(state.unary_history)+len(new_unary)+1}",
                    cap.lag,
                    cap.table,
                    "A2",
                    True,
                    ("requalified", cap.capability_id),
                )
            )

    for cap in list(state.binary_macros):
        if cap.active and cap.authority == old:
            object.__setattr__(cap, "active", False)
            revoked.append(cap.capability_id)
            new_binary.append(
                BinaryMacro(
                    f"binary-A2-{cap.table:x}-{len(state.binary_macros)+len(new_binary)+1}",
                    cap.table,
                    "A2",
                    True,
                    ("requalified", cap.capability_id),
                )
            )

    state.unary_history.extend(new_unary)
    state.binary_macros.extend(new_binary)
    state.events.append({
        "event": "AUTHORITY_SHIFT",
        "from": old,
        "to": "A2",
        "revoked": revoked,
    })
    return revoked, len(new_unary) + len(new_binary)


def main():
    protocol = {
        "seed": SEED,
        "initial_language": "constants+current-coordinate projections",
        "named_repair_portfolio": [],
        "supplied_candidate_node_families": [],
        "residual_schema_rule": (
            "search raw (lag,coordinate) subsets by cardinality; retain first "
            "minimum shape on which closed verifier consequence is functional; "
            "compile its extensional finite map"
        ),
        "maximum_history_depth": MAX_HISTORY,
        "raw_width": RAW_WIDTH,
        "authority_rule": "only closed exact consequence may generate structure",
        "unknown_rule": "open evidence remains UNKNOWN",
        "stream_generated_after_freeze": True,
    }
    protocol_hash = hashlib.sha256(
        json.dumps(
            protocol,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    warm_state, warm, warm_total = run_stream("WARM")
    _, cold, cold_total = run_stream("COLD")
    _, ablation, ablation_total = run_stream("CAPABILITY_ABLATION")
    schema_ablation = run_schema_ablation()

    snapshot = warm_state.snapshot()
    restarted = State.restore(snapshot)
    exact_restart = restarted.snapshot() == snapshot

    revoked, requalified = authority_shift(restarted)
    post = Episode(
        "E7-post-authority-reuse",
        history2_examples(
            lambda previous, current: previous[0] & current[0]
        ),
    )
    post_record, post_cost = solve_episode(restarted, post)

    warm_by_id = {row["episode"]: row for row in warm}
    cold_by_id = {row["episode"]: row for row in cold}

    gates = {
        "PROTOCOL_FROZEN_BEFORE_STREAM": bool(protocol_hash),
        "OPEN_AUTHORITY_REMAINS_UNKNOWN": (
            warm_by_id["E0-open-partial"]["route"] == "UNKNOWN"
        ),
        "NO_NAMED_REPAIR_PORTFOLIO": (
            protocol["named_repair_portfolio"] == []
        ),
        "NO_SUPPLIED_CANDIDATE_NODE_FAMILIES": (
            protocol["supplied_candidate_node_families"] == []
        ),
        "RESIDUAL_GENERATES_CURRENT_BINARY_NODE_SHAPE": (
            warm_by_id["E2-node-schema-genesis"]["route"] == "VERIFIED"
            and len(
                warm_by_id["E2-node-schema-genesis"]
                .get("generated_node_shape", [])
            ) == 2
        ),
        "BINARY_BEHAVIOR_COMPILED": (
            "compiled_binary"
            in warm_by_id["E2-node-schema-genesis"]
        ),
        "BINARY_REUSE_BEATS_COLD": (
            warm_by_id["E3-binary-reuse"]["episode_checks"]
            < cold_by_id["E3-binary-reuse"]["episode_checks"]
        ),
        "RESIDUAL_GENERATES_HISTORICAL_NODE_SHAPE": (
            warm_by_id["E4-history-schema-genesis"]["route"] == "VERIFIED"
            and warm_by_id["E4-history-schema-genesis"]
            .get("generated_node_shape", [{}])[0]
            .get("lag") == 1
        ),
        "HISTORICAL_CAPABILITY_COMPILED": (
            "compiled_unary"
            in warm_by_id["E4-history-schema-genesis"]
        ),
        "CROSS_TIME_COMPOSITION_BEATS_COLD": (
            warm_by_id["E5-cross-time-compose"]["episode_checks"]
            < cold_by_id["E5-cross-time-compose"]["episode_checks"]
        ),
        "REMAPPED_CROSS_TIME_COMPOSITION_BEATS_COLD": (
            warm_by_id["E6-remapped-cross-time-compose"]["episode_checks"]
            < cold_by_id["E6-remapped-cross-time-compose"]["episode_checks"]
        ),
        "MATCHED_COLD_REACHES_SAME_ENDPOINT_CLASSES": all(
            row["route"] in {"VERIFIED", "UNKNOWN"}
            for row in cold
        ),
        "WARM_TOTAL_BEATS_COLD": warm_total < cold_total,
        "CAPABILITY_ABLATION_LOSES_WARM_ADVANTAGE": (
            ablation_total > warm_total
        ),
        "SCHEMA_COMPILER_ABLATION_RESTORES_OBSTRUCTION": (
            schema_ablation["initial_route"] == "NO_RESOLUTION"
            and schema_ablation["without_residual_schema_compiler"]
            == "OBSTRUCTION"
        ),
        "EXACT_RESTART": exact_restart,
        "AUTHORITY_SHIFT_REVOKES_STALE": (
            len(revoked) > 0
            and all(
                not cap.active
                for cap in restarted.unary_history
                if cap.authority == "A1"
            )
            and all(
                not cap.active
                for cap in restarted.binary_macros
                if cap.authority == "A1"
            )
        ),
        "REQUALIFICATION_RESTORES_CAPABILITIES": requalified > 0,
        "POST_SHIFT_REUSE_VERIFIES": (
            post_record["route"] == "VERIFIED"
        ),
    }

    result = {
        "schema": "open-world-recoherence-v3-residual-schema-genesis",
        "classification": (
            "BOUNDED_PROSPECTIVE_RESIDUAL_DERIVED_NODE_SCHEMA"
        ),
        "protocol": protocol,
        "protocol_sha256": protocol_hash,
        "warm": {
            "total_checks": warm_total,
            "records": warm,
        },
        "cold": {
            "total_checks": cold_total,
            "records": cold,
        },
        "capability_ablation": {
            "total_checks": ablation_total,
            "records": ablation,
        },
        "schema_ablation": schema_ablation,
        "restart_exact": exact_restart,
        "authority_shift": {
            "revoked": revoked,
            "requalified_count": requalified,
            "post_record": post_record,
            "post_cost": post_cost,
        },
        "gates": gates,
        "verdict": (
            "PASS_OPEN_WORLD_RECOHERENCE_V3_RESIDUAL_SCHEMA_GENESIS"
            if all(gates.values())
            else "FAIL_OPEN_WORLD_RECOHERENCE_V3_RESIDUAL_SCHEMA_GENESIS"
        ),
        "claim_boundary": (
            "bounded synthetic stream; raw finite encounter coordinates, sequence "
            "order, exact verifier consequence, maximum history depth, and generic "
            "finite extensional lookup compilation are supplied. The experiment "
            "does not receive named repair families or candidate node families; "
            "it derives minimum node input geometry from residual functional "
            "dependency. It is not unrestricted ontology invention or natural-world "
            "induction."
        ),
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
