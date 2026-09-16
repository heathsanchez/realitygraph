# Parkinson Latent Wild V8 — Design

## Objective

Create one final, deliberately different competition submission by exploiting the already-cached frozen ResNet representations rather than adding more probability calibration. The goal is to discover missing ranking signal that can improve both log loss and AUROC over V6 without any test-set adaptation.

## Frozen inputs

Training rows: 1362 with existing labels/environments from `load_parent_context()`.

Representations already available on the RunPod workspace:

- `fixed_resnet18_stack.npy`: `(1362, 5, 512)` float32; primary latent source.
- `fixed_resnet18_7z.npy`: `(1362, 5, 7, 512)` float32; optional second-stage source only if the stack representation shows credible transfer.
- V6 OOF/full prediction streams from `parkinson_logloss_v6/logloss_tournament_v6.npz`.

The current V6 reference is log loss 0.327251 and AUROC 0.931768 under the existing 10-environment LOEO protocol.

## Architecture

### 1. Strict fold-local compression

Flatten `fixed_resnet18_stack.npy` to 2560 dimensions. For every held environment, fit `StandardScaler` and PCA only on the remaining environments. Test PCA dimensions 16, 32, 64, and 128, clipped to the feasible rank in each fold.

No global PCA, normalization, feature selection, or target-informed transform may be fitted before the held environment is excluded.

### 2. Latent learner tournament

For each PCA dimension, test a compact family designed for 1362 rows:

- L2 logistic regression over C values `{0.01, 0.03, 0.1, 0.3, 1.0}`.
- RBF-style prototype classifier using class centroids and diagonal/whitened distance, with temperature fitted on training environments only.
- LightGBM only if import succeeds; conservative trees/leaves with strong regularization and no large hyperparameter search. If unavailable, skip it rather than changing the runtime environment.

Each candidate produces full 10-way LOEO predictions and environment-level LL/AUROC diagnostics.

### 3. V6 stacking

For credible latent candidates, fit a two-stream logit stack `V6 + latent` inside LOEO folds. The outer held environment must not influence latent preprocessing, latent model fitting, or stack coefficients.

A final deployable latent model is then fit on all training rows using the selected frozen architecture and stacked with the already-frozen V6 model.

## Acceptance gates

V8 is built only if all of the following hold:

1. Overall LOEO log loss is below 0.327251.
2. Overall LOEO AUROC exceeds 0.931768.
3. Log-loss improvement occurs in at least 6 of 10 environments.
4. No single environment contributes more than half of the aggregate LL gain.
5. Improvement is not produced solely by an unconstrained calibration layer; the latent stream must have independent ranking value (latent AUROC above 0.931768 or stacked AUROC improvement of at least 0.001).

If no candidate clears the gate, V6 remains the submission.

## Optional 7z escalation

Only if the 2560-D stack produces a gated improvement, test one structured reduction of the `(5,7,512)` tensor rather than flattening 17,920 dimensions directly. Pool across the seven slices using mean, max, center, and low-order slice-position moments, yielding a manageable fixed feature vector per view before fold-local PCA. This stage is skipped entirely if the stack representation fails.

## Runtime / packaging

The wild submission must reuse the existing T75/R75 base assets and V6 runtime path. Additional latent model artifacts must be small, local, deterministic, and packageable inside the competition ZIP. Runtime inference must derive the same `make_7z_embedding`/stack representation already computed by `base_main.py`; do not add a second ResNet forward pass if the existing representation can be exposed or reproduced with the same preprocessing.

If clean runtime reuse would require invasive changes to the base model, stop and keep V6 rather than risking submission failure.

## Testing

- Unit-test fold-local preprocessing and stack math.
- Assert no held-environment row enters scaler/PCA/model fit in synthetic tests.
- Verify full LOEO result and environment diagnostics on RunPod.
- Build a separate `submission_final_latent_v8.zip`; never overwrite V5 or V6.
- Run the same one-row CPU end-to-end contract used for V6 before upload.

## Scope

This is a one-hour competition experiment, not a new general framework. No new CNN training, no test distribution fitting, no large hyperparameter search, and no modification of the already-validated V6 artifact.
