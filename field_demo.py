import random

from realitygraph import Field, Ledger, MG
from realitygraph.eca import (
    HiddenECA,
    all_rows,
    all_rules,
    compile_probe,
    compile_rule,
    probe_from_memory,
    rule_from_memory,
    step,
)


def identify_with_probe(world: HiddenECA, action: tuple[int, ...]):
    field = Field(all_rules())
    observed = world.observe(action)
    collision = field.collide(action, observed, step)
    if not field.resolved():
        raise AssertionError("probe did not identify one world-law")
    return field.hypotheses[0], observed, collision


def main():
    memory = MG(verifier="eca_step")
    ledger = Ledger()

    # World A pays the discovery cost for a universally separating probe.
    world_a = HiddenECA(110)  # Hidden from the learner.
    field_a = Field(all_rules())
    actions = all_rows(8)

    probe = field_a.choose(actions, step)
    probe_search_predictions = len(actions) * len(field_a.hypotheses)

    observed_a = world_a.observe(probe.action)
    collision_a = field_a.collide(probe.action, observed_a, step)
    if not field_a.resolved():
        raise AssertionError("field should identify one world-law")

    rule_a = field_a.hypotheses[0]
    probe_event = compile_probe(
        probe.action,
        ledger,
        memory,
        kernel_id="world-A",
    )
    rule_a_event = compile_rule(
        rule_a,
        probe.action,
        observed_a,
        ledger,
        memory,
        world_scope="world-A",
        kernel_id="world-A",
    )

    # Same world, much larger unseen state: no further acquisition action.
    rng = random.Random(20260915)
    heldout_a = tuple(rng.randrange(2) for _ in range(64))
    predicted_a = step(rule_from_memory(memory, "world-A"), heldout_a)
    heldout_a_ok = world_a.verify_heldout(heldout_a, predicted_a)

    # World B inherits how to learn. No search over experiments is needed.
    world_b = HiddenECA(30)
    inherited_probe = probe_from_memory(memory)
    rule_b, observed_b, collision_b = identify_with_probe(world_b, inherited_probe)
    rule_b_event = compile_rule(
        rule_b,
        inherited_probe,
        observed_b,
        ledger,
        memory,
        world_scope="world-B",
        kernel_id="world-B",
    )

    heldout_b = tuple(rng.randrange(2) for _ in range(64))
    predicted_b = step(rule_from_memory(memory, "world-B"), heldout_b)
    heldout_b_ok = world_b.verify_heldout(heldout_b, predicted_b)

    first_identification_predictions = probe_search_predictions + collision_a.before
    second_identification_predictions = collision_b.before
    reduction = first_identification_predictions / second_identification_predictions

    print("REALITYGRAPH / COMPOUNDING FIELD DEMO")
    print("------------------------------------")
    print("WORLD A: discover both the law and how to ask")
    print(f"possible world-laws:              {collision_a.before}")
    print(f"candidate experiments searched:   {len(actions)}")
    print(f"probe-search predictions:         {probe_search_predictions}")
    print(f"best outcome classes:             {probe.outcome_classes}")
    print(f"worst-case survivors:             {probe.largest_class}")
    print(f"real interactions:                {world_a.interactions}")
    print(f"surviving world-laws:             {collision_a.after}")
    print(f"learned rule:                     {rule_a}")
    print(f"64-cell held-out exact:           {heldout_a_ok}")
    print()
    print("WORLD B: inherit how to ask")
    print(f"candidate experiments searched:   0")
    print(f"probe-search predictions:         0")
    print(f"identification predictions:       {second_identification_predictions}")
    print(f"real interactions:                {world_b.interactions}")
    print(f"surviving world-laws:             {collision_b.after}")
    print(f"learned rule:                     {rule_b}")
    print(f"64-cell held-out exact:           {heldout_b_ok}")
    print(f"internal identification reduction:{reduction:.0f}x")
    print()
    print(f"probe event:                      {probe_event}")
    print(f"world-A rule event:               {rule_a_event}")
    print(f"world-B rule event:               {rule_b_event}")
    print(f"ledger events:                    {len(ledger.events)}")
    print()
    print("compiled .mg")
    print("------------")
    print(memory.text(), end="")


if __name__ == "__main__":
    main()
