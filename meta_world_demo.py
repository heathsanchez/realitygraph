from __future__ import annotations

import hashlib
import os
import random

from realitygraph import Ledger, MG
from realitygraph.lab import (
    HiddenFiniteWorld,
    batch_from_memory,
    compile_identifier,
    design_separating_batch,
    identify,
    retain_batch,
)
from realitygraph.meta_worlds import (
    affine_binary,
    affine_mod,
    eca8,
    lookup_bits,
    quadratic_mod,
)


def hidden_for(family, seed: str, tag: str) -> int:
    digest = hashlib.sha256(f"{seed}|{family.scope}|{tag}".encode()).digest()
    index = int.from_bytes(digest[:8], "big") % len(family.hypotheses)
    return family.hypotheses[index]


def shuffled(values, seed: str, salt: str):
    out = list(values)
    digest = hashlib.sha256(f"{seed}|{salt}".encode()).digest()
    random.Random(int.from_bytes(digest[:8], "big")).shuffle(out)
    return tuple(out)


def cold_compile(family, seed: str, memory: MG, ledger: Ledger):
    # Presentation order is deliberately scrambled. The field gets no named
    # family-specific selector; only hypotheses, actions, and predicted effects.
    hypotheses = shuffled(family.hypotheses, seed, family.scope + ":h")
    actions = shuffled(family.actions, seed, family.scope + ":a")
    plan = design_separating_batch(hypotheses, actions, family.predict)
    compiled = compile_identifier(
        family.scope,
        hypotheses,
        plan.actions,
        family.predict,
    )
    retain_batch(compiled, ledger, memory, kernel_id="meta-world")
    return plan, compiled


