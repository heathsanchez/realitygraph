# Verified Meta-Growth V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bounded meta-developmental layer that learns which frozen repair family resolves an exact obstruction geometry, promotes that mapping through independent calibration, and reuses it prospectively with zero repair-portfolio search while leaving object-level verification to the existing V2 executor.

**Architecture:** V3 wraps, but does not modify the semantics of, `execute_generation(state, spec)`. It adds exact obstruction fingerprints, a frozen repair-strategy portfolio, canonical meta-memory with candidate/promoted/revoked repair rules, a generic `execute_meta_growth(...)` path, exact meta snapshots, and two heterogeneous qualification families whose promoted rules transfer to untouched isomorphic future tasks.

**Tech Stack:** Python 3.12, `dataclasses`, `enum`, `itertools`, `json`, `hashlib` via existing canonical digest helpers, `unittest`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-verified-meta-growth-v3-design.md`

## Global Constraints

- V3 starts from final green V2 head `001f77c43d87f642dfa9bc8a2bec43ab0f5ca750`.
- `realitygraph/developmental_executor.py` remains the only object-level admission path and must not import V3 fixtures or dispatch on strategy IDs/family names.
- Search failure is never expressivity failure; incomplete current-language search routes `UNKNOWN_SEARCH`.
- Repair strategies are frozen proposal generators; they cannot mutate persistent state directly.
- Losing repair attempts are ephemeral and must not alter the object state or meta-memory.
- A repair rule is promoted only after an independently frozen calibration episode with the same exact obstruction fingerprint selects the same strategy and passes all object-level gates.
- Prospective rule hits must perform `portfolio_search_calls = 0` and `competitor_strategy_calls = 0`; object-level candidate search inside the selected strategy may be nonzero.
- Repair ties remain `UNKNOWN_CHOICE`; strategy names or enumeration order may not break ties.
- Exact restart is required for both object state and meta-memory.
- V3 must remain explicitly bounded to the declared finite repair portfolio and exact finite obstruction canonicalizer.

---

### Task 1: Exact obstruction fingerprint

**Files:**
- Create: `realitygraph/obstruction_fingerprint.py`
- Create: `tests/test_obstruction_fingerprint.py`

**Interfaces:**
- Consumes: `DevelopmentalState`, `GenerationSpec`, complete `LanguageEnumeration`, verifier outputs over a finite carrier.
- Produces: `ObstructionFingerprint`, `canonicalize_obstruction(...) -> ObstructionFingerprint`.

- [ ] **Step 1: Write failing invariance and inequality tests**

```python
from realitygraph.obstruction_fingerprint import canonicalize_obstruction


def test_fingerprint_is_invariant_under_surface_relabeling():
    a = canonicalize_obstruction(
        input_type="pair",
        output_type="bit",
        current_partition=(("a", "b"), ("c", "d")),
        consequence_partition=(("a", "c"), ("b", "d")),
        current_language_semantic_count=4,
        authority_snapshot="auth",
        verifier_id="verifier",
    )
    b = canonicalize_obstruction(
        input_type="pair",
        output_type="bit",
        current_partition=(("u", "v"), ("w", "z")),
        consequence_partition=(("u", "w"), ("v", "z")),
        current_language_semantic_count=4,
        authority_snapshot="auth",
        verifier_id="verifier",
    )
    assert a.digest == b.digest


def test_nonisomorphic_obstruction_has_different_fingerprint():
    crossing = canonicalize_obstruction(
        input_type="pair", output_type="bit",
        current_partition=(("a", "b"), ("c", "d")),
        consequence_partition=(("a", "c"), ("b", "d")),
        current_language_semantic_count=4,
        authority_snapshot="auth", verifier_id="verifier",
    )
    nested = canonicalize_obstruction(
        input_type="pair", output_type="bit",
        current_partition=(("a", "b", "c"), ("d",)),
        consequence_partition=(("a", "b"), ("c", "d")),
        current_language_semantic_count=4,
        authority_snapshot="auth", verifier_id="verifier",
    )
    assert crossing.digest != nested.digest
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_obstruction_fingerprint -v`

Expected: import failure for missing `realitygraph.obstruction_fingerprint`.

- [ ] **Step 3: Implement exact finite canonicalization**

```python
@dataclass(frozen=True)
class ObstructionFingerprint:
    input_type: str
    output_type: str
    current_class_count: int
    consequence_class_count: int
    canonical_incidence_matrix: tuple[tuple[int, ...], ...]
    carrier_size: int
    current_language_semantic_count: int
    authority_snapshot: str
    verifier_id: str

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="obstruction-fingerprint-v3:")
```

Canonicalization must exhaustively permute current-class labels and consequence-class labels, construct the multiplicity matrix for each relabeling, flatten row-major, and choose the lexicographically minimal matrix. Reject overlapping/missing partition elements and mismatched carriers.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_obstruction_fingerprint -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add exact obstruction fingerprints`

