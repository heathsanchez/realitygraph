# ABGP Pre-Freeze Test Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a DEV/QUAL-only qualification layer that proves the strengthened A/B/G/P confirmatory experiment can detect planted positives, reject ordinary explanations, classify protocol defects as `INVALID`, satisfy exact statistical-reference checks and power/sensitivity gates, and deterministically replay before any final lock can be frozen.

**Architecture:** Keep scientific analysis, fixture generation, qualification analysis, and lock validation separate. Scientific arms continue to emit ordinary raw records; a new qualification runner feeds frozen fixture families through the same analysis path, compares observed verdicts/reason codes to frozen expectations, runs independent statistical and power audits, and emits one canonical qualification artifact. Final-lock validation gains a prerequisite binding to a successful qualification digest but still cannot itself construct or unlock a final lock.

**Tech Stack:** Python 3.12 standard library, `unittest`, existing `realitygraph.abgp` modules, canonical JSON/SHA-256, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-abgp-test-qualification-design.md`

## Global Constraints

- `ABGP-CONFIRM-v1` must never be derived, inspected, printed, or executed during implementation or qualification.
- Qualification uses only `ABGP-DEV-*` and/or `ABGP-QUAL-*` namespaces.
- `INVALID` is reserved for protocol/inference validity failures, not scientific negatives such as failed transfer, failed ablation, or absence of an effect.
- Every fixture has a frozen expected verdict and, where applicable, exact expected validity reason code before execution.
- The scientific analyzer is blind to fixture class and expected verdict.
- A/B/P ordinary-explanation controls must include the approved same-acquisition-evidence Bayesian carry-forward and target-side bisimulation controls before qualification can become `QUALIFIED`.
- Minimum pre-freeze power target is `0.80` throughout the frozen nuisance envelope at the minimum meaningful effect.
- Qualification failure yields `NOT_QUALIFIED` and blocks final-lock validation.
- No code in this plan authorizes confirmatory execution.

---

### Task 1: Introduce explicit validity and `INVALID` semantics

**Files:**
- Create: `realitygraph/abgp/validity.py`
- Modify: `realitygraph/abgp/analysis.py`
- Test: `tests/test_abgp_validity.py`
- Test: `tests/test_abgp_analysis.py`

**Interfaces:**
- Produces: `ValidityIssue(code: str, detail: str)`, `validate_arm_input(arm: str, raw: Mapping[str, Any]) -> tuple[ValidityIssue, ...]`, and final arm verdicts in `{PASS, PARTIAL, FAIL, INVALID}`.
- Consumes: existing raw A/B/G/P analysis payloads and hard-gate fields.

- [ ] **Step 1: Write failing validity tests**

```python
class ABGPValidityTests(unittest.TestCase):
    def test_protocol_violation_is_invalid(self):
        raw = passing_matrix_fixture()
        raw["P"]["hard_gates"]["zero_verifier"] = False
        result = analyze_matrix(raw)
        self.assertEqual(result["arms"]["P"]["verdict"], "INVALID")
        self.assertIn("P_FUTURE_VERIFIER_ACCESS", result["arms"]["P"]["validity_reason_codes"])

    def test_valid_negative_is_fail_not_invalid(self):
        raw = passing_matrix_fixture()
        raw["P"]["targeted_deletion_effect"] = 0.0
        raw["P"]["hard_gates"]["zero_verifier"] = True
        result = analyze_matrix(raw)
        self.assertEqual(result["arms"]["P"]["verdict"], "FAIL")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m unittest tests.test_abgp_validity tests.test_abgp_analysis -v`
Expected: failure because `INVALID`, reason-code semantics, and the validity module do not exist.

- [ ] **Step 3: Implement the validity layer**

Create `validity.py` with a frozen arm/reason-code mapping. At minimum include:

```python
@dataclass(frozen=True)
class ValidityIssue:
    code: str
    detail: str

