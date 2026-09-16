# ABGP DEV-Only Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and adversarially validate an A/B/G/P development harness that enforces the preregistered design while making confirmatory execution impossible until a separate final lock is frozen.

**Architecture:** Add a small preregistration runtime under `realitygraph/abgp/` with four responsibilities: manifest/seed firewall, frozen analysis, DEV-only generators/runners, and lock construction. Arm-specific DEV fixtures exercise the exact interfaces and failure modes without exposing or deriving `ABGP-CONFIRM-v1` seeds. The final-lock builder records implementation digests but emits `REVIEW_PENDING`/`confirmatory_execution_enabled=false`; no task in this plan unlocks confirmation.

**Tech Stack:** Python 3.12 standard library, `unittest`, canonical JSON/SHA-256 patterns already used in RealityGraph, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-abgp-confirmatory-design.md`

## Global Constraints

- `preregistration/abgp-design-manifest-v1.json` and `preregistration/abgp-analysis-plan-v1.json` are normative scientific inputs.
- Development uses only seed namespace `ABGP-DEV-v1`.
- Any attempt to derive or execute `ABGP-CONFIRM-v1` before a separate frozen final lock must fail closed.
- No V3 task outcome contributes confirmatory observations.
- Confirmatory execution remains disabled throughout this plan.
- Arm verdicts are computed from emitted raw outcomes, not hidden runtime state.
- No post-hoc threshold, task-count, grammar-independence, corruption-schedule, source-distinctness, or PASS-semantics changes are permitted inside the harness.

---

### Task 1: Manifest Runtime and Seed Firewall

**Files:**
- Create: `realitygraph/abgp/__init__.py`
- Create: `realitygraph/abgp/manifest.py`
- Create: `tests/test_abgp_manifest.py`

**Interfaces:**
- Produces `ABGPDesign`, `ABGPAnalysisPlan`, `load_design_manifest(path)`, `load_analysis_plan(path)`, `derive_dev_seed(arm, cell, index, generator_version)`, and `reject_confirmatory_namespace(namespace, final_lock=None)`.
- Later tasks consume these exact functions.

- [ ] **Step 1: Write failing tests**

```python
class ABGPManifestTests(unittest.TestCase):
    def test_dev_seed_is_deterministic_and_namespace_separated(self):
        a = derive_dev_seed("A", "task", 7, "gen-v1")
        b = derive_dev_seed("A", "task", 7, "gen-v1")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_confirmatory_namespace_is_unavailable_without_frozen_lock(self):
        with self.assertRaises(ConfirmatoryLockedError):
            reject_confirmatory_namespace("ABGP-CONFIRM-v1", final_lock=None)

    def test_manifest_rejects_enabled_confirmation_in_review_state(self):
        design = load_design_manifest(DESIGN_PATH)
        self.assertFalse(design.confirmatory_execution_enabled)
        self.assertEqual(design.status, "REVIEW_PENDING")
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_manifest -v`
Expected: import failure for `realitygraph.abgp.manifest`.

- [ ] **Step 3: Implement canonical manifest parsing and seed derivation**

`ABGPDesign` must expose `status`, `confirmatory_execution_enabled`, `design_version`, `development_namespace`, `confirmatory_namespace`, `arms`, and canonical `digest`. `derive_dev_seed` must hard-code use of the manifest's development namespace and return SHA-256 hex of `namespace|arm|cell|index|generator_version`. No public function may accept an arbitrary namespace for development seed derivation.

- [ ] **Step 4: Run GREEN and full regression**

Run:
`python -m unittest tests.test_abgp_manifest -v`
`python -m unittest discover -s tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add ABGP manifest runtime and seed firewall`

---

### Task 2: Frozen Statistical Analysis

**Files:**
- Create: `realitygraph/abgp/analysis.py`
- Create: `tests/test_abgp_analysis.py`

**Interfaces:**
- Consumes `ABGPAnalysisPlan` from Task 1.
- Produces `exact_mcnemar_one_sided(pairs)`, `holm_bonferroni(raw_pvalues, alpha)`, `g_exact_randomization_pvalue(discordant_weight_counts, observed_statistic)`, `analyze_a(raw)`, `analyze_b(raw)`, `analyze_g(raw)`, `analyze_p(raw)`, and `analyze_matrix(raw_matrix)`.

- [ ] **Step 1: Write failing tests for exact statistics and verdict gates**

Tests must include known small exact McNemar cases, deterministic Holm tie handling `A < B < G < P`, an exact dynamic-programming G randomization distribution checked against brute force on <= 10 discordant pairs, and synthetic PASS/PARTIAL/FAIL fixtures for every arm.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_analysis -v`
Expected: missing-module failure.

