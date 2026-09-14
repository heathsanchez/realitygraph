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

## Compounding field demo

Run:

    python field_demo.py

World A starts with all 256 elementary binary radius-1 world-laws as live hypotheses. The learner is not told which law is true.

It evaluates every 8-cell experiment against every possible law:

    256 candidate experiments
    x 256 possible world-laws
    = 65,536 internal predictions

The generic field selects the experiment whose predicted consequences maximally separate the frontier. It discovers a perfect separator: one real observation collapses 256 lawful worlds to one.

That experiment is then independently verified against the entire declared 256-rule family and compiled into `.mg` as a reusable learning capability.

World B is a different hidden law. It inherits the compiled probe instead of searching 256 experiments again:

    cold identification:
      65,536 probe-search predictions
      + 256 collision predictions

    inherited identification:
      0 probe-search predictions
      + 256 collision predictions

    reduction = 257x

Both worlds require one real interaction. Each identified law is kept only in its own world scope; the probe alone is promoted across the whole verified family. Fresh 64-cell states are then predicted exactly from the retained instance laws without another acquisition interaction.

This is a bounded finite demonstration, not universal system identification. The point is architectural:

> **A solved world can teach the system how to learn the next world.**

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
