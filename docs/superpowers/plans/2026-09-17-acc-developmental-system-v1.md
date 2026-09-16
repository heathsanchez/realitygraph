# ACC Developmental System v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an ACC-native verified developmental system that learns residual-conditioned representation/action generators on the 424 certified cases, freezes before the 550 historically open cases, and maintains an independent Lean proof lane for parameterized recurrences.

**Architecture:** Start from `acc-developmental-system-v1`, which is based on `acc-consequence-closure-v1`. Preserve the existing exact/orbit closure baseline, import the already-written recurrence/source-transfer and exact-tail controls, then add a small ACC-native generator portfolio and controller. Every high-level action must expand to the official 14 primitive move IDs; the official SAIR verifier remains the final Discovery authority and pinned Lean remains the Proof authority.

**Tech Stack:** Python 3, pytest, GitHub Actions, official SAIR Andrews–Curtis verifier at commit `a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`, Lean/Mathlib from the pinned official Proof environment.

**Spec:** `docs/superpowers/specs/2026-09-16-acc-developmental-system-design.md`

## Global Constraints

- Never modify `main` or open an external PR.
- Freeze the scientific generator/controller policy before loading the 550 historically open rows.
- Every generated action must have an explicit primitive move expansion and replay to its claimed successor.
- Every claimed open solution must be accepted by the official SAIR verifier.
- Unsupported generator/controller regions return baseline/UNKNOWN, never inferred equivalence.
- Preserve exact restart and causal ablation for every promoted component.
- Keep Discovery and Proof claims independent.

---

### Task 1: Integrate existing ACC recurrence and exact-tail controls

**Files:**
- Create from existing branch content: `acc_exact_tail.py`
- Create from existing branch content: `acc_ms_recurrence.py`
- Create from existing branch content: `acc_source_transfer.py`
- Create from existing branch content: `tests/test_acc_exact_tail.py`
- Create from existing branch content: `tests/test_acc_ms_recurrence.py`
- Create from existing branch content: `docs/research/acc-ms-centralizer-recurrence.md`

**Interfaces:**
- Consumes: `realitygraph.acc.State`, `replay`, current ACC search helpers.
- Produces: `build_tail_bank(...)`, `search_with_tail(...)`, `ms_state(...)`, `macro_reduces_n(...)`, `symbolic_residual_word(...)`, `N_REDUCTION_MACRO`.

- [ ] **Step 1:** Copy only the already-reviewed source/test files from `acc-exact-tail-v1` into the integration branch.
- [ ] **Step 2:** Run `python -m pytest tests/test_acc_exact_tail.py tests/test_acc_ms_recurrence.py -q` and require all tests green.
- [ ] **Step 3:** Run the existing full ACC unit suite and require zero regressions.
- [ ] **Step 4:** Commit as `Integrate verified ACC tail and recurrence controls`.

### Task 2: Define the generator contract and target-free residual descriptor

**Files:**
- Test: `tests/test_acc_developmental_core.py`
- Create: `acc_developmental_core.py`

**Interfaces:**
- Produces `ACCResidual`, `GeneratedAction`, `GeneratorResult`, `primitive_expansion_ok(start, action)`, and `residual_from_search(...)`.
- `GeneratedAction` fields: `generator_id: str`, `moves: tuple[int,...]`, `successor: State`, `provenance: tuple[str,...]`.

- [ ] **Step 1: RED** — add tests asserting that a `GeneratedAction` with a false claimed successor is rejected, while a correct primitive expansion is accepted; add a test that `ACCResidual` serialization contains no target moves/outcome field.
- [ ] **Step 2:** Run `python -m pytest tests/test_acc_developmental_core.py -q`; expected failure is missing `acc_developmental_core`.
- [ ] **Step 3: GREEN** — implement immutable dataclasses, canonical JSON serialization, primitive replay validation, and a residual constructor using only source/public metadata plus search diagnostics.
- [ ] **Step 4:** Re-run the targeted tests and full ACC suite.
- [ ] **Step 5:** Commit as `Add ACC developmental generator and residual contract`.

