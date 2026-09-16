# Verified Language-Growth Closure v1 — Design

Date: 2026-09-17
Branch: `verified-language-growth-closure-v1`
Base: `capability-selective-representation-v4`

## Goal

Build one generic RealityGraph developmental core that can detect when its current effective language is provably insufficient, synthesize the smallest lawful extension from a declared lower substrate, promote only independently verified improvements, compose retained capabilities, actively seek counterexamples, recursively use earned constructors in later growth, and terminate a bounded generation with a machine-checkable closure certificate.

The system must preserve the constitutional discipline of *The Boundary Learns*: proposal, authority, and permission to modify remain separate; `UNKNOWN` is preserved whenever evidence does not license a transition; search failure alone never authorizes language growth.

The qualification target is a full bounded end-to-end demonstration, not merely implementation of interfaces.

## Scope

This branch is generic. Existing Parkinson, ACC, `meta-100x-v1`, predictive/residual, and selective-representation branches remain evidence/source branches. Their domain-specific experiment code is not merged into the generic core.

The branch may port or re-express only abstract mechanisms that already proved useful:

- typed residual routing and selective representation from `capability-selective-representation-v4`;
- recursive policy/self-compilation ideas from `meta-100x-v1`;
- representation-program generation and residual-conditioned expansion patterns from `parkinson-representation-genesis-v1`;
- exact proof/obstruction and verifier discipline from the ACC branches;
- restart, ablation, provenance, and retained-capability machinery already present in RealityGraph.

This branch does **not** claim open-ended autonomous invention, unbounded self-development, a universal least repair, or removal of external verifier/resource boundaries.

## Constitutional model

The active developmental state is:

```text
Omega_t = (E_t, Gamma_t, C_t, Pi_t, H_t)
```

where:

- `E_t` — active consequential distinctions / current observational quotient;
- `Gamma_t` — effective constructor and experiment language;
- `C_t` — retained executable capabilities;
- `Pi_t` — developmental selection, trust, budget, and invocation policy;
- `H_t` — immutable evidence/provenance needed for replay, audit, dependency tracking, and revocation.

Protected consequences and verifier authority remain external constraints and are frozen into an authority snapshot for each decisive qualification.

## Typed result family

Every obligation terminates in exactly one typed result:

```text
Authorized
Compiled
Refuted
UnknownIdentity
UnknownChoice
UnknownSearch
UnknownExpressivity
NamedObstruction
```

`Compiled` means a licensed structural change was independently verified and admitted into active state. It is distinct from `Authorized`, which means the current active state already sufficed without structural growth.

`UnknownExpressivity` is constructible only from both:

```text
Complete(Gamma_t, substrate_scope)
NoResolution(Gamma_t, residual)
```

A timeout, heuristic failure, budget exhaustion, or missed candidate can only produce `UnknownSearch` unless a separate completeness certificate exists.

`NamedObstruction` is a bounded terminal result for a generation when the obstruction is exact and replayable but no lawful extension is available inside the declared lower substrate/resource boundary.

## Residual Certificate

Introduce `ResidualCertificate` as the only object that can license EXPAND.

Required fields:

```text
ResidualCertificate
  obligation_id
  state_digest
  authority_snapshot
  language_id
  substrate_id
  protected_consequences
  residual_type
  observational_equivalence
  unresolved_pairs_or_obligations
  completeness_certificate
  no_resolution_certificate
  necessary_constraints     # K(rho)
  candidate_version_space_digest
  replay_evidence
```

The certificate states not merely that the system failed, but exactly what the complete current language cannot distinguish, construct, or resolve.

For `UnknownChoice`, the residual must instead identify the still-lawful alternatives and their disagreement region. `UnknownChoice` never licenses arbitrary grammar expansion.

For `UnknownIdentity`, the residual must identify the protected consequence that separates states currently collapsed by `E_t`; the lawful response is SPLIT.

## Grammar Grower

Introduce a generic `GrammarGrower` that receives:

```text
(residual_certificate, current_language, lower_substrate, provenance)
```

and enumerates/synthesizes candidate constructors from the declared lower substrate.

The generic growth pipeline is:

```text
atoms
  -> compose
  -> parameterize
  -> canonicalize
  -> quotient extensionally equivalent candidates
  -> test against K(rho)
  -> backward-delete unnecessary structure
  -> verify
  -> replay
```

