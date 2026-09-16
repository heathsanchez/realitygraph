# ABGP Ordinary-Explanation Controls Design

Date: 2026-09-17
Branch: `abgp-preregistration-freeze-v1`
Parent scientific design: `docs/superpowers/specs/2026-09-17-abgp-confirmatory-design.md`
Parent review head: `78f752e100edb34b190511b1966ef9c5f96f9613`
Status: **REVIEW_PENDING addendum; confirmatory execution remains disabled**

## 1. Purpose

This addendum strengthens the A/B/P confirmatory arms so that a clean PASS cannot be explained by either of the two strongest ordinary alternatives identified during preregistration review:

1. **ordinary Bayesian updating** on the same acquisition evidence without representational growth; or
2. **observational/bisimulation equivalence** already implied by the shared latent generator, without transferred or retained capability.

Arm G is unchanged.

The design deliberately gives the ordinary-explanation controls strong, in some cases idealized, information. The scientific claim is licensed only by residual performance that remains after those controls are granted everything they are entitled to under the frozen information boundary.

No `ABGP-CONFIRM-v1` task, seed, outcome, or derived statistic may be inspected while developing or attacking this addendum.

## 2. Global principle: ceiling, not strawman

A control intended to rule out an ordinary explanation must be the **best policy permitted by that explanation**, not a convenient implementation of it.

For finite confirmatory generators, all ordinary-explanation policies below are therefore computed exactly from the frozen generative distribution and frozen information boundary before confirmatory execution. They are not fit to realized confirmatory outcomes.

All priors are the exact sampling probabilities induced by the frozen generator. No posterior prior, smoothing rule, tie-break, action utility, quotient definition, or continuation set may be tuned after unlock.

Where the treatment sees an acquisition history before a future decision, the Bayesian control is allowed to condition on that same acquisition history and carry forward its exact posterior over the **frozen old/shared hypothesis space**. What it may not do is invent a new observable, new partition, new constructor, or transferred structural object.

Every oracle policy, posterior representation, quotient canonicalizer, prior table, and tie-break rule is hash-bound in the final lock.

## 3. Arm A is strengthened from information value to verified representation growth

### 3.1 Revised hypothesis

A non-identifying verified residual can license and earn an action-relevant representational refinement whose prospective value exceeds the exact Bayesian optimum available in the complete old representation, even after ordinary Bayes is allowed to retain everything it can infer from the same acquisition evidence.

A no longer treats improvement from a non-identifying verifier message by itself as construction evidence.

### 3.2 Episode structure

Each of the 256 confirmatory A units is an independent episode with two phases:

1. **acquisition/construction phase** — the system receives one admissible non-identifying verifier message and may perform one frozen construction/repair episode;
2. **sealed prospective phase** — the verifier message and verifier are absent, and the system must act on a fresh held-out future instance using only the resulting representation/capability plus the ordinary future observations permitted by the frozen task family.

The primary A outcome is exact protected-action correctness on the **sealed prospective phase**, not correctness on the acquisition instance.

This separates “the message contained useful information” from “the message caused a reusable representational change.”

### 3.3 Frozen old representation `R0`

Before confirmation, the old representation is specified extensionally by a finite observation map

`R0 : world -> old_observation_state`.

The complete old language and every permitted pre-construction observation are enumerated exactly.

Let `I0(w)` be the total constructor-visible information in world `w` before the verifier message. `I0` includes exactly the frozen old representation and permitted observations. It excludes:

- confirmatory task index or seed;
- protected answer/action identity;
- verifier hidden state;
- target labels unavailable to the constructor;
- harness metadata not exposed to the treatment;
- any post-construction observable.

The declared lower substrate may be available through the same frozen constructor/query interface to all acquisition conditions, but only the treatment may admit a new observable from it after satisfying the exact growth gates below. The fixed-language Bayes control remains restricted to policies measurable in the complete old information algebra. An unrestricted-substrate Bayes ceiling is reported separately as a diagnostic reference, so this restriction is explicit rather than hidden.

### 3.4 Non-identifying verifier message

For acquisition message `M=m`, define the exact compatible-world set

`W(I0,m) = { w : I0(w)=I0 and M(w)=m }`.

The existing direct-action insufficiency gate is retained and strengthened to the exact posterior support:

`| { a : P(Y=a | I0,m) > 0 } | > 1`

for every admitted message use.

Repeated binary elimination remains forbidden. There is exactly one admitted message and one repair/construction episode.

### 3.5 Exact fixed-language Bayes oracle with acquisition carry-forward