### Task 3: Wrap G0/G1/G2 as a common verified generator portfolio

**Files:**
- Test: `tests/test_acc_generator_portfolio.py`
- Create: `acc_generator_portfolio.py`

**Interfaces:**
- Consumes: exact-tail bank, orbit closure, `N_REDUCTION_MACRO`.
- Produces: `ExactTailGenerator`, `OrbitTailGenerator`, `RecurrenceGenerator`, `GeneratorPortfolio.generate(state, context)`.

- [ ] **Step 1: RED** — write tests for exact-tail emission, orbit-tail primitive bridge emission, recurrence positive guard, recurrence negative guard, and deterministic generator ordering.
- [ ] **Step 2:** Run targeted tests; require failure because portfolio module is absent.
- [ ] **Step 3: GREEN** — implement wrappers that emit only `GeneratedAction` values whose primitive expansion replay equals the claimed successor.
- [ ] **Step 4:** Run targeted tests and existing orbit/recurrence/tail tests.
- [ ] **Step 5:** Commit as `Add verified ACC generator portfolio baseline`.

### Task 4: Add non-monotone structural macro generator G3

**Files:**
- Test: `tests/test_acc_structural_generator.py`
- Create: `acc_structural_generator.py`

**Interfaces:**
- Produces: `mine_structural_macros(trajectories, ...)` and `StructuralMacroGenerator`.

- [ ] **Step 1: RED** — construct a certified toy trajectory where the useful two-step macro temporarily increases total relator length; assert the miner retains it when it has repeated verified support, unlike the old strict-length miner.
- [ ] **Step 2:** Run targeted test and confirm failure.
- [ ] **Step 3: GREEN** — mine repeated trajectory fragments keyed by target-free structural guards; require replay-valid successor, minimum repeated support, deterministic shortest/lexicographic tie-break; do not require immediate length decrease.
- [ ] **Step 4:** Add deletion/ablation test proving removal eliminates only G3 candidates.
- [ ] **Step 5:** Run targeted and full suite; commit `Add verifier-gated nonmonotone ACC structural generator`.

### Task 5: Add substitution/Nielsen supermove compiler G4

**Files:**
- Test: `tests/test_acc_substitution_generator.py`
- Create: `acc_substitution_generator.py`

**Interfaces:**
- Produces: `SubstitutionCandidate`, `compile_substitution(state, candidate) -> tuple[int,...]`, `SubstitutionGenerator`.

- [ ] **Step 1: RED** — add exhaustive small-word tests over words of length <=3 showing the compiled primitive sequence reaches exactly the same successor as the high-level substitution specification; include invalid candidates that must emit nothing.
- [ ] **Step 2:** Run targeted test and confirm failure.
- [ ] **Step 3: GREEN** — implement only substitutions expressible as official conjugations/rotations plus one legal relator multiplication; compile to primitive move IDs and replay-check every emission.
- [ ] **Step 4:** Add path-length and max-total guards; no finite-buffer/JAX equality shortcuts.
- [ ] **Step 5:** Run exhaustive targeted tests and full suite; commit `Add verified ACC substitution supermove compiler`.

### Task 6: Freeze a family-level scientific split and learn a generator/controller policy

**Files:**
- Test: `tests/test_acc_scientific_split.py`
- Test: `tests/test_acc_generator_controller.py`
- Create: `acc_scientific_split.py`
- Create: `acc_generator_controller.py`

**Interfaces:**
- Produces: `ScientificSplit`, `freeze_split(trajectories, seed)`, `GeneratorPolicy`, `learn_generator_policy(...)`, `apply_policy(...)`.