_FATAL_CODES = {
    "A": {
        "message_nonidentifying": "A_DIRECT_ACTION_IDENTIFYING_MESSAGE",
        "single_message": "A_MESSAGE_BUDGET_VIOLATION",
        "single_repair_round": "A_REPAIR_BUDGET_VIOLATION",
        "budget_ok": "A_COMPUTE_BUDGET_MISMATCH",
        "old_language_complete": "A_OLD_LANGUAGE_COMPLETENESS_MISSING",
        "future_no_verifier": "A_FUTURE_VERIFIER_ACCESS",
        "no_future_target_leak": "A_FUTURE_TARGET_LEAK",
        "sham_budget_matched": "A_SHAM_BUDGET_MISMATCH",
    },
    "B": {
        "grammar_independence": "B_GRAMMAR_INDEPENDENCE_VIOLATION",
        "no_translation": "B_TRANSLATION_LEAK",
        "no_primitive_dictionary_by_construction": "B_PRIMITIVE_DICTIONARY_LEAK",
        "no_shared_surface_serialization": "B_SURFACE_SERIALIZATION_LEAK",
        "all_12_ordered_directions": "B_DIRECTION_COVERAGE_MISSING",
        "all_interventions_present": "B_INTERVENTION_COVERAGE_MISSING",
        "bisimulation_bound": "B_BISIMULATION_SPEC_UNBOUND",
    },
    "G": {
        "preclassified": "G_POSTHOC_RELEVANCE_LABEL",
        "matched_corruption": "G_CORRUPTION_MISMATCH",
        "nonzero_dose_nonempty": "G_EMPTY_NONZERO_DOSE",
        "same_evaluator": "G_EVALUATOR_MISMATCH",
    },
    "P": {
        "zero_verifier": "P_FUTURE_VERIFIER_ACCESS",
        "zero_search": "P_FUTURE_RECONSTRUCTION_SEARCH",
        "label_free": "P_TARGET_LABEL_APPLICABILITY",
        "source_distinct": "P_SOURCE_DISTINCTNESS_VIOLATION",
        "restart_clean": "P_RESTART_STATE_LEAK",
        "lineage_targeted": "P_ABLATION_NOT_LINEAGE_TARGETED",
    },
}
```

`validate_arm_input()` returns issues only for protocol/inference validity conditions. Scientific gates such as treatment beating controls, causal deletion reducing performance, or transfer succeeding remain in the scientific analyzer and can yield `FAIL`.

Update `_finalize_verdict()` so any validity issue forces `INVALID`; otherwise non-positive direction or failed scientific falsification yields `FAIL`; positive-but-underpowered/effect-floor-miss yields `PARTIAL`; all gates/effect/significance yields `PASS`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m unittest tests.test_abgp_validity tests.test_abgp_analysis -v`
Expected: all pass, including the changed expectation that verifier access after restart is `INVALID` rather than `FAIL`.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/abgp/validity.py realitygraph/abgp/analysis.py tests/test_abgp_validity.py tests/test_abgp_analysis.py
git commit -m "Add explicit ABGP invalidity semantics"
```

---

### Task 2: Qualify statistical code against independent exact references

**Files:**
- Create: `realitygraph/abgp/statistical_reference.py`
- Create: `tests/test_abgp_statistical_reference.py`
- Modify: `realitygraph/abgp/analysis.py`

**Interfaces:**
- Produces: `reference_mcnemar(wins: int, losses: int) -> Fraction`, `reference_holm(raw: Mapping[str, Fraction], alpha: Fraction) -> dict[str, Fraction]`, `reference_g_randomization(weights: Sequence[int], observed: int) -> Fraction`, `run_statistical_reference_audit() -> dict[str, Any]`.
- Consumes: scientific functions `exact_mcnemar_one_sided`, `holm_bonferroni`, `g_exact_randomization_pvalue`.

- [ ] **Step 1: Write failing exhaustive-reference tests**

```python
class StatisticalReferenceTests(unittest.TestCase):
    def test_mcnemar_matches_fraction_reference_for_all_small_discordances(self):
        for wins in range(0, 9):
            for losses in range(0, 9 - wins):
                pairs = [(0, 1)] * wins + [(1, 0)] * losses
                self.assertEqual(
                    Fraction(exact_mcnemar_one_sided(pairs)).limit_denominator(),
                    reference_mcnemar(wins, losses),
                )

    def test_g_dp_matches_exhaustive_sign_enumeration(self):
        for weights in ((2,), (2, 5), (2, 2, 5), (2, 5, 10, 20)):
            for observed in range(-sum(weights), sum(weights) + 1):
                counts = Counter(weights)
                self.assertEqual(
                    Fraction(g_exact_randomization_pvalue(counts, observed)).limit_denominator(),
                    reference_g_randomization(weights, observed),
                )