The ordinary Bayesian baseline is not a heuristic model. It is the exact Bayes-optimal policy measurable in the frozen old information algebra.

Let `H_A` be the complete acquisition history visible to the treatment up to the end of the one-message acquisition phase, projected into the old representation. The fixed-language Bayes control receives the same `H_A`, including the same admitted verifier message, and computes the exact posterior over the frozen old/shared latent hypotheses:

`P_old(h | H_A)`.

That posterior may be retained without size restriction through the prospective phase. On a sealed future instance with old-language future observation `Z0_future`, the control chooses

`pi_A_old(H_A, Z0_future) = argmax_a P(Y_future=a | H_A, Z0_future)`.

Thus the A ordinary-Bayes control is allowed all belief updating and memory available in the old hypothesis space. It is denied only representational growth.

Three exact ceilings are reported:

- `C0_acquire = E[max_a P(Y=a | I0,M)]` — descriptive information value of the verifier message during acquisition;
- `C0_future = E[max_a P(Y_future=a | H_A,Z0_future)]` — the primary fixed-language Bayes ceiling after carrying acquisition information forward;
- `Csubstrate_future = E[max_a P(Y_future=a | H_A, full_permitted_lower_substrate_future)]` — an unrestricted-substrate diagnostic ceiling showing what would be possible if the lower substrate were directly available as information rather than requiring an earned constructor.

The control uses the exact frozen generator prior and deterministic tie-break. It has no newly admitted observable, no retained representational extension, no source-specific labels, and no verifier access in the future phase.

### 3.6 Information accounting

A reports, but does not use as a PASS threshold, the exact conditional information supplied by the verifier message:

`Delta_H = H(Y | I0) - H(Y | I0,M) = I(Y;M | I0)`.

This prevents the acquisition-phase gain from being misdescribed as construction when ordinary information accounting already explains it.

### 3.7 What counts as genuinely new representation

A candidate extension `c` is action-relevant representational growth only if all of the following hold:

1. **non-measurability in the old information:** there exist `w,w'` with identical old acquisition information and admitted message class but `c(w) != c(w')`;
2. **action-relevant collision witness:** at least one such old-indistinguishable pair has different protected optimal actions or protected action order;
3. **strict refinement:** the partition induced by `R1 = R0 join c` strictly refines the relevant old partition;
4. **future applicability:** the constructor can be evaluated on the sealed future instance from the frozen permitted lower-substrate interface without verifier access;
5. **independent semantic verification:** the constructor/probe semantics are verified under the frozen verifier boundary independently of the protected future answer being scored;
6. **no target-directed proposal leakage:** the proposal/search interface may consume only the frozen residual, old state, declared lower substrate, and allowed construction budget, never the protected future answer or confirmatory target label.

An extension that is only a deterministic re-encoding of `R0`, `R0+M`, or the old Bayesian posterior is not growth and cannot satisfy A.

### 3.8 Sham expansion control

A includes a matched-complexity **sham representational refinement**. It must receive the same acquisition history and construction/search budget as the treatment and must match the treatment extension on preregistered structural resources such as output cardinality, description-length band, constructor depth/cost band, and serialization form.

Its refinement is frozen to be consequence-irrelevant or consequence-coupling-shuffled relative to the protected action-relevant collisions.

The sham must itself be extensionally novel relative to `R0`; a no-op sham is forbidden.

### 3.9 Enriched-language Bayes reference ceiling

For diagnostic calibration only, compute the exact Bayes-optimal ceiling after the treatment representation is available:

`C1_future = E[max_a P(Y_future=a | H_A,R1_future,permitted_future_observations)]`.

RealityGraph is not required to beat `C1_future` or `Csubstrate_future`. Materially exceeding a correctly specified enriched/unrestricted ceiling is treated as a leakage or baseline-specification alarm, not as evidence of super-Bayesian construction.

### 3.10 A primary controls and statistic

Primary treatment: prospective correctness using the verified earned representation, with no future verifier message.

Primary paired controls:

- acquisition-carry-forward fixed-language Bayes oracle;
- matched-complexity sham expansion;
- equal-compute construction-free recheck/control path.

Each component uses a one-sided exact paired McNemar test with treatment > control.

The A arm-level unadjusted p-value is the **maximum** of the three component p-values, so all three ordinary/control explanations must be beaten.

Full A PASS requires:

