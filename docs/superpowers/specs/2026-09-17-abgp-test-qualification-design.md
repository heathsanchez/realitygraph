# ABGP Pre-Freeze Test Qualification Design

Date: 2026-09-17
Branch: `abgp-preregistration-freeze-v1`
Parent scientific design: `docs/superpowers/specs/2026-09-17-abgp-confirmatory-design.md`
Ordinary-explanation addendum: `docs/superpowers/specs/2026-09-17-abgp-ordinary-explanation-controls-design.md`
Status: **REVIEW_PENDING qualification design; confirmatory execution remains disabled**

## 1. Purpose

Before freezing the A/B/G/P confirmatory experiment, qualify the experiment itself on DEV-only worlds whose causal status is known by construction.

The goal is to make a future confirmatory failure interpretable. A scientific `FAIL` must mean that the preregistered hypothesis failed in a valid experiment, not that the harness was unable to detect the target phenomenon, the controls made the positive condition impossible, or a protocol defect invalidated the comparison.

This qualification layer is methodological only. It contributes no confirmatory observations and may never derive, inspect, print, or execute an `ABGP-CONFIRM-*` seed.

## 2. Four scientific verdicts

The arm-level scientific verdict vocabulary becomes:

- `PASS`: every hard validity gate passes; the preregistered effect floor passes; and the Holm-adjusted primary test passes.
- `PARTIAL`: every hard validity gate passes and the primary effect direction is positive, but the effect floor and/or adjusted significance requirement is not met.
- `FAIL`: every hard validity gate passes, but the valid experiment falsifies the arm-level claim by the frozen scientific rule.
- `INVALID`: one or more validity gates required to interpret the arm fail. `INVALID` is not evidence for or against the scientific hypothesis.

`INVALID` has precedence over `PASS`, `PARTIAL`, and `FAIL`. A protocol violation, leakage path, missing required control, namespace violation, malformed restart, broken independence condition, or invalid inferential unit can never be reported as a scientific failure.

The combined A/B/G/P result is scientific only if none of the four arms is `INVALID`.

## 3. Qualification classes

Every arm is exercised against three independently generated DEV-only fixture classes.

### 3.1 Planted-positive fixtures

These fixtures contain the target causal structure by construction and must satisfy the same information boundaries and runner path as the eventual study.

They test whether the frozen experiment is capable of recognizing the phenomenon it claims to test.

The planted mechanism is never injected directly into the analysis output. It must generate ordinary raw task records through the same runner, controls, serializers, restart boundaries, and analysis implementation used by the scientific harness.

A planted-positive fixture may not bypass an oracle, hard gate, ablation, or control merely because its truth is known during development.

### 3.2 Ordinary-explanation fixtures

These fixtures are deliberately constructed so that an ordinary explanation is sufficient and no stronger construction/retention interpretation is warranted.

They test false-positive resistance. The appropriate ordinary control must explain the treatment by construction, and the strengthened scientific arm must therefore not receive `PASS`.

Where possible, the fixture must fail for the specific explanatory reason being tested rather than merely through low power.

### 3.3 Broken-mechanics fixtures

These fixtures deliberately violate one preregistered validity condition while keeping the scientific signal otherwise arbitrary.

They test whether protocol defects are separated from scientific falsification. Every broken-mechanics fixture must return `INVALID` with a deterministic machine-readable reason code.

No broken-mechanics fixture may be silently dropped, converted to missing data, or counted as `FAIL`.

## 4. Arm A qualification

### 4.1 A planted positive

Construct a finite DEV family with all of the following properties certified exactly:

1. the frozen old representation `R0` is extensionally complete for its declared old language;
2. at least one old-information collision contains differently optimal future actions;
3. the single acquisition verifier message remains direct-action insufficient;
4. exact acquisition-carry-forward Bayes in `R0` cannot resolve the future collision;
5. a declared lower-substrate constructor can expose a new observable `c` that strictly refines the collision;
6. `c` is not measurable from `R0`, `R0 + M`, or the old posterior;
7. the constructor is proposed/admitted without future target-label access;
8. after the acquisition verifier is removed, the earned extension improves sealed prospective decisions by more than the frozen A effect floor relative to every A primary control;
9. matched novel sham expansion receives the same history and budget but does not resolve the action-relevant collision.