```

Also exhaustively test Holm for a fixed rational grid `{0, .01, .0125, .025, .05, .1, 1}` across all four arms and deterministic `A<B<G<P` tie-breaking.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_abgp_statistical_reference -v`
Expected: failure because independent reference functions do not exist.

- [ ] **Step 3: Implement independent references**

Use `fractions.Fraction`, `itertools.product`, and direct enumeration only. Do not call the scientific implementations from the reference calculations. `run_statistical_reference_audit()` must return exact counts of checked cases and `status="PASS"` only if every scientific/reference value agrees within an explicit floating-point tolerance of `1e-15`.

Include boundary vectors for zero discordance, all treatment wins, all control wins, exact ties, all-success, and all-failure.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m unittest tests.test_abgp_statistical_reference -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/abgp/statistical_reference.py tests/test_abgp_statistical_reference.py realitygraph/abgp/analysis.py
git commit -m "Qualify ABGP exact statistical implementations"
```

---

### Task 3: Build frozen qualification fixtures for A/B/G/P

**Files:**
- Create: `realitygraph/abgp/qualification_fixtures.py`
- Create: `tests/test_abgp_qualification_fixtures.py`
- Modify: `realitygraph/abgp/arm_a.py`
- Modify: `realitygraph/abgp/arm_b.py`
- Modify: `realitygraph/abgp/arm_g.py`
- Modify: `realitygraph/abgp/arm_p.py`

**Interfaces:**
- Produces: `QualificationFixture(fixture_id, arm, fixture_class, expected_verdict, expected_reason_codes, raw_input, witness)` and `qualification_fixtures() -> tuple[QualificationFixture, ...]`.
- Fixture classes are exactly `PLANTED_POSITIVE`, `ORDINARY_EXPLANATION`, `BROKEN_MECHANICS`.
- Scientific `analyze_matrix()` never receives `fixture_class`, `expected_verdict`, or `witness`.

- [ ] **Step 1: Write fixture inventory and blindness tests**

Require at least these fixture IDs:

```python
EXPECTED = {
    "A_PLANTED_GROWTH",
    "A_BAYES_SUFFICIENT",
    "A_REENCODING_ONLY",
    "A_SHAM_EQUIVALENT",
    "A_DIRECT_ANSWER_LEAK",
    "B_PLANTED_TRANSFER",
    "B_TARGET_BISIM_SUFFICIENT",
    "B_POSTERIOR_SUFFICIENT",
    "B_SHUFFLED_ONLY",
    "B_TRANSLATION_LEAK",
    "G_PLANTED_DOSE_RESPONSE",
    "G_NULL_RELEVANCE",
    "G_GLOBAL_DAMAGE_ONLY",
    "G_REVERSED_RELEVANCE",
    "G_POSTHOC_LABELS",
    "P_PLANTED_PERSISTENCE",
    "P_POSTERIOR_MEMORY_SUFFICIENT",
    "P_TARGET_BISIM_SUFFICIENT",
    "P_SHAM_SUFFICIENT",
    "P_NONCAUSAL_RETENTION",
    "P_RESTART_LEAK",
}
```

Assert all fixtures use namespace prefixes `ABGP-QUAL-` or `ABGP-DEV-`, and assert `json.dumps(fixture.raw_input)` contains none of `fixture_class`, `expected_verdict`, or `expected_reason_codes`.

- [ ] **Step 2: Run fixture tests and verify RED**

Run: `python -m unittest tests.test_abgp_qualification_fixtures -v`
Expected: failure because the fixture module and strengthened A/B/P raw fields do not exist.

- [ ] **Step 3: Implement finite fixture generators**

Use deterministic finite tables, not probabilistic tuning, for planted causal status. A planted positive must include an exact `R0` collision and a lower-substrate observable that splits differently optimal futures while same-history old-language Bayes remains ambiguous. B planted positive must leave target-only/acquisition-posterior bisimulation ambiguous but allow transferred structure to resolve all four interventions. G planted positive must generate a monotone relevant-only dose response with matched irrelevant corruption. P planted positive must make posterior-only and target-bisimulation baselines insufficient, survive hard restart from canonical retained bytes, and have lineage deletion collapse to the ordinary-control envelope followed by positive reacquisition search.

Ordinary-explanation fixtures must be constructed so the named control exactly matches or dominates treatment for the intended reason. Broken-mechanics fixtures alter one validity field only.

- [ ] **Step 4: Run fixture tests and verify GREEN**

Run: `python -m unittest tests.test_abgp_qualification_fixtures -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/abgp/qualification_fixtures.py realitygraph/abgp/arm_a.py realitygraph/abgp/arm_b.py realitygraph/abgp/arm_g.py realitygraph/abgp/arm_p.py tests/test_abgp_qualification_fixtures.py
git commit -m "Add ABGP qualification fixture families"
```

---

### Task 4: Add exact power and sensitivity qualification

**Files:**
- Create: `realitygraph/abgp/power.py`
- Create: `tests/test_abgp_power.py`
- Modify: `preregistration/abgp-analysis-plan-v1.json`

**Interfaces:**
- Produces: `paired_exact_power(n: int, p10: Fraction, p01: Fraction, alpha: Fraction) -> float`, `paired_power_surface(...)`, `g_power_surface(...)`, `qualification_power_audit(plan) -> dict[str, Any]`.
- Analysis plan gains explicit DEV-review fields `qualification_min_power=0.80` and frozen nuisance envelopes; status stays `REVIEW_PENDING`.

- [ ] **Step 1: Write failing power tests**

```python
class ABGPPowerTests(unittest.TestCase):
    def test_power_is_one_for_deterministic_all_treatment_wins_large_n(self):
        self.assertGreater(paired_exact_power(256, Fraction(1, 1), Fraction(0, 1), Fraction(1, 80)), 0.999)

    def test_zero_effect_does_not_report_high_power(self):
        value = paired_exact_power(256, Fraction(1, 10), Fraction(1, 10), Fraction(1, 80))
        self.assertLess(value, 0.20)

    def test_registered_minimum_power_is_point_eight(self):
        plan = load_analysis_plan(...)
        self.assertEqual(plan.raw["qualification"]["minimum_power"], 0.80)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_abgp_power -v`
Expected: failure because power functions and qualification-plan fields do not exist.

- [ ] **Step 3: Implement exact paired power**

Enumerate multinomial counts of treatment-only wins, control-only wins, ties-both-correct, and ties-both-wrong using the frozen paired probabilities. Reject using the same exact one-sided McNemar threshold used scientifically. For A/B/P arm-level maxima over multiple controls, report conservative per-component required alpha values implied by Holm and the arm-level max rule; do not assume independence between controls.

For G, compute DEV-only sensitivity using the frozen weighted exact statistic over preregistered dose-law grids. Freeze a nuisance envelope before confirmation; if current `n` fails `0.80` anywhere in the envelope, mark qualification `NOT_QUALIFIED` rather than silently weakening the requirement.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m unittest tests.test_abgp_power -v`
Expected: PASS and deterministic surfaces.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/abgp/power.py tests/test_abgp_power.py preregistration/abgp-analysis-plan-v1.json
git commit -m "Add pre-freeze ABGP power qualification"
```

---

### Task 5: Build the qualification runner and canonical artifact

**Files:**
- Create: `realitygraph/abgp/qualification.py`
- Create: `abgp_qualify.py`
- Create: `tests/test_abgp_qualification.py`
- Modify: `realitygraph/abgp/runner.py`

**Interfaces:**
- Produces: `run_qualification() -> dict[str, Any]`, `write_qualification_artifact(path, artifact)`, CLI marker `ABGP_QUALIFIED` only when all prerequisites pass.
- Consumes: frozen fixtures, scientific analyzer, validity layer, statistical-reference audit, power audit.

- [ ] **Step 1: Write failing end-to-end qualification tests**

Assert that a complete run:

```python
artifact = run_qualification()
self.assertEqual(artifact["mode"], "QUALIFICATION_ONLY")
self.assertFalse(artifact["confirmatory_namespace_used"])
self.assertEqual(artifact["verdict"], "QUALIFIED")
self.assertTrue(all(r["observed_verdict"] == r["expected_verdict"] for r in artifact["fixtures"]))
self.assertEqual(artifact, json.loads(json.dumps(artifact, sort_keys=True)))
```

Add a test that monkey-patching one expected planted-positive raw input to remove its causal signal yields `NOT_QUALIFIED`, and a test that `run_matrix(namespace="ABGP-CONFIRM-v1")` remains rejected.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest tests.test_abgp_qualification -v`
Expected: failure because the qualification runner does not exist.

