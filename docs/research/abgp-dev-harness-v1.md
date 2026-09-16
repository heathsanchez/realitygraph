# ABGP DEV Harness V1 — Qualification Record

Date: 2026-09-17
Branch: `abgp-preregistration-freeze-v1`
Base: `verified-meta-growth-v3` at `45c766cd3d5410cea90790a67958390be9ccb896`
Scientific status: **DEVELOPMENT MECHANICS ONLY — NOT CONFIRMATORY EVIDENCE**

## Purpose

This branch implements and adversarially qualifies the development-only harness for the preregistered A/B/G/P study on capability identity and verified future-action structure.

The harness exists to make the later confirmatory experiment harder to accidentally contaminate. It validates task generation, frozen analysis, negative controls, replay, seed isolation, persistence boundaries, and final-lock construction while keeping `ABGP-CONFIRM-v1` unavailable.

No A/B/G/P scientific claim is licensed by the DEV outcomes recorded here.

## Normative scientific inputs

The harness treats these files as normative:

- `docs/superpowers/specs/2026-09-17-abgp-confirmatory-design.md`
- `preregistration/abgp-design-manifest-v1.json`
- `preregistration/abgp-analysis-plan-v1.json`

The design manifest remains:

```text
status = REVIEW_PENDING
confirmatory_execution_enabled = false
development namespace = ABGP-DEV-v1
confirmatory namespace = ABGP-CONFIRM-v1
```

Any attempt to enter the confirmatory namespace from this branch fails closed before task generation.

## Code-complete qualification evidence

Code-complete head:

`41fbad5982841b522470cbe54a6718de7ea5f2bf`

Authoritative code-complete run:

`35160554522`

Job:

`105010075983`

Full regression suite:

```text
165 / 165 PASS
```

DEV evidence artifact:

```text
artifact id = 10472219247
name        = abgp-dev-harness-v1-evidence
zip sha256  = a8bce209a49fab4f41d3cf3b5c5f67896f66e62289855a1a487b530320788296
```

The dedicated workflow also passed every focused ABGP test group, inherited V3 qualification, the standalone DEV matrix, the explicit scientific safety boundary, and DEV-only artifact upload.

## What the harness now enforces

### A — verifier-channel mechanics

The DEV fixture checks the exact interface required by the preregistration:

- constructor-visible verifier messages remain non-identifying: every admitted message leaves more than one protected-optimal action live;
- exactly one verifier message and one repair round are used;
- equal-compute recheck and verifier-assisted paths expose matched compute accounting;
- the frozen paired analysis uses the preregistered exact one-sided McNemar/binomial-on-discordants test.

### B — independent grammar mechanics

The DEV fixture contains four independently parameterized grammar adapters:

- extensional;
- compositional;
- reachability;
- constraint/order.

They use pairwise-disjoint surface alphabets, distinct serialization schemas, different primitive signatures/arities, and distinct inference routes. No translation table is supplied. All 12 ordered acquisition-to-transfer directions are generated, and each is tested under the four frozen intervention classes:

- edge/relation deletion;
- protected-order reversal perturbation;
- scope change;
- constraint change.

Matched wrong-class and shuffled-coupling controls are emitted explicitly. Scoring is against protected future-action ordering rather than literal representation reconstruction.

### G — corruption-geometry mechanics

The DEV fixture:

- labels action-relevant versus action-irrelevant cells before corruption;
- matches corruption count and magnitude between the two classes at every nonzero dose;
- uses the frozen dose schedule;
- analyzes the preregistered dose-weighted relevance contrast with an exact dynamic-programmed paired randomization distribution rather than Monte Carlo.

### P — persistence mechanics

The DEV fixture exercises the harder persistence boundary:

- retain a non-verbal structural object plus explicit applicability metadata;
- canonical byte-exact serialization and hard restart;
- zero verifier calls after restart;
- zero reconstruction/search before future action;
- label-free applicability;
- source-distinct future instances;
- cold, equal-compute, verbal-rule, size-matched sham, and wrong-class controls;
- targeted retained-lineage deletion restoring the cold behavior and forcing positive reacquisition search.

### Raw replay and analysis

`abgp_dev_matrix.py` emits a canonical raw artifact. The complete A/B/G/P analysis can be recomputed from that JSON artifact alone. Live analysis and replay analysis are normalized to the same JSON data model, preventing Python tuple/list or integer/string-key representation differences from masquerading as statistical differences.

The frozen analysis implementation includes:

- exact one-sided paired McNemar tests;
- deterministic Holm-Bonferroni correction across A/B/G/P;
- exact dynamic-programmed randomization for G;
- mechanical PASS/PARTIAL/FAIL rules and hard-gate handling.

### Review-only final lock

`realitygraph/abgp/lock.py` can build a review candidate containing the required scientific/runtime hashes and can validate a separately produced future frozen lock.

It cannot freeze confirmation. The committed template `preregistration/abgp-final-lock-template-v1.json` is explicitly:

```text
status = REVIEW_PENDING
confirmatory_execution_enabled = false
builder_can_freeze = false
```

Any future `FROZEN` lock requires a separate explicit reviewed change outside this DEV-only implementation plan.

## DEV matrix output

For reproducibility, the code-complete DEV run produced:

```text
A dev_verdict=PASS effect=0.296875 raw_p=0.000438955 holm_p=0.000438955
B dev_verdict=PASS effect=0.770833 raw_p=5.29396e-23 holm_p=2.11758e-22
G dev_verdict=PASS effect=1.000000 raw_p=5.42101e-20 holm_p=1.6263e-19
P dev_verdict=PASS effect=0.718750 raw_p=1.42109e-14 holm_p=2.84217e-14
scientific_status DEVELOPMENT_MECHANICS_ONLY_NOT_CONFIRMATORY_EVIDENCE
confirmatory_namespace_used 0
ABGP_DEV_MATRIX_OK
ABGP_DEV_SAFETY_BOUNDARY_OK
```

These numbers are **synthetic development-fixture outcomes**. They demonstrate that the preregistered analysis and control paths execute and separate known DEV constructions. They must not be interpreted as estimates of confirmatory effect size, statistical power, or A/B/G/P scientific truth.

## Claim boundary

This branch establishes that the preregistered A/B/G/P protocol can be executed, audited, replayed, and fail-closed in a development environment while the confirmatory namespace remains inaccessible.

It does **not** establish:

- A, B, G, or P as a confirmatory scientific result;
- that the DEV effect sizes predict confirmatory outcomes;
- that the confirmatory task generator will yield the same signs or magnitudes;
- representation-independent capability identity;
- universal grammar invariance;
- verifier-independent persistence outside the frozen future study;
- arbitrary substrate invention or unbounded self-development.

## Next state

The next scientific step is not another DEV tuning cycle. It is a separate review/freeze step that binds the exact documentation-complete code tree, generator/verifier/evaluator/analysis hashes, runtime/environment versions, resource budgets, sham/corruption/ablation implementations, and one-shot execution policy into a final lock.

Only after that separate lock is reviewed and explicitly frozen may `ABGP-CONFIRM-v1` be exposed for a single confirmatory execution.

This document records the code-complete qualification run above. A later documentation-complete CI run necessarily has a newer commit SHA, so its exact run/artifact identifiers are intentionally reported externally rather than recursively editing this file and creating an infinite evidence-head chase.