- [ ] **Step 1: RED** — test deterministic disjoint acquisition/calibration/future partition by reduced `w_vector`, with larger `n` ordered later inside recurring families; assert the manifest hash is stable and future rows are not present in learner inputs.
- [ ] **Step 2:** Implement split/freeze serialization and re-run.
- [ ] **Step 3: RED** — test a synthetic residual stream where unconditional generation harms one baseline success but a threshold controller invokes only on the rescue region.
- [ ] **Step 4: GREEN** — learn a tiny deterministic conjunction/equality controller over `ACCResidual`; rank generators lexicographically by rescues, verified improvement, zero harms, verifier accepts, expansion reduction, cost, ID.
- [ ] **Step 5:** Require exact JSON restart and ablation to baseline.
- [ ] **Step 6:** Run targeted/full suite; commit `Add sealed ACC generator-controller learning`.

### Task 7: Build the scientific CI workflow and frozen 550 gate

**Files:**
- Create: `.github/workflows/acc-developmental-system-v1.yml`
- Create: `acc_developmental_experiment.py`
- Test: `tests/test_acc_open_freeze_gate.py`

**Interfaces:**
- Produces evidence files: `acc-dev-split.json`, `acc-generator-policy.json`, `acc-dev-future-summary.json`, `acc-dev-open-summary.json`, accepted candidate file, verifier receipts.

- [ ] **Step 1: RED** — test that `load_open_rows(...)` raises unless a freeze marker containing the policy hash exists.
- [ ] **Step 2:** Implement the freeze gate.
- [ ] **Step 3:** Implement acquisition -> controller calibration -> future evaluation using only the 424 certified cases; require at least one prospective verifier-backed rescue, zero harmed baseline successes, exact restart, and exact controller ablation before freeze.
- [ ] **Step 4:** Only after freeze, load the 550 open rows once and run the frozen policy; output only officially accepted candidate sequences.
- [ ] **Step 5:** Workflow pins official repo/hash, runs full unit suite, 424/424 replay, scientific experiment, then open gate, then uploads all evidence.
- [ ] **Step 6:** Run Actions and inspect complete logs; commit fixes only via RED/GREEN cycles.

### Task 8: Repair and complete the Lean recurrence proof lane

**Files:**
- Modify/create: `.github/workflows/acc-proof-theorem-v1.yml`
- Modify/create: `lean/ACCProofCandidate.lean`

**Interfaces:**
- Produces pinned Lean theorem receipt for a precise `AC.Reachable` recurrence statement.

- [ ] **Step 1:** Inspect official pinned Lean project files and use its declared toolchain/lock state; remove unnecessary `lake update` if the official project does not require it.
- [ ] **Step 2:** Make a base-environment-only workflow gate green before checking the candidate theorem.
- [ ] **Step 3: RED** — add the recurrence theorem statement with an incomplete proof and confirm Lean rejects it for the intended missing proof.
- [ ] **Step 4: GREEN** — prove the primitive-step reachability theorem under the centralizer guard, using official `AC` definitions.
- [ ] **Step 5:** Run pinned Lean check; record theorem result separately from Discovery results.

### Task 9: Add one recursive self-compilation generation

**Files:**
- Test: `tests/test_acc_recursive_policy.py`
- Create: `acc_recursive_policy.py`
- Modify: `acc_developmental_experiment.py`

**Interfaces:**
- Produces `compile_next_generation(parent_policy, earlier_evidence) -> GeneratorPolicy`.

- [ ] **Step 1: RED** — test that G2 policy compilation cannot see its future evidence and that a non-improving child is rejected.
- [ ] **Step 2: GREEN** — compile one child policy from only earlier sealed evidence; retain only if coverage/harm is no worse and at least one of verified rescues, cost, or supported scope strictly improves.
- [ ] **Step 3:** Run a sealed child future and compare verified consequence/search against parent.
- [ ] **Step 4:** Commit `Add sealed recursive ACC policy compilation`.

### Task 10: Final verification and evidence report

- [ ] Run the complete branch unit suite.
- [ ] Re-run 424/424 local replay and 424/424 official verifier.
- [ ] Confirm scientific policy hash was frozen before open-row load.
- [ ] Confirm every accepted open candidate has an official verifier receipt.
- [ ] Confirm generator/controller exact restart and lineage ablations.
- [ ] Confirm Proof lane status from pinned Lean CI.
- [ ] Report scientific, competition, and proof outcomes separately; do not merge or open a PR.
