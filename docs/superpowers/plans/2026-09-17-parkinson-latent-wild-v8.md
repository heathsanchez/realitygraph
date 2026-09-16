# Parkinson Latent Wild V8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one separate wild competition submission that mines independent ranking signal from the already-cached frozen ResNet latent representation, stacks it with V6, and packages it only if strict LOEO gates are cleared.

**Architecture:** Use `fixed_resnet18_stack.npy` `(1362,5,512)` as the primary latent source. Every validation fold fits its own scaler and PCA on training environments only, then trains a small latent learner and a two-stream `V6 + latent` logit stack. If the stack representation clears the gate, optionally test one structured pooled reduction of `fixed_resnet18_7z.npy`; otherwise stop. Runtime reuses the existing base ResNet path and V6 assets; V5/V6 artifacts remain untouched.

**Tech Stack:** Python 3.12 target runtime; NumPy, SciPy, scikit-learn, optional LightGBM if already importable, joblib, PyTorch/torchvision only through the existing base submission path.

**Spec:** `docs/superpowers/specs/2026-09-17-parkinson-latent-wild-v8-design.md`

## Global Constraints

- Training rows: 1362 with existing labels/environments from `load_parent_context()`.
- Primary latent source: `/workspace/dat_parkinsons/work/fixed_resnet18_stack.npy` with shape `(1362,5,512)` float32.
- Optional latent source only after a primary win: `/workspace/dat_parkinsons/work/fixed_resnet18_7z.npy` with shape `(1362,5,7,512)` float32.
- V6 reference: LOEO log loss `0.327251`, AUROC `0.931768`.
- No global scaler, PCA, feature selection, calibration, or learner fit may use a held environment.
- No new CNN training, no test-distribution fitting, no large hyperparameter search.
- Build V8 only if: LL < `0.327251`; AUROC > `0.931768`; LL improves in at least 6/10 environments; no one environment supplies >50% of aggregate LL gain; latent contributes independent ranking signal.
- Never overwrite `submission_final_v5.zip` or `submission_final_logloss_v6.zip`.

---

### Task 1: Fold-local latent pipeline

**Files:**
- Create: `realitygraph/latent_wild.py`
- Create: `tests/test_latent_wild.py`

**Interfaces:**
- Consumes: `X: np.ndarray` shaped `(n, d)`, `y: np.ndarray`, `env: np.ndarray`.
- Produces: `fit_fold_latent(X_train, y_train, pca_dim, learner, C) -> dict`; `predict_fold_latent(model, X_test) -> np.ndarray`; `loeo_latent_predictions(...) -> dict`.

- [ ] **Step 1: Write failing leakage test**

```python
import unittest
import numpy as np

from realitygraph.latent_wild import loeo_latent_predictions


class LatentWildTests(unittest.TestCase):
    def test_fold_local_transform_never_sees_held_environment(self):
        rng = np.random.default_rng(1)
        X = rng.normal(size=(30, 12))
        y = np.array([0, 1] * 15)
        env = np.repeat(np.arange(3), 10)
        result = loeo_latent_predictions(X, y, env, pca_dim=4, learner='logistic', C=0.1, audit=True)
        self.assertEqual(result['folds'], 3)
        for row in result['audit']:
            held = row['held']
            self.assertNotIn(held, row['fit_envs'])
            self.assertEqual(set(row['fit_envs']), set(np.unique(env)) - {held})
        self.assertEqual(result['predictions'].shape, (30,))
        self.assertTrue(np.isfinite(result['predictions']).all())
```

- [ ] **Step 2: Run test to verify RED**

Run:
```bash
python -m unittest tests.test_latent_wild.LatentWildTests.test_fold_local_transform_never_sees_held_environment -v
```
Expected: import failure because `realitygraph.latent_wild` does not exist.

- [ ] **Step 3: Implement minimal fold-local scaler/PCA/logistic path**

`fit_fold_latent` must create `StandardScaler`, fit PCA with `n_components=min(pca_dim, n_train-1, d)`, then fit `LogisticRegression(C=C, penalty='l2', solver='lbfgs', max_iter=3000)`. `loeo_latent_predictions` loops over unique environments, fits only on `env != held`, predicts only `env == held`, and records `fit_envs` when `audit=True`.

- [ ] **Step 4: Add prototype learner test and implementation**

