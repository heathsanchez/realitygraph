# RealityGraph

**Turn verified consequence into reusable intelligence.**

RealityGraph is deliberately small:

    raw world -> local kernels -> verifier/consequence
                       |              |
                       v              v
                  causal ledger -> compressed .mg

The kernel is:

    MOVE -> COLLIDE -> SHIFT -> KEEP -> REPEAT

- **Move**: make the cheapest useful construction or action.
- **Collide**: meet independently grounded consequence.
- **Shift**: change only what that collision warrants.
- **Keep**: retain only what changes future reach; preserve unresolved alternatives.
- **Repeat**: begin from the changed present.

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

## Verified learning demo

Run:

    python demo.py

The demo starts with empty `MG1` memory and a fresh graph-coloring problem. Exact 3-color search fails; the kernel minimizes the residual, recognizes one reusable obstruction, and compiles it into:

    +ow:hub(oddcycle)->chi>=4@finite-simple#<provenance>

A fresh 4-color witness is verified. Then a different, larger graph arrives. The learned law matches before 3-color search, so the second solve uses **zero 3-color search nodes**, while its positive witness is still checked exactly.

> **The second problem begins after the reasoning required for the first one.**

## Trust boundary

The proposer may be symbolic search, an LLM, a human, another kernel, or another `.mg`. It is not trusted.

    proposal != truth
    verified consequence -> earned structure

## Verify

    python -m unittest discover -s tests -v
    python demo.py

CI runs both on every push.