- [ ] **Step 3: Implement standard-library exact analysis**

Use `math.comb` for exact binomial tails. Implement G's null distribution by integer-weight dynamic programming over signed discordant contributions; do not Monte Carlo the primary p-value. `analyze_matrix` must use the arm-level p-values specified in `abgp-analysis-plan-v1.json`, apply Holm once, and then recompute PASS/PARTIAL/FAIL mechanically with hard-gate vectors.

- [ ] **Step 4: Run GREEN plus full regression**

Run:
`python -m unittest tests.test_abgp_analysis -v`
`python -m unittest discover -s tests -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: implement frozen ABGP analysis`

---

### Task 3: DEV World Model and Arm A/G Generators

**Files:**
- Create: `realitygraph/abgp/dev_world.py`
- Create: `realitygraph/abgp/arm_a.py`
- Create: `realitygraph/abgp/arm_g.py`
- Create: `tests/test_abgp_arm_a_g.py`

**Interfaces:**
- Produces deterministic finite `DevWorld`, `ProtectedAction`, `VerifierMessage`, `ARecord`, and `GRecord` values from DEV seeds only.
- `generate_a_dev_records(count)` emits one-shot, equal-recheck, verifier-assisted paired outcomes plus a direct-action-insufficiency audit for every message.
- `generate_g_dev_records(world_count)` emits pre-corruption relevance labels and matched corruption outcomes at doses `[0.0, 0.1, 0.25, 0.5, 1.0]`.

- [ ] **Step 1: Write failing tests**

Tests must prove: all A admitted messages satisfy `|A*(m)| > 1`; one-message/one-repair is enforced; equal-compute accounting is explicit; G relevance labels are computed before corruption; relevant/irrelevant corruption counts and magnitudes match at each nonzero dose; DEV outputs are deterministic from DEV seeds.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_arm_a_g -v`
Expected: missing-module failure.

- [ ] **Step 3: Implement minimal finite DEV generators**

The DEV world may be synthetic but must exercise the exact scientific interfaces. A's verifier message must constrain the world set without selecting one unique optimal action. G's evaluator must expose enough comparative cells for pre-run relevant/irrelevant classification and paired corruption.

- [ ] **Step 4: Run GREEN plus analysis integration**

Run:
`python -m unittest tests.test_abgp_arm_a_g tests.test_abgp_analysis -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add DEV generators for verifier and corruption arms`

---

### Task 4: Independent Grammar Families for DEV Arm B

**Files:**
- Create: `realitygraph/abgp/arm_b.py`
- Create: `tests/test_abgp_arm_b.py`

**Interfaces:**
- Produces four grammar-family adapters: `ExtensionalGrammar`, `CompositionalGrammar`, `ReachabilityGrammar`, `ConstraintOrderGrammar`.
- Produces `generate_b_dev_records(worlds_per_direction)` across all 12 ordered acquisition-to-transfer directions and all four frozen structural interventions.

- [ ] **Step 1: Write failing independence tests**

Tests must assert disjoint surface alphabets/serialization schemas, different primitive arities across at least two families, distinct composition/inference route metadata, absence of supplied cross-grammar translation tables, and no one-to-one primitive correspondence by construction. Also test wrong-class and shuffled-coupling controls.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_arm_b -v`
Expected: missing-module failure.

- [ ] **Step 3: Implement four independently parameterized grammar adapters**

All may consume the same latent DEV world and protected action-order oracle, but must generate their representational objects independently. Transfer scoring is behavioral: protected ordering under edge/relation deletion, order reversal, scope change, and constraint change. Literal relation reconstruction is not used as the target.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_abgp_arm_b -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add independent DEV grammar families for arm B`

---

### Task 5: Hard-Restart Persistence for DEV Arm P

**Files:**
- Create: `realitygraph/abgp/arm_p.py`
- Create: `tests/test_abgp_arm_p.py`

**Interfaces:**
- Produces `RetainedStructure.to_text()/from_text()`, `acquire_dev_structure(...)`, `run_p_dev_records(count)`, and targeted deletion controls.

- [ ] **Step 1: Write failing persistence-boundary tests**

Tests must prove canonical byte-exact restart; future verifier call count is zero; future reconstruction/search count is zero before action; applicability uses no target labels; source-distinct future tasks share no forbidden identifiers/templates/seeds/serialization/topologies/labels/verifier outputs; size-matched sham and wrong-class objects are distinct; targeted deletion removes the retained lineage and causes positive reacquisition search count.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_arm_p -v`
Expected: missing-module failure.