---

### Task 2: Frozen repair strategy protocol and portfolio identity

**Files:**
- Create: `realitygraph/repair_strategy.py`
- Create: `tests/test_repair_strategy.py`

**Interfaces:**
- Consumes: `ObstructionFingerprint`, `DevelopmentalState`, meta task context.
- Produces: `RepairStrategy` protocol, `RepairPortfolio`, stable `portfolio_digest`, deterministic declared structural rank.

- [ ] **Step 1: Write failing portfolio identity tests**

```python
def test_portfolio_digest_is_order_independent():
    a = RepairPortfolio((StubStrategy("s1", 1), StubStrategy("s2", 2)))
    b = RepairPortfolio((StubStrategy("s2", 2), StubStrategy("s1", 1)))
    assert a.digest == b.digest


def test_duplicate_strategy_id_is_rejected():
    with self.assertRaises(ValueError):
        RepairPortfolio((StubStrategy("s1", 1), StubStrategy("s1", 2)))
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_repair_strategy -v`

- [ ] **Step 3: Implement protocol and immutable portfolio**

```python
class RepairStrategy(Protocol):
    strategy_id: str
    strategy_version: str
    structural_cost: int

    def applicable(self, fingerprint, object_state, meta_spec) -> bool: ...
    def materialize_generation_spec(self, object_state, meta_spec) -> GenerationSpec: ...


@dataclass(frozen=True)
class RepairPortfolio:
    strategies: tuple[RepairStrategy, ...]

    @property
    def digest(self) -> str:
        rows = sorted(
            (s.strategy_id, s.strategy_version, s.structural_cost)
            for s in self.strategies
        )
        return canonical_digest(rows, prefix="repair-portfolio-v3:")
```

Do not encode a winner in portfolio ordering.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_repair_strategy -v`

- [ ] **Step 5: Commit**

Commit message: `feat: define frozen repair strategy portfolio`

---

### Task 3: Canonical meta-memory, rule promotion, revocation, and exact restart

**Files:**
- Create: `realitygraph/meta_memory.py`
- Create: `tests/test_meta_memory.py`

**Interfaces:**
- Consumes: obstruction fingerprint digest, strategy identity/version, portfolio digest, authority/verifier/interface identity, episode evidence.
- Produces: `RepairRule`, `RepairRuleStatus`, `MetaMemory`, candidate creation, calibration promotion, revocation/ablation, canonical text round-trip.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_rule_requires_independent_calibration_before_promotion():
    memory = MetaMemory.empty()
    memory = memory.record_success(source_episode(... strategy_id="add-observable"))
    self.assertEqual(memory.rules[0].status, RepairRuleStatus.CANDIDATE)
    memory2 = memory.record_success(calibration_episode(... strategy_id="add-observable"))
    self.assertEqual(memory2.rules[0].status, RepairRuleStatus.PROMOTED)


def test_disagreeing_calibration_does_not_promote():
    memory = MetaMemory.empty().record_success(source_episode(... strategy_id="s1"))
    memory = memory.record_success(calibration_episode(... strategy_id="s2"))
    self.assertFalse(any(r.status is RepairRuleStatus.PROMOTED for r in memory.rules))


def test_meta_memory_round_trip_is_byte_exact():
    text = memory.text()
    assert MetaMemory.from_text(text).text() == text
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_meta_memory -v`

- [ ] **Step 3: Implement immutable rule lineage**

```python
class RepairRuleStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    PROMOTED = "PROMOTED"
    REVOKED = "REVOKED"

@dataclass(frozen=True)
class RepairRule:
    rule_id: str
    obstruction_fingerprint: str
    strategy_id: str
    strategy_version: str
    portfolio_digest: str
    authority_snapshot: str
    verifier_id: str
    interface_digest: str
    source_episode_digests: tuple[str, ...]
    status: RepairRuleStatus
    selection_cost: int
    ablation_handle: str
```