def main():
    seed = os.environ.get("REALITYGRAPH_RUN_SEED", "local-20260915")

    memory = MG(verifier="finite-model-family")
    ledger = Ledger()

    training = [
        lookup_bits(12),
        affine_binary(7),
        affine_mod(17),
        eca8(),
    ]
    heldout = quadratic_mod(7)

    compiled = {}
    cold_design_predictions = 0
    cold_compile_predictions = 0
    cold_actions = 0
    cold_sequential_rounds = 0

    print("REALITYGRAPH / BLIND META-WORLD TRANSFER")
    print("---------------------------------------")
    print(f"freeze seed digest: {hashlib.sha256(seed.encode()).hexdigest()[:12]}")
    print()

    for family in training:
        plan, identifier = cold_compile(family, seed, memory, ledger)
        compiled[family.scope] = identifier
        cold_design_predictions += plan.design_predictions
        cold_compile_predictions += identifier.compile_predictions
        cold_actions += len(plan.actions)
        cold_sequential_rounds += len(plan.actions)

        world = HiddenFiniteWorld(
            hidden_for(family, seed, "train"),
            family.predict,
        )
        learned = identify(world, identifier)
        exact = world.verify(learned, family.actions)
        if not exact:
            raise AssertionError("cold compiled identifier failed exact verifier")

        print(
            f"{family.report_name:24} "
            f"H={len(family.hypotheses):4} "
            f"A={len(family.actions):3} "
            f"batch={len(plan.actions):2} "
            f"classes={plan.class_progress[-1]:4} "
            f"rounds={world.rounds} exact={exact}"
        )

    # Many fresh worlds reuse the compiled decoders. Identification now costs
    # no model-family scan: observation signature -> direct lookup.
    warm_worlds = 0
    warm_rounds = 0
    warm_actions = 0
    sequential_equivalent = 0

    for family in training:
        identifier = compiled[family.scope]
        for i in range(16):
            world = HiddenFiniteWorld(
                hidden_for(family, seed, f"warm-{i}"),
                family.predict,
            )
            learned = identify(world, identifier)
            if not world.verify(learned, family.actions):
                raise AssertionError("warm transfer failed exact verifier")
            warm_worlds += 1
            warm_rounds += world.rounds
            warm_actions += world.actions_spent
            sequential_equivalent += len(identifier.actions)

    # A process restart can rebuild the runtime decoder from tiny .mg source
    # without re-running experiment design.
    restart_predictions = 0
    for family in training:
        retained = batch_from_memory(memory, family.scope)
        rebuilt = compile_identifier(
            family.scope,
            shuffled(family.hypotheses, seed, family.scope + ":restart"),
            retained,
            family.predict,
        )
        restart_predictions += rebuilt.compile_predictions

    # Ablation: remove retained/compiled capability and the expensive design
    # path returns on a fresh affine world.
    ablation_family = affine_binary(7)
    ablation_plan = design_separating_batch(
        shuffled(ablation_family.hypotheses, seed, "ablate:h"),
        shuffled(ablation_family.actions, seed, "ablate:a"),
        ablation_family.predict,
    )

    # Held-out family: absent from .mg until this point. Generic machinery must
    # discover its separating batch after freeze, then a second world inherits it.
    try:
        batch_from_memory(memory, heldout.scope)
        raise AssertionError("held-out family leaked into memory")
    except ValueError:
        pass

    heldout_plan, heldout_identifier = cold_compile(heldout, seed, memory, ledger)
    heldout_world = HiddenFiniteWorld(
        hidden_for(heldout, seed, "heldout-cold"),
        heldout.predict,
    )
    heldout_learned = identify(heldout_world, heldout_identifier)
    heldout_exact = heldout_world.verify(heldout_learned, heldout.actions)

    heldout_warm_world = HiddenFiniteWorld(
        hidden_for(heldout, seed, "heldout-warm"),
        heldout.predict,
    )
    heldout_warm_learned = identify(heldout_warm_world, heldout_identifier)
    heldout_warm_exact = heldout_warm_world.verify(
        heldout_warm_learned,
        heldout.actions,
    )

    if not heldout_exact or not heldout_warm_exact:
        raise AssertionError("held-out transfer failed exact verifier")

    print()
    print("COMPOUNDING")
    print(f"cold experiment-design predictions: {cold_design_predictions}")
    print(f"cold decoder-compile predictions:    {cold_compile_predictions}")
    print(f"cold batch actions:                  {cold_actions}")
    print(f"cold interaction rounds:             {len(training)}")
    print(f"cold sequential-round equivalent:    {cold_sequential_rounds}")
    print(f"fresh worlds solved from cache:      {warm_worlds}")
    print(f"warm experiment-design predictions:  0")
    print(f"warm hypothesis-scan predictions:    0")
    print(f"warm interaction rounds:             {warm_rounds}")
    print(f"warm actions spent:                  {warm_actions}")
    print(f"warm sequential-round equivalent:    {sequential_equivalent}")
    print(
        f"restart rebuild vs cold design:      "
        f"{cold_design_predictions / restart_predictions:.2f}x cheaper"
    )
    print(
        f"ablation restores design cost:       "
        f"{ablation_plan.design_predictions} predictions"
    )

    print()
    print("HELD-OUT FAMILY AFTER FREEZE")
    print(f"hypotheses:                          {len(heldout.hypotheses)}")
    print(f"candidate actions:                   {len(heldout.actions)}")
    print(f"discovered batch size:               {len(heldout_plan.actions)}")
    print(f"design predictions:                  {heldout_plan.design_predictions}")
    print(f"first-world rounds:                  {heldout_world.rounds}")
    print(f"first-world exact:                   {heldout_exact}")
    print(f"next-world design predictions:       0")
    print(f"next-world hypothesis scan:          0")
    print(f"next-world rounds:                   {heldout_warm_world.rounds}")
    print(f"next-world exact:                    {heldout_warm_exact}")

    print()
    print("RETENTION")
    print(f"ledger events:                       {len(ledger.events)}")
    print(f".mg bytes:                           {len(memory.text().encode())}")
    print(memory.text(), end="")


if __name__ == "__main__":
    main()
