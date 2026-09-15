from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def main() -> None:
    files = sorted(Path("gathered-one-edit").rglob("one-edit-countermodel-shard-*.json"))
    if not files:
        raise SystemExit("no one-edit shard artifacts found")
    shards = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    expected = shards[0]["shards"]
    seen = {int(item["shard"]) for item in shards}
    if len(shards) != expected or seen != set(range(expected)):
        raise ValueError(f"expected shards 0..{expected-1}, got {sorted(seen)}")

    hits = {}
    assigned = 0
    totals = Counter()
    seed_orders = Counter()
    mutation_orders = Counter()
    for shard in shards:
        assigned += int(shard["assigned"])
        for problem_id, hit in shard["hits"].items():
            if problem_id in hits:
                raise ValueError(f"duplicate problem across shards: {problem_id}")
            hits[problem_id] = hit
        work = shard["work"]
        for key in (
            "seed_model_checks",
            "seed_assignments_checked",
            "source_valid_seed_models",
            "mutation_candidates_generated",
            "unique_mutations_tested",
            "target_checks",
            "target_assignments_checked",
            "source_rechecks_after_target_break",
            "source_recheck_assignments",
            "source_preserving_target_breaks",
        ):
            totals[key] += int(work[key])
        seed_orders.update({int(k): int(v) for k, v in work["seed_order_counts"].items()})
        mutation_orders.update(
            {int(k): int(v) for k, v in work["mutation_order_counts"].items()}
        )

    if assigned != 570:
        raise ValueError(f"expected 570 unresolved residuals, got {assigned}")

    order_hits = Counter(int(hit["n"]) for hit in hits.values())
    donors = Counter(hit["seed_donor_id"] for hit in hits.values())

    result = {
        "experiment": "realitygraph-one-edit-countermodel-repair-v1",
        "input_frontier": 570,
        "new_exact_hits": len(hits),
        "frontier_after_one_edit": 570 - len(hits),
        "collapse_by_model_order": dict(sorted(order_hits.items())),
        "top_seed_donors": donors.most_common(20),
        "hits": hits,
        "work": {
            **dict(totals),
            "seed_order_counts": dict(sorted(seed_orders.items())),
            "mutation_order_counts": dict(sorted(mutation_orders.items())),
            "fresh_random_models": 0,
        },
        "signal": {
            "minimal_verified_model_repair_adds_consequences": len(hits) > 0,
            "one_seed_generalizes_to_multiple_residuals": any(
                count > 1 for count in donors.values()
            ),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    out = Path("results/equational-one-edit-countermodel-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