- [ ] **Step 3: Implement the runner**

For each fixture, construct a complete four-arm matrix by combining the arm-under-test raw input with deterministic neutral/passing raw inputs for the other arms, call only the scientific analysis API, then compare the resulting tested-arm verdict and reason codes with the fixture’s frozen expectation outside the analyzer. Include machine-checkable witness digests, statistical-reference audit, power surfaces, exact design/spec/code hashes available locally, replay digest, and `confirmatory_namespace_used=False`.

Use canonical JSON: `sort_keys=True`, separators `(',', ':')`, ASCII-safe, trailing newline.

`abgp_qualify.py` writes `abgp-qualification-summary.json`, prints a compact report, and prints `ABGP_QUALIFIED` only for `QUALIFIED`; otherwise exits nonzero with `ABGP_NOT_QUALIFIED`.

- [ ] **Step 4: Run focused tests and CLI twice for deterministic replay**

Run:

```bash
python -m unittest tests.test_abgp_qualification -v
python abgp_qualify.py
sha256sum abgp-qualification-summary.json
python abgp_qualify.py
sha256sum abgp-qualification-summary.json
```

Expected: tests PASS; both SHA-256 values are identical; marker is `ABGP_QUALIFIED`.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/abgp/qualification.py realitygraph/abgp/runner.py abgp_qualify.py tests/test_abgp_qualification.py
git commit -m "Add deterministic ABGP test qualification runner"
```

---

### Task 6: Make successful qualification a prerequisite for final-lock validation

**Files:**
- Modify: `realitygraph/abgp/lock.py`
- Modify: `preregistration/abgp-final-lock-template-v1.json`
- Modify: `tests/test_abgp_lock.py`

**Interfaces:**
- `build_review_lock(...)` remains review-only and cannot freeze.
- `validate_final_lock(...)` additionally requires `qualification_status="QUALIFIED"`, a 64-hex `qualification_evidence_digest`, and exact binding to the qualified scientific/analysis hashes.

- [ ] **Step 1: Write failing lock tests**

Add tests that a syntactically FROZEN lock with missing qualification fields is rejected, a `NOT_QUALIFIED` lock is rejected, and a `QUALIFIED` lock with an altered qualification digest is rejected.

- [ ] **Step 2: Run lock tests and verify RED**

Run: `python -m unittest tests.test_abgp_lock -v`
Expected: new tests fail because qualification is not yet a lock prerequisite.

- [ ] **Step 3: Implement qualification binding**

Add final-lock requirements:

```json
{
  "qualification_status": "QUALIFIED",
  "qualification_evidence_digest": "<64 hex>",
  "qualification_schema": "realitygraph.abgp.qualification.v1"
}
```

The review template keeps `status="REVIEW_PENDING"`, `confirmatory_execution_enabled=false`, `review_only=true`, `builder_can_freeze=false`. `validate_final_lock()` rejects any qualification status other than `QUALIFIED`, malformed/missing evidence digest, or scientific hash map inconsistent with the qualification binding.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python -m unittest tests.test_abgp_lock -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/abgp/lock.py preregistration/abgp-final-lock-template-v1.json tests/test_abgp_lock.py
git commit -m "Require qualification before ABGP final lock"
```

