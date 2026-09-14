import random

from realitygraph import Field, Ledger, MG
from realitygraph.eca import (
    HiddenECA,
    all_rows,
    all_rules,
    compile_rule,
    rule_from_memory,
    step,
)


def main():
    world = HiddenECA(110)  # Hidden from the learner.
    field = Field(all_rules())
    actions = all_rows(8)

    probe = field.choose(actions, step)
    internal_predictions = len(actions) * len(field.hypotheses)

    observed = world.observe(probe.action)
    collision = field.collide(probe.action, observed, step)

    if not field.resolved():
        raise AssertionError("field should identify one world-law")

    learned_rule = field.hypotheses[0]
    memory = MG(verifier="eca_step")
    ledger = Ledger()
    event_id = compile_rule(
        learned_rule,
        probe.action,
        observed,
        ledger,
        memory,
        kernel_id="eca-field",
    )

    rng = random.Random(20260915)
    heldout = tuple(rng.randrange(2) for _ in range(64))
    compiled_rule = rule_from_memory(memory)
    predicted = step(compiled_rule, heldout)
    heldout_ok = world.verify_heldout(heldout, predicted)

    print("REALITYGRAPH / ONE-COLLISION FIELD DEMO")
    print("--------------------------------------")
    print(f"possible world-laws:       {collision.before}")
    print(f"candidate experiments:     {len(actions)}")
    print(f"internal predictions:      {internal_predictions}")
    print(f"best outcome classes:      {probe.outcome_classes}")
    print(f"worst-case survivors:      {probe.largest_class}")
    print(f"real interactions spent:   {world.interactions}")
    print(f"surviving world-laws:      {collision.after}")
    print(f"learned rule:              {learned_rule}")
    print(f"ledger event:              {event_id}")
    print(f"held-out world width:      {len(heldout)}")
    print(f"held-out exact:            {heldout_ok}")
    print(f"extra learning actions:    {world.interactions - 1}")
    print()
    print("compiled .mg")
    print("------------")
    print(memory.text(), end="")


if __name__ == "__main__":
    main()