Promotion requires at least two distinct episode digests, one acquisition and one calibration, with identical fingerprint/strategy/version/portfolio/authority/verifier/interface identities.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_meta_memory -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add verified repair memory`

---

### Task 4: Generic meta-growth executor

**Files:**
- Create: `realitygraph/meta_executor.py`
- Create: `tests/test_meta_executor.py`
- Do not modify object-level semantics in `realitygraph/developmental_executor.py`.

**Interfaces:**
- Consumes: `DevelopmentalState`, `MetaMemory`, `MetaGrowthSpec`, frozen `RepairPortfolio`.
- Produces: `execute_meta_growth(...) -> MetaGrowthResult`, `MetaGrowthRoute`, exact counters and traces.

- [ ] **Step 1: Write failing cold/hit/control tests**

```python
def test_cold_path_evaluates_portfolio_from_same_parent():
    result = execute_meta_growth(state, MetaMemory.empty(), spec)
    assert result.route == MetaGrowthRoute.COMPILED
    assert result.portfolio_search_calls == len(spec.portfolio.strategies)
    assert all(d == state.digest for d in result.strategy_parent_digests)


def test_promoted_rule_hit_skips_competitors():
    result = execute_meta_growth(state, promoted_memory, spec)
    assert result.portfolio_search_calls == 0
    assert result.competitor_strategy_calls == 0
    assert result.selected_strategy_calls == 1


def test_partial_obstruction_stays_unknown_search():
    result = execute_meta_growth(state, MetaMemory.empty(), partial_spec)
    assert result.route == MetaGrowthRoute.UNKNOWN_SEARCH


def test_equal_ranked_repairs_stay_unknown_choice():
    result = execute_meta_growth(state, MetaMemory.empty(), tied_spec)
    assert result.route == MetaGrowthRoute.UNKNOWN_CHOICE
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_meta_executor -v`

- [ ] **Step 3: Implement `MetaGrowthSpec` and meta trace types**

```python
@dataclass(frozen=True)
class MetaGrowthSpec:
    episode_id: str
    phase: str  # ACQUISITION | CALIBRATION | FUTURE | CONTROL
    object_template: GenerationSpec
    fingerprint_builder: FingerprintBuilder
    portfolio: RepairPortfolio
    authority_snapshot: str
    verifier_id: str
    interface_digest: str
    portfolio_budget: int
