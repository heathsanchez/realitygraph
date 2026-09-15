from __future__ import annotations

import json
import os
from pathlib import Path

from compiled_transfer_demo import (
    compile_from_discovery,
    discover_minimal_transfer,
    evaluate_untouched_future,
    without_group,
)
from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.ledger import Ledger
from realitygraph.transfer_memory import model_memory, model_to_law


def all_worlds(datasets):
    worlds = []
    for dataset_index, dataset in enumerate(datasets):
        for group in sorted({str(group) for group in dataset.groups}):
            worlds.append((dataset_index, dataset.name, group))
    return worlds


def main():
    world_index = int(os.environ["REALITYGRAPH_FUTURE_WORLD"])
    seed = os.environ.get("REALITYGRAPH_FUTURE_BANK_SEED", "future-bank")
    result_path = Path(
        os.environ.get(
            "REALITYGRAPH_FUTURE_RESULT",
            f"results/future-world-{world_index:02d}.json",
        )
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)

    datasets = grouped_real_datasets(".cache/grouped-real")
    worlds = all_worlds(datasets)
    if world_index < 0 or world_index >= len(worlds):
        raise ValueError(f"world index {world_index} outside 0..{len(worlds)-1}")

    dataset_index, expected_name, future_group = worlds[world_index]
    dataset = datasets[dataset_index]
    if dataset.name != expected_name:
        raise AssertionError("world manifest drift")

    discovery = without_group(dataset, future_group)
    if future_group in {str(group) for group in discovery.groups}:
        raise AssertionError("future group leaked into discovery")

    candidate, mean_gain, cold_calls = discover_minimal_transfer(
        discovery,
        f"{seed}|world={world_index}|{dataset.name}",
    )

    result = {
        "world_index": world_index,
        "dataset": dataset.name,
        "future_group": future_group,
        "groups": dataset.group_count,
        "discovery_groups": len(set(discovery.groups)),
        "cold_candidate_certifications": cold_calls,
        "candidate": None,
        "compiled_rules": [],
        "mean_discovery_gain": mean_gain,
        "mg_bytes": 0,
        "future_rows": sum(1 for group in dataset.groups if str(group) == future_group),
        "future_search_calls": 0,
        "baseline_log_loss": None,
        "compiled_log_loss": None,
        "auc": None,
        "max_group_harm": None,
        "future_accepted": False,
        "memory_active_after_future": False,
        "compile_refused": candidate is None,
    }

    print("REALITYGRAPH / ONE COUNTERFACTUAL FUTURE")
    print("----------------------------------------")
    print(
        f"world={world_index} dataset={dataset.name} "
        f"untouched_future={future_group}"
    )
    print(
        f"discovery_groups={result['discovery_groups']} "
        f"future_rows={result['future_rows']} "
        f"cold_candidate_certifications={cold_calls}"
    )

    if candidate is None:
        print("compile=REFUSED future_verdict=UNKNOWN future_search_calls=0")
        result_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(f"FUTURE_WORLD_COMPLETE out={result_path}")
        return

    result["candidate"] = [dataset.probe_names[i] for i in candidate]
    model = compile_from_discovery(
        discovery,
        candidate,
        f"{seed}|world={world_index}|{dataset.name}",
    )
    result["compiled_rules"] = [rule.probe_name for rule in model.rules]

    provenance = (
        f"future-bank-{world_index:02d}-"
        f"{dataset.name.replace(' ', '_')[:16]}"
    )
    law = model_to_law(
        dataset.source_hashes,
        model,
        provenance=provenance,
    )
    ledger = Ledger()
    ledger.append_add(law, "future-bank-transfer-compiler")
    memory = ledger.materialize("sealed-natural-group-transfer-v1")
    memory_text = memory.text()
    result["mg_bytes"] = len(memory_text.encode())

    accepted, baseline_loss, _, metrics, future_rows = evaluate_untouched_future(
        dataset,
        future_group,
        memory_text,
    )
    if future_rows != result["future_rows"]:
        raise AssertionError("future row count drift")

    result["baseline_log_loss"] = baseline_loss
    result["compiled_log_loss"] = metrics.log_loss
    result["auc"] = metrics.auc
    result["max_group_harm"] = metrics.max_group_harm
    result["future_accepted"] = accepted

    if not accepted:
        ledger.append_revoke(
            law.id,
            "future-bank-verifier",
            reason=f"failed untouched group {future_group}",
        )
    active = ledger.materialize("sealed-natural-group-transfer-v1")
    result["memory_active_after_future"] = law.id in active.laws

    if accepted and metrics.max_group_harm > 1e-12:
        raise AssertionError("accepted compiled law harmed untouched future")
    if result["future_search_calls"] != 0:
        raise AssertionError("future used search despite compiled memory")

    print(
        f"candidate={result['candidate']} compiled_rules={result['compiled_rules']} "
        f".mg_bytes={result['mg_bytes']} future_search_calls=0"
    )
    print(
        f"baseline_LL={baseline_loss:.6f} compiled_LL={metrics.log_loss:.6f} "
        f"AUC={metrics.auc:.6f} harm={metrics.max_group_harm:.6f}"
    )
    print(
        f"future_accepted={accepted} "
        f"memory_active_after_future={result['memory_active_after_future']}"
    )

    result_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"FUTURE_WORLD_COMPLETE out={result_path}")


if __name__ == "__main__":
    main()