```python
def test_prototype_predictions_are_probabilities(self):
    rng = np.random.default_rng(2)
    X = rng.normal(size=(40, 10))
    y = np.array([0] * 20 + [1] * 20)
    env = np.repeat(np.arange(4), 10)
    result = loeo_latent_predictions(X, y, env, pca_dim=4, learner='prototype', C=1.0)
    p = result['predictions']
    self.assertTrue(((p > 0.0) & (p < 1.0)).all())
```

Prototype implementation: in PCA space compute class centroids `mu0`, `mu1`; score each row with `d0 - d1` using Euclidean squared distance; fit a single scalar temperature plus bias on the training score using bounded `scipy.optimize.minimize` against Bernoulli log loss; apply sigmoid to held scores.

- [ ] **Step 5: Run unit tests GREEN**

```bash
python -m unittest tests.test_latent_wild -v
```
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add realitygraph/latent_wild.py tests/test_latent_wild.py
git commit -m "feat: add fold-local latent validation pipeline"
```

---

### Task 2: One-shot latent tournament and V6 stack

**Files:**
- Create: `parkinson_latent_wild_v8.py`
- Modify: `.github/workflows/parkinson-latent-wild-v8.yml` if workflow is absent, otherwise create it with the test/compile commands below.

**Interfaces:**
- Consumes: `/workspace/dat_parkinsons/work/fixed_resnet18_stack.npy`, `/workspace/parkinson_logloss_v6/logloss_tournament_v6.npz`, `load_parent_context()`.
- Produces: `/workspace/parkinson_latent_v8/latent_model.joblib`, `/workspace/parkinson_latent_v8/latent_meta.json`, `/workspace/parkinson_latent_v8/latent_v8_oof.npz` only when the hard gate clears.

- [ ] **Step 1: Add runner contract test to `tests/test_latent_wild.py`**

```python
def test_two_stream_stack_reduces_to_finite_probability(self):
    from realitygraph.latent_wild import fit_two_stream_stack, apply_two_stream_stack
    y = np.array([0, 0, 1, 1, 0, 1], dtype=float)
    v6 = np.array([.1, .2, .8, .7, .3, .6])
    latent = np.array([.2, .3, .7, .9, .4, .8])
    m = fit_two_stream_stack(v6, latent, y, ridge=0.01)
    p = apply_two_stream_stack(m, v6, latent)
    self.assertEqual(p.shape, y.shape)
    self.assertTrue(((p > 0) & (p < 1)).all())
```

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_latent_wild.LatentWildTests.test_two_stream_stack_reduces_to_finite_probability -v
```
Expected: failure because stack helpers do not exist.

- [ ] **Step 3: Implement stack helpers**

Use logits of clipped probabilities, optimize `b + a*z_v6 + c*z_latent` with L2 penalty around identity target `[a,c,b]=[1,0,0]`, and expose JSON-serializable coefficients.

- [ ] **Step 4: Implement tournament runner**

Primary candidate grid only:

```python
PCA_DIMS = (16, 32, 64, 128)
LOGISTIC_C = (0.01, 0.03, 0.1, 0.3, 1.0)
LEARNERS = ('logistic', 'prototype')
STACK_RIDGE = (0.001, 0.01, 0.05)
```

For each `(pca_dim, learner, C)` produce 10-way latent LOEO predictions. For each credible latent candidate, produce a fully outer-folded V6+latent stack: within each outer held environment, train the latent preprocessing/model only on outer-train rows and fit the stack only on outer-train predictions. Report overall LL/AUC plus environment LL gains versus the already stored V6 OOF stream.

Select by lowest stacked LOEO LL, breaking ties by higher AUROC and then smaller PCA dimension.

- [ ] **Step 5: Implement hard gate**

The runner prints exactly one of:

```text
LATENT_WILD_EARNS_V8_BUILD
LATENT_WILD_FAILS_GATE_KEEP_V6
```

Gate conditions are the five Global Constraints above. When passed, refit scaler/PCA/latent learner on all rows, fit final two-stream stack using cross-fitted latent predictions plus V6 OOF predictions, and serialize model/meta artifacts.

- [ ] **Step 6: Run tournament on RunPod**