The expected verdict is `PASS`.

### 4.2 A ordinary explanations

At minimum, freeze separate DEV fixtures for:

- **Bayes-sufficient:** the acquisition message/posterior fully explains the prospective gain inside `R0`; no genuine new observable is needed.
- **Re-encoding-only:** the proposed `R1` is extensionally novel in syntax but measurable from `R0` or the old posterior.
- **Sham-equivalent:** a matched consequence-shuffled extension performs as well as the treatment.
- **Verifier-answer channel:** at least one message class uniquely identifies the protected action.

The first three are valid scientific negative fixtures and must not `PASS` the stronger A claim. The direct-answer-channel fixture is a protocol invalidity and must return `INVALID`, not `FAIL`.

### 4.3 A broken mechanics

At minimum:

- future verifier access after the sealed split;
- proposal/admission access to protected future labels;
- missing old-language completeness certificate;
- mismatched sham compute/resource budget;
- unbound or nondeterministic Bayes tie-break/prior.

Each must return `INVALID` with the corresponding reason.

## 5. Arm B qualification

### 5.1 B planted positive

Construct four genuinely independent DEV grammar families satisfying the frozen B independence rules. The acquisition grammar contains evidence that supports a transferable structural capability; the target grammar alone, even after granting the ordinary control exact acquisition-posterior carry-forward plus target-side greatest-bisimulation knowledge, leaves a residual ambiguity that the transferred structural object resolves.

The same transferred object must predict the protected action-order response to all four held-out intervention classes. Wrong-class, shuffled-coupling, and acquisition-posterior/target-bisimulation controls must remain below the frozen B effect floor.

Expected verdict: `PASS`.

### 5.2 B ordinary explanations

At minimum:

- **dictionary-sufficient:** independent-looking surfaces hide a recoverable one-to-one primitive mapping;
- **target-bisimulation-sufficient:** the target grammar and shared latent generator already determine the protected order without transferred capability;
- **posterior-sufficient:** ordinary acquisition posterior carry-forward plus target observations determines the protected order;
- **marginal-only:** shuffled coupling preserves superficial statistics while destroying the relevant consequence relation.

Dictionary leakage is a validity failure and must return `INVALID`. The remaining ordinary-explanation cases are valid scientific negatives and must not `PASS` B.

### 5.3 B broken mechanics

At minimum:

- supplied deterministic cross-grammar translation;
- shared prohibited surface symbols or serialization schema;
- paired cross-grammar demonstrations;
- missing structural intervention class;
- malformed bisimulation continuation set or non-hash-bound canonicalizer.

Each must return `INVALID`.

## 6. Arm G qualification

### 6.1 G planted positive

Construct a DEV family in which action-relevant cells are known independently of the corruption outcome and corruption of those cells causally changes protected action order with a preregistered dose response, while count- and magnitude-matched action-irrelevant corruption does not.

The frozen exact dose-weighted randomization analysis must detect the planted relevance-by-dose effect at the minimum scientifically meaningful regime selected during pre-freeze power qualification.

Expected verdict: `PASS`.

### 6.2 G ordinary explanations

At minimum:

- no relevance interaction: relevant and irrelevant corruption have the same flip process;
- global-damage-only: apparent degradation is explained by corruption amount/magnitude rather than relevance;
- reversed relevance: irrelevant corruption produces the stronger effect.

These are valid scientific negatives and must not `PASS` G; the reversed case must produce `FAIL` under the frozen directional rule.

### 6.3 G broken mechanics

At minimum:

- relevance labels computed after corruption;
- unmatched corruption count;
- unmatched corruption magnitude;
- evaluator mismatch between relevance classification and protected-order scoring;
- post-hoc cell relabeling.

