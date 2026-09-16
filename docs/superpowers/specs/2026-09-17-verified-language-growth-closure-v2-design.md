# Verified Language-Growth Closure v2 — Generic Recursive Developmental Executor

Date: 2026-09-17
Branch: `verified-language-growth-closure-v2`
Base: `81477f74a3855b047c04c5c3bcc76504d65bbeb6` (`verified-language-growth-closure-v1`, fully green)

## Goal

Remove the strongest remaining objection to v1: v1 proves a genuine verified G1 -> G2 recursive language-growth edge, but each generation is still orchestrated by a generation-specific fixture function.

V2 must show that one generic developmental executor can repeatedly take a frozen finite generation specification and current retained state, classify the residual lawfully, certify expressive inadequacy only when completeness plus no-resolution are established, grow the language minimally from a declared lower substrate, compile and attack the resulting capability, persist it, restart exactly, and begin the next generation from the changed present.

The decisive qualification is three generations:

```text
G0 state
  -> generic executor -> G1
G1 state
  -> same executor    -> G2, explicitly dependent on G1
G2 state
  -> same executor    -> G3, explicitly dependent on G2
```

No generation-specific branch may exist in the executor.

The bounded scientific verdict is:

```text
PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2
```

V2 does **not** claim open-ended or unbounded self-development. It establishes bounded depth-3 recursive development under frozen finite substrates, verifier authority, protected consequences, and resource envelopes.

## V1 baseline inherited unchanged

V2 starts from the verified v1 core and preserves all v1 guarantees:

- typed residual family;
- `UnknownExpressivity` constructible only from `Complete + NoResolution`;
- stale/authority-mismatched certificate rejection;
- extensionally novel grammar deltas;
- independent verification;
- exact restart and ablation;
- typed capability DAG and transitive invalidation;
- bounded exhaustive attacks;
- `UnknownSearch` cannot EXPAND;
- `UnknownChoice` cannot be silently selected;
- replayable `CLOSED_BOUNDED` certificate;
- explicit exclusion of open-ended closure.

V2 changes orchestration, not the trust boundary.

## Central thesis

The developmental loop itself must become a reusable capability.

Instead of fixture code doing this:

```text
build_g1()
build_g2(g1)
build_g3(g2)
```

V2 introduces one generic transition:

```text
execute_generation(state, generation_spec) -> GenerationResult
```

The `GenerationSpec` supplies only the frozen problem boundary and adapters. It does not decide which residual type occurred, which candidate should be retained, whether growth is licensed, whether restart succeeded, whether an attack survived, or whether downstream dependency invalidation is causal. Those are executor responsibilities.

## Architecture

### 1. DevelopmentalState

Introduce one canonical persistent state:

```text
DevelopmentalState
  generation_index
  grammar
  capability_graph
  admitted_deltas
  terminal_records
  authority_snapshot
  protected_consequence_digest
  provenance_ids
  state_digest
```

State is immutable-by-transition: `execute_generation` returns a new state rather than mutating the input in place.

The digest is canonical and covers all consequential fields.

### 2. GenerationSpec

A generation is data plus explicit adapters:

```text
GenerationSpec
  generation_id
  obligation_id
  input_type
  output_type
  current_language_adapter
  lower_substrate_adapter
  verifier_adapter
  attack_adapter
  acquisition_manifest
  growth_manifest
  future_manifest
  resource_envelope
  authority_snapshot
  protected_consequences
  required_dependency_ids
```

The spec may define a finite domain adapter, but it may not contain a hand-written selected constructor or a generation-specific control-flow hook.

All manifests and adapter identities are hashed before decisive future evaluation.

### 3. CurrentLanguageAdapter

Protocol:

```text
enumerate_current(state, spec) -> LanguageEnumeration
```

where:

```text
LanguageEnumeration
  complete: bool
  constructors/signatures
  carrier_digest
  enumeration_digest
  replay_evidence
  search_exhausted: bool
```

Only `complete=True` may produce a `CompletenessCertificate`.

A budget stop or partial enumeration produces `UnknownSearch`, never `UnknownExpressivity`.

### 4. LowerSubstrateAdapter

Protocol:

```text
enumerate_candidates(state, residual, spec) -> CandidateEnumeration
```

The adapter declares the lower substrate and produces candidates in a deterministic canonical order.

