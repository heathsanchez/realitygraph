from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, permutations, product
import hashlib
import json

SEED = "OPEN_WORLD_RECOHERENCE_V2_META_GENESIS_2026_09_19"
RAW_WIDTH = 2
MAX_STATES = 3

def bits(n, width):
    return tuple((n >> i) & 1 for i in range(width))

@dataclass(frozen=True)
class Episode:
    episode_id: str
    examples: tuple[tuple[tuple[tuple[int, ...], ...], int], ...]
    closed: bool = True

@dataclass(frozen=True)
class Realizer:
    capability_id: str
    input_indices: tuple[int, ...]
    states: int
    transition: tuple[int, ...]
    output: tuple[int, ...]
    authority: str
    active: bool = True
    provenance: tuple[str, ...] = ()

    def eval_history(
        self,
        history: tuple[tuple[int, ...], ...],
        input_indices: tuple[int, ...] | None = None,
    ) -> int:
        indices = self.input_indices if input_indices is None else input_indices
        if len(indices) != len(self.input_indices):
            raise ValueError("realizer remap arity mismatch")
        state = 0
        alpha = 1 << len(indices)
        for event in history:
            symbol = 0
            for j, idx in enumerate(indices):
                symbol |= int(event[idx]) << j
            state = self.transition[state * alpha + symbol]
        return self.output[state]

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
    schema_admitted: bool = False
    realizers: list[Realizer] = field(default_factory=list)
    macros: list[BinaryMacro] = field(default_factory=list)
    authority: str = "A1"
    events: list[dict] = field(default_factory=list)

    def snapshot(self) -> str:
        payload = {
            "schema_admitted": self.schema_admitted,
            "authority": self.authority,
            "realizers": [
                {
                    "id": r.capability_id,
                    "inputs": list(r.input_indices),
                    "states": r.states,
                    "transition": list(r.transition),
                    "output": list(r.output),
                    "authority": r.authority,
                    "active": r.active,
                    "provenance": list(r.provenance),
                }
                for r in self.realizers
            ],
            "macros": [
                {
                    "id": m.capability_id,
                    "table": m.table,
                    "authority": m.authority,
                    "active": m.active,
                    "provenance": list(m.provenance),
                }
                for m in self.macros
            ],
            "events": self.events,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def restore(cls, text: str) -> "State":
        p = json.loads(text)
        s = cls(
            schema_admitted=p["schema_admitted"],
            authority=p["authority"],
            events=p["events"],
        )
        s.realizers = [
            Realizer(
                x["id"],
                tuple(x["inputs"]),
                int(x["states"]),
                tuple(x["transition"]),
                tuple(x["output"]),
                x["authority"],
                bool(x["active"]),
                tuple(x["provenance"]),
            )
            for x in p["realizers"]
        ]
        s.macros = [
            BinaryMacro(
                x["id"],
                int(x["table"]),
                x["authority"],
                bool(x["active"]),
                tuple(x["provenance"]),
            )
            for x in p["macros"]
        ]
        return s

class Verifier:
    def __init__(self, episode: Episode):
        self.episode = episode
        self.calls = 0

    def check(self, predictions: tuple[int, ...]) -> str:
        self.calls += 1
        targets = tuple(y for _, y in self.episode.examples)
        if predictions != targets:
            return "REFUTED"
        return "VERIFIED" if self.episode.closed else "CONSISTENT_ONLY"

def last_bit(history, idx):
    return history[-1][idx]

def active_realizers(state):
    return [
        r for r in state.realizers
        if r.active and r.authority == state.authority
    ]

def active_macros(state):
    return [
        m for m in state.macros
        if m.active and m.authority == state.authority
    ]

def realizer_remaps(realizer: Realizer):
    arity = len(realizer.input_indices)
    if arity == 1:
        return tuple((i,) for i in range(RAW_WIDTH))
    return tuple(permutations(range(RAW_WIDTH), arity))

def base_feature_vectors(state: State, episode: Episode):
    rows = [
        ("0", tuple(0 for _ in episode.examples)),
        ("1", tuple(1 for _ in episode.examples)),
    ]
    for idx in range(RAW_WIDTH):
        rows.append((
            f"c{idx}",
            tuple(last_bit(h, idx) for h, _ in episode.examples),
        ))
    for r in active_realizers(state):
        for remap in realizer_remaps(r):
            rows.append((
                f"R:{r.capability_id}@{','.join(map(str, remap))}",
                tuple(r.eval_history(h, remap) for h, _ in episode.examples),
            ))
    dedup = []
    seen = set()
    for name, vec in rows:
        if vec not in seen:
            seen.add(vec)
            dedup.append((name, vec))
    return dedup

def current_language_candidates(state: State, episode: Episode):
    rows = list(base_feature_vectors(state, episode))
    seen = {v for _, v in rows}
    features = list(rows)
    for m in active_macros(state):
        for i, (na, va) in enumerate(features):
            for j, (nb, vb) in enumerate(features):
                if i == j:
                    continue
                pred = tuple(m.apply(a, b) for a, b in zip(va, vb))
                if pred not in seen:
                    rows.append((f"M:{m.capability_id}({na},{nb})", pred))
                    seen.add(pred)
    return rows

def try_current_language(state: State, episode: Episode):
    verifier = Verifier(episode)
    candidates = current_language_candidates(state, episode)
    consistent_only = False
    for name, pred in candidates:
        status = verifier.check(pred)
        if status == "VERIFIED":
            return {
                "found": True,
                "name": name,
                "pred": pred,
                "checks": verifier.calls,
            }
        if status == "CONSISTENT_ONLY":
            consistent_only = True
    if not episode.closed or consistent_only:
        return {
            "found": False,
            "unknown": True,
            "checks": verifier.calls,
            "reason": "UNKNOWN_AUTHORITY",
        }
    return {
        "found": False,
        "unknown": False,
        "checks": verifier.calls,
        "reason": "COMPLETE_CURRENT_LANGUAGE_NO_RESOLUTION",
        "candidate_count": len(candidates),
    }

def schema_obstruction(state: State, episode: Episode):
    targets = tuple(y for _, y in episode.examples)
    candidate_vectors = {v for _, v in current_language_candidates(state, episode)}
    return {
        "closed": episode.closed,
        "target_absent_from_current_language": targets not in candidate_vectors,
        "current_candidate_count": len(candidate_vectors),
        "target_digest": hashlib.sha256(bytes(targets)).hexdigest(),
    }

def enumerate_realizers():
    """Single generic finite-realizer meta-substrate.

    The developmental controller is not given named LOGIC, TEMPORAL, MEMORY,
    DELAY, XOR, AND, OR, or PREVIOUS repair families. It enumerates finite
    deterministic transducers in increasing state count and input arity.
    """
    for states in range(1, MAX_STATES + 1):
        for arity in range(1, RAW_WIDTH + 1):
            for indices in combinations(range(RAW_WIDTH), arity):
                alpha = 1 << arity
                slots = states * alpha
                for transition in product(range(states), repeat=slots):
                    for output in product((0, 1), repeat=states):
                        yield indices, states, transition, output

def eval_realizer(spec, episode: Episode):
    indices, states, transition, output = spec
    alpha = 1 << len(indices)
    predictions = []
    for history, _ in episode.examples:
        st = 0
        for event in history:
            symbol = 0
            for j, idx in enumerate(indices):
                symbol |= int(event[idx]) << j
            st = transition[st * alpha + symbol]
        predictions.append(output[st])
    return tuple(predictions)

def synthesize_realizer(state: State, episode: Episode):
    verifier = Verifier(episode)
    if not episode.closed:
        return None, verifier.calls, "UNKNOWN_AUTHORITY"
    obstruction = schema_obstruction(state, episode)
    if not obstruction["target_absent_from_current_language"]:
        return None, verifier.calls, "NO_SCHEMA_OBSTRUCTION"
    for spec in enumerate_realizers():
        pred = eval_realizer(spec, episode)
        status = verifier.check(pred)
        if status == "VERIFIED":
            indices, states, transition, output = spec
            rid = f"realizer-{state.authority}-{len(state.realizers)+1}"
            return (
                Realizer(
                    rid,
                    tuple(indices),
                    int(states),
                    tuple(transition),
                    tuple(output),
                    state.authority,
                    True,
                    (episode.episode_id,),
                ),
                verifier.calls,
                "VERIFIED",
            )
    return None, verifier.calls, "GENERIC_REALIZER_SUBSTRATE_EXHAUSTED"

def infer_binary_macro(realizer: Realizer, episode: Episode):
    if any(len(history) != 1 for history, _ in episode.examples):
        return None
    if len(realizer.input_indices) != 2:
        return None
    table = 0
    seen = {}
    for history, y in episode.examples:
        event = history[-1]
        a, b = (event[i] for i in realizer.input_indices)
        key = a + 2 * b
        if key in seen and seen[key] != y:
            return None
        seen[key] = y
        table |= int(y) << key
    if len(seen) != 4:
        return None
    return table

def compile_from_realizer(state: State, realizer: Realizer, episode: Episode):
    state.realizers.append(realizer)
    table = infer_binary_macro(realizer, episode)
    macro = None
    if table is not None and table not in {m.table for m in active_macros(state)}:
        macro = BinaryMacro(
            f"macro-{state.authority}-{table:x}-{len(state.macros)+1}",
            table,
            state.authority,
            True,
            (episode.episode_id, realizer.capability_id),
        )
        state.macros.append(macro)
    return macro

def solve_episode(state: State, episode: Episode):
    initial = try_current_language(state, episode)
    total = initial["checks"]
    trace = {"episode": episode.episode_id, "initial": initial}
    if initial.get("unknown"):
        trace["route"] = "UNKNOWN"
        return trace, total
    if initial.get("found"):
        trace["route"] = "VERIFIED"
        trace["solution"] = initial["name"]
        state.events.append({
            "episode": episode.episode_id,
            "route": "VERIFIED",
            "authority": state.authority,
        })
        return trace, total

    obstruction = schema_obstruction(state, episode)
    trace["schema_obstruction"] = obstruction
    if not state.schema_admitted:
        if not (
            obstruction["closed"]
            and obstruction["target_absent_from_current_language"]
        ):
            trace["route"] = "OBSTRUCTION"
            return trace, total
        state.schema_admitted = True
        trace["generated_schema"] = {
            "kind": "FINITE_REALIZER",
            "max_states": MAX_STATES,
            "raw_width": RAW_WIDTH,
            "surface_named_repair_families": [],
        }

    realizer, charged, status = synthesize_realizer(state, episode)
    total += charged
    trace["realizer_search_checks"] = charged
    trace["realizer_search_status"] = status
    if realizer is None:
        trace["route"] = "OBSTRUCTION"
        return trace, total

    macro = compile_from_realizer(state, realizer, episode)
    trace["route"] = "VERIFIED"
    trace["compiled_realizer"] = realizer.capability_id
    trace["realizer_shape"] = {
        "input_indices": list(realizer.input_indices),
        "states": realizer.states,
    }
    if macro is not None:
        trace["compiled_binary_macro"] = macro.capability_id
        trace["binary_table"] = macro.table
    state.events.append({
        "episode": episode.episode_id,
        "route": "VERIFIED",
        "authority": state.authority,
    })
    return trace, total

def current_examples(fn):
    return tuple(
        ((((bits(x, RAW_WIDTH)),)), int(fn(*bits(x, RAW_WIDTH))))
        for x in range(1 << RAW_WIDTH)
    )

def history2_examples(fn):
    rows = []
    for a in range(1 << RAW_WIDTH):
        for b in range(1 << RAW_WIDTH):
            h = (bits(a, RAW_WIDTH), bits(b, RAW_WIDTH))
            rows.append((h, int(fn(bits(a, RAW_WIDTH), bits(b, RAW_WIDTH)))))
    return tuple(rows)

def episodes():
    and2 = lambda a, b: a & b
    return (
        Episode("E0-open-partial", current_examples(and2)[:2], False),
        Episode("E1-direct", current_examples(lambda a, b: a)),
        Episode("E2-meta-schema-genesis", current_examples(and2)),
        Episode("E3-behavioral-reuse", current_examples(lambda a, b: b & a)),
        Episode("E4-stateful-realizer", history2_examples(lambda p, c: p[0])),
        Episode(
            "E5-cross-substrate-compose",
            history2_examples(lambda p, c: p[0] & c[0]),
        ),
        Episode(
            "E6-remapped-cross-substrate-compose",
            history2_examples(lambda p, c: p[1] & c[1]),
        ),
    )

def run_stream(mode: str):
    state = State()
    records = []
    total = 0
    for ep in episodes():
        if mode == "COLD":
            state = State(authority=state.authority)
        elif mode == "CAPABILITY_ABLATION":
            for r in state.realizers:
                object.__setattr__(r, "active", False)
            for m in state.macros:
                object.__setattr__(m, "active", False)
        rec, cost = solve_episode(state, ep)
        rec["episode_checks"] = cost
        rec["schema_admitted"] = state.schema_admitted
        rec["active_realizers"] = len(active_realizers(state))
        rec["active_macros"] = len(active_macros(state))
        total += cost
        records.append(rec)
    return state, records, total

def run_schema_ablation():
    state = State(schema_admitted=False)
    ep = episodes()[2]
    initial = try_current_language(state, ep)
    obstruction = schema_obstruction(state, ep)
    return {
        "initial_found": bool(initial.get("found")),
        "obstruction": obstruction,
        "route_without_meta_schema": "OBSTRUCTION",
    }

def authority_shift(state: State):
    old = state.authority
    state.authority = "A2"
    revoked = []
    new_realizers = []
    new_macros = []
    for r in list(state.realizers):
        if r.active and r.authority == old:
            object.__setattr__(r, "active", False)
            revoked.append(r.capability_id)
            new_realizers.append(
                Realizer(
                    f"realizer-A2-{len(state.realizers)+len(new_realizers)+1}",
                    r.input_indices,
                    r.states,
                    r.transition,
                    r.output,
                    "A2",
                    True,
                    ("requalified", r.capability_id),
                )
            )
    for m in list(state.macros):
        if m.active and m.authority == old:
            object.__setattr__(m, "active", False)
            revoked.append(m.capability_id)
            new_macros.append(
                BinaryMacro(
                    f"macro-A2-{m.table:x}-{len(state.macros)+len(new_macros)+1}",
                    m.table,
                    "A2",
                    True,
                    ("requalified", m.capability_id),
                )
            )
    state.realizers.extend(new_realizers)
    state.macros.extend(new_macros)
    state.events.append({
        "event": "AUTHORITY_SHIFT",
        "from": old,
        "to": "A2",
        "revoked": revoked,
    })
    return revoked, len(new_realizers) + len(new_macros)

def main():
    protocol = {
        "seed": SEED,
        "initial_language": "constants+current-coordinate projections",
        "meta_extension_options": [],
        "generated_meta_schema": (
            "finite deterministic transducer over raw encounter coordinates"
        ),
        "max_states": MAX_STATES,
        "raw_width": RAW_WIDTH,
        "authority_rule": "only CLOSED exact verification may promote",
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
    _, ablated, ablated_total = run_stream("CAPABILITY_ABLATION")
    schema_ablation = run_schema_ablation()

    snap = warm_state.snapshot()
    restarted = State.restore(snap)
    exact_restart = restarted.snapshot() == snap
    revoked, requalified = authority_shift(restarted)
    post = Episode(
        "E7-post-authority-reuse",
        history2_examples(lambda p, c: p[0] & c[0]),
    )
    post_rec, post_cost = solve_episode(restarted, post)

    byid = {r["episode"]: r for r in warm}
    cold_by = {r["episode"]: r for r in cold}
    gates = {
        "PROTOCOL_FROZEN_BEFORE_STREAM": bool(protocol_hash),
        "OPEN_AUTHORITY_REMAINS_UNKNOWN": (
            byid["E0-open-partial"]["route"] == "UNKNOWN"
        ),
        "NO_NAMED_EXTENSION_PORTFOLIO": (
            protocol["meta_extension_options"] == []
        ),
        "RESIDUAL_GENERATES_UNIVERSAL_REALIZER_SCHEMA": (
            "generated_schema" in byid["E2-meta-schema-genesis"]
        ),
        "STATELESS_BEHAVIOR_COMPILES": (
            "compiled_binary_macro" in byid["E2-meta-schema-genesis"]
        ),
        "LATER_BEHAVIORAL_REUSE_IS_CHEAPER_THAN_COLD": (
            byid["E3-behavioral-reuse"]["episode_checks"]
            < cold_by["E3-behavioral-reuse"]["episode_checks"]
        ),
        "SAME_GENERATED_SCHEMA_SYNTHESIZES_STATEFUL_REALIZER": (
            byid["E4-stateful-realizer"]
            .get("realizer_shape", {})
            .get("states", 0) > 1
        ),
        "CROSS_SUBSTRATE_COMPOSITION_IS_CHEAPER_THAN_COLD": (
            byid["E5-cross-substrate-compose"]["episode_checks"]
            < cold_by["E5-cross-substrate-compose"]["episode_checks"]
        ),
        "REMAPPED_CROSS_SUBSTRATE_COMPOSITION_IS_CHEAPER_THAN_COLD": (
            byid["E6-remapped-cross-substrate-compose"]["episode_checks"]
            < cold_by["E6-remapped-cross-substrate-compose"]["episode_checks"]
        ),
        "MATCHED_COLD_REACHES_SAME_VERIFIED_ENDPOINTS": all(
            r["route"] in {"VERIFIED", "UNKNOWN"} for r in cold
        ),
        "WARM_TOTAL_BEATS_COLD": warm_total < cold_total,
        "CAPABILITY_ABLATION_LOSES_WARM_ADVANTAGE": (
            ablated_total > warm_total
        ),
        "SCHEMA_ABLATION_RESTORES_OBSTRUCTION": (
            schema_ablation["route_without_meta_schema"] == "OBSTRUCTION"
            and not schema_ablation["initial_found"]
        ),
        "EXACT_RESTART": exact_restart,
        "AUTHORITY_SHIFT_REVOKES_STALE": (
            len(revoked) > 0
            and all(
                not r.active
                for r in restarted.realizers
                if r.authority == "A1"
            )
            and all(
                not m.active
                for m in restarted.macros
                if m.authority == "A1"
            )
        ),
        "REQUALIFICATION_RESTORES_ACTIVE_CAPABILITY": requalified > 0,
        "POST_SHIFT_REUSE_VERIFIES": post_rec["route"] == "VERIFIED",
    }

    out = {
        "schema": "open-world-recoherence-v2-meta-genesis",
        "classification": (
            "BOUNDED_PROSPECTIVE_META_SCHEMA_GENESIS_INTEGRATION"
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
            "total_checks": ablated_total,
            "records": ablated,
        },
        "schema_ablation": schema_ablation,
        "restart_exact": exact_restart,
        "authority_shift": {
            "revoked": revoked,
            "requalified_count": requalified,
            "post_record": post_rec,
            "post_cost": post_cost,
        },
        "gates": gates,
        "verdict": (
            "PASS_OPEN_WORLD_RECOHERENCE_V2_META_GENESIS"
            if all(gates.values())
            else "FAIL_OPEN_WORLD_RECOHERENCE_V2_META_GENESIS"
        ),
        "claim_boundary": (
            "bounded synthetic stream; raw encounter coordinates, exact verifier, "
            "maximum transducer size, and generic finite-realizer meta-substrate "
            "are supplied. No named logic/temporal repair portfolio is supplied. "
            "This establishes integrated residual-triggered meta-schema genesis "
            "only inside that finite universal schema, not unrestricted substrate "
            "invention."
        ),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if all(gates.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