```bash
PYTHONPATH=/workspace/rg-genesis \
python -u /workspace/rg-genesis/parkinson_latent_wild_v8.py \
  | tee /workspace/parkinson_latent_wild_v8.txt
```
Expected: completes from cached latent in minutes, not hours.

- [ ] **Step 7: Commit runner**

```bash
git add parkinson_latent_wild_v8.py .github/workflows/parkinson-latent-wild-v8.yml realitygraph/latent_wild.py tests/test_latent_wild.py
git commit -m "feat: add Parkinson latent wild tournament"
```

---

### Task 3: Runtime latent inference and V8 packaging

**Files:**
- Create: `parkinson_runtime_latent_patch.py`
- Create: `parkinson_build_latent_v8.py`
- Extend: `tests/test_latent_wild.py`

**Interfaces:**
- Consumes: base submission `make_7z_embedding(x)`, serialized `latent_model.joblib`, `latent_meta.json`, existing V6 runtime assets.
- Produces: `patch_probability_v8(nifti_path, canonical_probability, v5_model, v6_meta, latent_bundle, *, already_parent=False) -> float`; `/workspace/submission_final_latent_v8.zip`.

- [ ] **Step 1: Write failing runtime-math test**

Use a synthetic serialized scaler/PCA/logistic bundle and assert `apply_latent_bundle(features, bundle)` matches direct sklearn `predict_proba` within `1e-10`; assert final two-stream stack matches `apply_two_stream_stack`.

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_latent_wild.LatentWildTests.test_runtime_bundle_matches_training_math -v
```
Expected: import failure because runtime patch does not exist.

- [ ] **Step 3: Implement runtime patch without a second ResNet pass**

Do not call a new `resnet18`. Modify only the V8 wrapper path so the base inference exposes or reuses the already-computed `z7`/stack representation. Preferred mechanism: import the base module, call its existing preprocessing and `make_7z_embedding` once, then compute the same canonical/base probability path and latent feature from that object. If the base code cannot be cleanly reused without duplicating inference, abort Task 3 and keep V6.

- [ ] **Step 4: Implement ZIP builder**

Copy the T75/R75 source directory, retain all existing assets, add V5/V6 assets, `latent_model.joblib`, `latent_meta.json`, runtime patch, and a V8 `main.py` wrapper. Validate root entries include `main.py`, `base_main.py`, `latent_model.joblib`, `latent_meta.json`, `model.json`, and `logloss_model.json`.

- [ ] **Step 5: Run packaging tests**

```bash
python -m unittest tests.test_latent_wild -v
python -m py_compile parkinson_runtime_latent_patch.py parkinson_build_latent_v8.py
```
Expected: all tests pass and compile succeeds.

- [ ] **Step 6: Commit**

```bash
git add parkinson_runtime_latent_patch.py parkinson_build_latent_v8.py tests/test_latent_wild.py
git commit -m "feat: package latent wild v8 submission"
```

---

### Task 4: Final verification and one-row smoke contract

**Files:**
- No source changes unless verification exposes a defect.

**Interfaces:**
- Consumes: `/workspace/submission_final_latent_v8.zip`.
- Produces: final hash and one-row `submission.csv` proof.

- [ ] **Step 1: Build only if gate passed**

```bash
PYTHONPATH=/workspace/rg-genesis \
python -u /workspace/rg-genesis/parkinson_build_latent_v8.py \
  --source-dir /workspace/submission_t75r75_build \
  --v5-patch-dir /workspace/parkinson_final_submission_v5 \
  --v6-meta /workspace/parkinson_logloss_v6/logloss_model.json \
  --latent-dir /workspace/parkinson_latent_v8 \
  --output /workspace/submission_final_latent_v8.zip
```

- [ ] **Step 2: Run one-row CPU end-to-end check**

Preserve `/code_execution/data`, replace submitted code with the V8 ZIP, then run:

```bash
CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS="$(nproc)" python -u /code_execution/main.py
```

Validate with Python `csv` that exactly one row exists, columns are exactly `uid,is_pathologic`, the probability is finite, and `0 <= p <= 1`.

- [ ] **Step 3: Record artifact hash**

```bash
sha256sum /workspace/submission_final_latent_v8.zip
```

- [ ] **Step 4: Final decision**

Upload V8 as the extra wild submission only if both the statistical gate and runtime smoke pass. Otherwise submit/retain V6 unchanged.