Candidates may depend on already-earned constructors/capabilities through explicit IDs. Missing or inactive dependencies reject admission.

The adapter cannot admit anything. Admission remains in the generic executor through the existing grammar-growth gates.

### 5. VerifierAdapter

Protocol:

```text
classify_obligation(...)
verify_candidate(...)
verify_future(...)
verify_protected_consequences(...)
```

Proposal and authority remain separate. The executor never treats adapter proposal output as proof.

### 6. AttackAdapter

Protocol:

```text
attack_space(state, capability, spec) -> finite challenges
oracle(challenge) -> protected consequence
```

The executor runs the attack and records `SURVIVE / NARROW_SCOPE / REVOKE / UNKNOWN_ATTACK` using the generic attack semantics inherited from v1.

## Generic executor transition

`execute_generation` performs the same ordered protocol for every generation:

```text
1. Validate state/spec authority and frozen manifests.
2. Attempt REUSE from the active capability DAG.
3. If unresolved, enumerate the declared current language.
4. If enumeration is incomplete -> UnknownSearch; structural growth forbidden.
5. If complete and a current constructor resolves the obligation -> Authorized/Compiled reuse.
6. If complete and none resolves -> emit NoResolution.
7. Build ResidualCertificate -> UnknownExpressivity.
8. Enumerate the declared lower substrate in canonical order.
9. Apply v1 admission gates:
     license
     extensional novelty
     adequacy
     preservation
     minimality
     replayability
     independent verification
     ablatability
10. Admit exactly one justified GrammarDelta, or preserve UnknownChoice / NamedObstruction as required.
11. Compile retained capability with explicit dependencies.
12. Add capability to the DAG and validate acyclicity/dependency closure.
13. Serialize and reconstruct the new state exactly.
14. Run the bounded attack.
15. Evaluate sealed future obligations with zero new grammar search.
16. Emit terminal record and new DevelopmentalState.
```

No branch may test `generation_id`, fixture class, constructor name, G1/G2/G3 label, or semantic target name.

## Executor trace

Every run emits a canonical transition trace:

```text
GenerationTrace
  generation_id
  state_before_digest
  spec_digest
  route
  completeness_digest | null
  no_resolution_digest | null
  residual_digest | null
  candidate_enumeration_digest | null
  admitted_delta_id | null
  retained_capability_id | null
  restart_digest
  attack_digest
  future_evidence_digest
  state_after_digest
```

This is both replay evidence and a way to prove that the same executor protocol produced all generations.

## Persistent snapshot and cold restart

Introduce canonical state serialization:

```text
DevelopmentalSnapshot
  grammar_text
  capability_graph_text
  delta_texts
  terminal_record_texts
  authority_snapshot
  protected_consequence_digest
  generation_index
  snapshot_digest
```

Cold restart must reconstruct the exact active semantics and dependency graph **without calling generation candidate enumerators again**.

Required equality after restart:

```text
snapshot_text_before == snapshot_text_after
state_digest_before == state_digest_after
active_capability_ids_before == active_capability_ids_after
active_constructor_ids_before == active_constructor_ids_after
```

## Three-generation qualification

### G1 — inherited Boolean observer growth

Use the v1 Boolean fixture as a `GenerationSpec`, not `build_g1()` orchestration.

Frozen current language:

```text
all four Boolean functions of x
```

Declared lower substrate:

```text
atoms {0,1,x,y} + NAND composition by canonical depth
```

Required result:

```text
nand-d3-0110
```

The constructor name is not supplied as a target; the verifier specifies the required consequence/semantic constraint. Selection arises from canonical candidate enumeration plus generic admission.

G1 must retain all v1 gates: completeness, no-resolution, novelty, verification, restart, composition, attack, future zero-search reuse, and ablation.

### G2 — inherited stateful observer growth

Express the v1 history fixture as a second `GenerationSpec`.

Frozen current language:

```text
complete declared stateless present-observer class
```

Declared lower substrate:

```text
generic two-state Moore machines over the earned G1 signal
```

Required result is whichever minimal verified machine the canonical enumeration earns. Its constructor/capability must explicitly depend on the admitted G1 constructor/capability.

The executor must produce G2 without any G2-specific control flow.

### G3 — three-state temporal observer growth

Add a third finite fixture whose purpose is to prove a second recursive structural edge.

Input signal:

```text
output of the earned G2 capability
```

Frozen current language:

