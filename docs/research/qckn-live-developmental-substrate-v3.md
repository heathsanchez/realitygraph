# QCKN Live Developmental Substrate V3 — Two Prospectively Frozen Real Cycles

## Purpose

V3 moves beyond the finite six-invariant Flash conformance gate and runs the
qualified developmental machinery through two prospectively frozen target
episodes.

Each episode freezes the selected experiment and promotion/classification rule
in RealityGraph **before** the target Lean run, then ingests the resulting
evidence, recompiles the present, removes exactly the now-settled acquisition
route, and reranks the remaining portfolio.

## Starting point

Flash V1 mechanics were already hard-gated in:

- run `35421558310`
- artifact `10576778954`
- digest
  `sha256:d14ee07eabbaf9481fcd731e207b8d7fd1ac1c327f5f76e21fd2c3b207f4d55b`

All six required behaviors were green:

- cross-frontier propagation
- dormant-capability revival
- negative propagation
- dependency-cone incrementality
- revocation/reclosure
- restart from compiled present without discovery replay

## Real cycle 1 — scoped WHNF cache

Precommit:

`7a2806d8efa5b1b018c1adeb53bffbab6f2dbe54`

The frozen question was whether the previously verified exact-identity localdef
WHNF cache could become economically active by restricting it to the already
measured `Nat.succ_le_succ` hotspot.

Target run:

https://github.com/heathsanchez/lean-kernel-arena/actions/runs/35421936419

Artifact:

`10576959191`

Digest:

`sha256:38d389a8fa8e452f8cf872d5db2cbe2d152995600459730f278eb063c38aada1`

Measured result:

- cold: **7,379 ms**
- full identity cache: **7,774 ms**
- scoped cache: **7,685 ms**
- restart scoped: **7,740 ms**
- scoped verified cache hits: **2,868,158**

The scoped representation improved over the full cache by about **1.14%**, but
remained about **4.15% slower than cold**.

Therefore the precommitted promotion rule classified it:

`economic_status = RESERVE`

The semantic capability was retained, but the exact realization route was
compiled away and the economic obstruction:

`lean:succ-le-succ-scoped-cache-not-profitable:v1`

was added.

RealityGraph reclosure run:

https://github.com/heathsanchez/realitygraph/actions/runs/35422069761

Artifact:

`10577249725`

Digest:

`sha256:4d2b1bb252c0865738c4ceaefac82c0b3708a5d523c07081c0edf2e4b6dccf1f`

Exactly **one future acquisition route** was eliminated.

The graph reranked the Battle market to:

`lean-cache-overhead-decomposition`

while Discovery continued to select:

`flash-platform-next`

under conservative, neutral and aggressive priors.

## Real cycle 2 — overhead decomposition

The second experiment was frozen before its target run in RealityGraph commit:

`596038b0d96fcda4780056be10bc69766bbcdaf7`

The frozen question was whether verified WHNF consequence reuse was intrinsically
valuable but hidden by lookup overhead, or whether this memoization realization
was economically neutral/negative at the current frontier.

Target run:

https://github.com/heathsanchez/lean-kernel-arena/actions/runs/35422152175

Artifact:

`10576714731`

Digest:

`sha256:eb405f9383ad5a2b765ea466e8a0fe58637ea9747747b9d4107b7a77f478d6b6`

Paired median totals over three repetitions per case:

- cold: **10,073 ms**
- declaration guard only: **9,949 ms**
- lookup only: **10,113 ms**
- scoped cache: **10,676 ms**

Frozen classification:

- guard overhead positive: **false**
- lookup overhead positive: **true**
- reuse gross-beneficial under this measurement contract: **false**
- net win: **false**

So the prospectively specified next route was:

`pivot-away-from-whnf-memoization`

This result is narrowly scoped. It does not claim that memoization is universally
harmful; it establishes that the tested exact memoization realizations do not
earn economic promotion on these two deep-list frontiers under the frozen 2M
semantic-step / GitHub-runner contract.

RealityGraph reclosure run:

https://github.com/heathsanchez/realitygraph/actions/runs/35422326680

Artifact:

`10578065010`

Digest:

`sha256:12dd7f614f93dfe79883bad21c862172039acbf0d291b7c619f033a31e2b508e`

The graph compiled:

`lean:whnf-memoization-no-net-win-at-2m:v1`

removed the exact overhead-decomposition acquisition route, retained the
semantically valid memoization capability in reserve, and reranked the remaining
market.

Cumulative exact acquisition routes eliminated by the two prospective cycles:

**2**

Next Battle selection, stable under all three priors:

`lean-nat-le-transition-quotient-diagnostic`

Next Discovery selection:

`flash-platform-next`

## Developmental interpretation

These two cycles demonstrate the intended distinction between success and
capital.

Cycle 1 did not produce an active optimization. It produced a narrower
representation and an exact economic obstruction.

Cycle 2 did not rescue memoization. It converted the failed realization family
into a compiled negative consequence and removed another future acquisition
route.

The live sequence was therefore:

```text
verified recurrence
→ exact cache realization
→ semantic success / economic failure
→ narrower scoped realization
→ prospective target test
→ reserve + economic obstruction
→ reclose
→ overhead decomposition
→ prospective target test
→ memoization obstruction
→ reclose
→ select transition-quotient diagnostic
```

This is the desired Flash behavior: informative failures change the future
search graph rather than merely appearing in a report.

## Claim boundary

The cumulative route-elimination count is a count of exact planned acquisition
routes in this prospectively frozen Lean episode chain. It is not a scalarized
cross-domain cost.

Wall-time measurements remain local to these GitHub-runner experiments. No
claim is made that the same timing order holds on all machines, all budgets or
all Lean workloads.

The next selected Lean experiment concerns transition quotienting rather than
memoization. No semantic `Nat.le` shortcut has yet been authorized.