- prospective treatment accuracy at least `0.05` above **each** primary control;
- Holm-adjusted A significance at familywise alpha `0.05`;
- exact old-language completeness certificate;
- at least one action-relevant old-language collision witness per admitted construction class;
- non-measurability/strict-refinement certificate for the earned extension;
- sham-matching gates;
- direct-action insufficiency for every acquisition message;
- exactly one acquisition message and one construction episode;
- no verifier message or verifier access in the scored future phase;
- all frozen compute/resource gates.

### 3.11 A falsification

A fails as evidence of construction if any of the following occurs:

- acquisition-carry-forward fixed-language Bayes matches the treatment within the effect floor;
- sham expansion explains the treatment gain;
- the earned extension is measurable from the old information or old posterior;
- no action-relevant old-language collision is resolved;
- future value disappears when the acquisition verifier message is absent;
- the extension proposal or admission sees the protected future answer;
- a direct-action-identifying acquisition message is used.

Acquisition-phase verifier improvement may still be reported descriptively if A fails, but it must be attributed to verified information value rather than representational construction.

## 4. Arm B gets an acquisition-posterior + target-bisimulation Bayes oracle

### 4.1 Revised hypothesis

Cross-grammar transfer recovers protected future-action structure beyond what ordinary Bayesian updating from the same acquisition evidence plus target-side observational equivalence under the shared latent generator already determine.

### 4.2 Acquisition history available to the ordinary control

Let `H_B` be every acquisition-side observation legitimately visible to the treatment before transfer, projected onto the preregistered shared latent hypothesis space without using a cross-grammar dictionary or retained structural object.

The ordinary control is allowed to compute and retain the exact posterior

`P_shared(h | H_B)`

over the frozen shared latent hypotheses.

It may carry that posterior into the transfer phase. This explicitly rules out “the treatment merely remembered an ordinary Bayesian posterior from acquisition” as an explanation.

### 4.3 Target-blind labelled transition system

For each transfer grammar, construct a finite labelled transition system using only:

- observations available in that transfer grammar;
- the frozen allowed continuation/intervention operators;
- the preregistered shared latent generator and protected objective semantics.

The LTS must exclude:

- the transferred/retained structural object;
- cross-grammar demonstrations or dictionaries;
- source identifiers or seeds;
- realized protected answers/order labels from confirmatory units;
- verifier outputs unavailable at transfer time.

The control may condition on `H_B` only through its exact posterior over the frozen shared latent hypotheses; it may not carry source-grammar syntax, a learned translator, or a newly constructed relation object.

### 4.4 Greatest bisimulation quotient

Compute the greatest bisimulation relation `~B` over the target-only LTS before confirmation. Two states are equivalent only when their permitted observable labels agree and every frozen continuation/intervention has matching successor equivalence classes.

Canonicalize the quotient structurally, without surface-name identity or a cross-grammar primitive dictionary. The canonicalizer is frozen and hash-bound.

### 4.5 Acquisition-posterior target-bisimulation Bayes oracle

Let `QB(s)` be the canonical target-only bisimulation class. Define

`pi_B_obs(H_B,q) = argmax_o P(O*=o | H_B, QB=q, I_shared)`

where `O*` is the protected action order and `I_shared` is exactly the preregistered shared generator/objective information available without a transferred structural object.

The conditional distribution is computed from the full frozen generator, never estimated from realized confirmatory outcomes.

This oracle is intentionally advantaged: it receives the same acquisition evidence as ordinary Bayes, retains the exact acquisition posterior, and receives ideal target-only bisimulation knowledge. If that combination determines the protected order, B must not call the same behavior evidence of transferred capability.

### 4.6 B primary controls and statistic

B retains the existing matched-complexity wrong-class and shuffled-coupling controls and adds `acquisition_posterior_target_bisimulation_bayes` as a third primary control.

Treatment and each control are scored on the existing ordered acquisition-to-transfer unit success: exact protected-order agreement under **all four** frozen interventions.

Each component comparison uses one-sided exact paired McNemar, treatment > control.

The B arm-level unadjusted p-value becomes the **maximum of all three component p-values**.

The existing B effect-floor rule is preserved rather than tuned to DEV outcomes: treatment unit-success rate must exceed **each** primary control, including the acquisition-posterior/bisimulation oracle, by at least `0.15` absolute.

The existing pooled intervention agreement hard gate `>= 0.90` remains.

### 4.7 B falsification

B fails the stronger transfer interpretation if acquisition-posterior + target-bisimulation Bayes reaches the treatment within the 0.15 effect floor, even when wrong-class and shuffled controls are defeated.

