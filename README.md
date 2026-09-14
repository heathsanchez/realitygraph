# RealityGraph

**Turn verified consequence into reusable intelligence.**

RealityGraph is deliberately small:

    raw world -> local kernels / hypothesis field -> verifier/consequence
                                  |                       |
                                  v                       v
                             causal ledger -> compressed .mg

The kernel is:

    MOVE -> COLLIDE -> SHIFT -> KEEP -> REPEAT

- **Move**: make the cheapest useful construction or action.
- **Collide**: meet independently grounded consequence.
- **Shift**: change only what that collision warrants.
- **Keep**: retain only what changes future reach; preserve unresolved alternatives.
- **Repeat**: begin from the changed present.

## One collision can update a whole field

Run:

    python field_demo.py

The learner starts with all 256 elementary binary radius-1 world-laws as live hypotheses. It is not told which law is true.

It evaluates all 256 possible 8-cell experiments against all 256 hypotheses:

    256 candidate experiments
    x 256 possible world-laws
    = 65,536 internal predictions

The generic field chooses the experiment whose predicted consequences maximally separate the surviving laws. For this finite family it finds a perfect separator: 256 distinct predicted outcomes.

Then it spends one real interaction.

    256 lawful worlds
      -> one chosen move
      -> one observed consequence
      -> 1 surviving world-law

The survivor is compiled through the causal ledger into `.mg`. A fresh 64-cell world is then predicted exactly from the retained law with zero additional learning interactions. The held-out verifier checks the prediction without revealing the hidden law to the learner.

This is a bounded finite demonstration, not a claim of universal system identification. The point is architectural:

> **parallelize counterfactual reasoning; economize contact with reality; make the collision update the whole frontier.**

## Ledger and .mg

They are different objects.

    Ledger = immutable causal evidence
    .mg     = compressed consequential present

Every consequential change is an event in a content-addressed causal DAG. Events carry parents, so RealityGraph knows whether two edits were sequential or genuinely concurrent without trusting wall-clock order.

Concurrent edits never use last-write-wins:

    K1: x -> A
    K2: x -> B

materializes as two live alternatives until consequence separates them.

A revoke removes only versions it causally observed. A concurrent edit survives. Merge is deterministic set union over immutable events, so kernels can write locally and reconcile later without a global lock.

The live `.mg` remains tiny because history is not cognition. It is a projection of the surviving frontier:

    event DAG -> merge -> verify -> compress -> .mg

## Verified compilation demo

Run:

    python demo.py

The graph-colouring demo starts with empty `MG1` memory and a fresh problem. Exact 3-colour search fails; the kernel minimizes the residual, recognizes one reusable obstruction, verifies it, and compiles it.

A different larger graph then begins after that reasoning has already been paid for, so it requires zero 3-colour search nodes while its positive witness is still checked exactly.

## Trust boundary

A proposer may be symbolic search, an LLM, a human, another kernel, or another `.mg`. It is not trusted.

    proposal != truth
    verified consequence -> earned structure

## Verify

    python -m unittest discover -s tests -v
    python demo.py
    python field_demo.py

CI runs all three on every push.
