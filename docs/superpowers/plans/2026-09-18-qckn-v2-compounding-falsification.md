# QCKN V2 Compounding Falsification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the smallest frozen finite experiment that can falsify verified capability compounding through reuse, independently re-certified composition, active-state re-minimisation, restart, transfer, and matched controls.

**Architecture:** A single top-level experiment module orchestrates existing frozen V1 primitives: `build_g1`, `FiniteCapability`, `compose_capabilities`, `exhaustive_attack`, `Ledger`, and `CompiledPresent`. Experiment-local immutable result records separate acquisition search, authority checks, active representation, reserve decisions, and target-arm costs; no generalized V2 runtime framework or QCK semantic change is introduced.

**Tech Stack:** Python 3.12 standard library, `unittest`, RealityGraph V1 finite capability/ledger/MG2 APIs, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-18-qckn-v2-compounding-falsification-design.md`

## Global Constraints

- Base remains `qckn-v1-frozen` at `527cb7df1d931be53a61b1523abeaae20501af27`; never modify a frozen V1 branch.
- Preserve QCK semantic meanings and the frozen authority/verifier boundary.
- Use one acquisition-search unit for G1, G2, G3, COLD, WARM, RAW_HISTORY, SHAM, and ANCESTOR_ABLATION.
- G1/G2/G3 acquisition search must be exactly `10 > 3 > 0`; verification checks are reported separately.
- Never clear dependencies on the dependent composition. Create a new dependency-free identity only after a separate exhaustive authority returns `SURVIVE` over all four source inputs.
- Re-minimise ACTIVE from 3 capabilities to 1 only after replay proves the protected `Pair -> Label` consequence unchanged.
- Preserve A, B, dependent-composite identity, and certificates as causal/provenance evidence; do not confuse provenance with recoverability.
- When independent future decoder recovery is declared, classify B as RESERVE and reject its removal with `RecoveryUnavailable`.
- WARM must start only from an exact restarted `CompiledPresent`, with discovery disabled.
- COLD, WARM, RAW_HISTORY, SHAM, and ANCESTOR_ABLATION use the same target carrier, complete candidate universe, oracle, and exhaustive authority.
- If a mandatory gate fails, emit a named obstruction and do not relax or replace the metric.
- Keep all 158 frozen V1 regression tests green.

---

## File Map

- Create `qckn_v2_compounding_falsification.py`: frozen carriers and candidate orders, immutable metrics, generation acquisition, independent re-certification, experiment-local retention decision, compilation/restart, transfer arms, gate evaluation, deterministic JSON CLI.
- Create `tests/test_qckn_v2_compounding_falsification.py`: behavior-first falsification gates and negative controls using only real finite capabilities and authorities.
- Create `.github/workflows/qckn-v2-compounding-falsification.yml`: focused tests, full V1 regression suite, deterministic probe execution, and evidence artifact upload.
- Create `docs/research/qckn-v2-compounding-falsification.md`: measured result, gate table, exact claim boundary, and any named obstruction.

---

### Task 1: Encode the Generation-Cost and Independent Re-certification Gates

**Files:**
- Create: `tests/test_qckn_v2_compounding_falsification.py`
- Create: `qckn_v2_compounding_falsification.py`

**Interfaces:**
- Consumes: `build_g1() -> dict`, `compose_capabilities(str, FiniteCapability, FiniteCapability) -> FiniteCapability`, and `exhaustive_attack(FiniteCapability, Mapping[str, str], Sequence[str], budget=int) -> AttackEvidence`.
- Produces: `acquire_generations() -> GenerationBundle`, where `GenerationBundle.measurements` is a 3-tuple of `GenerationMeasurement`, and `.parity`, `.decoder`, `.dependent`, `.standalone` are real `FiniteCapability` values.
- Produces: `CompoundingObstruction(code: str, detail: str, separating_input: str | None = None)` for fail-closed outcomes.

- [ ] **Step 1: Write failing tests for the frozen cost sequence and dependency boundary**

```python
class GenerationGateTests(unittest.TestCase):
    def test_acquisition_costs_use_one_unit_and_are_exactly_10_3_0(self):
        bundle = acquire_generations()
        self.assertEqual(
            tuple(item.acquisition_search_calls for item in bundle.measurements),
            (10, 3, 0),
        )

    def test_composition_stays_dependent_until_new_identity_is_certified(self):
        bundle = acquire_generations()
        self.assertEqual(
            set(bundle.dependent.dependencies),
            {bundle.parity.capability_id, bundle.decoder.capability_id},
        )
        self.assertNotEqual(bundle.standalone.capability_id, bundle.dependent.capability_id)
        self.assertEqual(bundle.standalone.dependencies, ())
        self.assertNotEqual(bundle.standalone.certificate_id, bundle.dependent.certificate_id)
        self.assertEqual(bundle.standalone.semantic_table, bundle.dependent.semantic_table)
        self.assertEqual(bundle.measurements[2].authority_checks, 8)
