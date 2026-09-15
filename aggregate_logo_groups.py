from __future__ import annotations

import json
import os
from pathlib import Path


def main():
    root = Path(os.environ.get("REALITYGRAPH_LOGO_RESULTS_DIR", "gathered-logo"))
    files = sorted(root.rglob("logo-*.json"))
    if len(files) != 2:
        raise AssertionError(f"expected 2 leave-one-group-out results, got {len(files)}")

    rows = [json.loads(path.read_text()) for path in files]
    summary = {"datasets": {}}

    print("REALITYGRAPH / EXHAUSTIVE NATURAL-GROUP AGGREGATE")
    print("------------------------------------------------")

    for row in sorted(rows, key=lambda item: item["dataset"]):
        groups = row["groups"]
        accepted = row["accepted"]
        residual = row["residual_accepted"]
        if accepted == groups:
            status = "UNIVERSALLY_TRANSFERABLE"
        elif accepted == 0:
            status = "NO_GROUP_TRANSFER"
        else:
            status = "PARTIAL_GROUP_TRANSFER"

        if residual == groups:
            residual_status = "UNIVERSALLY_TRANSFERABLE"
        elif residual == 0:
            residual_status = "NO_GROUP_TRANSFER"
        else:
            residual_status = "PARTIAL_GROUP_TRANSFER"

        summary["datasets"][row["dataset"]] = {
            "groups": groups,
            "accepted": accepted,
            "residual_accepted": residual,
            "status": status,
            "residual_status": residual_status,
            "stable_probes_75pct": row["stable_probes_75pct"],
            "stable_residual_probes_75pct": row[
                "stable_residual_probes_75pct"
            ],
            "source_hashes": row["source_hashes"],
        }

        print(row["dataset"])
        print(f"  accepted={accepted}/{groups} status={status}")
        print(
            f"  residual_accepted={residual}/{groups} "
            f"status={residual_status}"
        )
        print(f"  stable_probes_75pct={row['stable_probes_75pct']}")
        print(
            "  stable_residual_probes_75pct="
            f"{row['stable_residual_probes_75pct']}"
        )
        print()

    out = root / "summary.json"
    out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print("VERDICT")
    print("EXHAUSTIVE_NATURAL_GROUP_AGGREGATE_COMPLETE")


if __name__ == "__main__":
    main()
