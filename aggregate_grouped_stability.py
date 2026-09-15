from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path


def main():
    root = Path(os.environ.get("REALITYGRAPH_GROUP_RESULTS_DIR", "gathered-group"))
    files = sorted(root.rglob("grouped-stability-*.json"))
    if len(files) != 16:
        raise AssertionError(f"expected 16 grouped stability results, got {len(files)}")

    rows = [json.loads(path.read_text()) for path in files]
    replays = sorted(row["replay"] for row in rows)
    if replays != list(range(16)):
        raise AssertionError(f"incomplete replay set: {replays}")

    names = sorted(rows[0]["datasets"])
    summary = {"replays": 16, "datasets": {}}

    print("REALITYGRAPH / PARALLEL NATURAL-GROUP AGGREGATE")
    print("----------------------------------------------")

    for name in names:
        accepted = 0
        residual_accepted = 0
        gains = []
        residual_gains = []
        probes = Counter()
        residual_probes = Counter()
        single_probe_acceptance = Counter()
        single_probe_gains = Counter()
        exposed = set()
        expected_groups = None

        for row in rows:
            item = row["datasets"][name]
            expected_groups = item["groups"]
            exposed.update(item["test_groups"])

            if item["accepted"]:
                accepted += 1
                gains.append(item["gain"])
                if item["group_harm"] > 1e-12:
                    raise AssertionError(f"{name}: accepted result contains group harm")
                probes.update(item["probes"])

            if item["residual_accepted"]:
                residual_accepted += 1
                residual_gains.append(item["residual_gain"])
                if item["residual_group_harm"] > 1e-12:
                    raise AssertionError(f"{name}: accepted residual contains group harm")
                residual_probes.update(item["residual_probes"])

            for probe, result in item.get("single_probes", {}).items():
                if result["accepted"]:
                    if result["group_harm"] > 1e-12:
                        raise AssertionError(
                            f"{name}/{probe}: accepted primitive contains group harm"
                        )
                    single_probe_acceptance[probe] += 1
                    single_probe_gains[probe] += result["gain"]

        if len(exposed) != expected_groups:
            raise AssertionError(
                f"{name}: sealed futures exposed {len(exposed)}/{expected_groups} groups"
            )

        stable = [
            [probe, count]
            for probe, count in probes.most_common()
            if accepted and count / accepted >= 0.75
        ]
        stable_residual = [
            [probe, count]
            for probe, count in residual_probes.most_common()
            if residual_accepted and count / residual_accepted >= 0.75
        ]
        transferable = accepted == 16
        residual_transferable = residual_accepted == 16
        primitive_transferable = [
            probe
            for probe, count in sorted(single_probe_acceptance.items())
            if count == 16
        ]
        primitive_counts = [
            [probe, count]
            for probe, count in single_probe_acceptance.most_common()
        ]
        primitive_mean_gains = {
            probe: single_probe_gains[probe] / count
            for probe, count in single_probe_acceptance.items()
            if count
        }

        summary["datasets"][name] = {
            "accepted": accepted,
            "residual_accepted": residual_accepted,
            "transferable": transferable,
            "residual_transferable": residual_transferable,
            "stable_probes_75pct": stable,
            "stable_residual_probes_75pct": stable_residual,
            "groups_exposed": len(exposed),
            "mean_gain": sum(gains) / len(gains) if gains else 0.0,
            "mean_residual_gain": (
                sum(residual_gains) / len(residual_gains)
                if residual_gains
                else 0.0
            ),
            "primitive_transferable": primitive_transferable,
            "primitive_acceptance_counts": primitive_counts,
            "primitive_mean_gains": primitive_mean_gains,
        }

        print(name)
        print(f"  grouped_acceptance={accepted}/16")
        print(f"  residual_acceptance={residual_accepted}/16")
        print(f"  stable_probes_75pct={stable}")
        print(f"  stable_residual_probes_75pct={stable_residual}")
        print(f"  primitive_acceptance_counts={primitive_counts}")
        print(f"  primitive_transferable={primitive_transferable}")
        print(f"  distinct_groups_exposed={len(exposed)}/{expected_groups}")
        print(f"  transferable={transferable}")
        print(f"  residual_transferable={residual_transferable}")
        print()

    out = root / "summary.json"
    out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print("VERDICT")
    print("PARALLEL_NATURAL_GROUP_STABILITY_COMPLETE")


if __name__ == "__main__":
    main()
