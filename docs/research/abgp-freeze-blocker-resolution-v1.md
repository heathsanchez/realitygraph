# ABGP Pre-Freeze Blocker Resolution V1

Status: **REVIEW_PENDING / NOT FROZEN / NOT CONFIRMATORY**

This record addresses the three methodological issues raised in the 17 September pre-freeze review. It does not change the A/B/G/P hypotheses, effect floors, PASS criteria, source-distinctness requirements, or confirmatory namespace. `ABGP-CONFIRM-v1` remains inaccessible.

## Verification state

Implementation head before this documentation commit: `f9764a3696f880e2ec09e8eb7b60054f92b8ac53`.

GitHub Actions run `35251639106` completed successfully on that code head. The full regression, explicit DEV/QUAL safety boundary, methodological fixture harness, DEV matrix, and artifact upload steps all succeeded. This remains development/review evidence only.

## 1. A/P inferential units — earliest stochastic ancestor

The new audit traces each scored episode to the earliest sampled object rather than treating a hard restart or future seed as sufficient evidence of independence.

### A

Each episode has its own acquisition seed and a separately derived sealed-future seed. The old-language definition, constructor family, verifier-message alphabet, generator code/version, and analysis rule are fixed protocol objects rather than sampled ancestors. The audit fails if any episode-specific sampled ancestor is reused across episodes.

Current DEV/QUAL audit result: `shared_stochastic_ancestor_count = 0`.

### P

Each inferential unit begins with its own acquisition seed. The acquired retained object is a descendant of that within-episode acquisition and is the only state crossing that episode's restart. The four nested future seeds are episode-specific and remain nested measurements rather than independent `n`.

The 24-policy candidate space, abstract context classes, acquisition algorithm/version, restart template, and analysis rule are fixed protocol objects. They are not counted as stochastic clusters.

Current DEV/QUAL audit result: `shared_stochastic_ancestor_count = 0`.

**Boundary:** this establishes the ancestry structure of the frozen finite generator. It is not a claim that arbitrary future task generators are independent.

## 2. B — executable recovery and executable ordinary-explanation control

The former DEV placeholders have been removed from the B generator.

The treatment path now executes:

1. source-grammar representation of the baseline world;
2. source-grammar-specific inference of the protected ordering;
3. retention of the resulting capability-order object;
4. capability prediction under each of the four frozen structural interventions;
5. independent target-grammar representation and target-grammar-specific inference;
6. success only when retained prediction, target-grammar recovery, and protected evaluator order all agree.

The four grammar families use different surface carriers, serialization schemas, primitive inventories/arity patterns, and inference routes. No cross-grammar translation table is supplied.

The controls are executable rather than seed-generated outcome bits:

- wrong-class: a distinct capability class with a different protected ordering;
- shuffled coupling: source acquisition from an independently seeded world while preserving the mechanism and breaking the source-to-target coupling;
- target-bisimulation/Bayesian control: a frozen coarse observation merges two candidate protected orders; at least one registered structural intervention separates those observationally equivalent candidates, and the control's success is scored by actual prediction.

Each ordered-direction world root is independently seeded; interventions remain nested inside that world unit.

The small routine DEV matrix can remain `PARTIAL` for B because it deliberately uses far fewer worlds per direction than any final count. That routine is a mechanics check, not evidence for B.

## 3. B alpha provenance

`alpha = 0.0125` is the worst-case component threshold inherited from the **four-arm** Holm family (`0.05 / 4`) for pre-freeze power planning. It is **not** a 36-component Bonferroni correction inside B.

B remains an intersection-union arm: all 12 directions × 3 primary controls must satisfy their registered component requirements, and the B arm p-value is the maximum of those 36 p-values. That single arm p-value then enters Holm with A, G, and P.

## 4. G — design-level exchangeability contract

DP/brute-force agreement checks only the arithmetic. A separate design audit now checks the assumptions that make the world-level sign exchange meaningful.