No domain-specific constructor name is privileged by the core.

Candidate constructors are evaluated under a deterministic complexity order. Search may use heuristics, learned ranking, or a proposer model, but promotion depends only on the declared verifier and admission constitution.

### Candidate admission gates

A constructor is promotable only if all gates pass:

1. **Licensed growth** — the exact `ResidualCertificate` authorizes EXPAND.
2. **Extensional novelty** — the candidate is not behaviorally equivalent to any existing constructor over the certified old-language scope.
3. **Adequacy** — it resolves at least one certified unresolved obligation in `K(rho)`.
4. **Preservation** — all protected prior consequences remain unchanged or improve under the declared order.
5. **Minimality** — removing any newly introduced component destroys adequacy or violates preservation, up to declared behavioral quotienting.
6. **Replayability** — the candidate and its evidence reconstruct exactly from immutable provenance.
7. **Independent verification** — proposer output never self-authorizes.
8. **Ablatability** — the admitted delta has an exact dependency and revocation handle.

## Grammar Delta

A successful language extension is stored as a typed `GrammarDelta` rather than arbitrary code:

```text
GrammarDelta
  delta_id
  parent_language_id
  child_language_id
  added_constructors
  semantic_contracts
  primitive_expansions
  applicability_guards
  verifier_bindings
  dependency_ids
  authority_snapshot
  provenance_ids
  ablation_handle
```

Applying the delta yields `Gamma_(t+1)`.

Every admitted constructor becomes an atom available to later `GrammarGrower` generations. This is the recursive edge required for verified grammar growth:

```text
Gamma_t -> verified new constructor -> Gamma_(t+1)
Gamma_(t+1) -> larger lawful invention space -> Gamma_(t+2)
```

The qualification must demonstrate this edge at least once: a second admitted constructor must depend semantically on a constructor earned in the first growth generation.

## Capability algebra

Introduce one generic semantic wrapper:

```text
Capability[A, B]
  capability_id
  input_type
  output_type
  applicability_guard
  execute
  semantic_contract
  verifier_binding
  certificate_id
  dependencies
  provenance
  cost_model
  protected_scope
  ablation_handle
  status
```

This type covers retained predictors, experiment generators, search macros, adapters, recurrence schemas, proof lemmas, representation operators, controllers, and compiled composite procedures.

### Composition

Given:

```text
C1 : A -> B
C2 : B -> C
```

RealityGraph may propose `C2 o C1 : A -> C` only when interface types match.

Promotion additionally requires:

- both applicability guards hold in sequence;
- both certificates replay;
- dependency closure is intact;
- protected consequences are preserved;
- the composed semantic contract is independently checked;
- cost accounting includes composition overhead.

Composition produces a capability DAG, not silent inlining.

### CONTRACT

When a verified capability path is repeatedly used, CONTRACT may compile it into a smaller persistent composite capability only if behavioral parity with the expanded path is replay-verified over the declared protected scope.

The expanded dependency path remains in provenance for audit and revocation.

## Active falsification

Every retained capability gets a generic attack interface:

```text
Attack(C, attack_space, budget, authority) -> ChallengeSet
```

The attacker seeks the cheapest admissible challenge likely to violate the capability's semantic contract.

The core treats domain-specific attack generation as an adapter, but the result accounting is generic:

```text
SURVIVE
NARROW_SCOPE
REVOKE
UNKNOWN_ATTACK
```

A surviving capability earns broader evidence, not universal truth. A successful attack revokes or narrows only the implicated capability and downstream dependents.

Examples of adapters include countermodel search, distinguishing continuations, worst-group natural environments, guard-boundary search, and primitive replay attacks.

## Disagreement-driven experiment generation

For an `UnknownChoice` residual with lawful candidates `C_1 ... C_n`, construct the disagreement region:

```text
D = {x | exists i,j. C_i(x) != C_j(x)}
```

The experiment selector chooses an admissible challenge maximizing expected discrimination per cost under the frozen authority/resource boundary.

Future outcomes may SELECT or REVOKE lawful candidates. They do not retroactively change the frozen candidate-generation process.

This generalizes the existing value-evidence separator pattern into a generic evidence-growth mechanism.

## Route semantics

Residual classes have distinct lawful responses:

