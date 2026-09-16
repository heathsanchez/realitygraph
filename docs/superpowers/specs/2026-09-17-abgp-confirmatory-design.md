# ABGP Confirmatory Study Design

Date: 2026-09-17
Branch: `abgp-preregistration-freeze-v1`
Base: `verified-meta-growth-v3` at `45c766cd3d5410cea90790a67958390be9ccb896`
Status: reviewable scientific design; confirmatory execution disabled until final lock

## 1. Purpose

RealityGraph V3 establishes a bounded verified meta-growth mechanism: a structural obstruction can be classified, a repair family can be selected from a frozen portfolio, the resulting object capability can be independently verified, the repair rule can be calibrated before promotion, and a later structurally equivalent obstruction can trigger the retained repair rule without portfolio search or competitor calls.

V3 does **not** answer four stronger scientific questions:

- **A — Verifier channel:** whether non-identifying verifier feedback improves protected action selection beyond equal-compute reconsideration without simply transmitting the answer.
- **B — Grammar invariance:** whether the retained future-action structure survives genuinely independent relation grammars rather than only alternative encodings of one grammar.
- **G — Corruption geometry:** whether downstream performance tracks corruption of action-relevant distinctions rather than overall representational fidelity.
- **P — Persistence form:** whether a retained non-verbal structural object survives a hard restart and transfers to source-distinct future tasks with no verifier and zero reconstruction/search.

This design freezes those four questions into a confirmatory protocol without using V3 outcomes as confirmatory evidence.

## 2. Scientific object

The study target is not a literal operator, relation, or complete reconstructed world. It is a **protected future-action structure**: an equivalence class or order over live continuations sufficient to preserve the ordering of actions relevant to the protected objective, relative to a frozen effective language and information boundary.

The confirmatory study therefore evaluates behavioral and intervention-level recovery, not literal syntactic identity.

## 3. Separation of development and confirmation

No confirmatory task is available to the development harness.

Two deterministic seed namespaces are defined:

- `ABGP-DEV-v1`: development, unit tests, negative controls, dry runs, debugging, performance tuning, and harness validation.
- `ABGP-CONFIRM-v1`: single confirmatory execution only after final lock.

Every generated instance seed is derived as:

`SHA256(root_namespace || arm || cell || index || generator_version)`.

The final confirmatory runner refuses to execute unless all of the following are true:

1. the design manifest digest matches the committed design manifest;
2. a separate final lock contains exact generator, evaluator, verifier, analysis, sham, ablation, and model/version hashes;
3. the lock records `status = FROZEN`;
4. the current repository tree matches the locked code tree hash;
5. the confirmatory namespace has not previously emitted a completion record for that lock digest.

Development runs never receive or print `ABGP-CONFIRM-v1` derived instance seeds.

## 4. Statistical family

There is one primary confirmatory hypothesis per arm: A, B, G, and P.

The four primary arm-level p-values are controlled with Holm-Bonferroni at familywise alpha `0.05`.

A full PASS requires both:

- the arm-specific precommitted effect-size floor; and
- the arm's Holm-adjusted primary test to pass.

Secondary metrics are descriptive or corroborating unless explicitly listed as hard gates below. Statistical significance alone cannot override a failed structural, ablation, leakage, independence, or zero-search gate.

All interval estimates reported for primary binary rates use exact or score-based 95% confidence intervals selected before confirmation in the final analysis module; the same method must be used for every arm where applicable.

## 5. Arm A — non-identifying verifier channel

### Hypothesis

A non-identifying verified residual can improve protected action selection beyond equal-compute reconsideration.

### Frozen task count

256 fresh paired confirmatory tasks.

Each task is evaluated under the same frozen compute budget in three primary conditions:

1. one-shot;
2. equal-compute recheck with no verifier information;
3. verifier-assisted with exactly one admitted verifier message and one repair round.

### Direct-action insufficiency gate

For every constructor-visible verifier message `m`, before the constructor acts we compute:

- `W(m)`: protected worlds compatible with exactly the constructor's frozen prior information plus `m`;
- `A*(m)`: the union of actions optimal in at least one world in `W(m)`.

A message class is admissible only if `|A*(m)| > 1` on every use in the non-identifying arm.

Any message use that uniquely identifies the protected action invalidates that task for A and triggers a design-violation failure rather than post hoc filtering.

Repeated binary elimination is forbidden.

### Primary test and effect floor

Primary paired outcome: exact protected-action selection for verifier-assisted versus equal-compute recheck.

Full A PASS requires:

- absolute paired improvement of at least `0.05` in exact protected-action rate;
- Holm-adjusted primary significance at familywise alpha `0.05`;
- direct-action insufficiency gate satisfied for every admitted message;
- interaction and message budgets exactly respected.

Downstream task success is a secondary corroborating metric.

### Falsification

A fails if improvement over equal-compute recheck is below 5 percentage points, does not survive familywise correction, or depends on any message class that uniquely identifies the protected action.

## 6. Arm B — grammar invariance

### Hypothesis