Each must return `INVALID`.

## 7. Arm P qualification

### 7.1 P planted positive

Construct a source-distinct DEV family in which acquisition creates a retained structural object that contains decision-relevant structure not recoverable from either:

- target-only observational equivalence; or
- an exact posterior-only Bayesian memory of the same acquisition experience.

The object is canonically serialized, hard-restarted from retained bytes only, invoked label-free, and used on untouched future tasks with zero verifier calls and zero reconstruction/search before action.

Treatment must exceed every P primary ordinary baseline by more than the frozen P effect floor. Targeted lineage deletion must collapse performance into the frozen ordinary-control envelope, and explicit reacquisition must re-enter positive search/construction and restore the pre-deletion capability within the frozen tolerance.

Expected verdict: `PASS`.

### 7.2 P ordinary explanations

At minimum:

- **posterior-memory-sufficient:** a posterior-only retained Bayesian state explains all future advantage;
- **target-bisimulation-sufficient:** future observations and shared generator alone determine the action;
- **sham-sufficient:** size-matched sham performs as well as the retained treatment;
- **noncausal-retention:** deletion leaves the claimed advantage intact.

These are valid scientific negatives and must not `PASS` P. The noncausal-retention case must fail the causal interpretation even if raw treatment accuracy is high.

### 7.3 P broken mechanics

At minimum:

- verifier call after restart;
- reconstruction/search before future action;
- target-label use in applicability selection;
- prohibited shared source identifiers/templates/serialization/exact structures;
- restart that silently preserves pre-restart process state;
- deletion path that is not lineage-targeted;
- reacquisition path that never actually re-enters search/construction.

Each must return `INVALID`.

## 8. Statistical-code qualification

Before any scientific DEV effect is interpreted, the exact statistical implementation must be independently checked against closed-form or exhaustive small-state references.

Required checks:

1. exact one-sided McNemar/binomial discordant-pair probabilities for all small `n` configurations up to a frozen tractable bound;
2. Holm-Bonferroni ordering, adjusted p-values, and tie-breaking for exhaustive small four-arm p-value grids;
3. G exact dynamic-programming randomization distribution against brute-force sign enumeration on small discordant sets;
4. Wilson/Newcombe interval implementation against an independent reference formula/test vector;
5. zero-discordance, all-success, all-failure, exact-tie, and boundary-effect cases;
6. deterministic replay from raw artifact only, with no hidden runtime state.

A mismatch in statistical-code qualification blocks freezing and is not a scientific result.

## 9. Power and sensitivity qualification

No confirmatory namespace is needed to audit whether the frozen sample sizes and tests can detect the minimum effects the study says it cares about.

### 9.1 Exact paired-test power surfaces

For A, B, and P, compute exact rejection probability over a preregistered grid of paired discordance probabilities `(p10, p01)` consistent with each proposed minimum effect floor. Because McNemar power depends on discordance, not only the marginal accuracy difference, report the full surface rather than a single optimistic number.

Before freeze, choose and document a scientifically defensible nuisance envelope for discordance. The locked task count must achieve at least `0.80` power at the minimum meaningful effect throughout that envelope. If it does not, change the task count **before** freeze or explicitly raise the minimum detectable effect; do not discover low power after confirmation.

### 9.2 G sensitivity

For G, use the exact frozen randomization statistic to compute or exhaustively simulate from DEV-only generative laws the rejection probability across a frozen grid of relevance-by-dose effects, including the proposed minimum dose-1.0 gap. The chosen `n_worlds` must provide at least `0.80` power at the minimum meaningful planted interaction under the frozen nuisance envelope.

### 9.3 Type-I calibration

Under valid null/ordinary-explanation fixture families, empirical or exhaustive rejection rates must be consistent with the exact nominal arm-level test size. This check validates implementation; it does not replace the exact p-value calculation.