```text
UnknownIdentity      -> SPLIT
UnknownChoice        -> generate separating evidence -> SELECT / REVOKE
UnknownSearch        -> search/backoff/reorder only; no structural mutation
UnknownExpressivity  -> EXPAND from declared lower substrate
NamedObstruction     -> stop this bounded generation with exact obstruction
Authorized           -> REUSE / persist / compose as licensed
Compiled             -> persist / compose / attack / prospective reuse
Refuted              -> record counterexample and revoke affected claims
```

No route may be silently coerced into another.

## Bounded Closure Certificate

Introduce `ClosureCertificate` parameterized by a frozen boundary:

```text
Boundary
  world_manifest_digest
  language_digest
  substrate_digest
  verifier_digest
  protected_consequence_digest
  resource_envelope
```

A generation is `CLOSED_BOUNDED` iff every obligation in the frozen manifest has a replayable terminal classification in:

```text
AUTHORIZED
COMPILED
REFUTED
NAMED_OBSTRUCTION
TYPED_UNKNOWN
```

and all of the following hold:

1. no untyped failure remains;
2. every `UnknownExpressivity` either produced an admitted `GrammarDelta` or was converted to an exact `NamedObstruction` because the declared lower substrate/resource boundary was itself exhausted;
3. every admitted delta has preservation, restart, and ablation evidence;
4. every retained capability has a valid dependency DAG and authority snapshot;
5. every `UnknownChoice` records the surviving lawful version space and why the current evidence cannot select among it;
6. every `UnknownSearch` records why completeness is absent and therefore why growth is forbidden;
7. replay from immutable provenance reproduces the same terminal classifications.

`CLOSED_BOUNDED` says nothing about worlds, constructors, attacks, or resources outside the frozen boundary.

## Qualification fixture: recursive finite observer growth

The primary scientific fixture is a finite, fully exhaustible observer-development world chosen because it lets every expressivity and novelty claim be proved exactly.

It has two growth generations.

### Generation 0: stateless observer-language growth

The initial observer language contains the frozen old constant/unary Boolean observations used by the earlier experiment-language programme. The lower substrate contains only the declared Boolean atoms and NAND composition.

The frozen obligation includes at least one pair that the complete old observer language cannot separate.

The qualification must:

1. exhaustively enumerate the old language and emit `Complete`;
2. exhaustively prove no old observer resolves the residual and emit `NoResolution`;
3. construct a `ResidualCertificate`;
4. synthesize an XOR-equivalent observer from the NAND substrate without naming XOR as a primitive target constructor;
5. prove extensional novelty against every old observer;
6. independently verify the new observer over the full finite input carrier;
7. admit it as `GrammarDelta G1`;
8. serialize/restart and reproduce its denotation exactly;
9. compose it with an already-retained consequence decoder to form a verified composite capability;
10. exhaustively attack the composite over the full finite attack space;
11. ablate G1 and restore the old inability to resolve the designated obligation.

### Generation 1: stateful observer-meta-substrate growth

The second frozen obligation presents histories that remain indistinguishable to every stateless observer in the declared complete stateless substrate but require different protected outcomes.

The lower substrate is a generic finite-machine constructor space. It is not given a named history, delay, memory, or stateful separator primitive.

The second generation must:

1. exhaustively certify the declared stateless substrate complete for its bounded carrier;
2. prove no stateless observer resolves the history residual;
3. build a second `ResidualCertificate`;
4. synthesize a two-state observer from the generic finite-machine substrate;
5. require the candidate's transition/output program to use the G1 observer as an admitted atom, thereby proving the earlier grammar delta changed the later invention space;
6. verify the stateful observer over the complete bounded history carrier;
7. admit it as `GrammarDelta G2` with an explicit dependency on G1;
8. restart and replay the two-delta grammar exactly;
9. demonstrate untouched future reuse of G2 with zero grammar search;
10. attack G2 over the complete declared finite history space;
11. ablate G1 and require G2 to become invalid through dependency closure;
12. restore G1 but ablate G2 and require only the stateful gain to disappear.

This two-generation fixture is the decisive recursive-growth qualification. It establishes that an earned constructor can become part of the substrate from which a later constructor is synthesized.

## Secondary route-control fixtures

### UnknownChoice fixture

Use a finite repair space with multiple incomparable minimal lawful repairs. Exhaustively certify the candidate set and preserve `UnknownChoice` until an independently frozen disagreement experiment supplies selection authority.

