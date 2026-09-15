from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def main() -> None:
    files = sorted(Path("gathered-exhaustive").rglob("exhaustive-countermodel-shard-*.json"))
    if not files:
        raise SystemExit("no shard artifacts found")

    shards = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    expected = shards[0]["shards"]
    seen = {int(item["shard"]) for item in shards}
    if len(shards) != expected or seen != set(range(expected)):
        raise ValueError(f"expected shards 0..{expected-1}, got {sorted(seen)}")

    hits = {}
    total_assigned = 0
    work = Counter()
    order_tests = Counter()
    order_holds = Counter()
    for shard in shards:
        total_assigned += int(shard["assigned"])
        for problem_id, hit in shard["hits"].items():
            if problem_id in hits:
                raise ValueError(f"duplicate hit across shards: {problem_id}")
            hits[problem_id] = hit
        w = shard["work"]
        for key in (
            "candidate_model_transfers_tested",
            "unique_source_model_checks",
            "source_assignments_checked",
            "premise_holding_transfers",
            "target_assignments_checked",
        ):
            work[key] += int(w[key])
        order_tests.update({int(k): int(v) for k, v in w["order_tests"].items()})
        order_holds.update(
            {int(k): int(v) for k, v in w["order_premise_holds"].items()}
        )

    if total_assigned != 571:
        raise ValueError(f"expected 571 residuals across shards, got {total_assigned}")

    new_hits = {
        problem_id: hit
        for problem_id, hit in hits.items()
        if not hit.get("already_retained", False)
    }
    collapse_by_order = Counter(int(hit["n"]) for hit in hits.values())
    donor_counts = Counter(hit["donor_id"] for hit in hits.values())

    result = {
        "experiment": "realitygraph-exhaustive-countermodel-replay-v1",
        "shards": expected,
        "current_residual": 571,
        "unique_literal_models": shards[0]["bank"]["unique_literal_models"],
        "exact_hits_total": len(hits),
        "already_retained_hits": len(hits) - len(new_hits),
        "new_exact_hits": len(new_hits),
        "frontier_after_replay": 571 - len(hits),
        "collapse_by_model_order": dict(sorted(collapse_by_order.items())),
        "top_reusable_donors": donor_counts.most_common(20),
        "new_hits": new_hits,
        "all_hits": hits,
        "work": {
            **dict(work),
            "order_tests": dict(sorted(order_tests.items())),
            "order_premise_holds": dict(sorted(order_holds.items())),
            "new_model_search": 0,
        },
        "signal": {
            "exhaustive_compiled_experience_adds_new_consequences": len(new_hits) > 0,
            "one_model_solves_multiple_current_residuals": any(
                count > 1 for count in donor_counts.values()
            ),
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-exhaustive-countermodel-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