---

### Task 7: Harden CI, run the full DEV/QUAL qualification, and record evidence

**Files:**
- Modify: `.github/workflows/abgp-dev-preregistration-v1.yml`
- Create: `docs/research/abgp-test-qualification-v1.md`
- Modify: `README.md`

**Interfaces:**
- CI must execute the qualification suite and artifact generation without any confirmatory namespace.
- Evidence record captures exact branch HEAD, run/job IDs, test counts, qualification artifact SHA-256, and explicit `confirmatory_namespace_used=false` after the run is observed.

- [ ] **Step 1: Add CI assertions before running remotely**

Workflow must run, in order:

```bash
python -m unittest tests.test_abgp_validity -v
python -m unittest tests.test_abgp_statistical_reference -v
python -m unittest tests.test_abgp_qualification_fixtures -v
python -m unittest tests.test_abgp_power -v
python -m unittest tests.test_abgp_qualification -v
python -m unittest discover -s tests -p 'test_*.py'
python abgp_qualify.py | tee abgp-qualification.log
grep -q '^ABGP_QUALIFIED$' abgp-qualification.log
python - <<'PY'
import json
s=json.load(open('abgp-qualification-summary.json'))
assert s['mode']=='QUALIFICATION_ONLY'
assert s['confirmatory_namespace_used'] is False
assert s['verdict']=='QUALIFIED'
PY
```