```

Breaks caught: changing acquisition units between generations; clearing dependencies on the dependent object; minting a standalone identity without complete four-input authority.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification.GenerationGateTests -v
```

Expected: import failure for missing `qckn_v2_compounding_falsification`.

- [ ] **Step 3: Implement the minimal generation acquisition path**

Implement immutable records with these exact fields:

```python
@dataclass(frozen=True)
class GenerationMeasurement:
    generation: str
    capability_id: str
    acquisition_search_calls: int
    authority_checks: int

@dataclass(frozen=True)
class GenerationBundle:
    measurements: tuple[GenerationMeasurement, ...]
    parity: FiniteCapability
    decoder: FiniteCapability
    dependent: FiniteCapability
    standalone: FiniteCapability
    attacks: tuple[AttackEvidence, ...]
```

Freeze the decoder portfolio in this order:

```python
DECODER_TABLES = (
    (("0", "EVEN"), ("1", "EVEN")),
    (("0", "ODD"), ("1", "EVEN")),
    (("0", "EVEN"), ("1", "ODD")),
    (("0", "ODD"), ("1", "ODD")),
)
```

For each candidate, use `exhaustive_attack` against `{"0": "EVEN", "1": "ODD"}` with challenges `("0", "1")` and budget 2. Count one acquisition-search call per candidate attempted and sum `AttackEvidence.checked` only into the separate authority counter. Require the third candidate to survive.

Call `compose_capabilities("g3-dependent-parity-label-v2", parity, decoder)` without mutating its dependencies. Exhaustively attack the dependent result against the literal source oracle:

```python
SOURCE_LABEL_ORACLE = {
    "00": "EVEN",
    "01": "ODD",
    "10": "ODD",
    "11": "EVEN",
}
```

Only on `AttackStatus.SURVIVE` create `g3-standalone-parity-label-v2` with dependency-free semantics copied from the verified result, certificate `cert:g3-standalone-exhaustive-v2`, the same authority/verifier, and provenance IDs naming A, B, the dependent ID, and all three source certificate IDs. Independently attack that new standalone identity over the same four inputs before accepting its certificate. Set G3 acquisition search to 0 and authority checks to 8 (four composition checks plus four standalone re-certification checks). Raise `CompoundingObstruction("RECERTIFICATION_FAILED", ...)` otherwise.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification.GenerationGateTests -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit the generation slice**

```bash
git add qckn_v2_compounding_falsification.py tests/test_qckn_v2_compounding_falsification.py
git commit -m "test: encode V2 generation falsification gates"
```

---

### Task 2: Encode ACTIVE Re-minimisation, PROVENANCE, RESERVE, and Restart

**Files:**
- Modify: `tests/test_qckn_v2_compounding_falsification.py`
- Modify: `qckn_v2_compounding_falsification.py`

**Interfaces:**
- Consumes: `GenerationBundle` from Task 1.
- Produces: `build_retained_state(bundle: GenerationBundle, require_decoder_recovery: bool = False) -> RetainedState`.
- `RetainedState` exposes `.ledger`, `.decision`, `.present`, `.source_replay_digest`, and `.restart_exact`.
- `RetentionDecision` exposes literal ID tuples `.active_ids`, `.reserve_ids`, `.provenance_ids`, `.deleted_from_active_ids`, and `.deletion_evidence`.

- [ ] **Step 1: Add failing tests for contraction, restart, provenance, and reserve refusal**

