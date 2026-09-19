# QCKN Live Developmental Substrate V2 — Flash V1 Hard-Gate Qualification

Authoritative run:
https://github.com/heathsanchez/realitygraph/actions/runs/35421558310

Artifact:
`10576778954`

Artifact digest:
`sha256:d14ee07eabbaf9481fcd731e207b8d7fd1ac1c327f5f76e21fd2c3b207f4d55b`

## Purpose

V2 converts the six implementation requirements from the Flash Architecture
Note V1 into hard CI gates over a provenance-aware incremental runtime.

The six required behaviors are:

1. cross-frontier propagation;
2. dormant-capability revival;
3. negative propagation;
4. incrementality over the affected dependency cone;
5. revocation with restoration/reclosure;
6. restart from the compiled present without replaying discovery history.

The event vocabulary is also typed:

- `VERIFIED_EQUIVALENCE`
- `VERIFIED_SEPARATOR`
- `PROMOTED_CAPABILITY`
- `OBSTRUCTION`
- `PREFERENCE_CHANGE`
- `REVOCATION`

## Prospective episode

The dependency rules and frontier graph were committed before the qualification
run.

The episode includes live/developmental frontiers for:

- SAIR
- ARC
- Lean kernel
- Collatz
- GPU IR
- Flash platform

It imports the current authority-closed Real Multidomain Flash V3 graph, the
current persistent cross-repository live event state, and measured Lean WHNF
cache evidence.

## Qualification result

Every hard gate passed:

```text
PASS_FLASH_CROSS_FRONTIER_PROPAGATION
PASS_FLASH_DORMANT_CAPABILITY_REVIVAL
PASS_FLASH_NEGATIVE_PROPAGATION
PASS_FLASH_INCREMENTALITY
PASS_FLASH_REVOCATION
PASS_FLASH_RESTART_BENEFIT
PASS_FLASH_SEMANTIC_ECONOMIC_SEPARATION
PASS_QCKN_LIVE_DEVELOPMENTAL_SUBSTRATE_V2
```

The fixed-point admission test also passed: re-admitting an already active
identical warranted event touches zero frontiers and performs zero closure
iterations.

## Semantic promotion is not economic promotion

V2 also hard-gates the separation between lawfulness and preference.

### String-context localdef WHNF cache

The exact string-keyed local-definition WHNF cache is semantically qualified:

- successful exact-context WHNF reuse;
- restart reproduces;
- ablation removes the reuse;
- no wrong reject.

But measured wall time is worse than cold:

- cold total: **9,312 ms**
- warm total: **12,238 ms**
- ratio: **1.3142× cold**

Therefore:

```text
semantic_status = VERIFIED
economic_status = RESERVE
```

### Identity-triple key

The follow-up exact identity key compresses the applicability representation from
serialized declaration/parameter/context strings to exact runtime identities.

It materially improves the prior representation:

- string-key total: **10,033 ms**
- identity-triple total: **8,531 ms**
- improvement vs string key: **14.97%**
- exact verified cache hits: **2,875,688**
- restart hits: **2,875,688**

But the declared incumbent remains faster:

- cold: **8,041 ms**
- identity-triple: **8,531 ms**
- identity-triple / cold: **1.06094×**

So it also remains:

```text
semantic_status = VERIFIED
economic_status = RESERVE
```

This is the intended Warranted Consequential Quotienting separation: semantic
equivalence licenses substitution; the declared preference relation decides
whether the representative should become active.

## Incrementality

The ARC obstruction event touched only the ARC frontier. The Collatz obstruction
event touched only the Collatz frontier. The four-domain verified-state
compilation event touched only its declared SAIR, ARC, Lean and GPU-IR dependency
cone; unrelated Collatz and Flash-platform frontiers were not recomputed.

## Revocation

The exact ARC refutation removes the frozen repeated-transfer route. Revoking its
warrant restores that route while leaving the independent Collatz obstruction in
place. Re-admitting the ARC warrant removes it again.

This is provenance-aware reclosure rather than syntactic deletion.

## Restart

The compiled present is serialized and loaded directly. The restart gate requires:

- identical frontier state;
- identical active event identities;
- zero historical event replay.

It passed.

## Claim boundary

This is a finite, prospectively frozen conformance qualification for the Flash V1
runtime requirements. The four-domain meta-capability is grounded in the existing
Real Flash V3 authority graph, and the negative routes use current live
cross-repository evidence identities.

The dormant-capability-revival arm is a controlled conformance replay using a
real compiled capability identity; it is not presented as evidence that the
historical SAIR event occurred in that exact order.

The finite scheduler/search costs in this episode are test units, not
cross-domain measured quantities. No scalar comparison between SAIR calls,
Lean kernel steps, ARC verifier work and GPU measurements is implied.
