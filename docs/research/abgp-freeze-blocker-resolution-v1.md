# ABGP Pre-Freeze Progress and Acceptance Record

Publication correction: 18 September 2026.

**Status: REVIEW_PENDING / IMPLEMENTATION ACCEPTANCE PENDING / NOT FROZEN.**

This corrects the stronger "addressed" and "remaining substantive item is power" interpretation in the preceding version of this record. The previous version remains in Git history at `0e37943e3364e8dda671b4fc47ded812c437a56d`. No scientific hypothesis, margin, count, source-distinctness rule, analysis plan or confirmatory namespace is changed by this documentation update.

## Evidence identity

Reviewed implementation: `f9764a3696f880e2ec09e8eb7b60054f92b8ac53`; source snapshot including the later documentation: `0e37943e3364e8dda671b4fc47ded812c437a56d`.

Historical run `35251639106` completed successfully. Its artifact `10509835364` was downloaded and its archive SHA-256 matched `df64e32e17acb26760e457bb0015ae1db34b5636a45075814b32a61ebedace10`. Its legacy `QUALIFIED` output concerns the synthetic-fixture/statistical harness, not end-to-end scientific implementation qualification. This publication did not rerun the full source regression or execute confirmation.

## What the current source actually establishes

### A/P ancestry

`audit_a_stochastic_ancestry()` and `audit_p_stochastic_ancestry()` in `realitygraph/abgp/freeze_review.py` count reuse of listed acquisition/future seed strings. Their fixed/sampled-object inventories are supplied descriptions. The saved small DEV matrix has zero duplicates among those listed fields. This is not an independently discovered complete stochastic dependency graph. Absence of a hidden shared ancestor is not disproved, but earliest-ancestor independence cannot be called established solely by this check.

### B recovery and ordinary-explanation control

The direct `recovered_order = target_order` assignment is gone, and grammar-specific encode/infer paths now execute. However, `GrammarAdapter.represent()` still calls `encode_order(_protected_order_slots(...), ...)`, and supplied slot-token mappings recover shared canonical slots. The retained predictor uses the shared `_apply_intervention()`.

`_bisimulation_control()` groups hidden states by `hidden % 2`, selects a candidate order and scores its predictions. This is an executable coarse-control demonstrator. It does not construct greatest bisimulation from a declared transition/observation system or compute the required posterior from the complete admissible acquisition history. Independent grammar acquisition and the agreed ordinary-explanation separator remain acceptance requirements.

### G generation and exchangeability

Unordered matched-pair ranking is implemented. The null demonstration duplicates `_label_blind_null_flip(r)` in both positions before swapping them. Such a constructed `(x, x)` pair is symmetric by construction; it does not establish exchangeability of the actual outcome process. `arm_g.py` still assigns planted `relevant_flip = int(count >= 5)` and `irrelevant_flip = 0`.

A complete fixed dose schedule and contiguous world indices also do not alone prove the absence of upstream outcome-dependent selection/stopping. G still requires actual outcome execution and a design-level justification covering the entire procedure. The paired sharp-null wording is proposed, not jointly frozen.

### P restart and causal deletion

The inspected `_independent_episode()` serializes and deserializes in the same process. It assigns `cross_restart_state_keys=("retained_object_bytes",)` and `post_deletion_episode_success=cold_success`; several access/source-distinctness fields are assigned values. This checks serialization and record mechanics, not the enforced hard-restart boundary and executed causal lineage deletion required by the thread. End-to-end acceptance evidence remains pending.

## Statistical interpretation

B's maximum of 36 component p-values is its single IUT arm p-value, conditional on all required component alternatives being necessary. The diagnostic alpha `.0125` comes from conservative four-arm Holm planning, not a second multiplicity correction inside B.

An independent finite-binomial calculation reproduces the significance-plus-observed-floor component probabilities at true effect equal to the floor: A/P `0.498856`, B component `0.487144`, G max-dose-only `0.474616`, each minimized only over the explicit listed q grid. These are not complete-arm PASS probabilities or a continuum-envelope guarantee. A zero union-bound lower bound does not imply zero actual joint success probability.

The reproduction checks 24 small cases against exhaustive rational-probability enumeration. It generates no study tasks and accesses no confirmatory namespace. Full-PASS planning must cover joint controls, B's agreement gate, P's deletion/reacquisition conditions and G's full dose vector under jointly reviewed assumptions. No planning alternative is adopted here.

## Existing text discrepancy

The supplied LinkedIn thread requires P deletion to return performance within two percentage points of cold. The current normative candidate refers to an ordinary/no-retention control envelope. This discrepancy remains open; this documentation update does not silently choose a scientific interpretation.

## Acceptance disposition

`implementation_qualified=false`

`complete_pass_power_qualified=false`

`freeze_authorized=false`

The outstanding work is not only a power-planning decision. Complete the actual acquisition/control paths, isolated P execution and causal deletion, complete ancestry/sampling justification, G's actual design argument, and text consistency before requesting final-lock review. No confirmatory execution is authorized by this record.

The public review is maintained under Metalogic Labs at `docs/research/abgp-prefreeze-resolution-review-v3/` on the MathGraph review branch. Its PDF, evidence excerpts, diagnostic and readiness record distinguish executable progress from scientific acceptance.