```python
class RetentionGateTests(unittest.TestCase):
    def test_recertified_composite_contracts_active_3_to_1_without_behavior_change(self):
        state = build_retained_state(acquire_generations())
        self.assertEqual(state.decision.active_before_count, 3)
        self.assertEqual(state.decision.active_after_count, 1)
        self.assertEqual(state.present.capability_graph.active_ids(), state.decision.active_ids)
        self.assertEqual(state.source_replay_before, state.source_replay_after)
        self.assertTrue(state.restart_exact)
        self.assertEqual(state.present.restart().text(), state.present.text())

    def test_ancestry_stays_in_ledger_and_provenance_not_active_memory(self):
        bundle = acquire_generations()
        state = build_retained_state(bundle)
        self.assertEqual(
            set(state.decision.deleted_from_active_ids),
            {bundle.parity.capability_id, bundle.decoder.capability_id},
        )
        self.assertEqual(set(state.present.capability_graph.active_ids()), {bundle.standalone.capability_id})
        self.assertTrue({bundle.parity.capability_id, bundle.decoder.capability_id}.issubset(set(state.decision.provenance_ids)))
        self.assertEqual(len(state.ledger.events), 3)

    def test_declared_decoder_recovery_moves_decoder_to_reserve_and_refuses_deletion(self):
        state = build_retained_state(acquire_generations(), require_decoder_recovery=True)
        self.assertEqual(state.decision.reserve_ids, (state.bundle.decoder.capability_id,))
        with self.assertRaisesRegex(CompoundingObstruction, "RecoveryUnavailable"):
            state.decision.require_removal(state.bundle.decoder.capability_id)
```

Breaks caught: retaining three capabilities in ACTIVE; losing protected semantics after contraction; storing causal ancestors in active MG2; treating provenance as recoverability; deleting a declared reserve item.

- [ ] **Step 2: Run the retention tests and verify RED**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification.RetentionGateTests -v
```

Expected: failures because `build_retained_state` and retention records do not exist.

- [ ] **Step 3: Implement the minimal bounded retention gate**

Create a `Ledger`; append promotions for parity and decoder as independent parents, then append standalone promotion with both source event IDs as parents. Do not promote the dependency-bearing candidate.

Define the pre-contraction active graph as `(parity, decoder, standalone)`. Replay the literal four source inputs through standalone and compare the exact tuple to the dependent composite. If unequal, raise `CompoundingObstruction("REMINIMISATION_SEPARATION", ..., separating_input=<first mismatch>)`.

Compile the post-contraction graph with only standalone:

```python
present = CompiledPresent.compile(
    CapabilityGraph((bundle.standalone,)),
    MetaMemory.empty(),
)
restarted = present.restart()
```

The primary contract has empty reserve. The recovery negative control sets the decoder ID in `reserve_ids`; `RetentionDecision.require_removal(id)` raises `CompoundingObstruction("RecoveryUnavailable", ...)` for any reserve ID. This records the exact bounded classification without adding a competing runtime memory format.

Deletion evidence must name the protected oracle digest, standalone certificate, and exact replay result. `provenance_ids` must include parity, decoder, dependent-composite identity, and all source/standalone certificate IDs. `CompiledPresent` remains the only state allowed to alter target execution.

- [ ] **Step 4: Run generation and retention tests and verify GREEN**

Run:

```bash
python -m unittest \
  tests.test_qckn_v2_compounding_falsification.GenerationGateTests \
  tests.test_qckn_v2_compounding_falsification.RetentionGateTests -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit the retention slice**

```bash
git add qckn_v2_compounding_falsification.py tests/test_qckn_v2_compounding_falsification.py
git commit -m "feat: re-minimise certified composite active state"
```

---

### Task 3: Encode Unseen Transfer and All Causal Controls

**Files:**
- Modify: `tests/test_qckn_v2_compounding_falsification.py`
- Modify: `qckn_v2_compounding_falsification.py`

**Interfaces:**
- Consumes: exact restarted `CompiledPresent` from Task 2.
- Produces: `run_target_arm(name: str, *, present: CompiledPresent | None = None, raw_history: str = "") -> ArmMeasurement`.
- Produces: `run_probe() -> ProbeResult`, including `.generations`, `.retained`, `.arms`, `.passed`, `.failed_gates`, and `.metrics()`.

- [ ] **Step 1: Add failing tests for WARM/COLD parity and matched controls**