```text
all canonical two-state binary-input Moore machines,
quotiented by denotation over the complete frozen sequence carrier
```

Frozen carrier:

```text
all binary signal sequences of lengths 0..4
```

Protected target consequence:

```text
1 iff the G2-output sequence has contained two consecutive 1 values;
0 otherwise
```

The fixture must first exhaustively confirm that no two-state Moore machine realizes this consequence over the frozen carrier. If that empirical premise is false, the fixture must fail and be redesigned rather than weakening completeness or silently changing the target.

Declared lower substrate:

```text
all canonical three-state binary-input Moore machines
```

Raw bounded space before extensional quotienting is finite:

```text
3^(3*2) transition tables * 2^3 output tables = 5,832 machines
```

The candidate must explicitly depend on G2 as its input-signal capability. The executor must synthesize a verified three-state observer, retain it as G3, restart it exactly, attack it over the complete frozen sequence carrier, and reuse it on sealed future sequences with zero grammar search.

The chosen semantic target is intentionally a standard finite-state property so the lower-bound claim can be exhaustively checked rather than argued heuristically.

## Recursive-edge causal gates

The qualification must establish the dependency chain:

```text
G1 -> G2 -> G3
```

and the following exact ablations:

```text
ablate G1 -> G1,G2,G3 inactive
ablate G2 -> G1 active; G2,G3 inactive
ablate G3 -> G1,G2 active; G3 inactive
```

Grammar deltas must obey the same causal pattern for constructors.

No descendant may remain active when an explicit dependency has been removed.

## Same-executor proof

The scientific qualification must demonstrate all of:

1. G1, G2, and G3 invoke the same public `execute_generation` entry point.
2. The executor module imports no qualification fixture modules.
3. The executor contains no generation-name or constructor-name dispatch.
4. Each generation's `GenerationTrace` has the same protocol schema.
5. The only generation-specific material is contained in `GenerationSpec` adapters/data.
6. Reordering spec registration does not change an individual generation result when starting from the same required state snapshot.

This is the main delta from v1.

## Route controls retained

V2 must retain v1 negative/control fixtures under the generic executor boundary:

- incomplete current-language enumeration -> `UnknownSearch`, no EXPAND;
- exact multiple incomparable lawful repairs without selection evidence -> `UnknownChoice`;
- stale residual -> rejected;
- authority mismatch -> rejected;
- extensionally duplicate candidate -> rejected;
- sham candidate -> rejected;
- broken/missing dependency -> rejected;
- attack counterexample -> narrow/revoke implicated capability only;
- unsupported candidate outside declared substrate -> rejected;
- verifier exception -> apparatus failure, not truth/falsity.

## Closure semantics

V2 closure is parameterized by the frozen three-generation programme boundary:

```text
BoundaryV2
  initial_state_digest
  generation_spec_digests = [G1,G2,G3]
  authority_snapshot
  protected_consequence_digest
  resource_envelopes
  final_state_digest
```

`CLOSED_BOUNDED_DEPTH3` requires:

- all three generation traces replay;
- every structural growth event has complete + no-resolution evidence;
- every admitted delta has restart, attack, future, and ablation evidence;
- the final snapshot cold-restarts exactly;
- dependency DAG and grammar-delta lineage are acyclic and intact;
- route controls remain typed;
- no untyped failure remains inside the frozen programme manifest.

For compatibility with v1 `ClosureCertificate`, the artifact may carry both:

```text
status = CLOSED_BOUNDED
qualification_depth = 3
```

The human-facing scientific label is `CLOSED_BOUNDED_DEPTH3`.

## Required modules

Keep the v1 modules stable where possible. Add focused orchestration modules:

```text
realitygraph/developmental_executor.py
realitygraph/developmental_state.py
realitygraph/generation_spec.py
realitygraph/developmental_snapshot.py
```

Add fixture adapters outside the core:

```text
realitygraph/fixtures/generation_specs_v2.py
realitygraph/fixtures/three_state_observer_growth.py
```

Add qualification executable:

```text
verified_language_growth_closure_v2.py
```

Add tests:

```text
tests/test_developmental_executor.py
tests/test_developmental_snapshot.py
tests/test_three_state_observer_growth.py
tests/test_verified_language_growth_closure_v2.py
```

The executor and state modules must not import anything from `realitygraph.fixtures`.

## Scientific qualification sequence

