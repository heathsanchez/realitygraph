# Verified Language-Growth Closure v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and qualify a generic bounded developmental loop that distinguishes search failure from expressive inadequacy, synthesizes verified grammar extensions, composes and attacks retained capabilities, recursively uses an earned constructor in a later growth generation, and emits a replayable bounded closure certificate.

**Architecture:** Add a small standard-library-only core alongside the existing RealityGraph modules. The core represents certificates and finite semantics canonically, keeps residual routing separate from proposal machinery, models grammar additions as replayable deltas, models retained knowledge as typed finite capabilities with explicit dependency DAGs, and audits closure against a frozen boundary. A deterministic finite Boolean/stateful-observer qualification fixture exercises the complete two-generation path without importing Parkinson- or ACC-specific code.

**Tech Stack:** Python 3.12 standard library, `dataclasses`, `enum`, `hashlib`, `json`, existing `unittest` test style and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-verified-language-growth-closure-design.md`

## Global Constraints

- Generic core modules MUST NOT import Parkinson- or ACC-specific modules.
- Search failure, timeout, or budget exhaustion MUST NOT construct `UnknownExpressivity` without separate completeness and no-resolution certificates.
- Grammar admission MUST be extensionally novel, adequate for the certified residual, preservation-safe, independently verified, replayable, and ablatable.
- G2 MUST record and semantically use the G1 constructor as a dependency.
- Missing/stale authority, replay mismatch, dependency cycles, and malformed certificates fail closed.
- `CLOSED_BOUNDED` is relative only to the frozen manifest, grammar/substrate, verifier, protected consequences, and resource envelope.
- No new third-party dependencies.

---

### Task 1: Typed developmental results and residual licensing

**Files:**
- Create: `realitygraph/developmental_types.py`
- Create: `realitygraph/residual_certificate.py`
- Test: `tests/test_developmental_types.py`

**Interfaces:**
- Produces: `ResultKind`, `CertificateRef`, `BoundarySnapshot`, `DevelopmentalResult`, `CompletenessCertificate`, `NoResolutionCertificate`, `ResidualCertificate`, `make_expressivity_residual(...)`.
- Later tasks consume `ResidualCertificate.digest`, `authority_snapshot`, `language_id`, `substrate_id`, and `necessary_constraints`.

- [ ] **Step 1: Write failing result/certificate tests** covering canonical digests, exact restart, missing completeness, missing no-resolution, stale state digest, and authority mismatch.

```python
with self.assertRaises(ValueError):
    make_expressivity_residual(..., completeness=None, no_resolution=no_sep)
with self.assertRaises(ValueError):
    make_expressivity_residual(..., completeness=complete, no_resolution=None)