```python
class TransferControlTests(unittest.TestCase):
    def test_warm_restart_beats_cold_with_identical_verified_endpoint(self):
        result = run_probe()
        cold = result.arm("COLD")
        warm = result.arm("WARM")
        self.assertLess(warm.search_calls, cold.search_calls)
        self.assertEqual(warm.search_calls, 0)
        self.assertEqual(warm.verified_semantics, cold.verified_semantics)
        self.assertEqual(warm.authority_snapshot, cold.authority_snapshot)
        self.assertEqual(warm.verifier_id, cold.verifier_id)

    def test_raw_history_and_sham_do_not_receive_warm_shortcut(self):
        result = run_probe()
        cold = result.arm("COLD")
        self.assertEqual(result.arm("RAW_HISTORY").search_calls, cold.search_calls)
        self.assertEqual(result.arm("SHAM").search_calls, cold.search_calls)

    def test_relevant_ablation_restores_exact_cold_cost(self):
        result = run_probe()
        self.assertEqual(
            result.arm("ANCESTOR_ABLATION").search_calls,
            result.arm("COLD").search_calls,
        )

    def test_every_falsification_gate_passes_without_metric_substitution(self):
        result = run_probe()
        self.assertTrue(result.passed, result.failed_gates)
        self.assertEqual(result.failed_gates, ())
```

Breaks caught: literal source replay masquerading as transfer; giving history or a type-shaped sham the shortcut; cost advantage surviving removal of the retained standalone cause; reporting success by substituting another metric.

- [ ] **Step 2: Run transfer tests and verify RED**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification.TransferControlTests -v
```

Expected: failures because arm execution and `run_probe` do not exist.

- [ ] **Step 3: Implement the complete frozen target universe and arms**

Freeze:

```python
TARGET_INPUTS = ("aa", "ab", "ba", "bb")
TARGET_TO_SOURCE = {"aa": "00", "ab": "01", "ba": "10", "bb": "11"}
TARGET_LABEL_ORACLE = {
    "aa": "EVEN",
    "ab": "ODD",
    "ba": "ODD",
    "bb": "EVEN",
}
```

Enumerate all 16 total target maps with `itertools.product(("EVEN", "ODD"), repeat=4)` in lexicographic product order. COLD performs one acquisition-search call per candidate and exhaustively attacks each until the correct candidate survives; with the frozen order its literal expected cost is 7.

WARM accepts only a restarted present containing a `pair -> label` capability with the frozen authority/verifier and exact standalone certificate. Transport its output through `TARGET_TO_SOURCE`, mint a target candidate, and run the same complete four-input authority before returning zero search calls. Discovery is not invoked on this route.

RAW_HISTORY receives `ledger.jsonl()` but no present, and therefore follows COLD. SHAM receives a restarted present containing a four-row, same-type, same-cost wrong capability; it fails the same target authority and then follows COLD. ANCESTOR_ABLATION receives an exact restarted empty `CompiledPresent` and follows COLD.

Every arm returns:

```python
@dataclass(frozen=True)
class ArmMeasurement:
    name: str
    search_calls: int
    authority_checks: int
    verified_semantics: tuple[tuple[str, str], ...]
    authority_snapshot: str
    verifier_id: str
    used_compiled_capability: bool
```

`run_probe()` evaluates the 13 spec gates literally. If any fails, `passed` is false and `failed_gates` contains stable gate codes; it never changes the cost definition or authority.

- [ ] **Step 4: Run the complete focused module and verify GREEN**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification -v
```

Expected: all focused tests pass; COLD/RAW_HISTORY/SHAM/ANCESTOR_ABLATION each report 7 search calls and WARM reports 0.

- [ ] **Step 5: Commit the transfer/control slice**

```bash
git add qckn_v2_compounding_falsification.py tests/test_qckn_v2_compounding_falsification.py
git commit -m "feat: add controlled unseen compounding transfer probe"
```

---

### Task 4: Produce Deterministic Evidence and CI Qualification

**Files:**
- Modify: `tests/test_qckn_v2_compounding_falsification.py`
- Modify: `qckn_v2_compounding_falsification.py`
- Create: `.github/workflows/qckn-v2-compounding-falsification.yml`
- Create: `docs/research/qckn-v2-compounding-falsification.md`

**Interfaces:**
- Consumes: `run_probe()`.
- Produces: `main() -> int`, writing canonical JSON to `QCKN_V2_RESULT_PATH` when set and printing the same payload to stdout.
- Produces: GitHub artifact `qckn-v2-compounding-falsification-evidence` containing `qckn-v2-compounding-result.json`.

- [ ] **Step 1: Add a failing CLI evidence test**

