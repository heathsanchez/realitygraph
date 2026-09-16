# Verified Language-Growth Closure v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace generation-specific orchestration with one generic developmental executor and qualify a bounded G1 -> G2 -> G3 recursive language-growth chain with exact restart, attack, future zero-search reuse, causal ablation, and bounded depth-3 closure.

**Architecture:** Keep the verified v1 trust kernel unchanged where possible. Add immutable developmental state, frozen generation-spec protocols, canonical snapshot serialization, and one `execute_generation(state, spec)` transition that owns routing, licensing, growth admission, capability retention, restart, attack, future evaluation, and trace emission. Express G1, G2, and the new G3 only as adapters/data outside the executor.

**Tech Stack:** Python 3.12, stdlib `dataclasses`, `enum`, `hashlib`, `json`, `itertools`, `unittest`; existing RealityGraph v1 grammar/capability/attack/closure modules; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-verified-language-growth-closure-v2-design.md`

## Global Constraints

- Base exactly from green v1 head `81477f74a3855b047c04c5c3bcc76504d65bbeb6`.
- Preserve v1 rule: `UnknownExpressivity` requires separate `Complete + NoResolution`; partial search remains `UnknownSearch`.
- `realitygraph/developmental_executor.py` and state/snapshot modules must not import `realitygraph.fixtures`.
- Executor must not dispatch on generation IDs, G1/G2/G3 labels, constructor names, or semantic target names.
- All candidate orderings deterministic and canonical.
- G3 two-state impossibility must be established exhaustively on the frozen carrier before three-state growth is licensed; if false, qualification returns `NEGATIVE_FIXTURE` rather than weakening the boundary.
- Every structural admission requires novelty, adequacy, preservation, replayability, independent verification, explicit dependencies, attack evidence, future zero-search evidence, and ablation evidence.
- Final scientific verdict is `PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2` only when every gate passes.
- Final closure remains bounded: `status=CLOSED_BOUNDED`, `qualification_depth=3`; no open-ended/unbounded claim.

---

## File map

### New generic core files

- `realitygraph/developmental_state.py` — immutable `DevelopmentalState`, terminal records, canonical state digest.
- `realitygraph/generation_spec.py` — generic protocol/data types for current-language, lower-substrate, verifier, attack, and frozen manifests.
- `realitygraph/developmental_snapshot.py` — canonical snapshot text, cold restart, exact equality checks.
- `realitygraph/developmental_executor.py` — one public `execute_generation(state, spec)` transition and canonical `GenerationTrace`.

### New fixture/adapters

- `realitygraph/fixtures/generation_specs_v2.py` — wraps v1 Boolean and stateful fixtures as data/adapters; no orchestration authority.
- `realitygraph/fixtures/three_state_observer_growth.py` — exhaustive two-state current language and three-state lower substrate for G3.

### Qualification / tests / CI

- `verified_language_growth_closure_v2.py` — sealed three-generation qualification and JSON artifact.
- `tests/test_developmental_state.py`
- `tests/test_generation_spec.py`
- `tests/test_developmental_snapshot.py`
- `tests/test_developmental_executor.py`
- `tests/test_three_state_observer_growth.py`
- `tests/test_verified_language_growth_closure_v2.py`
- `.github/workflows/verified-language-growth-closure-v2.yml`
- `docs/research/verified-language-growth-closure-v2.md`
- `README.md` — bounded V2 section after final green run.

---

### Task 1: Immutable developmental state and canonical serialization

**Files:**
- Create: `realitygraph/developmental_state.py`
- Create: `tests/test_developmental_state.py`

**Interfaces:**
- Produces: `TerminalRecord`, `DevelopmentalState`, `DevelopmentalState.with_generation(...)`, `DevelopmentalState.to_text()`, `DevelopmentalState.from_text()`, `DevelopmentalState.digest`.
- Consumes: existing `Grammar`, `GrammarDelta`, `FiniteCapability`, `CapabilityGraph`, `canonical_digest`.

- [ ] **Step 1: Write failing round-trip and immutability tests**

```python
from realitygraph.developmental_state import DevelopmentalState, TerminalRecord