self.assertEqual(cert, ResidualCertificate.from_text(cert.text()))
```

- [ ] **Step 2: Run the focused tests and require failure**

Run: `python -m unittest tests.test_developmental_types -v`
Expected: FAIL because the modules do not exist.

- [ ] **Step 3: Implement immutable canonical types** using sorted compact JSON for digests and serialization. `ResidualCertificate.__post_init__` must require `residual_type == ResultKind.UNKNOWN_EXPRESSIVITY`, matching language/state/authority across both prerequisite certificates, and at least one unresolved obligation plus one necessary constraint.

- [ ] **Step 4: Run focused tests and require pass**

Run: `python -m unittest tests.test_developmental_types -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/developmental_types.py realitygraph/residual_certificate.py tests/test_developmental_types.py
git commit -m "feat: add typed residual licensing"
```

### Task 2: Finite grammar semantics, novelty, growth, and replayable deltas

**Files:**
- Create: `realitygraph/grammar.py`
- Create: `realitygraph/grammar_growth.py`
- Test: `tests/test_grammar_growth.py`

**Interfaces:**
- Consumes: `ResidualCertificate` from Task 1.
- Produces: `FiniteConstructor`, `Grammar`, `GrammarDelta`, `CandidateVerdict`, `GrammarGrowthResult`, `grow_grammar(...)`, `apply_delta(...)`, `ablate_delta(...)`.

`FiniteConstructor` stores a canonical finite semantic table:

```python
FiniteConstructor(
    constructor_id: str,
    input_type: str,
    output_type: str,
    semantics: tuple[tuple[str, str], ...],
    complexity: int,
    dependencies: tuple[str, ...] = (),
    primitive_expansion: tuple[str, ...] = (),
)
```

- [ ] **Step 1: Write failing tests** proving that extensionally duplicate constructors are rejected, the deterministic minimum-complexity adequate novel constructor is chosen, stale residuals are rejected, `GrammarDelta` round-trips byte-exactly, and ablating a delta restores its parent grammar.

- [ ] **Step 2: Run focused tests and require failure**

Run: `python -m unittest tests.test_grammar_growth -v`
Expected: FAIL because grammar modules do not exist.

- [ ] **Step 3: Implement canonical finite grammar**. `Grammar.extensional_classes()` groups constructors by `(input_type, output_type, semantic signature)`. `Grammar.digest` hashes canonical serialized constructor payloads. `apply_delta` must verify `parent_language_id == grammar.digest` and reject duplicate IDs or missing dependencies.

- [ ] **Step 4: Implement `grow_grammar`**. Inputs are the exact residual, parent grammar, deterministic candidate sequence, frozen authority snapshot, `adequate(candidate, residual)`, `preserves(candidate)`, and `verify(candidate)`. Sort by `(complexity, constructor_id)`, quotient extensionally, reject old-language equivalents, and return the first candidate passing all gates. The emitted delta records residual digest, authority snapshot, dependency IDs, verifier ID, provenance IDs, and ablation handle.

- [ ] **Step 5: Run focused tests and require pass**

Run: `python -m unittest tests.test_grammar_growth -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add realitygraph/grammar.py realitygraph/grammar_growth.py tests/test_grammar_growth.py
git commit -m "feat: add verified grammar growth"
```

### Task 3: Typed capability algebra, dependency DAG, composition, and attack

**Files:**
- Create: `realitygraph/capability.py`
- Create: `realitygraph/capability_graph.py`
- Create: `realitygraph/attack.py`
- Test: `tests/test_capability_algebra.py`

**Interfaces:**
- Produces: `FiniteCapability`, `CapabilityGraph`, `compose_capabilities(...)`, `AttackStatus`, `AttackEvidence`, `exhaustive_attack(...)`.

`FiniteCapability` stores finite input/output semantics plus `input_type`, `output_type`, guard inputs, certificate ID, dependency IDs, authority snapshot, verifier ID, provenance IDs, and cost.

- [ ] **Step 1: Write failing tests** for type-mismatched composition, correct composition, dependency-cycle rejection, missing-dependency inactivation, transitive invalidation after G1 ablation, G2-only ablation preserving G1, exhaustive attack survival, and attack-triggered revocation.

- [ ] **Step 2: Run focused tests and require failure**

Run: `python -m unittest tests.test_capability_algebra -v`
Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement finite capability composition**. For every guarded C1 input, C1 output must be a guarded C2 input; the composite table is evaluated explicitly and the composite dependencies are the union of both source IDs and their declared dependencies. Reject authority/verifier mismatch unless a separately supplied verifier callback certifies the bridge.

- [ ] **Step 4: Implement `CapabilityGraph`** with deterministic topological validation, `active_ids()`, `ablate(capability_id)` and dependency-closure invalidation. Ablation must not mutate unrelated branches.

- [ ] **Step 5: Implement exhaustive attack** comparing a capability to a frozen oracle table over an explicit challenge set and budget. Return `SURVIVE` only if every in-budget challenge passes; return `REVOKE` with the first deterministic counterexample on semantic failure; return `UNKNOWN_ATTACK` if budget is insufficient for the declared complete challenge set.

- [ ] **Step 6: Run focused tests and require pass**

Run: `python -m unittest tests.test_capability_algebra -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add realitygraph/capability.py realitygraph/capability_graph.py realitygraph/attack.py tests/test_capability_algebra.py
git commit -m "feat: add capability algebra and attacks"
```

### Task 4: Developmental router and bounded closure audit

**Files:**
- Create: `realitygraph/developmental_core.py`
- Create: `realitygraph/closure.py`
- Test: `tests/test_developmental_closure.py`

**Interfaces:**
- Consumes Tasks 1-3.
- Produces: `route_residual(...)`, `TerminalRecord`, `FrozenBoundary`, `ClosureCertificate`, `audit_closure(...)`.

- [ ] **Step 1: Write failing tests** proving route separation: `UnknownSearch` never returns EXPAND; `UnknownChoice` returns EVIDENCE; `UnknownIdentity` returns SPLIT; only a valid expressivity certificate returns EXPAND. Add closure tests for untyped failure rejection, unresolved expressivity rejection, typed unknown acceptance, invalid dependency rejection, and byte-exact certificate replay.

- [ ] **Step 2: Run focused tests and require failure**

Run: `python -m unittest tests.test_developmental_closure -v`
Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement router and closure certificate**. `audit_closure` receives the frozen boundary, terminal records, grammar deltas, capability graph, restart/ablation evidence IDs, and replay digest. It emits `CLOSED_BOUNDED` only when every manifest obligation has exactly one replayable terminal record and all structural admissions have restart + ablation evidence.

- [ ] **Step 4: Run focused tests and require pass**

Run: `python -m unittest tests.test_developmental_closure -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add realitygraph/developmental_core.py realitygraph/closure.py tests/test_developmental_closure.py
git commit -m "feat: add developmental routing and bounded closure"
```

### Task 5: Two-generation recursive observer-growth qualification

**Files:**
- Create: `realitygraph/fixtures/__init__.py`
- Create: `realitygraph/fixtures/boolean_observer_growth.py`
- Create: `realitygraph/fixtures/stateful_observer_growth.py`
- Create: `verified_language_growth_closure_v1.py`
- Test: `tests/test_verified_language_growth_closure.py`

**Interfaces:**
- Consumes all generic core interfaces.
- Produces: deterministic fixture manifests, G1/G2 candidates, `run_qualification() -> dict`, and result artifact `verified-language-growth-closure-v1-summary.json`.

- [ ] **Step 1: Write failing integration tests** for these gates:

```python
summary = run_qualification()
self.assertTrue(summary["passed"])
self.assertEqual(summary["verdict"], "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1")
self.assertTrue(summary["gates"]["g1_old_language_complete"])
self.assertTrue(summary["gates"]["g1_extensional_novelty"])
self.assertTrue(summary["gates"]["g2_depends_on_g1"])
self.assertTrue(summary["gates"]["g1_ablation_invalidates_g2"])
self.assertTrue(summary["gates"]["unknown_search_blocks_growth"])
self.assertTrue(summary["gates"]["unknown_choice_preserved"])
self.assertTrue(summary["gates"]["closed_bounded"])
```

- [ ] **Step 2: Run integration test and require failure**

Run: `python -m unittest tests.test_verified_language_growth_closure -v`
Expected: FAIL because fixture/runner do not exist.

- [ ] **Step 3: Implement G1 fixture**. Freeze the four-function old language over a declared `x`-only substrate (`0`, `1`, `x`, `not-x`) and the obligation separating `(x=0,y=0)` from `(x=0,y=1)`. Exhaustively certify the four extensional functions complete for that old substrate and certify no separator. Enumerate a lower NAND substrate over atoms `0,1,x,y` in deterministic increasing depth/size order; do not include a named target constructor. Require the selected novel constructor to separate the residual, verify its complete truth table, admit G1, restart, compose G1 with a retained bit-to-label decoder, exhaustively attack the composition, and show G1 ablation restores the old limitation.

- [ ] **Step 4: Implement G2 fixture**. Use histories whose present `(x,y)` is identical but whose prior G1 output differs. Exhaustively certify every stateless Boolean denotation over the present pair cannot separate the designated histories. Enumerate generic two-state Moore machines whose transition/output tables are encoded as finite tables and whose input signal is explicitly the admitted G1 constructor. Select the deterministic minimum-complexity two-state separator, verify it over the complete declared finite history carrier, admit G2 with `dependencies=(G1_ID,)`, restart both deltas, reuse on untouched histories with `grammar_search_calls == 0`, exhaustively attack, then test G1 transitive ablation and G2-only ablation.

- [ ] **Step 5: Implement route controls and closure**. Add an `UnknownSearch` budget fixture with no completeness certificate; an `UnknownChoice` fixture with two incomparable repairs and no selection evidence; stale authority/residual controls; extensionally duplicate/sham extension controls; and the final `ClosureCertificate` audit.

- [ ] **Step 6: Run qualification and full unit suite**

Run:

```bash
python -m unittest discover -s tests -v
python verified_language_growth_closure_v1.py
```

Expected: all tests PASS and final stdout contains `PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1`.

- [ ] **Step 7: Commit**

```bash
git add realitygraph/fixtures verified_language_growth_closure_v1.py tests/test_verified_language_growth_closure.py
git commit -m "feat: qualify recursive verified language growth"
```

### Task 6: CI evidence gate and public branch documentation

**Files:**
- Create: `.github/workflows/verified-language-growth-closure-v1.yml`
- Modify: `README.md`

**Interfaces:**
- CI artifact: `verified-language-growth-closure-v1-summary.json`.

- [ ] **Step 1: Add dedicated branch workflow** triggered on pushes to `verified-language-growth-closure-v1` and manual dispatch. Use Python 3.12; run the four focused new test modules, full unittest discovery, then `python verified_language_growth_closure_v1.py`; upload the JSON summary with `if-no-files-found: error`.

- [ ] **Step 2: Add a bounded README section** stating exactly what the branch proves and explicitly excluding open-ended/unbounded self-development claims.

- [ ] **Step 3: Push/observe CI and diagnose any failure**. Fetch the workflow run/job logs, fix root causes, and rerun until the dedicated gate is green.

- [ ] **Step 4: Final verification**

Require all of:

```text
PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1
G1 extensional novelty = true
G2 explicit dependency on G1 = true
G1 ablation invalidates G2 = true
UnknownSearch cannot EXPAND = true
UnknownChoice remains unselected without evidence = true
CLOSED_BOUNDED = true
```

- [ ] **Step 5: Commit final docs/CI changes**

```bash
git add .github/workflows/verified-language-growth-closure-v1.yml README.md
git commit -m "ci: gate verified language-growth closure"
```

## Plan self-review

- Spec coverage: typed residuals, grammar growth, deltas, capability algebra, attacks, disagreement/search controls, recursive G1→G2 dependency, restart, ablation, closure, negative controls, and CI evidence are all assigned to tasks.
- No placeholders: every task names files, interfaces, test commands, and pass/fail expectations.
- Type consistency: `ResidualCertificate` is imported from `realitygraph.residual_certificate` to avoid colliding with the existing predictive `realitygraph.residual.ResidualCertificate`; the top-level package export need not change until qualification is stable.
- Scope: the implementation remains one bounded generic subsystem plus deterministic fixtures; no Parkinson/ACC domain code enters the core.