A sham or ablated evidence stream must restore `UnknownChoice`.

### UnknownSearch fixture

Use an intentionally incomplete syntactic search with a strict budget. Exhaustion of that budget must yield `UnknownSearch`. The absence of a completeness certificate must make construction of `UnknownExpressivity` impossible.

## Full bounded qualification protocol

The scientific qualification must be sealed before decisive future evaluation.

### Partitions

Use three deterministic partitions where applicable:

- **Acquisition** — retain baseline capabilities and any search ranking needed only for efficiency;
- **Growth calibration** — choose residual-compatible candidate ordering and freeze growth policy;
- **Future** — untouched obligations used only after grammar/policy freeze.

The finite observer fixture additionally uses complete exhaustive truth-table/history carriers for semantic proof; the prospective split governs which obligations are allowed to influence candidate selection.

Split logic and manifests must be frozen into digests before future outcomes are loaded.

### Required causal sequence

The qualification passes only if the complete run demonstrates all of:

1. baseline REUSE on at least one obligation;
2. exact old-language exhaustion on at least one obligation;
3. separate completeness and no-resolution certificates;
4. licensed `UnknownExpressivity`;
5. extensionally novel G1 constructor from a lower substrate;
6. independent semantic verification of G1;
7. exact restart of G1;
8. prospective reuse of G1 without repeating grammar search;
9. verified composition of G1 with a retained capability;
10. active attack evidence for G1/composite;
11. causal G1 ablation;
12. second exact expressivity residual after G1;
13. extensionally novel G2 constructor whose implementation depends on G1;
14. independent semantic verification of G2;
15. exact two-generation restart;
16. untouched future reuse of G2 without grammar search;
17. dependency-aware G1/G2 ablations;
18. `UnknownChoice` control that refuses arbitrary repair selection;
19. `UnknownSearch` control that refuses structural growth;
20. stale/mismatched residual and authority certificates rejected;
21. sham extension rejected;
22. final frozen manifest receives a valid `ClosureCertificate`.

### Negative controls

The qualification must include:

- incomplete-language control: missing completeness certificate blocks EXPAND;
- existing-separator control: if the old language already resolves the residual, growth is blocked;
- stale-certificate control;
- authority-snapshot mismatch control;
- extensionally duplicate constructor control;
- sham constructor control;
- broken dependency/composition control;
- G1 ablation invalidates G2 dependency;
- G2-only ablation preserves G1 behavior;
- budget exhaustion produces `UnknownSearch`, not `UnknownExpressivity`;
- unresolved non-canonical repair produces `UnknownChoice`, not arbitrary selection.

## Implementation boundaries

Create focused modules rather than one large runtime:

```text
realitygraph/developmental_types.py
realitygraph/residual_certificate.py
realitygraph/grammar.py
realitygraph/grammar_growth.py
realitygraph/capability.py
realitygraph/capability_graph.py
realitygraph/attack.py
realitygraph/closure.py
realitygraph/developmental_core.py
```

Add qualification adapters/fixtures outside the core:

```text
verified_language_growth_closure_v1.py
realitygraph/fixtures/boolean_observer_growth.py
realitygraph/fixtures/stateful_observer_growth.py
```

Keep existing `mg.py`, ledger/provenance, retained capability, and verifier adapters where compatible.

The generic core must not import Parkinson- or ACC-specific modules.

Domain adapters live outside the core and satisfy explicit protocols.

## Data flow

```text
obligation
  -> attempt with current Capability DAG
  -> external verify
  -> terminal success/refutation OR typed residual
  -> diagnose weakest lawful residual class
  -> if Identity: SPLIT
  -> if Choice: disagreement experiment
  -> if Search: search/backoff only
  -> if Expressivity: require Complete + NoResolution
  -> build ResidualCertificate
  -> GrammarGrower(lower substrate)
  -> canonicalize / quotient candidates
  -> verify novelty + adequacy + preservation + minimality
  -> admit GrammarDelta
  -> construct/compose Capability
  -> restart
  -> attack
  -> prospective future reuse
  -> later residual may use admitted constructor as substrate atom
  -> ablate causal source / dependency closure
  -> closure audit
  -> ClosureCertificate or typed remaining boundary
```

## Error handling and anti-drift