```python
class EvidenceTests(unittest.TestCase):
    def test_canonical_evidence_round_trips_and_contains_all_cost_classes(self):
        result = run_probe()
        payload = result.metrics()
        self.assertEqual(payload["generation_acquisition_search"], {"G1": 10, "G2": 3, "G3": 0})
        self.assertEqual(payload["active_capabilities"], {"before": 3, "after": 1})
        self.assertEqual(payload["reserve_item_count"], 0)
        self.assertEqual(payload["reserve_negative_control_count"], 1)
        self.assertIn("generation_authority_checks", payload)
        self.assertIn("target_search_calls", payload)
        self.assertIn("compiled_present_bytes", payload)
        self.assertIn("ledger_event_count", payload)
        self.assertIn("provenance_pointer_count", payload)
        self.assertIn("restart_digest", payload)
        self.assertIn("protected_replay_digest", payload)
        self.assertTrue(payload["passed"])
```

Break caught: collapsing search and verification into one flattering total or omitting the evidence needed to audit restart, representation, reserve, provenance, and causal attribution.

- [ ] **Step 2: Run the evidence test and verify RED**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification.EvidenceTests -v
```

Expected: failure because `ProbeResult.metrics()` is incomplete or absent.

- [ ] **Step 3: Implement canonical evidence output and execute it**

Use `json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"`. `main()` returns 0 only when all gates pass; otherwise it prints the named failed gates and returns 1. Write the file only after the result is fully measured.

Run:

```bash
QCKN_V2_RESULT_PATH=/tmp/qckn-v2-compounding-result.json \
  python qckn_v2_compounding_falsification.py
```

Expected: exit 0 and canonical JSON reporting `10 > 3 > 0`, ACTIVE `3 -> 1`, WARM 0, COLD 7, exact control restoration, and all gate codes passing.

- [ ] **Step 4: Add the workflow and measured evidence record**

The workflow must trigger only on `qckn-v2-compounding-falsification-v1` pushes and manual dispatch, use Python 3.12, run the focused test module, run all tests with:

```bash
PYTHONPATH="${GITHUB_WORKSPACE}/realitygraph:${GITHUB_WORKSPACE}/qckn-contract" \
python -m unittest discover -s tests -p 'test_*.py' -v
```

check out `heathsanchez/Minimal-Sufficient-Interface` at frozen QCK commit `51ea5ab8121099173bc8d4edb6c83a5bcb7f3fb1`, execute the probe with `QCKN_V2_RESULT_PATH`, and upload the JSON via `actions/upload-artifact@v4` even on failure.

Write `docs/research/qckn-v2-compounding-falsification.md` from the measured local JSON. Include the exact commits, toolchain, metrics table, 13 gate outcomes, claim boundary, and either `PASS` or the smallest named obstruction. Do not generalize beyond the finite fixture.

- [ ] **Step 5: Run focused and full local verification**

Run:

```bash
python -m unittest tests.test_qckn_v2_compounding_falsification -v
PYTHONPATH="$PWD:/workspace/scratch/e453c7c0eddc/Minimal-Sufficient-Interface" \
  python -m unittest discover -s tests -p 'test_*.py' -q
QCKN_V2_RESULT_PATH=/tmp/qckn-v2-compounding-result.json \
  python qckn_v2_compounding_falsification.py
git diff --check
```

Expected: focused tests pass; all pre-existing 158 tests plus the new focused tests pass; probe exits 0; no whitespace errors.

- [ ] **Step 6: Commit the qualification slice**

```bash
git add \
  qckn_v2_compounding_falsification.py \
  tests/test_qckn_v2_compounding_falsification.py \
  .github/workflows/qckn-v2-compounding-falsification.yml \
  docs/research/qckn-v2-compounding-falsification.md
git commit -m "ci: qualify QCKN V2 compounding falsification"
```

---

## Final Self-Review

- Spec coverage: Tasks 1-4 cover the frozen generation sequence, independent authority, dependency preservation, ACTIVE contraction, exact restart, PROVENANCE, RESERVE negative control, unseen relabelled transfer, all five arms, separated metrics, deterministic evidence, CI, and bounded claims.
- Placeholder scan: every implementation step, test expectation, interface, and command is concrete.
- Type consistency: `GenerationBundle` feeds `build_retained_state`; `RetainedState.present` feeds `run_target_arm`; `run_probe` owns the aggregate `ProbeResult`; `ProbeResult.metrics()` is the sole CLI/workflow evidence payload.
- Mutation check: tests fail on changed search counts, dependency clearing, incomplete recertification, missing contraction, lost semantics, erased ancestry, reserve deletion, history/sham shortcut, ablation non-restoration, authority drift, or missing cost-class evidence.