- [ ] **Step 3: Implement the non-verbal retained structure and hard restart**

Serialize only behaviorally consequential state plus explicit applicability metadata. The future evaluator must accept a deserialized retained object and source-distinct task, with no reference to acquisition fixtures or verifier object.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_abgp_arm_p -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add DEV hard-restart persistence arm`

---

### Task 6: Unified DEV Runner and Raw Artifact Schema

**Files:**
- Create: `realitygraph/abgp/runner.py`
- Create: `abgp_dev_matrix.py`
- Create: `tests/test_abgp_runner.py`

**Interfaces:**
- Consumes Tasks 1-5.
- Produces `run_dev_matrix()` and a canonical `abgp-dev-matrix-summary.json` containing raw per-arm records, manifest/analysis digests, search/verifier accounting, hard-gate audits, and mechanical analysis.

- [ ] **Step 1: Write failing end-to-end tests**

Tests must assert that every emitted seed digest is DEV-derived; confirmatory namespace text never appears in raw task records; analysis can be recomputed from the JSON artifact alone; and trying `run_matrix(namespace="ABGP-CONFIRM-v1")` raises `ConfirmatoryLockedError` before generating any task.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_runner -v`
Expected: missing-module failure.

- [ ] **Step 3: Implement canonical runner**

The runner defaults to small DEV counts for CI while preserving manifest-defined confirmatory counts as metadata only. It must never silently substitute reduced counts for confirmatory execution.

- [ ] **Step 4: Run GREEN and standalone DEV matrix**

Run:
`python -m unittest tests.test_abgp_runner -v`
`python abgp_dev_matrix.py`
Expected: PASS and `ABGP_DEV_MATRIX_OK`; no confirmatory verdict is emitted.

- [ ] **Step 5: Commit**

Commit message: `feat: assemble DEV-only ABGP matrix runner`

---

### Task 7: Final-Lock Builder That Cannot Unlock Confirmation

**Files:**
- Create: `realitygraph/abgp/lock.py`
- Create: `preregistration/abgp-final-lock-template-v1.json`
- Create: `tests/test_abgp_lock.py`

**Interfaces:**
- Produces `build_review_lock(repo_file_map, runtime_metadata) -> dict` and `validate_final_lock(lock, design, analysis)`.

- [ ] **Step 1: Write failing lock tests**

Tests must assert all required digest fields are present, code hashes change when scientific code changes, `build_review_lock` always emits `status="REVIEW_PENDING"` and `confirmatory_execution_enabled=false`, and `validate_final_lock` rejects missing hashes/tree mismatch/non-FROZEN status.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_abgp_lock -v`
Expected: missing-module failure.

- [ ] **Step 3: Implement lock hashing**

Use SHA-256 over exact UTF-8 file bytes for Python/JSON scientific inputs and canonical JSON for runtime metadata. Do not add any function that flips the lock to FROZEN; that requires a separate explicit future review step.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_abgp_lock -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add review-only ABGP final-lock builder`

---

### Task 8: DEV CI Gate and Evidence Record

**Files:**
- Create: `.github/workflows/abgp-dev-preregistration-v1.yml`
- Create: `docs/research/abgp-dev-harness-v1.md`
- Modify: `README.md`

**Interfaces:**
- CI runs focused ABGP tests, inherited V3 tests, full regression, DEV matrix runner, and explicit grep/assertions proving confirmation remains disabled.

- [ ] **Step 1: Add CI with explicit scientific safety assertions**

Workflow must assert:

```python
assert design.status == "REVIEW_PENDING"
assert design.confirmatory_execution_enabled is False
assert summary["mode"] == "DEV_ONLY"
assert summary["confirmatory_namespace_used"] is False
```

and upload only DEV evidence artifacts.

- [ ] **Step 2: Run branch CI and inspect logs**

Expected: all ABGP focused tests, inherited V3 qualification, full suite, DEV runner, and lock tests PASS; no confirmatory result or confirmatory-seed material is emitted.

- [ ] **Step 3: Record exact DEV evidence and claim boundary**

Document that DEV results validate harness mechanics only and do not count toward A/B/G/P confirmation.

- [ ] **Step 4: Final exact-head verification**

Run dedicated workflow on documentation-complete HEAD and record run ID, test count, DEV artifact ID, and branch head.

- [ ] **Step 5: Commit**

Commit message: `docs: record ABGP DEV harness qualification`
