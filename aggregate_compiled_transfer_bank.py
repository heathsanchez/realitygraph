from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path


def main():
    root = Path(os.environ.get("REALITYGRAPH_FUTURE_RESULTS_DIR", "gathered-futures"))
    files = sorted(root.rglob("future-world-*.json"))
    if len(files) != 49:
        raise AssertionError(f"expected 49 future worlds, got {len(files)}")

    rows = [json.loads(path.read_text()) for path in files]
    indices = sorted(row["world_index"] for row in rows)
    if indices != list(range(49)):
        raise AssertionError(f"incomplete future bank: {indices}")

    by_dataset = defaultdict(list)
    for row in rows:
        by_dataset[row["dataset"]].append(row)

    total_cold = sum(row["cold_candidate_certifications"] for row in rows)
    total_future_search = sum(row["future_search_calls"] for row in rows)
    compiled = [row for row in rows if not row["compile_refused"]]
    accepted = [row for row in compiled if row["future_accepted"]]
    rejected = [row for row in compiled if not row["future_accepted"]]

    print("REALITYGRAPH / EVERY NATURAL GROUP IS THE FUTURE")
    print("------------------------------------------------")
    print(f"future_worlds={len(rows)}")
    print(f"cold_candidate_certifications={total_cold}")
    print(f"future_search_calls={total_future_search}")
    print(
        f"compiled_memories={len(compiled)} "
        f"accepted_memories={len(accepted)} revoked_memories={len(rejected)}"
    )
    print()

    summary = {
        "future_worlds": len(rows),
        "cold_candidate_certifications": total_cold,
        "future_search_calls": total_future_search,
        "compiled_memories": len(compiled),
        "accepted_memories": len(accepted),
        "revoked_memories": len(rejected),
        "datasets": {},
    }

    for name, items in sorted(by_dataset.items()):
        compile_count = sum(not row["compile_refused"] for row in items)
        accept_count = sum(row["future_accepted"] for row in items)
        refused = sum(row["compile_refused"] for row in items)
        revoked = sum(
            (not row["compile_refused"]) and (not row["future_accepted"])
            for row in items
        )
        candidate_counts = Counter(
            tuple(row["candidate"] or ())
            for row in items
            if not row["compile_refused"]
        )
        accepted_rows = [row for row in items if row["future_accepted"]]
        total_future_rows = sum(row["future_rows"] for row in items)
        weighted_baseline = (
            sum(row["baseline_log_loss"] * row["future_rows"] for row in accepted_rows)
            / sum(row["future_rows"] for row in accepted_rows)
            if accepted_rows else None
        )
        weighted_compiled = (
            sum(row["compiled_log_loss"] * row["future_rows"] for row in accepted_rows)
            / sum(row["future_rows"] for row in accepted_rows)
            if accepted_rows else None
        )
        mean_auc = (
            sum(row["auc"] for row in accepted_rows) / len(accepted_rows)
            if accepted_rows else None
        )
        max_harm = max(
            (row["max_group_harm"] for row in accepted_rows),
            default=0.0,
        )
        all_zero_search = all(row["future_search_calls"] == 0 for row in items)
        all_groups_accounted = len(items) == items[0]["groups"]

        print(name)
        print(
            f"  worlds={len(items)}/{items[0]['groups']} "
            f"future_rows={total_future_rows}"
        )
        print(
            f"  compile={compile_count} accepted={accept_count} "
            f"refused={refused} revoked={revoked}"
        )
        print(f"  candidate_counts={dict(candidate_counts)}")
        if accepted_rows:
            print(
                f"  weighted_baseline_LL={weighted_baseline:.6f} "
                f"weighted_compiled_LL={weighted_compiled:.6f} "
                f"mean_AUC={mean_auc:.6f} max_harm={max_harm:.6f}"
            )
        print(f"  all_future_search_zero={all_zero_search}")
        print()

        summary["datasets"][name] = {
            "worlds": len(items),
            "groups": items[0]["groups"],
            "future_rows": total_future_rows,
            "compiled": compile_count,
            "accepted": accept_count,
            "refused": refused,
            "revoked": revoked,
            "candidate_counts": {
                "|".join(candidate): count
                for candidate, count in candidate_counts.items()
            },
            "weighted_baseline_log_loss": weighted_baseline,
            "weighted_compiled_log_loss": weighted_compiled,
            "mean_auc": mean_auc,
            "max_group_harm": max_harm,
            "all_future_search_zero": all_zero_search,
            "all_groups_accounted": all_groups_accounted,
        }

        if not all_groups_accounted:
            raise AssertionError(f"{name}: future bank did not cover every natural group")
        if not all_zero_search:
            raise AssertionError(f"{name}: some future world used search")
        if max_harm > 1e-12:
            raise AssertionError(f"{name}: accepted memory harmed a future group")

    if total_future_search != 0:
        raise AssertionError("future bank performed search after compilation")

    out = root / "summary.json"
    out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print("VERDICT")
    print("EVERY_NATURAL_GROUP_BECAME_AN_UNTOUCHED_ZERO_SEARCH_FUTURE")


if __name__ == "__main__":
    main()