A B failure under this control means the tested behavior is explainable by ordinary posterior transfer plus target-side observational equivalence under the shared generator and is not evidence of an acquired cross-grammar structural capability.

## 5. Arm P gets two ordinary-explanation ceilings and a stronger deletion criterion

### 5.1 Revised hypothesis

A retained structural object provides source-distinct future-action capability after hard restart beyond both target-only observational equivalence and an exact posterior-only Bayesian memory of the same acquisition experience, and targeted deletion removes exactly that residual advantage.

### 5.2 Target-only no-retention quotient

Construct `QP(x)` as the greatest bisimulation quotient of the future-task information available at invocation **without** the retained object or acquisition episode.

The quotient may use every observation, continuation, shared protected objective principle, and generator fact that a no-retention system is legitimately entitled to use. It excludes:

- acquisition examples or acquisition state;
- retained-object bytes or lineage metadata;
- verifier output;
- source identifiers, source labels, or instance seeds;
- target labels unavailable to the treatment;
- source-specific structures prohibited by the existing source-distinctness gate.

### 5.3 Target-only no-retention bisimulation/Bayes oracle

Define and precompute

`pi_P_target(q) = argmax_a P(Y=a | QP=q, I_shared)`.

This oracle gets no acquisition memory. It answers whether the future task plus shared generator already determine the treatment behavior through ordinary target-side observational equivalence.

### 5.4 Posterior-only retained Bayes oracle

Let `H_P` be the complete acquisition history legitimately visible before restart, projected into the frozen old/shared hypothesis space.

Construct the exact posterior

`P_shared(h | H_P)`

before restart and serialize **only that posterior plus its frozen hypothesis-space identity and deterministic tie-break metadata**. No new observables, learned operators, structural constructors, source syntax, verifier output, or source identifiers may be retained.

After hard restart, combine that posterior with the target-only quotient and choose

`pi_P_posterior(H_P,q) = argmax_a P(Y=a | H_P, QP=q, I_shared)`.

This is intentionally a very strong ordinary-Bayesian persistence control. It may use an exact posterior regardless of whether its byte size exceeds the treatment object's byte size; the point is to test explanatory sufficiency, not compression efficiency. Size-matched sham remains a separate control.

Both P ordinary-Bayes controls are precomputed/hash-locked and use zero future verifier calls and zero reconstruction/search at invocation.

If either already achieves the retained treatment's behavior, the stronger persistence/construction interpretation is not licensed.

### 5.5 P primary baselines and statistic

P primary baselines become:

- cold;
- equal-compute recheck;
- size-matched sham retained object;
- wrong-class retained object;
- target-only no-retention bisimulation/Bayes oracle;
- posterior-only retained Bayes + target-bisimulation oracle;
- targeted retained-lineage deletion.

The verbal-rule negative remains secondary.

Each primary baseline receives a one-sided exact paired McNemar comparison with retained treatment > baseline.

The P arm-level unadjusted p-value becomes the **maximum of the seven component p-values**.

The existing P effect floor is preserved: retained-object accuracy must exceed **every** primary baseline by at least `0.05` absolute.

### 5.6 Stronger targeted-deletion gate

Let `B_ordinary_max` be the highest accuracy among the ordinary/no-retention primary baselines excluding targeted deletion itself.

Targeted lineage deletion must satisfy all of:

1. `accuracy_deleted <= B_ordinary_max + 0.02`;
2. `accuracy_treatment - accuracy_deleted >= 0.05`;
3. future verifier calls remain zero until the explicit reacquisition phase;
4. future reconstruction/search before action remains zero on the deleted path;
5. explicit reacquisition causes search/construction count to become positive;
6. after reacquisition, accuracy returns to within `0.02` absolute of the pre-deletion retained-treatment accuracy.

This replaces the weaker requirement that deletion merely return to within 0.02 of the cold baseline.

### 5.7 P falsification

P fails the stronger persistence interpretation if:

- target-only bisimulation/Bayes explains the treatment within the 0.05 effect floor;
- posterior-only retained Bayes + target-bisimulation explains the treatment within the 0.05 effect floor;
- targeted deletion leaves a residual advantage above the ordinary-control envelope;
- deletion does not force reacquisition/search;
- reacquisition fails to restore the capability;
- the future path uses verifier access, reconstruction/search, labels, or prohibited source-specific structure.

## 6. Arm G

No change. G continues to test whether causal value concentrates on action-relevant distinctions under the preregistered matched corruption-dose intervention.

## 7. Updated interpretation table

