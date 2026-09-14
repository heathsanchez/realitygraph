# RealityGraph

**Turn verified consequence into reusable intelligence.**

RealityGraph is deliberately small:

    raw world -> adapter/IR -> Kernel <-> .mg
                              |
                           verifier

The Kernel is:

    construct -> verify -> residual -> minimal repair -> compress -> reuse

`.mg` is not a transcript. It is the portable residue of lessons worth paying for only once.

## Verified demo

Run:

    python demo.py

The demo starts with empty `MG1` memory and a fresh graph-coloring problem. Exact 3-color search fails; the kernel minimizes the residual, recognizes one reusable obstruction, and compiles it into:

    +ow:hub(oddcycle)->chi>=4@finite-simple#<provenance>

A fresh 4-color witness is verified. Then a different, larger graph arrives. The learned law matches before 3-color search, so the second solve uses **zero 3-color search nodes**, while its positive witness is still checked exactly.

> **The second problem begins after the reasoning required for the first one.**

## Memory

Canonical memory is tiny:

    MG1
    v:proper_k_coloring
    +ow:hub(oddcycle)->chi>=4@finite-simple#5c01292aeda9

History is discarded after it compiles into reusable structure. If two `.mg` files disagree about one identifier, merge preserves the disagreement rather than silently choosing.

## Trust boundary

The proposer may be symbolic search, an LLM, a human, or another `.mg`. It is not trusted.

    proposal != truth
    verified consequence -> earned structure

## Verify

    python -m unittest discover -s tests -v
    python demo.py

CI runs both on every push.
