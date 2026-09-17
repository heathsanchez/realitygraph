# ABGP Final Implementation Qualification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the remaining A/B/G/P demonstration paths with executed finite generators that implement the agreed information boundaries, ordinary-explanation controls, causal interventions, persistence boundary, and review-ready power analysis without touching confirmation.

**Architecture:** Build one finite structural-capability substrate centered on an XOR-reduce capability that is outside a frozen old representation consisting only of constants/projections. A constructs the capability from source consequence observations after a non-identifying authorization message; P persists the same compiled reducer across a true restricted-process restart into source-distinct length-4 futures; B expresses the same latent capability through four independently parameterized grammar families and scores transfer under four structural interventions; G uses a separate randomized matched-pair causal world whose protected evaluator is actually cell-dependent and whose exact null law is enumerable. Existing synthetic fixture qualification remains harness-only. Complete-PASS power is reported over an explicit sensitivity grid; the normative planning alternative remains REVIEW_PENDING for collaborator sign-off.

**Tech Stack:** Python 3.12 stdlib, exact finite enumeration, GitHub Actions, Linux seccomp worker boundary already present.

**Spec:** `preregistration/abgp-analysis-plan-v1.json`, `preregistration/abgp-design-manifest-v1.json`, and the jointly reviewed A/B/G/P requirements summarized in `docs/research/abgp-executed-boundaries-v1.md`.

## Global Constraints

- Do not access or derive `ABGP-CONFIRM-v1` seeds or outcomes.
- Do not change hypotheses, PASS floors, source-distinctness requirements, inferential-unit definitions, or Holm/IUT semantics.
- DEV/QUAL outcomes are mechanics evidence only.
- Same-information Bayesian/posterior controls must receive all information permitted to their frozen hypothesis class; never weaken a control to manufacture a treatment advantage.
- A/P representation advantage may only come from a newly admitted capability outside the frozen old hypothesis class.
- B grammar families may share only the latent world, protected objective/action-order semantics, and the abstract intervention vocabulary; surface vocabulary, primitive inventory, arity pattern, serialization, derivation route, and grammar seeds are independent.
- G validity must follow from the actual generator/evaluator and exact assignment law, not from a synthetic duplicate-output null.
- Any unresolved scientific choice remains `REVIEW_PENDING` and blocks freeze.

---

### Task 1: Exact structural-capability substrate and executed A

**Files:**
- Create: `realitygraph/abgp/structural_world.py`
- Create: `realitygraph/abgp/executed_a.py`
- Create: `tests/test_abgp_executed_a.py`
- Modify: `realitygraph/abgp/runner.py`

**Interfaces:**
- `old_representation(vector) -> int`
- `enumerate_old_policies(source_rows) -> exact finite control result`
- `construct_reducer(source_rows, verifier_message) -> ConstructionReceipt`
- `run_a_episode(index) -> AExecutedEpisode`

- [ ] **Step 1:** Add RED tests requiring exhaustive old-language obstruction, a verifier message with constructor-visible protected-action support >1, unique construction of `XOR_REDUCE` from source consequence observations, no future verifier calls, and exact same-information old-Bayes/sham/recheck controls.
- [ ] **Step 2:** Run `python -m unittest tests.test_abgp_executed_a -v` and verify failures are missing executed substrate/constructor behavior.
- [ ] **Step 3:** Implement the finite source domain: balanced length-2 Boolean vectors with consequence `xor(bits)`; old language exposes only one-bit projections/constants; candidate construction language contains fixed reducers with XOR uniquely adequate. Verifier authorization is one fixed non-identifying message and never carries a target action.
- [ ] **Step 4:** Implement sealed length-4 future probes with independently generated raw vectors and visible consequence-to-action maps; treatment applies retained XOR, controls remain in the old class or matched sham reducer.
- [ ] **Step 5:** Run focused tests and commit.

### Task 2: Source-distinct executed P on retained structural capability

**Files:**
- Modify: `realitygraph/abgp/sandbox_runtime.py`
- Modify: `realitygraph/abgp/p_acquisition_worker.py`
- Modify: `realitygraph/abgp/p_worker.py`
- Modify: `realitygraph/abgp/p_posterior_worker.py`
- Modify: `realitygraph/abgp/executed_p.py`
- Create: `tests/test_abgp_structural_p.py`

**Interfaces:**
- acquisition emits only canonical reducer bytes plus lineage/checksum;
- invocation accepts source-distinct future vector + visible action map;
- posterior worker retains only exact posterior over the frozen old hypothesis class;
- deletion removes exact reducer lineage and reacquisition re-enters the frozen constructor.

- [ ] **Step 1:** Add RED tests requiring length-2 acquisition to length-4 futures, disjoint serialization/seed families, true process restart, zero source/verifier/search access, target-only and posterior-only old-class controls, size-matched sham, wrong-class reducer, executed deletion and positive-search reacquisition.
- [ ] **Step 2:** Run focused tests and verify RED.
- [ ] **Step 3:** Extend fixed workers with reducer schema and exact old-class posterior state. Preserve current policy-table mechanism tests as negative controls.
- [ ] **Step 4:** Execute all primary P baselines against identical future probes and independently score outcomes. Do not assert treatment superiority; report the actual result.
- [ ] **Step 5:** Run focused tests and commit.

### Task 3: Independent B grammar generators and transfer

**Files:**
- Create: `realitygraph/abgp/independent_grammars.py`
- Create: `realitygraph/abgp/executed_b.py`
- Create: `tests/test_abgp_executed_b.py`
- Modify: `realitygraph/abgp/runner.py`