The core must fail closed.

- malformed or missing certificates -> typed `UNKNOWN`, never implicit admission;
- verifier exception -> apparatus failure, never evidence of truth/falsity;
- hash/provenance mismatch -> hard qualification failure;
- nondeterministic candidate order -> hard failure unless randomness is explicitly seeded and recorded;
- stale authority snapshot -> reject transition;
- dependency cycle -> reject capability graph;
- replay mismatch -> revoke the affected admission and fail qualification;
- unsupported constructor outside declared substrate -> reject candidate rather than widening the substrate silently;
- downstream capability with missing dependency -> inactive/invalid, never silently retained.

Scientific result strings must distinguish `PASS`, `PARTIAL`, `NEGATIVE`, and `UNKNOWN`; CI success alone is never treated as a scientific pass.

## Testing strategy

### Unit tests

Cover:

- residual constructor invariants;
- inability to create `UnknownExpressivity` without both certificates;
- grammar canonicalization and extensional duplicate deletion;
- minimality deletion;
- grammar-delta dependency recording;
- capability composition guards and dependency closure;
- transitive invalidation after dependency ablation;
- attack outcomes and selective revocation;
- closure audit classification;
- serialization/restart round trip;
- stale/mismatched certificate rejection.

### Property/exhaustive tests

For the finite observer fixtures:

- exhaustively enumerate the old stateless observer language;
- exhaustively establish old-language no-resolution;
- exhaustively quotient candidate constructors under their declared behavioral carrier;
- exhaustively verify G1 denotation over all Boolean inputs;
- exhaustively verify G2 over the declared finite history carrier;
- exhaustively attack admitted semantic contracts inside the declared fixture boundaries.

### Integration tests

One deterministic integration run must exercise:

```text
REUSE
-> UnknownExpressivity
-> certified EXPAND
-> COMPILED G1
-> composition
-> restart reuse
-> attack
-> later UnknownExpressivity
-> certified EXPAND using G1 as substrate atom
-> COMPILED G2
-> two-generation restart
-> dependency ablation
-> CLOSED_BOUNDED
```

A second fixture must terminate in `UnknownChoice` before independent evidence and then SELECT only after the frozen disagreement experiment.

A third fixture must terminate in `UnknownSearch` after budget exhaustion and prove that no language-growth constructor is reachable from that result type.

## Success criteria

The branch is complete when all of the following are true:

- generic core modules contain no domain-specific imports;
- all unit/property/integration tests pass;
- the old language is exhaustively certified complete in both expressivity-growth stages;
- old-language impossibility is exact, not inferred from budget exhaustion;
- G1 is extensionally novel and synthesized from the lower Boolean substrate;
- G2 is extensionally novel and synthesized from the lower finite-machine substrate;
- G2 has an explicit semantic/dependency edge to G1, proving recursive grammar growth;
- both deltas are independently verified, serialized, restarted, prospectively reused, attacked, and causally ablated;
- at least one verified capability composition survives restart and attack;
- all negative controls behave as specified;
- the final qualification emits `PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1` only when every gate passes;
- the final artifact includes manifests, hashes, terminal classifications, capability DAG, both grammar deltas, attack evidence, restart evidence, ablation evidence, and closure certificate.

## Non-goals

Do not claim:

- universal or open-ended closure;
- autonomous invention of a lowest-level substrate;
- optimal grammar-growth search;
- universal transfer across arbitrary domains;
- a canonical least repair when multiple lawful minimal repairs remain;
- that surviving a bounded attack proves universal correctness;
- that the internal system chooses ultimate values or verifier authority.

## Expected result

If successful, this branch will establish the following bounded claim:

> Given a frozen world set, authority boundary, protected consequences, complete current language, declared lower substrates, and resource envelope, RealityGraph can distinguish search failure from expressive inadequacy; turn a certified expressive residual into a minimal extensionally novel language constructor; independently verify, retain, compose, attack, restart, reuse, and causally ablate that constructor; use the earned constructor as part of the synthesis substrate for a later verified constructor; preserve `UnknownChoice` and `UnknownSearch` when those are the lawful residuals; and produce a replayable bounded closure certificate for the resulting generation.

That is the intended completion of the current RealityGraph developmental loop. It does not establish unbounded self-development, but it closes the missing recursive edge from verified residual to verified growth of the language used for future invention.
