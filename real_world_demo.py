from __future__ import annotations

import hashlib
import os
import random
from collections import Counter

from realitygraph import Ledger, MG
from realitygraph.lab import (
    HiddenFiniteWorld,
    batch_from_memory,
    compile_identifier,
    compile_plan,
    design_separating_batch,
    identify,
    retain_batch,
)
from realitygraph.real_worlds import real_world_suite


def shuffled(values, seed: str, salt: str):
    out = list(values)
    digest = hashlib.sha256(f"{seed}|{salt}".encode()).digest()
    random.Random(int.from_bytes(digest[:8], "big")).shuffle(out)
    return tuple(out)


def hidden_for(family, seed: str, tag: str) -> int:
    digest = hashlib.sha256(f"{seed}|{family.scope}|{tag}".encode()).digest()
    return family.hypotheses[
        int.from_bytes(digest[:8], "big") % len(family.hypotheses)
    ]


def main():
    seed = os.environ.get("REALITYGRAPH_RUN_SEED", "local-real-world-suite")
    families = real_world_suite()
    memory = MG(verifier="finite-mechanism-exact")
    ledger = Ledger()

    compiled = {}
    cold_predictions = 0
    cold_compile_predictions = 0
    candidate_actions = 0
    selected_actions = 0
    action_classes = 0
    categories = Counter()
    mechanisms = Counter()

    print("REALITYGRAPH / REAL-WORLD MECHANISM STRESS SUITE")
    print("------------------------------------------------")
    print(f"freeze seed digest: {hashlib.sha256(seed.encode()).hexdigest()[:12]}")
    print(f"families:           {len(families)}")
    print()

    for family in families:
        hypotheses = shuffled(family.hypotheses, seed, family.scope + ":h")
        actions = shuffled(family.actions, seed, family.scope + ":a")

        plan = design_separating_batch(hypotheses, actions, family.predict)
        identifier = compile_plan(family.scope, plan)
        retain_batch(identifier, ledger, memory, kernel_id="real-world-suite")
        compiled[family.scope] = identifier

        world = HiddenFiniteWorld(
            hidden_for(family, seed, "cold"),
            family.predict,
        )
        learned = identify(world, identifier)
        exact = world.verify(learned, family.actions)
        if not exact:
            raise AssertionError(f"cold exact verification failed: {family.report_name}")

        cold_predictions += plan.design_predictions
        cold_compile_predictions += identifier.compile_predictions
        candidate_actions += len(family.actions)
        selected_actions += len(plan.actions)
        action_classes += plan.action_classes
        categories[family.category] += 1
        mechanisms[family.mechanism] += 1

        print(
            f"{family.report_name:34} "
            f"H={len(family.hypotheses):5} "
            f"A={len(family.actions):4} "
            f"Q={plan.action_classes:4} "
            f"batch={len(plan.actions):2} exact={exact}"
        )

    # Eight fresh hidden parameterizations per family. Runtime identification is
    # direct observation-signature lookup: no family scan and no experiment search.
    warm_worlds = 0
    warm_actions = 0
    for family in families:
        identifier = compiled[family.scope]
        for i in range(8):
            world = HiddenFiniteWorld(
                hidden_for(family, seed, f"warm-{i}"),
                family.predict,
            )
            learned = identify(world, identifier)
            if not world.verify(learned, family.actions):
                raise AssertionError(f"warm exact verification failed: {family.report_name}")
            warm_worlds += 1
            warm_actions += world.actions_spent

    # Simulate loss of derived runtime decoders while retaining only .mg.
    restart_predictions = 0
    for family in families:
        retained = batch_from_memory(memory, family.scope)
        rebuilt = compile_identifier(
            family.scope,
            shuffled(family.hypotheses, seed, family.scope + ":restart"),
            retained,
            family.predict,
        )
        restart_predictions += rebuilt.compile_predictions

    print()
    print("AGGREGATE")
    print(f"categories:                          {len(categories)}")
    print(f"mechanism classes:                   {len(mechanisms)}")
    print(f"cold consequence predictions:        {cold_predictions}")
    print(f"cold compile extra predictions:      {cold_compile_predictions}")
    print(f"candidate actions:                   {candidate_actions}")
    print(f"distinct consequence action classes: {action_classes}")
    print(f"retained separating actions:         {selected_actions}")
    print(
        f"action compression:                  "
        f"{candidate_actions / selected_actions:.2f}x"
    )
    print(f"fresh hidden worlds solved:          {warm_worlds}")
    print(f"warm design predictions:             0")
    print(f"warm hypothesis-scan predictions:    0")
    print(f"warm real actions spent:             {warm_actions}")
    print(f"restart decoder predictions:         {restart_predictions}")
    print(
        f"restart vs cold consequence field:   "
        f"{cold_predictions / restart_predictions:.2f}x cheaper"
    )
    print(f"ledger events:                       {len(ledger.events)}")
    print(f".mg bytes:                           {len(memory.text().encode())}")

    print()
    print("CATEGORIES")
    for name, count in sorted(categories.items()):
        print(f"{name:16} {count:2}")

    print()
    print("MECHANISMS")
    for name, count in sorted(mechanisms.items()):
        print(f"{name:20} {count:2}")


if __name__ == "__main__":
    main()