def test_state_round_trip_is_byte_exact():
    state = DevelopmentalState.empty(
        authority_snapshot="authority-v2",
        protected_consequence_digest="protected-v2",
    )
    rebuilt = DevelopmentalState.from_text(state.to_text())
    assert rebuilt.to_text() == state.to_text()
    assert rebuilt.digest == state.digest


def test_with_generation_returns_new_state():
    state = DevelopmentalState.empty("authority-v2", "protected-v2")
    next_state = state.with_generation(
        grammar=state.grammar,
        capability_graph=state.capability_graph,
        admitted_delta=None,
        terminal_record=TerminalRecord(
            generation_id="probe",
            obligation_id="o",
            route="UNKNOWN_SEARCH",
            evidence_digest="e",
        ),
        provenance_ids=("p",),
    )
    assert state.generation_index == 0
    assert next_state.generation_index == 1
    assert state.digest != next_state.digest
```

- [ ] **Step 2: Run to verify RED**

Run: `python -m unittest tests.test_developmental_state -v`

Expected: import failure because `developmental_state` does not exist.

- [ ] **Step 3: Implement minimal canonical state model**

Use frozen dataclasses. Serialize one canonical JSON object with sorted keys and compact separators. Store grammar via `grammar.text()`, capabilities as canonical capability dictionaries sorted by `capability_id`, admitted deltas via `delta.text()`, terminal records sorted by generation order, authority/protected digests, provenance, and generation index. `digest` must hash the canonical text with prefix `developmental-state-v2:`.

Public signatures:

```python
@dataclass(frozen=True)
class TerminalRecord:
    generation_id: str
    obligation_id: str
    route: str
    evidence_digest: str
    retained_capability_id: str | None = None
    admitted_delta_id: str | None = None

@dataclass(frozen=True)
class DevelopmentalState:
    generation_index: int
    grammar: Grammar
    capability_graph: CapabilityGraph
    admitted_deltas: tuple[GrammarDelta, ...]
    terminal_records: tuple[TerminalRecord, ...]
    authority_snapshot: str
    protected_consequence_digest: str
    provenance_ids: tuple[str, ...]

    @classmethod
    def empty(cls, authority_snapshot: str, protected_consequence_digest: str) -> "DevelopmentalState": ...
    @property
    def digest(self) -> str: ...
    def to_text(self) -> str: ...
    @classmethod
    def from_text(cls, text: str) -> "DevelopmentalState": ...
    def with_generation(... ) -> "DevelopmentalState": ...
```

- [ ] **Step 4: Run focused and inherited core tests**

Run:

```bash
python -m unittest tests.test_developmental_state -v
python -m unittest tests.test_capability_algebra tests.test_grammar_growth -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/developmental_state.py tests/test_developmental_state.py
git commit -m "feat: add immutable developmental state"
```

---

### Task 2: Frozen generation specification and adapter contracts

**Files:**
- Create: `realitygraph/generation_spec.py`
- Create: `tests/test_generation_spec.py`

**Interfaces:**
- Produces: `LanguageEnumeration`, `CandidateEnumeration`, `FutureEvaluation`, `GenerationSpec`, adapter protocols, `GenerationSpec.digest`.
- Consumes: `FiniteConstructor`, `ResidualCertificate`, `DevelopmentalState`.

- [ ] **Step 1: Write failing contract/digest tests**

```python
def test_generation_spec_digest_changes_when_future_manifest_changes():
    a = make_spec(future_manifest=("f1",))
    b = make_spec(future_manifest=("f2",))
    assert a.digest != b.digest


def test_partial_language_enumeration_cannot_claim_complete():
    enum = LanguageEnumeration(
        constructors=(), carrier_digest="c", enumeration_digest="e",
        replay_evidence=("budget-stop",), complete=False, search_exhausted=False,
    )
    assert enum.complete is False
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_generation_spec -v`

Expected: missing module.

- [ ] **Step 3: Implement explicit protocols and frozen manifests**

Use `typing.Protocol` with these required call signatures:

```python
class CurrentLanguageAdapter(Protocol):
    adapter_id: str
    def enumerate_current(self, state: DevelopmentalState, spec: "GenerationSpec") -> LanguageEnumeration: ...