The proposed generator resolution uses pre-outcome matched relevant/irrelevant cell pairs. Pair ranking depends on an unordered pair identity, so exchanging the relevance labels cannot change which matched pairs are selected. Corruption count and magnitude are identical within each selected pair. The full dose schedule is fixed in advance and there is no outcome-dependent stopping.

The exact randomization claim is explicitly conditional on the registered sharp null:

> conditional on the fixed matched-pair construction and all non-label inputs, the complete within-world outcome vector is unchanged by one joint exchange of relevant/irrelevant labels across every nonzero dose.

The audit instantiates a label-blind null potential-outcome path and checks the complete within-world vector after the joint exchange. It fails closed if matched counts, magnitudes, pair membership, schedule, or stopping invariance is broken.

**Boundary:** this is a design/model contract for this finite generator. It is not a theorem that arbitrary natural-domain relevance classes are exchangeable. The matched-pair generation procedure is therefore part of the exact text–implementation candidate that still requires joint review before freeze.

## 5. Complete-PASS power — remaining methodological choice

The earlier values around `0.80–0.83` were component-significance power diagnostics, not power for the complete PASS rules.

The new audit adds the observed effect-floor requirement to the exact paired calculation. This exposes a structural issue in the earlier planning rule: the historical calculation used a **true effect equal to the same value required as the observed PASS floor**.

At that planning alternative, the observed paired difference is centered on the PASS threshold. Even with large `n`, the probability that the observed difference itself lands at or above its own true mean remains about one half. Therefore increasing `n` cannot make `significance AND observed effect >= floor` an 80% event at a true effect exactly equal to the floor.

This affects A and P directly and every B direction×control component; B additionally requires the pooled `>= 0.90` exact-agreement gate, and P additionally requires deletion/reacquisition gates. Joint multi-control dependence also matters for complete-arm power.

The code now reports the historical component-power result separately and sets:

`complete_pass_power_qualified = false`

until a planning alternative is jointly frozen **strictly above** the observed PASS floor (and the relevant B/P gate-level alternative/dependence specification is fixed).

This is not a reason to change the scientific PASS thresholds. It is a reason not to pretend those thresholds themselves are a valid 80%-power alternative.

## Requirement-to-evidence map

| Review requirement | Implementation/evidence | Status |
|---|---|---|
| A/P earliest shared stochastic ancestor | explicit per-episode ancestry digest audit; zero reused sampled ancestors in current generator | implemented / reviewable |
| B real recovered structure | grammar-specific encode/infer → retained capability → target-grammar intervention recovery | implemented / reviewable |
| B posterior/bisimulation control | executable coarse-control prediction plus separating-intervention witness | implemented / reviewable |
| B `0.0125` provenance | explicitly four-arm Holm worst-case planning alpha; not 36-way B correction | implemented / documented |
| B complete-PASS power | exact component+effect-floor diagnostic reveals current power rule is insufficient; 90% gate also needs an alternative | **joint planning choice still required** |
| G world-level exchangeability | matched-pair pre-outcome selection + label-blind sharp-null vector swap + fixed schedule/no stopping | implemented as proposed design contract / reviewable |
| Confirmatory isolation | design remains `REVIEW_PENDING`; confirmatory execution disabled | preserved |

## Current disposition

The implementation gaps that previously made the public `QUALIFIED` label too broad have been reduced materially: A/P ancestry is now audited from the stochastic root, B no longer uses the recovered-order or posterior/bisimulation placeholders, and G has an explicit design-level sharp-null exchangeability contract rather than only a DP arithmetic check.

The candidate is **not yet freeze-ready**. The remaining substantive item is the complete-PASS power planning alternative (including the B 90% gate and P gate structure), plus joint review of the proposed G matched-pair generation procedure. Those require agreement before the normative manifest/analysis plan can be marked `FROZEN`.