The strengthened arms license the following interpretations only:

- **A PASS:** within the frozen finite regime, ordinary Bayesian updating in the complete old representation, with the same acquisition evidence and exact posterior carry-forward, is exactly insufficient; a non-identifying verified residual licenses a genuinely new action-relevant representation whose value transfers prospectively after the message is removed.
- **B PASS:** cross-grammar recovery contains a residual advantage beyond exact Bayesian carry-forward of the same acquisition evidence plus target-only greatest-bisimulation equivalence under the shared latent generator.
- **G PASS:** causal value concentrates on preregistered action-relevant distinctions rather than global representational fidelity.
- **P PASS:** the retained structural object contributes a persistent residual advantage beyond both target-only observational equivalence and posterior-only Bayesian memory after hard restart, and targeted lineage deletion specifically removes that advantage and forces reacquisition.

The strongest combined interpretation still requires `A=PASS`, `B=PASS`, `G=PASS`, and `P=PASS` with no cross-arm compensation.

## 8. Required implementation changes after approval

After this addendum is approved, implementation must revise the still-`REVIEW_PENDING` preregistration rather than patch the confirmatory system after unlock.

Required changes:

1. version and update the design manifest and analysis plan before any final lock;
2. replace the current A DEV fixture with an episode generator that has an exact old-language ambiguity, a frozen lower substrate, a non-identifying acquisition residual, and a message-absent sealed future phase;
3. implement exact acquisition-carry-forward old-language Bayes policies and information accounting from the full DEV generator distribution;
4. implement matched novel sham expansion plus enriched-language and unrestricted-substrate reference ceilings;
5. implement target-only greatest-bisimulation quotient construction and canonicalization for B/P DEV generators;
6. implement B acquisition-posterior + target-bisimulation Bayes as a primary control;
7. implement P target-only and posterior-only-retained Bayes/bisimulation controls as primary controls;
8. strengthen P targeted deletion/reacquisition records;
9. revise arm-level p-value aggregation mechanically as specified above;
10. add raw-artifact fields sufficient to replay every posterior, oracle, quotient, collision, extension and ablation claim;
11. rerun the complete DEV qualification and inherited V3 tests using only `ABGP-DEV-*` namespaces;
12. disclose the previous DEV qualification as pilot/mechanics evidence only;
13. only after joint review, hash the exact scientific code and create a new frozen final lock.

No confirmatory seed may be derived or executed during this process.

## 9. Final-lock additions

The final lock must additionally bind exact hashes/digests for:

- `R0` observation language/enumerator and completeness procedure;
- A acquisition-message generator and direct-action insufficiency checker;
- A old/shared hypothesis space, exact prior, posterior updater, and acquisition-carry-forward Bayes oracle;
- A sham-expansion generator/matching rule;
- A extension novelty/non-measurability checker;
- A enriched-language and unrestricted-substrate Bayes reference implementations;
- A prospective future split/generator;
- B acquisition-history projection and shared-hypothesis posterior updater;
- B target-only LTS builder;
- B greatest-bisimulation fixed-point implementation and quotient canonicalizer;
- B acquisition-posterior target-bisimulation Bayes policy;
- P acquisition-history projection and posterior-only retained-memory serializer;
- P target-only LTS/quotient builder;
- P target-only and posterior-only-retained observational-equivalence Bayes policies;
- P strengthened deletion/reacquisition implementation;
- all tie-break rules, continuation sets, utilities, and exact finite priors used by the oracle policies.

## 10. Claim boundary

Even a strengthened four-arm PASS does not establish a generally representation-independent intelligence process, universal abstraction induction, universal Bayesian inadequacy, universal grammar invariance, arbitrary substrate invention, or unbounded self-development.

It would establish the narrower result that, in the preregistered finite regime, the observed A/B/P effects survive exact ordinary-explanation ceilings strong enough to absorb same-evidence Bayesian updating, posterior carry-forward, and target-side observational equivalence before any residual effect is attributed to construction, transfer, or persistence.

## 11. Freeze rule

This addendum is part of the scientific design. If approved, the existing manifest/analysis plan remain `REVIEW_PENDING` until they are revised to match it, attacked on DEV-only data, jointly reviewed, and then hash-frozen.

Any post-freeze change to the old-language boundary, lower-substrate interface, priors, hypothesis spaces, posterior retention rules, Bayes policies, bisimulation relation, continuation set, oracle tie-breaks, effect floors, sham matching, deletion criterion, or future information boundary requires a new preregistration version and a new confirmatory namespace.