class LowerSubstrateAdapter(Protocol):
    adapter_id: str
    def enumerate_candidates(self, state: DevelopmentalState, residual: ResidualCertificate, spec: "GenerationSpec") -> CandidateEnumeration: ...

class VerifierAdapter(Protocol):
    adapter_id: str
    def current_resolves(self, state, spec, constructor: FiniteConstructor) -> bool: ...
    def candidate_adequate(self, state, spec, candidate: FiniteConstructor) -> bool: ...
    def verify_candidate(self, state, spec, candidate: FiniteConstructor) -> bool: ...
    def verify_protected(self, state, spec, candidate: FiniteConstructor) -> bool: ...
    def compile_capability(self, state, spec, candidate: FiniteConstructor, delta: GrammarDelta) -> FiniteCapability: ...
    def verify_future(self, state, spec, capability: FiniteCapability) -> FutureEvaluation: ...

class AttackAdapter(Protocol):
    adapter_id: str
    def challenges(self, state, spec, capability: FiniteCapability) -> tuple[str, ...]: ...
    def oracle(self, state, spec, challenge: str) -> str: ...
```

`GenerationSpec` must include the exact spec fields and canonical adapter IDs/manifests; its digest prefix is `generation-spec-v2:`.

- [ ] **Step 4: Run tests**

Run:

```bash
python -m unittest tests.test_generation_spec -v
python -m unittest tests.test_developmental_types -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/generation_spec.py tests/test_generation_spec.py
git commit -m "feat: define frozen generation specifications"
```

---

### Task 3: Exact developmental snapshots and cold restart

**Files:**
- Create: `realitygraph/developmental_snapshot.py`
- Create: `tests/test_developmental_snapshot.py`

**Interfaces:**
- Produces: `DevelopmentalSnapshot.from_state(state)`, `.to_text()`, `.digest`, `.restore()`.
- Consumes: `DevelopmentalState` only; restore must not call any generation adapter.

- [ ] **Step 1: Write failing snapshot tests**

```python
def test_snapshot_cold_restart_is_exact_and_adapter_free():
    state = seeded_state()
    snap = DevelopmentalSnapshot.from_state(state)
    restored = snap.restore()
    assert snap.to_text() == DevelopmentalSnapshot.from_state(restored).to_text()
    assert restored.digest == state.digest
    assert restored.capability_graph.active_ids() == state.capability_graph.active_ids()
    assert tuple(c.constructor_id for c in restored.grammar.constructors) == tuple(
        c.constructor_id for c in state.grammar.constructors
    )
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_developmental_snapshot -v`

- [ ] **Step 3: Implement canonical snapshot wrapper**

Snapshot stores exactly `state.to_text()` plus redundant top-level digests for corruption detection:

```python
@dataclass(frozen=True)
class DevelopmentalSnapshot:
    state_text: str
    state_digest: str
    grammar_digest: str
    active_capability_ids: tuple[str, ...]
    admitted_delta_ids: tuple[str, ...]

    @classmethod
    def from_state(cls, state: DevelopmentalState) -> "DevelopmentalSnapshot": ...
    def restore(self) -> DevelopmentalState: ...
```

`restore()` must validate every redundant digest/id list and raise `ValueError` on mismatch.

- [ ] **Step 4: Run snapshot + restart tests**

Run:

```bash
python -m unittest tests.test_developmental_snapshot -v
python -m unittest tests.test_retained_capability tests.test_grammar_growth -v
```

- [ ] **Step 5: Commit**

```bash
git add realitygraph/developmental_snapshot.py tests/test_developmental_snapshot.py
git commit -m "feat: add exact developmental snapshots"
```

---

### Task 4: Generic executor transition

**Files:**
- Create: `realitygraph/developmental_executor.py`
- Create: `tests/test_developmental_executor.py`

**Interfaces:**
- Produces: `GenerationRoute`, `GenerationTrace`, `GenerationResult`, `execute_generation(state, spec)`.
- Consumes: tasks 1-3 plus existing v1 residual, grammar growth, capability graph, attack modules.

- [ ] **Step 1: Write failing route and no-dispatch tests**

Required tests:

```python
def test_partial_current_language_routes_unknown_search_without_growth():
    result = execute_generation(empty_state(), partial_spec())
    assert result.trace.route == "UNKNOWN_SEARCH"
    assert result.state.digest == empty_state().digest
    assert result.trace.admitted_delta_id is None