```

- [ ] **Step 4: Implement exact cold path**

Flow:

```text
certify complete current language
-> build exact fingerprint
-> if no valid promoted rule: run each applicable strategy against immutable parent
-> retain only COMPILED successes as ephemeral results
-> select by (structural_cost, candidate.complexity)
-> if exact tie remains: UNKNOWN_CHOICE
-> commit only selected object's resulting state
-> emit episode evidence for meta-memory
```

`strategy_id` and capability ID may be recorded after a winner exists but must not be tie breakers.

- [ ] **Step 5: Implement promoted-rule hit path and strict validation**

A rule applies only when fingerprint, portfolio digest, authority, verifier, interface, strategy ID and strategy version all match an active portfolio strategy. The hit path materializes only that one strategy.

- [ ] **Step 6: Implement failure routes**

- incomplete current-language proof -> `UNKNOWN_SEARCH`
- portfolio budget exhausted before all applicable strategies checked and none succeeds -> `UNKNOWN_SEARCH`
- all applicable strategies completely checked and none succeeds -> `NAMED_META_OBSTRUCTION`
- exact tied winning repairs -> `UNKNOWN_CHOICE`
- object-level verifier/attack/future rejection -> losing ephemeral attempt, never persistent state mutation

- [ ] **Step 7: Source-level anti-dispatch test**

Assert `meta_executor.py` contains none of:

```text
realitygraph.fixtures
Family C
Family T
add_observable ==
add_finite_memory_2 ==
strategy_id == "
```

- [ ] **Step 8: Run GREEN**

Run: `python -m unittest tests.test_meta_executor -v`

- [ ] **Step 9: Commit**

Commit message: `feat: add generic verified meta-growth executor`

---

### Task 5: Exact meta snapshot

**Files:**
- Create: `realitygraph/meta_snapshot.py`
- Create: `tests/test_meta_snapshot.py`

**Interfaces:**
- Consumes: `DevelopmentalState`, `MetaMemory`, portfolio/authority identities.
- Produces: `MetaSnapshot.from_present(...)`, `restore() -> tuple[DevelopmentalState, MetaMemory]`.

- [ ] **Step 1: Write failing adapter-free restart test**

```python
def test_meta_snapshot_restart_is_exact_and_does_not_call_strategies():
    snapshot = MetaSnapshot.from_present(state, memory, portfolio.digest, "auth")
    restored_state, restored_memory = snapshot.restore()
    assert restored_state.digest == state.digest
    assert restored_memory.digest == memory.digest
    assert restored_memory.text() == memory.text()
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_meta_snapshot -v`

- [ ] **Step 3: Implement canonical snapshot wrapper**

Snapshot text includes exact canonical object-state text, meta-memory text, portfolio digest and authority snapshot. `restore()` may call only `DevelopmentalState.from_text(...)` and `MetaMemory.from_text(...)`; no strategy/fixture adapter calls.

- [ ] **Step 4: Run GREEN**

Run: `python -m unittest tests.test_meta_snapshot -v`

- [ ] **Step 5: Commit**

Commit message: `feat: add exact meta-growth snapshots`

---

### Task 6: Two heterogeneous repair families and frozen acquisition/calibration/future episodes

**Files:**
- Create: `realitygraph/fixtures/meta_growth_v3.py`
- Create: `tests/test_meta_growth_v3_fixtures.py`

**Interfaces:**
- Consumes: V2 `GenerationSpec` adapters, V3 strategy/meta interfaces.
- Produces: frozen four-strategy portfolio, Family-C and Family-T acquisition/calibration/future specs, tied/partial/stale/sham controls.

- [ ] **Step 1: Write fixture tests before implementation**

Required assertions:

```python
def test_family_c_variants_share_fingerprint_and_family_t_is_different(): ...
def test_family_c_cold_winner_is_add_observable(): ...
def test_family_t_cold_winner_is_add_finite_memory_2(): ...
def test_family_t_three_state_also_succeeds_but_costs_more(): ...
def test_acquisition_and_calibration_use_different_surface_labels(): ...
def test_future_capability_id_is_new_not_source_capability_id(): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_meta_growth_v3_fixtures -v`

- [ ] **Step 3: Implement the four frozen repair strategies**

```text
deepen_stateless_composition
add_observable
add_finite_memory_2
add_finite_memory_3
```

Each strategy must materialize a normal V2 `GenerationSpec`; no strategy may directly admit grammar/capability state.

- [ ] **Step 4: Implement Family C**

Use a finite pair carrier where the complete current language observes one coordinate only. Acquisition/calibration/future variants must use disjoint surface labels while inducing the same quotient/consequence incidence geometry. `add_observable` exposes the missing coordinate and wins. Finite-memory strategies declare themselves inapplicable on this nonsequential interface.

- [ ] **Step 5: Implement Family T**

Use finite histories where complete current language sees only present symbol while required consequence depends on a past/present distinction. `deepen_stateless_composition` and `add_observable` remain unable to separate histories that are identical under all declared present-only observables. Complete two-state memory succeeds; three-state memory also succeeds but has higher `structural_cost`.

- [ ] **Step 6: Implement control fixtures**

Include:
- partial current-language enumeration;
- partial repair-portfolio budget;
- exact tied successful strategies with same structural/candidate complexity;
- stale authority/verifier;
- forged matching surface label but wrong fingerprint/portfolio digest.

- [ ] **Step 7: Run GREEN**

Run: `python -m unittest tests.test_meta_growth_v3_fixtures -v`

- [ ] **Step 8: Commit**

Commit message: `feat: add heterogeneous meta-growth qualification worlds`

---

### Task 7: Acquisition, calibration promotion, prospective transfer, and causal ablation

**Files:**
- Create: `tests/test_verified_meta_growth_v3.py`
- Create: `verified_meta_growth_v3.py`

**Interfaces:**
- Consumes: all V3 core modules and frozen fixtures.
- Produces: sealed `run_qualification(write_result=True) -> dict` and exact verdict.

- [ ] **Step 1: Write the qualification tests first**

```python
def test_two_distinct_repair_rules_require_calibration_before_promotion(): ...
def test_future_family_c_uses_rule_with_zero_portfolio_search(): ...
def test_future_family_t_uses_rule_with_zero_portfolio_search(): ...
def test_future_object_capabilities_are_new_and_verified(): ...
def test_rule_ablation_restores_cold_portfolio_search(): ...
def test_wrong_fingerprint_stale_sham_partial_and_choice_controls(): ...
def test_exact_meta_snapshot_restart(): ...
def test_inherited_v2_qualification_remains_green(): ...
def test_claim_is_explicitly_bounded(): ...
```

- [ ] **Step 2: Run RED**

Run: `python -m unittest tests.test_verified_meta_growth_v3 -v`

Expected: import failure for missing `verified_meta_growth_v3`.

- [ ] **Step 3: Implement sealed episode sequence**

Sequence exactly:

```text
C-acquisition cold -> candidate C rule
T-acquisition cold -> candidate T rule
C-calibration cold -> promote C rule
T-calibration cold -> promote T rule
exact meta snapshot/restart
C-future -> promoted-rule hit, no portfolio search
T-future -> promoted-rule hit, no portfolio search
ablate C rule -> C-future returns to cold portfolio search
ablate T rule -> T-future returns to cold portfolio search
run all controls
run inherited V2 qualification
```

- [ ] **Step 4: Build bounded closure summary**

Required top-level JSON fields:

```text
version
verdict
passed
gates
acquisition
calibration
promoted_rules
future
ablations
controls
snapshot
closure
claims
```

Expected exact verdict:

```text
PASS_VERIFIED_META_GROWTH_V3
```

Expected exact closure display status:

```text
CLOSED_BOUNDED_META_GROWTH_V3
```

- [ ] **Step 5: Run GREEN**

Run: `python -m unittest tests.test_verified_meta_growth_v3 -v`

- [ ] **Step 6: Run entire suite**

Run: `python -m unittest discover -s tests -v`

Expected: zero failures/errors including inherited V1/V2 suites.

- [ ] **Step 7: Run standalone sealed qualification**

Run: `python verified_meta_growth_v3.py`

Expected final lines contain exact verdict and closure status.

- [ ] **Step 8: Commit**

Commit message: `feat: qualify verified learning of repair strategies`

---

### Task 8: Dedicated authoritative CI gate and evidence artifact

**Files:**
- Create: `.github/workflows/verified-meta-growth-v3.yml`

**Interfaces:**
- Consumes: V3 tests and sealed runner.
- Produces: authoritative branch-scoped run and artifact `verified-meta-growth-v3-evidence`.

- [ ] **Step 1: Add branch-scoped workflow**

Workflow must run, in order:

```text
obstruction fingerprint tests
repair strategy tests
meta memory tests
meta executor tests
meta snapshot tests
V3 fixture tests
V3 sealed qualification tests
inherited V2 qualification tests
full regression suite
standalone verified_meta_growth_v3.py
exact JSON assertions
artifact upload
```

- [ ] **Step 2: Assert exact scientific gates in CI**

The workflow must fail unless all are true:

```python
assert d["passed"] is True
assert d["verdict"] == "PASS_VERIFIED_META_GROWTH_V3"
assert d["closure"]["status"] == "CLOSED_BOUNDED_META_GROWTH_V3"
assert d["gates"]["two_distinct_promoted_repair_rules"] is True
assert d["gates"]["future_c_zero_portfolio_search"] is True
assert d["gates"]["future_t_zero_portfolio_search"] is True
assert d["gates"]["future_c_zero_competitor_calls"] is True
assert d["gates"]["future_t_zero_competitor_calls"] is True
assert d["gates"]["rule_ablation_restores_cold_search"] is True
assert d["gates"]["unknown_choice_preserved"] is True
assert d["claims"]["open_ended_meta_growth"] is False
assert d["claims"]["arbitrary_substrate_invention"] is False
```

- [ ] **Step 3: Push and observe the workflow**

Read the full job result and logs; do not infer success from a green badge alone.

- [ ] **Step 4: Fetch artifact metadata**

Record run ID, artifact ID, closure digest, promoted rule IDs, selected strategy IDs and future counters.

- [ ] **Step 5: Commit**

Commit message: `ci: gate verified meta-growth v3`

---

### Task 9: Permanent bounded evidence record and README

**Files:**
- Create: `docs/research/verified-meta-growth-v3.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: authoritative final scientific run evidence.
- Produces: permanent exact claim boundary and reproduction instructions.

- [ ] **Step 1: Write evidence record from actual green run**

Include exact:
- final scientific code head;
- workflow run ID;
- full test count;
- verdict and closure status;
- artifact ID;
- closure digest;
- acquisition/calibration fingerprints;
- promoted rule IDs and strategy classes;
- cold portfolio calls;
- future zero-search counters;
- repair-rule ablation evidence;
- explicit non-claims.

- [ ] **Step 2: Add bounded README section**

Explain in plain language:

> RealityGraph can now learn a verified mapping from an exact obstruction geometry to one of several predeclared repair families, independently requalify that mapping, and reuse it on an untouched isomorphic obstruction without re-searching competing repair families. The newly selected object capability is still synthesized and verified normally.

Also state explicitly that V3 does not invent arbitrary substrate families from nothing and does not establish open-ended self-development.

- [ ] **Step 3: Commit docs**

Commit message: `docs: record verified meta-growth v3`

- [ ] **Step 4: Run the authoritative V3 workflow on the actual final documentation-complete head**

Do not call V3 complete until this exact final tree is green and its final artifact is fetched.