**Interfaces:**
- four grammar families generate local representations from family-specific seeds;
- each family has its own parser/evaluator and disjoint surface/primitive/serialization inventory;
- source acquisition produces the abstract reducer capability; target grammar independently computes protected action order under the four frozen interventions;
- exact posterior+bisimulation control remains within frozen old hypotheses and target quotient.

- [ ] **Step 1:** Add RED tests for disjoint/randomized grammars, no supplied translation table, no one-to-one primitive dictionary, 12 directions, fresh world roots, four nested interventions, and a separating target quotient witness.
- [ ] **Step 2:** Run focused tests and verify RED.
- [ ] **Step 3:** Implement extensional, compositional, reachability, and constraint/order representations with distinct local semantics and family seeds. Encode latent Boolean structural worlds without exposing a cross-family token map.
- [ ] **Step 4:** Implement transfer scoring and all three controls from their permitted information. Fail closed if exact source posterior explains treatment.
- [ ] **Step 5:** Run focused tests and commit.

### Task 4: Causal G generator with exact design-based exchangeability

**Files:**
- Create: `realitygraph/abgp/science_g.py`
- Create: `tests/test_abgp_science_g.py`
- Modify: `realitygraph/abgp/runner.py`

**Interfaces:**
- each world contains ten matched cell pairs and one preregistered world-level assignment bit;
- the assignment chooses which member of every pair is action-relevant;
- protected order is computed from relevant cell state;
- corruption actually mutates cells and re-evaluates protected order;
- exact two-assignment enumeration proves the within-world paired vector swaps under the sharp null/design law.

- [ ] **Step 1:** Add RED tests requiring actual cell dependence, matched count/magnitude, fixed doses, no adaptive stopping, monotone corruption effect in the planted finite mechanism, and exact joint-swap law under assignment enumeration.
- [ ] **Step 2:** Run focused tests and verify RED.
- [ ] **Step 3:** Implement the matched-pair world, evaluator, corruption schedule, counterfactual paired outcomes, and exact assignment-law audit.
- [ ] **Step 4:** Wire the real outcomes to the existing world-blocked statistic; legacy label-only G remains INVALID.
- [ ] **Step 5:** Run focused tests and commit.

### Task 5: End-to-end implementation qualification and honest verdicts

**Files:**
- Create: `abgp_implementation_qualify.py`
- Create: `tests/test_abgp_implementation_qualification.py`
- Modify: `realitygraph/abgp/qualification.py`
- Modify: `.github/workflows/abgp-executed-boundaries-v1.yml`
- Create: `docs/research/abgp-implementation-qualification-v1.md`

**Interfaces:**
- qualification runs A/B/G/P executed DEV mechanisms from exact code paths;
- reports `IMPLEMENTATION_QUALIFIED` only when all protocol-validity gates pass, regardless of scientific PASS/PARTIAL/FAIL;
- scientific verdicts remain separate and developmental.

- [ ] **Step 1:** Add RED tests that distinguish protocol validity from scientific outcome and prevent synthetic fixtures from satisfying implementation qualification.
- [ ] **Step 2:** Run focused tests and verify RED.
- [ ] **Step 3:** Implement the qualification runner, raw receipts, hashes, ancestry ledger, source-distinct audits, and exact control-information manifests.
- [ ] **Step 4:** Run full regression plus qualification CLI; record actual developmental verdicts without tuning generators after seeing them.
- [ ] **Step 5:** Commit.

### Task 6: Complete-PASS power sensitivity and final-lock candidate

**Files:**
- Create: `realitygraph/abgp/complete_power.py`
- Create: `tests/test_abgp_complete_power.py`
- Create: `abgp_power_review.py`
- Create: `docs/research/abgp-final-lock-review-v1.md`
- Modify public Metalogic review package only after exact-head CI is green.

**Interfaces:**
- exact paired component probability includes significance AND observed effect floor;
- multi-component arm bounds account for 3 A controls, 36 B IUT components + 90% pooled agreement, G world-blocked test + max-dose floor, 7 P controls + deletion/reacquisition gates;
- sensitivity table spans planning alternatives above the PASS floors; no single alternative is silently made normative.

- [ ] **Step 1:** Add RED exact-small-case tests against exhaustive enumeration, including the ~0.5-at-the-floor phenomenon.
- [ ] **Step 2:** Implement exact/safely conservative sensitivity calculations and candidate sample-size tables over predeclared effect grids.
- [ ] **Step 3:** Generate one final-lock review document separating fixed scientific criteria, implemented mechanisms, actual DEV results, and the remaining collaborator choice of planning alternative.
- [ ] **Step 4:** Run full regression, both qualification CLIs, source/hash audit, and confirm `ABGP-CONFIRM-v1` was never accessed.
- [ ] **Step 5:** Publish the exact review package under `metalogiclabs/mathgraph`; do not mark `FROZEN` or run confirmation until Bill explicitly approves the planning alternative and final text–implementation mapping.

## Self-review

All agreed implementation gaps are covered: A execution/information boundary (Task 1), P source-distinct hard restart/deletion and old-posterior control (Task 2), B independent grammars and bisimulation/posterior separator (Task 3), G actual evaluator and exchangeability law (Task 4), protocol-vs-science qualification (Task 5), and complete-PASS power/final lock review (Task 6). No task authorizes confirmation or silently changes normative scientific criteria.