def test_complete_unresolved_language_can_license_growth():
    result = execute_generation(empty_state(), tiny_growth_spec())
    assert result.trace.route == "COMPILED"
    assert result.trace.completeness_digest
    assert result.trace.no_resolution_digest
    assert result.trace.admitted_delta_id


def test_executor_source_has_no_fixture_import_or_generation_dispatch():
    source = Path("realitygraph/developmental_executor.py").read_text()
    assert "realitygraph.fixtures" not in source
    for forbidden in ("G1", "G2", "G3", "generation_id ==", "constructor_id =="):
        assert forbidden not in source
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_developmental_executor -v`

- [ ] **Step 3: Implement minimal executor protocol**

Public result types:

```python
class GenerationRoute(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    COMPILED = "COMPILED"
    UNKNOWN_SEARCH = "UNKNOWN_SEARCH"
    UNKNOWN_CHOICE = "UNKNOWN_CHOICE"
    NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"
    REFUTED = "REFUTED"

@dataclass(frozen=True)
class GenerationTrace:
    generation_id: str
    state_before_digest: str
    spec_digest: str
    route: str
    completeness_digest: str | None
    no_resolution_digest: str | None
    residual_digest: str | None
    candidate_enumeration_digest: str | None
    admitted_delta_id: str | None
    retained_capability_id: str | None
    restart_digest: str | None
    attack_digest: str | None
    future_evidence_digest: str | None
    state_after_digest: str

@dataclass(frozen=True)
class GenerationResult:
    state: DevelopmentalState
    trace: GenerationTrace
    capability: FiniteCapability | None
    future: FutureEvaluation | None
```

Algorithm exactly follows spec steps 1-16. Use `grow_grammar(...)` for admission. If current enumeration is incomplete, return unchanged state with `UNKNOWN_SEARCH`. If current complete and a constructor resolves, return `AUTHORIZED` without delta. If complete/no-resolution and candidate enumeration yields no adequate verified unique minimal candidate, preserve typed choice/obstruction according to candidate verdicts; never invent growth.

After admission:

1. compile capability via verifier adapter;
2. add to `CapabilityGraph`;
3. build new state;
4. snapshot/restore and require exact digest equality;
5. run `exhaustive_attack` over adapter challenge set;
6. fail/revoke on counterexample according to existing attack semantics;
7. call `verify_future` only after freeze and record its digest;
8. emit terminal record and trace.

- [ ] **Step 4: Run focused + v1 constitutional tests**

Run:

```bash
python -m unittest tests.test_developmental_executor -v
python -m unittest tests.test_developmental_types tests.test_developmental_closure tests.test_capability_algebra -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/developmental_executor.py tests/test_developmental_executor.py
git commit -m "feat: add generic developmental executor"
```

---

### Task 5: Express V1 G1 and G2 as GenerationSpec adapters

**Files:**
- Create: `realitygraph/fixtures/generation_specs_v2.py`
- Modify only if required for extraction: `realitygraph/fixtures/boolean_observer_growth.py`, `realitygraph/fixtures/stateful_observer_growth.py`
- Extend: `tests/test_developmental_executor.py`

**Interfaces:**
- Produces: `make_g1_spec()`, `make_g2_spec(g1_state)`, deterministic adapters that expose existing v1 finite spaces without selecting candidates themselves.
- Consumes: generic executor/spec/state APIs.

- [ ] **Step 1: Write failing same-executor G1/G2 tests**

```python
def test_v1_g1_and_g2_are_executed_by_same_entry_point():
    s0 = initial_v2_state()
    r1 = execute_generation(s0, make_g1_spec())
    r2 = execute_generation(r1.state, make_g2_spec(r1.state))
    assert r1.trace.route == "COMPILED"
    assert r2.trace.route == "COMPILED"
    assert r2.capability.dependencies == (r1.capability.capability_id,)
    assert r1.future.grammar_search_calls == 0
    assert r2.future.grammar_search_calls == 0
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_developmental_executor -v`

- [ ] **Step 3: Implement adapters by extracting, not duplicating, finite semantics**

G1 current adapter must enumerate the four x-only Boolean denotations from v1. G1 lower adapter must enumerate NAND denotations by canonical compositional depth and expose candidate constructors. Verifier adapter requires semantic signature `0110` but does not supply a constructor ID.

G2 current adapter must enumerate the complete 16 current-pair Boolean source denotations and the effective history signatures used in v1. G2 lower adapter must enumerate canonical two-state Moore-machine candidates over the **active G1 capability signal** and stamp explicit G1 dependency IDs. Verifier must compile G2 capability with dependency on G1.

No adapter may call `build_g1()` or `build_g2()` from inside `execute_generation`; old builders remain regression evidence only.

- [ ] **Step 4: Run focused and old V1 integration tests**

Run:

```bash
python -m unittest tests.test_developmental_executor tests.test_verified_language_growth_closure -v
```

Expected: both new generic path and old V1 qualification remain green.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/fixtures/generation_specs_v2.py realitygraph/fixtures/boolean_observer_growth.py realitygraph/fixtures/stateful_observer_growth.py tests/test_developmental_executor.py
git commit -m "feat: route g1 and g2 through generic executor"
```

---

### Task 6: Prove G3 premise and implement three-state observer fixture

**Files:**
- Create: `realitygraph/fixtures/three_state_observer_growth.py`
- Create: `tests/test_three_state_observer_growth.py`

**Interfaces:**
- Produces: `SEQUENCE_CARRIER`, `target_contains_11(sequence)`, `enumerate_two_state_denotations(g2_capability)`, `enumerate_three_state_candidates(g2_capability)`, `make_g3_spec(g2_state)`.

- [ ] **Step 1: Write premise-first failing tests**

```python
def test_two_state_language_is_complete_and_cannot_realize_target():
    g2 = seeded_g2_capability()
    enumeration = enumerate_two_state_denotations(g2)
    assert enumeration.raw_machine_count == 64
    assert enumeration.complete is True
    assert TARGET_SIGNATURE not in enumeration.semantic_signatures


def test_three_state_space_contains_a_verified_target_candidate():
    g2 = seeded_g2_capability()
    candidates = enumerate_three_state_candidates(g2)
    matching = [c for c in candidates.constructors if c.semantic_signature == TARGET_SIGNATURE]
    assert matching
    assert all(g2.capability_id in c.dependencies for c in matching)
```

Important: for two-state binary-input Moore machines the **raw machine count is `2^(2*2) * 2^2 = 64`**, not the source-signature count after quotienting. For three-state binary-input Moore machines the raw count is `3^(3*2) * 2^3 = 5,832`.

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_three_state_observer_growth -v`

- [ ] **Step 3: Implement exhaustive machine enumeration**

Define:

```python
SEQUENCE_CARRIER = tuple(
    "".join(bits)
    for length in range(0, 5)
    for bits in product("01", repeat=length)
)
```

`target_contains_11(sequence)` returns `"1"` iff substring `"11"` occurs, else `"0"`.

Generic Moore machine representation:

```python
@dataclass(frozen=True)
class MooreMachine:
    state_count: int
    transitions: tuple[int, ...]  # state-major, then input 0/1
    outputs: tuple[int, ...]
    def run(self, signal_sequence: str) -> str: ...
```

Canonicalization is extensional over the full `SEQUENCE_CARRIER`: retain the least `(complexity, machine_id)` representative per semantic signature. Completeness certificate records raw-space count and carrier digest.

Before constructing the G3 spec, assert exactly:

```python
if TARGET_SIGNATURE in two_state.semantic_signatures:
    raise NegativeFixtureError("G3 target realizable by two-state machine")
```

Then enumerate 5,832 three-state machines, quotient extensionally, and expose the deterministic minimal target-realizing candidate(s). Every candidate constructor and compiled capability has explicit dependency on the active G2 capability ID.

- [ ] **Step 4: Run exhaustive G3 tests**

Run: `python -m unittest tests.test_three_state_observer_growth -v`

Expected: complete two-state space, exact no-resolution, at least one verified three-state candidate.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/fixtures/three_state_observer_growth.py tests/test_three_state_observer_growth.py
git commit -m "feat: add exhaustive g3 state-growth fixture"
```

---

### Task 7: Three-generation qualification, restart, and causal ablation

**Files:**
- Create: `verified_language_growth_closure_v2.py`
- Create: `tests/test_verified_language_growth_closure_v2.py`

**Interfaces:**
- Produces: `run_qualification(write_result: bool = True) -> dict`, summary file `verified-language-growth-closure-v2-summary.json`.
- Consumes: `execute_generation`, G1/G2/G3 specs, snapshot, capability graph ablation, v1 closure semantics.

- [ ] **Step 1: Write failing end-to-end tests**

Required tests:

```python
def test_three_generations_share_executor_and_form_real_dependency_chain():
    d = run_qualification(write_result=False)
    assert d["gates"]["same_executor_g1_g2_g3"]
    assert d["gates"]["g2_depends_on_g1"]
    assert d["gates"]["g3_depends_on_g2"]


def test_causal_ablation_chain():
    d = run_qualification(write_result=False)
    assert d["gates"]["g1_ablation_invalidates_g2_g3"]
    assert d["gates"]["g2_ablation_invalidates_g3_preserves_g1"]
    assert d["gates"]["g3_ablation_preserves_g1_g2"]


def test_v2_claim_is_bounded_depth3():
    d = run_qualification(write_result=False)
    assert d["closure"]["status"] == "CLOSED_BOUNDED"
    assert d["closure"]["qualification_depth"] == 3
    assert d["claims"]["open_ended_closure"] is False
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_verified_language_growth_closure_v2 -v`

- [ ] **Step 3: Implement sealed qualification**

Qualification sequence:

```python
s0 = initial_v2_state()
r1 = execute_generation(s0, make_g1_spec())
s1 = DevelopmentalSnapshot.from_state(r1.state).restore()
r2 = execute_generation(s1, make_g2_spec(s1))
s2 = DevelopmentalSnapshot.from_state(r2.state).restore()
r3 = execute_generation(s2, make_g3_spec(s2))
s3 = DevelopmentalSnapshot.from_state(r3.state).restore()
```

Then verify:

- traces all have same schema and public executor identity;
- G1 -> G2 -> G3 explicit capability dependencies;
- full snapshot byte/digest equality;
- all three future evaluations have `grammar_search_calls == 0`;
- all three attacks survive the complete declared challenge spaces;
- ablation sets exactly `{G1,G2,G3}`, `{G2,G3}`, `{G3}` respectively;
- `UnknownSearch`, `UnknownChoice`, stale certificate, sham extension controls inherited from v1 remain true;
- executor source has no fixture import/generation dispatch;
- final closure artifact has `status=CLOSED_BOUNDED`, `qualification_depth=3`.

Summary must contain exact digests for initial/final state, all specs, traces, deltas, capabilities, attacks, snapshots, ablations, and closure.

Final stdout:

```text
PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2
```

only when every gate is true.

- [ ] **Step 4: Run qualification tests + full suite**

Run:

```bash
python -m unittest tests.test_verified_language_growth_closure_v2 -v
python -m unittest discover -s tests -v
python verified_language_growth_closure_v2.py
```

Expected: all tests PASS and exact verdict emitted.

- [ ] **Step 5: Commit**

```bash
git add verified_language_growth_closure_v2.py tests/test_verified_language_growth_closure_v2.py
git commit -m "feat: qualify generic depth-three language growth"
```

---

### Task 8: Dedicated CI evidence gate, research record, and README boundary

**Files:**
- Create: `.github/workflows/verified-language-growth-closure-v2.yml`
- Create: `docs/research/verified-language-growth-closure-v2.md`
- Modify: `README.md`

**Interfaces:**
- Produces authoritative run artifact `verified-language-growth-closure-v2-evidence` containing JSON + log.

- [ ] **Step 1: Add dedicated branch workflow**

Workflow must trigger on `verified-language-growth-closure-v2` and `workflow_dispatch`, Python 3.12, and run in this order:

```bash
python -m unittest tests.test_developmental_state -v
python -m unittest tests.test_generation_spec -v
python -m unittest tests.test_developmental_snapshot -v
python -m unittest tests.test_developmental_executor -v
python -m unittest tests.test_three_state_observer_growth -v
python -m unittest tests.test_verified_language_growth_closure_v2 -v
python -m unittest tests.test_verified_language_growth_closure -v
python -m unittest discover -s tests -v
python verified_language_growth_closure_v2.py | tee verified-language-growth-closure-v2.log
grep -Fx 'PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2' verified-language-growth-closure-v2.log
```

Then Python JSON assertions must require:

```python
assert d["passed"] is True
assert d["verdict"] == "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2"
assert d["closure"]["status"] == "CLOSED_BOUNDED"
assert d["closure"]["qualification_depth"] == 3
assert d["gates"]["same_executor_g1_g2_g3"] is True
assert d["gates"]["g3_two_state_no_resolution"] is True
assert d["gates"]["g3_depends_on_g2"] is True
assert d["gates"]["g1_ablation_invalidates_g2_g3"] is True
assert d["claims"]["open_ended_closure"] is False
```

Upload JSON + log using `actions/upload-artifact@v4`, `if-no-files-found: error`, retention 30 days.

- [ ] **Step 2: Run/observe final CI and debug fail-closed**

Use workflow logs as authoritative execution environment. Any scientific premise failure in G3 is not patched around; return to Task 6 and redesign the finite target if exhaustive evidence disproves the premise.

- [ ] **Step 3: Record exact evidence only after green run**

`docs/research/verified-language-growth-closure-v2.md` must record branch/head/run/job/artifact/certificate digest, G1/G2/G3 constructor IDs, search counts, zero-future-search counts, all ablation outcomes, and explicit non-goals.

- [ ] **Step 4: Add bounded README section**

State that V2 demonstrates one generic executor across three finite generations and explicitly does **not** establish open-ended or unbounded self-development.

- [ ] **Step 5: Re-run final workflow on the documentation-complete tree**

Require another green run on the exact final head before calling the branch complete.

- [ ] **Step 6: Commit final evidence/docs**

```bash
git add .github/workflows/verified-language-growth-closure-v2.yml docs/research/verified-language-growth-closure-v2.md README.md
git commit -m "ci: gate generic depth-three language growth"
```

---

## Plan self-review

- **Spec coverage:** state, spec protocols, same executor, G1/G2 adapter conversion, G3 exhaustive lower-bound premise, snapshot restart, attacks, zero-search future, typed route controls, causal ablation, depth-3 closure, CI evidence, and bounded claim all have explicit tasks.
- **Placeholder scan:** no TBD/TODO/"similar to" implementation placeholders remain; every code task names signatures and test commands.
- **Type consistency:** `DevelopmentalState`, `GenerationSpec`, `GenerationTrace`, `GenerationResult`, `DevelopmentalSnapshot`, and `execute_generation(state, spec)` names are fixed across tasks. `FutureEvaluation` owns `grammar_search_calls`; capability dependencies use capability IDs; constructor dependencies stay in `FiniteConstructor.dependencies`.
- **Important correction locked in:** G3 raw two-state Moore-machine space is 64 machines (`2^(2*2) * 2^2`), while the three-state space is 5,832 (`3^(3*2) * 2^3`). The implementation must distinguish raw completeness from extensional quotient size.
- **Scope:** one new generic orchestration subsystem plus deterministic finite adapters; no Parkinson/ACC imports enter the core; no open-ended-development claim.