No task count, effect floor, nuisance envelope, or power target may be tuned using `ABGP-CONFIRM-*` data.

## 10. Logical satisfiability audit

The strengthened controls must not make a positive result logically impossible.

Before freeze, DEV qualification must produce at least one fully specified finite planted-positive world family for A, B, G, and P in which all validity gates are simultaneously satisfiable and the corresponding stronger claim is true by construction.

The qualification artifact must include machine-checkable witnesses for:

- A old-language collision plus non-measurable useful refinement;
- B residual ambiguity after acquisition-posterior + target-bisimulation oracle, resolved by transferred structure;
- G pre-corruption relevance distinction with causal dose response;
- P residual advantage beyond both ordinary ceilings plus causal deletion/reacquisition.

If no such family can be constructed without cheating a frozen information boundary, the design is rejected before confirmation.

## 11. Qualification verdict

The pre-freeze harness receives a single methodological qualification verdict.

`QUALIFIED` requires all of the following:

1. every planted-positive fixture produces the preregistered expected scientific `PASS`;
2. every ordinary-explanation fixture produces its preregistered non-PASS verdict for the intended reason;
3. every broken-mechanics fixture produces `INVALID` with the exact expected reason code;
4. statistical-code qualification is exact;
5. power/sensitivity qualification meets the locked minimum-power requirement;
6. logical satisfiability witnesses exist for all four arms;
7. deterministic artifact replay reproduces every verdict bit-for-bit;
8. no confirmatory namespace, seed, instance, or outcome was touched.

Any failure yields `NOT_QUALIFIED`. `NOT_QUALIFIED` blocks final lock creation and confirmatory execution.

The qualification suite may be repaired and rerun on DEV-only fixtures until `QUALIFIED`, but every scientific design change made during this process must remain visible in version history and must occur before final freeze.

## 12. Anti-overfitting rules

Qualification is allowed to debug mechanics; it is not allowed to become an indirect pilot on hidden confirmatory tasks.

Therefore:

- qualification fixtures use dedicated `ABGP-QUAL-*` or existing `ABGP-DEV-*` namespaces only;
- their generators are separate from confirmatory instance seeds;
- no confirmatory seed derivation is permitted even for dry-run inspection;
- positive fixtures are defined from causal construction requirements, not from observed treatment failures;
- negative fixtures are defined from named ordinary explanations, not from whichever control happened to perform best;
- sample-size/power revisions use analytic or DEV-only sensitivity calculations;
- all discarded qualification designs remain visible in git history.

## 13. Artifacts and lock binding

A successful qualification run emits an immutable DEV-only artifact containing:

- design/addendum digests;
- scientific-code and qualification-code hashes;
- qualification namespace identifiers;
- raw fixture records;
- expected versus observed verdicts;
- validity reason codes;
- statistical-reference comparisons;
- power/sensitivity surfaces and nuisance envelope;
- logical-satisfiability witnesses;
- deterministic replay digest;
- explicit `confirmatory_namespace_used = false` assertion;
- final `QUALIFIED` or `NOT_QUALIFIED` verdict.

The final scientific lock must bind the exact qualified scientific code, analysis code, validity semantics, fixture-schema version, and qualification evidence digest. Qualification fixtures themselves are never included as confirmatory evidence.

## 14. Implementation boundary after approval

After this written design is approved, implementation should proceed test-first and in this order:

1. add `INVALID` and validity-reason semantics without changing any confirmatory unlock;
2. add independent statistical reference tests;
3. add planted-positive/ordinary-explanation/broken-mechanics fixture generators for A/B/G/P;
4. add exact power/sensitivity audit code;
5. add logical-satisfiability witness production;
6. add a qualification runner and canonical artifact/replay;
7. integrate qualification as a hard prerequisite for final-lock validation;
8. run only DEV/QUAL namespaces until the complete suite is `QUALIFIED`;
9. only then return to joint preregistration review and final freeze.

No implementation step in this design authorizes `ABGP-CONFIRM-v1` execution.