Upload only DEV/QUAL evidence artifacts; never upload confirmatory seeds or instances.

- [ ] **Step 2: Run local/static test suite where available and push workflow change**

Expected: no confirmatory execution path becomes enabled; review manifest remains `REVIEW_PENDING`.

- [ ] **Step 3: Observe the exact-head GitHub Actions run**

Fetch the workflow run and job logs. Require every focused qualification suite, inherited V3/ABGP suite, full regression suite, `ABGP_QUALIFIED`, and safety assertions to be green. If any failure appears, use systematic debugging and rerun only after a causal fix.

- [ ] **Step 4: Record evidence**

Create `docs/research/abgp-test-qualification-v1.md` with the exact observed commit, run/job, total tests, fixture counts by class, statistical-reference case counts, minimum observed power over the frozen nuisance envelope, qualification verdict, artifact ID/SHA-256, and explicit statement that no confirmatory namespace was used.

README should link the qualification evidence and state that `QUALIFIED` validates the experiment mechanics only; it is not A/B/G/P confirmatory evidence.

- [ ] **Step 5: Re-run exact-head CI after documentation commit**

Expected: final exact HEAD is green and emits the same qualification verdict under the same frozen DEV/QUAL design.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/abgp-dev-preregistration-v1.yml docs/research/abgp-test-qualification-v1.md README.md
git commit -m "Qualify ABGP confirmatory test mechanics"
```