The same protected future-action structure can be recovered across genuinely independent relation grammars, rather than through equivalent syntax or a hidden dictionary.

### Grammar families

Four independently generated families are frozen:

1. extensional action-observation-consequence relations;
2. compositional operator grammars;
3. graph/reachability grammars;
4. constraint/order grammars expressed through pairwise dominance or partial-order structure.

Across families, only these may be shared:

- the latent world/task generator;
- the protected objective;
- the protected action-order semantics.

These must be independently generated across grammar families:

- surface symbols;
- primitive relations/operators;
- primitive arity;
- composition rules;
- derivation templates and inference paths;
- serialization;
- candidate-set generation.

No deterministic grammar translation is supplied. A simple one-to-one primitive dictionary must not be recoverable by construction.

### Cross-grammar matrix

All 12 ordered acquisition-to-transfer directions between the four grammar families are evaluated.

Each ordered direction uses 32 fresh latent worlds, for 384 acquisition/transfer world pairs.

For every latent world, evaluation includes four predeclared held-out structural intervention classes capable of changing protected action ordering:

1. edge/relation deletion;
2. protected-order reversal perturbation;
3. scope change;
4. constraint change.

### Primary behavioral criterion

Literal relation reconstruction is neither required nor sufficient.

Recovery is measured by exact agreement on the protected action ordering and its change under the held-out interventions.

Full B PASS requires:

- at least `0.90` exact protected-order agreement across the pooled cross-grammar held-out intervention evaluations;
- at least a `0.15` absolute advantage over the matched-complexity wrong-class control;
- at least a `0.15` absolute advantage over the shuffled-coupling control;
- Holm-adjusted primary significance for cross-grammar recovery versus the stronger of the two negative controls;
- no deterministic translation, primitive dictionary, symbol reuse, serialization reuse, or paired cross-grammar demonstration leakage.

### Controls

- pure renaming/encoding control;
- matched-complexity wrong-class control inducing a different protected action ordering;
- shuffled-coupling control preserving marginal statistics while breaking observation-to-future-consequence coupling.

### Falsification

B fails if recovery collapses across independent grammars, depends on a translation/dictionary, or the grammars disagree about how protected action ordering changes under the frozen structural interventions despite nominal static-answer agreement.

## 7. Arm G — action-relevance corruption dose response

### Hypothesis

Downstream behavior tracks corruption of distinctions that can change protected action ordering, not total representational fidelity.

### Frozen task count and dose schedule

256 fresh latent worlds.

Corruption doses:

`0.00, 0.10, 0.25, 0.50, 1.00`.

Within every world, corruption is paired between cells classified before corruption as:

- action-relevant: changing the cell can alter the protected ordering among live actions under the frozen evaluator;
- action-irrelevant: changing the cell cannot alter that protected ordering under the frozen evaluator.

Corruption count and magnitude are matched between relevance classes at each dose.

### Primary test

Primary test: predeclared relevance-by-corruption-dose interaction on exact protected action-order flip probability.

Full G PASS requires:

- interaction in the predicted direction with Holm-adjusted significance at familywise alpha `0.05`;
- at the maximum nonzero dose, an absolute action-order flip-rate gap of at least `0.15` between relevant and irrelevant corruption;
- corruption classes computed before corruption;
- no post hoc relabeling of cells by observed downstream effect.

### Secondary measures

- downstream task accuracy;
- zero-target-entropy rate where applicable;
- monotonicity of flip rate across doses;
- matched random-location corruption.

### Falsification

G fails if the preregistered interaction is absent or reversed, or if action-irrelevant corruption harms protected ordering comparably to action-relevant corruption across the dose schedule.

## 8. Arm P — retained persistence without verifier

### Hypothesis

A verifier-induced non-verbal structural object can persist through hard restart and transfer to source-distinct future tasks without verifier feedback or reconstruction/search.

### Frozen task count

256 source-distinct held-out tasks.

### Acquisition and persistence boundary

Acquisition occurs under frozen verified feedback and may perform the full allowed construction/search protocol.

After acquisition:

1. retain only the declared non-verbal structural object plus its explicit applicability metadata;
2. serialize it canonically;
3. hard-restart from that retained object only;
4. remove the verifier entirely;
5. select future applicability without target labels;
6. run untouched future tasks with zero reconstruction/search.

The held-out future task generator may share only the protected objective/action-order principle with acquisition. It must exclude shared:

- entity identifiers;
- lexical templates;
- instance seeds;
- surface serialization;
- exact structures/topologies;
- source-specific labels;
- verifier outputs.

### Baselines and controls

- cold;
- equal-compute recheck;
- failed/verbal-rule persistence baseline;
- size-matched sham retained object;
- wrong-class retained object;
- targeted retained-lineage deletion.

### Primary criterion

Primary outcome: exact protected-action selection.

Full P PASS requires:

- retained-object accuracy at least `0.05` above the strongest of cold, equal-compute recheck, size-matched sham, and wrong-class controls;
- Holm-adjusted primary significance at familywise alpha `0.05`;
- zero future reconstruction/search;
- zero verifier access after restart;
- label-free applicability selection;
- targeted deletion reduces performance to within `0.02` absolute of the cold baseline and forces reacquisition search to resume.

