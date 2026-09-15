from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from realitygraph.consequence import compile_consequence_model, evaluate_consequences
from realitygraph.empirical import fetch_dataset
from realitygraph.empirical_sources import uci_sources
from realitygraph.selective import sealed_split


def main():
    seed = os.environ["REALITYGRAPH_FREEZE_SEED"]
    cache = Path(".cache/real-datasets")
    totals = Counter()

    print("REALITYGRAPH / CONSEQUENCE STABILITY SEED")
    print("-----------------------------------------")
    print(f"seed={seed}")
    print()

    for source in uci_sources():
        dataset = fetch_dataset(source, cache)
        split = sealed_split(dataset, seed)
        model = compile_consequence_model(split.train, split.calibration)
        result = evaluate_consequences(split.test, model)

        if result.wrong:
            raise AssertionError(
                f"{source.name}: {result.wrong} wrong informative consequences"
            )

        totals["test"] += result.total
        totals["informative"] += result.informative
        totals["exact"] += result.exact
        totals["partial"] += result.partial
        totals["interval"] += result.interval
        totals["unknown"] += result.unknown
        totals["wrong"] += result.wrong

        print(
            f"{source.name:34} test={result.total:4} "
            f"info={result.informative:4} exact={result.exact:3} "
            f"set={result.partial:3} interval={result.interval:3} "
            f"UNKNOWN={result.unknown:4} wrong={result.wrong}"
        )

    coverage = totals["informative"] / totals["test"] if totals["test"] else 0.0
    print()
    print("AGGREGATE")
    for key in ("test","informative","exact","partial","interval","unknown","wrong"):
        print(f"{key:16} {totals[key]}")
    print(f"coverage         {100 * coverage:.2f}%")
    print("VERDICT          ZERO_WRONG_CONSEQUENCES")


if __name__ == "__main__":
    main()
