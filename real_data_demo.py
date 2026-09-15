from __future__ import annotations

from collections import Counter
from pathlib import Path

from realitygraph.empirical import (
    compile_identity,
    design_target_batch,
    evaluate_target_plan,
    fetch_dataset,
)
from realitygraph.empirical_sources import uci_sources


def main():
    cache = Path(".cache/real-datasets")
    totals = Counter()

    print("REALITYGRAPH / REAL MEASURED DATA")
    print("--------------------------------")
    print("authority: UCI source bytes + finite exact consequence")
    print("policy:    ambiguity => UNKNOWN; never guess")
    print()

    for source in uci_sources():
        dataset = fetch_dataset(source, cache)
        identity, identity_predictions = compile_identity(dataset)
        target = design_target_batch(dataset)
        correct, unknown, wrong = evaluate_target_plan(dataset, target)

        rows = len(dataset.features)
        unique = len(identity.representative_rows)
        duplicate_rows = sum(
            len(members)
            for members in identity.class_members.values()
            if len(members) > 1
        )
        identity_unknown = 0
        for row_index in range(rows):
            status, _ = identity.identify_row(row_index)
            identity_unknown += status == "UNKNOWN"

        if identity_unknown != duplicate_rows:
            raise AssertionError(
                f"{source.name}: identity UNKNOWN mismatch "
                f"{identity_unknown} != {duplicate_rows}"
            )
        if wrong:
            raise AssertionError(f"{source.name}: target wrong verdicts={wrong}")
        if correct + unknown != rows:
            raise AssertionError(f"{source.name}: incomplete consequence accounting")

        totals["datasets"] += 1
        totals["rows"] += rows
        totals["features"] += len(source.feature_names)
        totals["unique"] += unique
        totals["identity_unknown"] += identity_unknown
        totals["identity_predictions"] += identity_predictions
        totals["identity_probes"] += len(identity.feature_indices)
        totals["target_predictions"] += target.design_predictions
        totals["target_probes"] += len(target.feature_indices)
        totals["target_correct"] += correct
        totals["target_unknown"] += unknown
        totals["target_wrong"] += wrong

        print(source.name)
        print(
            f"  domain={source.domain} rows={rows} features={len(source.feature_names)} "
            f"sha256={dataset.source_sha256[:16]}..."
        )
        print(
            f"  observational classes={unique} duplicate/UNKNOWN rows={identity_unknown}"
        )
        print(
            f"  identity probes={len(identity.feature_indices)} "
            f"field predictions={identity_predictions}"
        )
        print(
            f"  target probes={len(target.feature_indices)} "
            f"correct={correct} UNKNOWN={unknown} wrong={wrong}"
        )
        print(
            f"  target unresolved signatures={target.unresolved_signatures} "
            f"unresolved rows={target.unresolved_rows}"
        )
        print()

    if totals["target_wrong"] != 0:
        raise AssertionError("global zero-wrong invariant violated")

    print("AGGREGATE")
    for key in (
        "datasets",
        "rows",
        "features",
        "unique",
        "identity_unknown",
        "identity_predictions",
        "identity_probes",
        "target_predictions",
        "target_probes",
        "target_correct",
        "target_unknown",
        "target_wrong",
    ):
        print(f"{key:24} {totals[key]}")

    print()
    print("VERDICT")
    print("ZERO_WRONG_VERDICTS")
    print("ambiguity preserved as UNKNOWN")


if __name__ == "__main__":
    main()