### Falsification

P fails if the retained object does not beat the strongest baseline by the effect floor, requires verifier access or reconstruction/search, leaks source-specific structure, or survives targeted deletion without loss of the claimed gain.

## 9. PASS / PARTIAL / FAIL semantics

Each arm receives one of `PASS`, `PARTIAL`, or `FAIL`.

`PASS` means every statistical, effect-size, leakage, structural, and hard control gate for that arm passes.

`PARTIAL` means the direction is supported but at least one predeclared full-pass gate is not met, while no fatal design violation occurs. A partial result never upgrades the licensed claim to the full PASS claim.

`FAIL` means the primary falsification occurs or a fatal design violation invalidates the arm.

The strongest combined interpretation requires `A=PASS`, `B=PASS`, `G=PASS`, and `P=PASS`.

If A fails, no downstream combination may be described as excluding answer transmission.

If B fails, the retained object's identity remains grammar-dependent within the tested regime.

If G fails, decision-sufficient partial structure is not supported as the explanation of representation/action dissociation.

If P fails, the result remains online verifier-assisted reorganization rather than independently persistent retained structure.

## 10. Harness architecture

The implementation will add four clearly separated layers:

### `abgp_manifest`

Parses and validates the review-approved design manifest. Owns arm sizes, thresholds, statistical family, grammar-family declarations, seed namespaces, control definitions, and confirmatory lock requirements.

### `abgp_generators`

Owns task/world generation for A/B/G/P and derives all seeds from an injected namespace. It contains no code path that silently substitutes the confirmatory namespace during development.

### `abgp_runner`

Executes one frozen arm or the full matrix. It records all constructor-visible channels, search counts, verifier calls, retained-object bytes, applicability decisions, ablations, controls, and raw paired outcomes.

### `abgp_analysis`

Computes the predeclared primary statistics, Holm-Bonferroni correction, effect floors, structural hard gates, and arm verdicts. Analysis must operate from the emitted raw result artifact rather than hidden runtime state.

A separate final lock file binds exact implementation hashes to the approved design manifest. Confirmation remains disabled until that lock is committed with `status=FROZEN`.

## 11. Development-harness policy

Development may use only `ABGP-DEV-v1` seeds. Development runs may test:

- determinism;
- generator coverage;
- negative controls;
- leakage detection;
- statistical code against synthetic fixtures;
- failure behavior;
- exact restart and serialization;
- artifact schemas;
- runtime and resource bounds.

Development must not estimate expected confirmatory effect sizes by repeatedly sampling the confirmatory generator namespace.

Any change to scientific thresholds, task counts, grammar independence, intervention classes, corruption schedule, source-distinctness, or PASS semantics after confirmatory unlock creates a new preregistration version and a new confirmatory namespace.

## 12. Final lock contents

The final confirmatory lock must contain exact digests for:

- this design manifest;
- repository tree;
- A/B/G/P generator code;
- verifier implementation;
- protected evaluator;
- analysis implementation;
- grammar-family generators;
- sham-object construction;
- wrong-class construction;
- corruption implementation;
- ablation implementation;
- model/runtime versions;
- dependency lock/environment;
- resource budgets.

The lock also records the confirmatory namespace identifier and a one-shot execution marker policy.

## 13. Evidence artifacts

Every confirmatory run must emit:

- immutable design-manifest digest;
- final-lock digest;
- repository/tree hash;
- per-arm raw outcomes;
- per-task seed digests without revealing any future unused task material;
- channel audit for A;
- cross-grammar independence audit and intervention outcomes for B;
- pre-corruption relevance labels and corruption realization for G;
- retained-object bytes/digest, zero-search accounting, no-verifier audit, and ablation trace for P;
- primary and adjusted statistics;
- effect sizes and intervals;
- arm verdicts;
- combined interpretation selected mechanically from the preregistered interpretation table.

## 14. Claim boundary

Even a four-arm PASS does not establish representation-independent invention, universal grammar invariance, arbitrary substrate invention, unbounded self-development, universal verifier sufficiency, or transfer outside the frozen generators and protected objectives.

The strongest licensed claim would be:

> Within the preregistered bounded regime, non-identifying verified residuals induce a decision-sufficient future-action structure that is recoverable across independently parameterized grammars, whose causal value concentrates on action-relevant distinctions, and which persists through hard restart to source-distinct future tasks without verifier feedback or reconstruction search.

## 15. Relationship to V3

V3 remains pilot and methodological evidence only. It may justify the existence of implementation primitives and controls, but no V3 task, effect size, success rate, or retained rule contributes observations to A/B/G/P confirmation.

The confirmatory study starts only after:

1. this written spec is reviewed;
2. the design manifest is accepted;
3. the harness is implemented and attacked on `ABGP-DEV-v1` only;
4. exact implementation hashes are written to the final lock;
5. the final lock is committed and frozen;
6. confirmatory execution is explicitly unlocked.