The branch passes only when one sealed run demonstrates:

```text
initial state
-> execute_generation(G1 spec)
-> G1 compiled and attacked
-> exact restart
-> execute_generation(G2 spec)
-> G2 compiled with explicit G1 dependency
-> exact restart
-> execute_generation(G3 spec)
-> G3 compiled with explicit G2 dependency
-> exact full-state cold restart
-> sealed future zero-search reuse for all three generations
-> complete attacks
-> causal G3-only ablation
-> causal G2 ablation
-> causal G1 ablation
-> retained UnknownSearch / UnknownChoice controls
-> closure audit
-> CLOSED_BOUNDED_DEPTH3
```

## Required pass gates

At minimum:

```text
gate_same_executor_g1_g2_g3
gate_executor_has_no_fixture_imports
gate_executor_has_no_generation_dispatch

gate_g1_complete
gate_g1_no_resolution
gate_g1_novel
gate_g1_restart_exact
gate_g1_attack_survives
gate_g1_future_zero_search

gate_g2_complete
gate_g2_no_resolution
gate_g2_novel
gate_g2_depends_on_g1
gate_g2_restart_exact
gate_g2_attack_survives
gate_g2_future_zero_search

gate_g3_two_state_language_complete
gate_g3_two_state_no_resolution
gate_g3_three_state_novel
gate_g3_depends_on_g2
gate_g3_restart_exact
gate_g3_attack_survives
gate_g3_future_zero_search

gate_full_snapshot_restart_exact
gate_g1_ablation_invalidates_g2_g3
gate_g2_ablation_invalidates_g3_preserves_g1
gate_g3_ablation_preserves_g1_g2

gate_unknown_search_blocks_growth
gate_unknown_choice_preserved
gate_stale_certificate_rejected
gate_sham_extension_rejected

gate_closed_bounded_depth3
```

## CI evidence

Dedicated branch workflow:

```text
.github/workflows/verified-language-growth-closure-v2.yml
```

It must run:

1. focused v2 unit tests;
2. inherited v1 focused tests;
3. the complete repository unittest suite;
4. `python verified_language_growth_closure_v2.py`;
5. exact verdict grep;
6. JSON gate assertions;
7. artifact upload with `if-no-files-found: error`.

Evidence artifact:

```text
verified-language-growth-closure-v2-summary.json
verified-language-growth-closure-v2.log
```

The JSON must include all spec/state/trace/delta/capability/attack/restart/ablation/closure digests needed to replay the bounded claim.

## Failure policy

Fail closed.

- If the G3 target is realizable by a two-state machine on the frozen carrier, V2 is `NEGATIVE_FIXTURE` until the fixture is redesigned. Do not fake an expressivity residual.
- If current-language enumeration is partial, classify `UnknownSearch`.
- If multiple incomparable minimal growth candidates survive and no independent selection evidence exists, preserve `UnknownChoice`.
- If restart differs by one consequential byte/digest, fail qualification.
- If an ablated ancestor leaves a dependent descendant active, fail qualification.
- If future evaluation invokes candidate enumeration, fail the zero-search gate.
- If the executor imports fixture modules or dispatches on generation identity, fail the same-executor gate.
- CI green without the exact scientific verdict is not a scientific pass.

## Non-goals

Do not claim:

- open-ended autonomous recursive improvement;
- unbounded generation count;
- autonomous invention of verifier authority or terminal values;
- a universal lowest substrate;
- universal optimal synthesis;
- cross-domain generality merely from the three finite fixtures;
- that bounded attack survival implies universal truth;
- that `CLOSED_BOUNDED_DEPTH3` closes anything outside the frozen manifests/substrates/resources.

## Expected bounded claim

If successful, V2 establishes:

> Given an initial verified developmental state and a finite ordered sequence of frozen generation specifications, one generic RealityGraph developmental executor can repeatedly distinguish reuse, search incompleteness, choice ambiguity, and certified expressive inadequacy; synthesize and independently verify minimal extensionally novel language growth only when licensed; retain the resulting capability with explicit dependencies; restart, attack, and prospectively reuse it; use earned capabilities as substrate dependencies for later generations; preserve causal invalidation under ancestor ablation; and emit a replayable bounded depth-3 closure certificate — without generation-specific control flow in the executor.

This removes the principal orchestration objection left by v1 while retaining the explicit boundary against open-ended self-development.