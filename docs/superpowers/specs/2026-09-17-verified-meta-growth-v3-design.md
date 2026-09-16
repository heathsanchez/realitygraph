# Verified Meta-Growth V3 — Design Specification

Date: 2026-09-17
Branch: `verified-meta-growth-v3`
Base: `001f77c43d87f642dfa9bc8a2bec43ab0f5ca750` (`verified-language-growth-closure-v2` final green head)

## 1. Objective

V1 proved that a certified expressive obstruction can license a new language element and that the admitted element can be retained, replayed, attacked, ablated, and reused.

V2 proved that the same generic `execute_generation(state, spec)` path can carry a real three-generation dependency chain without fixture imports or G1/G2/G3 dispatch in the executor.

V3 targets the next remaining human bottleneck:

> the system is still told which lower substrate family to search.

The V3 objective is therefore:

> **Given a certified obstruction and a frozen portfolio of lawful repair strategies, learn which kind of developmental move resolves that obstruction, retain that repair-selection rule, and reuse the rule on an independently frozen isomorphic obstruction without searching the whole repair portfolio again.**

The central upgrade is from verified capability growth to **verified learning of how to grow**.

V3 remains finite and bounded. It does not claim autonomous invention of substrate families from no prior primitives.

## 2. Approaches considered

### A. Add G4 to V2

Extend the same generic executor to a fourth hand-specified substrate.

This would increase recursive depth but would leave the human-selected-substrate bottleneck untouched. Rejected as insufficient.

### B. Verified repair-strategy portfolio with learned transfer — chosen

Freeze several heterogeneous repair strategy families before the experiment. For each certified obstruction, test the strategies under identical authority, verifier, resource, and future-evidence rules. Retain the verified obstruction-to-repair mapping as meta-memory. On a later certified isomorphic obstruction, use the retained rule to choose the repair family directly.

This isolates the precise missing capability while preserving V1/V2 evidence discipline.

### C. Open-ended synthesis of new repair languages

Allow V3 to invent arbitrary new repair operators, new primitive substrates, or new meta-languages recursively.

This is the long-term direction but is not yet earned by V2. It would make a clean failure uninterpretable and would outrun the bounded evidence. Rejected for V3.

## 3. Constitutional constraints

V3 inherits the existing developmental laws unchanged.

1. Search failure is not expressivity failure.
2. Structural growth requires completeness plus independently replayable no-resolution evidence.
3. A repair proposal is not authority.
4. Losing repair attempts cannot mutate persistent state.
5. A retained repair-selection rule is advisory capability, not truth; the resulting object-level capability must still pass the normal verifier, attack, future evaluation, replay, and admission gates.
6. A stale authority snapshot, verifier identity, portfolio identity, or obstruction fingerprint invalidates the rule.
7. If several repair strategies remain equally lawful under the declared selection order, V3 returns `UNKNOWN_CHOICE` rather than silently choosing one.
8. If the repair portfolio is not exhaustively checked within the declared resource envelope, failure remains `UNKNOWN_SEARCH`.

## 4. Architecture

V3 adds a meta-developmental layer around the existing V2 executor. It does not replace `execute_generation`.

The high-level loop becomes:

```text
object state
  -> certify current obstruction
  -> canonical obstruction fingerprint
  -> consult retained repair memory
       | hit                         | miss
       v                             v
     choose one repair          evaluate frozen portfolio
       |                             |
       +-----------+-----------------+
                   v
          materialize GenerationSpec
                   v
          execute_generation(...)
                   v
        verify / attack / future gate
                   v
       admit object capability if earned
                   v
       retain or update repair rule
                   v
             exact meta snapshot
```

The critical property is that the meta layer chooses **which lower substrate adapter to instantiate**, while the existing V2 executor remains the only path that may admit the resulting object-level grammar delta and capability.

## 5. Exact obstruction fingerprint

V3 must not transfer repair rules by task name, source identity, surface symbol names, fixture names, or generation number.

The new `ObstructionFingerprint` is an exact isomorphism-invariant description of the bounded partition failure.

For a frozen carrier, construct the bipartite multigraph induced by:

- the equivalence classes created by the complete current language, and
- the required consequence classes for the acquisition/growth obligation.

Every carrier element contributes one incidence between its current-language class and required-consequence class. Multiplicity is preserved.

The canonical fingerprint is obtained by lexicographically minimizing the finite incidence representation over all allowed relabelings of the quotient-class nodes. The bounded fixtures are intentionally small enough for exact exhaustive canonicalization.

The fingerprint payload includes:

```text
input_type
output_type
current_class_count
consequence_class_count
canonical_incidence_matrix
carrier_size
current_language_semantic_count
authority_snapshot
verifier_id
```

Surface carrier labels are excluded.

Two obligations may share a fingerprint only when their certified quotient/consequence failures are isomorphic under this declared finite canonicalizer.

This is a deliberately stronger key than a hand-authored label such as `needs_memory` or `needs_composition`.

## 6. Repair strategy protocol

A repair strategy is a proposal generator for one class of developmental move.

```text
RepairStrategy
  strategy_id
  strategy_version
  structural_cost
  applicable(fingerprint, object_state, meta_spec)
  materialize_generation_spec(object_state, meta_spec)
```

A strategy never mutates state directly. It may only construct a normal V2 `GenerationSpec` with a particular lower-substrate adapter and associated resource envelope.

V3's initial frozen portfolio contains four generic strategy families:

1. `deepen_stateless_composition`
   - expands composition depth while preserving the same observables and no internal state;
2. `add_observable`
   - expands the declared stateless observation vocabulary without adding memory;
3. `add_finite_memory_2`
   - introduces the complete declared two-state finite-memory substrate over the existing earned signal interface;
4. `add_finite_memory_3`
   - introduces the corresponding complete three-state substrate at higher structural cost.

The strategy IDs and implementations are frozen before qualification.

The portfolio is not claimed to be complete over all possible repair types. It is complete only over this declared V3 repair portfolio.

## 7. Meta executor

Add one generic entry point:

```text
execute_meta_growth(object_state, meta_memory, meta_spec)
    -> MetaGrowthResult
```

It performs the following steps.

### 7.1 Certify the obstruction once

The meta spec first exhausts and certifies the current object language using the same completeness/no-resolution semantics as V2. If this cannot be done, V3 cannot search repair families structurally.

Routes:

- incomplete current language -> `UNKNOWN_SEARCH`
- current language already resolves obligation -> `AUTHORIZED`
- complete current language + no resolution -> exact `ObstructionFingerprint`

### 7.2 Consult repair memory

Look for an active promoted repair rule matching:

```text
fingerprint
portfolio_digest
authority_snapshot
verifier_id
input/output interface
```

A valid hit selects exactly one repair strategy before any competing strategy is materialized.

On a hit:

```text
portfolio_search_calls = 0
competitor_strategy_calls = 0
```

The selected repair family may still perform its own bounded object-level candidate search. V3 claims avoided **repair-family search**, not universal zero search.

### 7.3 Cold portfolio evaluation

On a miss, run each applicable frozen strategy from the exact same immutable parent object state.

Each strategy materializes a V2 `GenerationSpec` and is evaluated through the unchanged `execute_generation` path.

Losing attempts are ephemeral.

A strategy counts as successful only if the resulting generation route is `COMPILED` and all underlying V2 admission gates pass.

If no strategy succeeds:

- incomplete portfolio evaluation -> `UNKNOWN_SEARCH`;
- complete portfolio evaluation -> `NAMED_META_OBSTRUCTION`.

If more than one succeeds, selection is by the predeclared structural order:

```text
(strategy.structural_cost,
 admitted_constructor.complexity,
 strategy_id,
 retained_capability_id)
```

If two candidates remain observationally and structurally tied under the declared order, return `UNKNOWN_CHOICE`.

### 7.4 Retain the developmental move

A successful cold acquisition does not immediately create a trusted transfer rule. It creates a candidate `RepairRule` supported by that source episode.

A rule is promoted only after an independently frozen calibration episode with the same obstruction fingerprint independently selects the same strategy and passes all object-level verification gates.

Only promoted rules may bypass portfolio search on prospective future tasks.

## 8. Repair memory

Introduce persistent `MetaMemory` containing immutable repair rules and evidence lineage.

```text
RepairRule
  rule_id
  obstruction_fingerprint
  strategy_id
  strategy_version
  portfolio_digest
  authority_snapshot
  verifier_id
  interface_digest
  source_episode_digests
  status = CANDIDATE | PROMOTED | REVOKED
  selection_cost
  ablation_handle
```

`MetaMemory` must have canonical serialization, byte-exact restart, deterministic merge-free ordering for this bounded experiment, and explicit rule ablation.

A rule is not a replacement for the object capability it helps construct. It is a retained **developmental capability**: a verified mapping from an obstruction geometry to a repair family.

## 9. Qualification worlds

V3 must show that the meta policy is not simply hard-coded to one repair type. The qualification therefore uses two distinct obstruction families.

### 9.1 Family C — compositional obstruction

Current language sees only one coordinate of a finite pair carrier and is complete over that declared one-coordinate language. The target distinction is not present.

Cold portfolio behavior must establish:

- deeper same-observable stateless structure alone does not resolve the obstruction within the frozen bound;
- finite memory is inapplicable to the nonsequential interface;
- the declared stateless composition repair yields the minimal verified successful extension;
- the winning strategy class is `deepen_stateless_composition`.

The acquisition and calibration variants use different surface carrier names and syntactic encodings but have the same exact obstruction fingerprint.

### 9.2 Family T — temporal obstruction

The complete current language sees only the present symbol, while required consequence distinguishes histories that share the present but differ in the past.

Cold portfolio behavior must establish:

- stateless composition cannot separate histories collapsed by identical present observation;
- adding only another stateless present observable within the declared vocabulary does not resolve the obstruction;
- a two-state memory repair succeeds;
- a three-state memory repair is also available but is structurally more expensive;
- the selected strategy class is `add_finite_memory_2`.

Again, acquisition and calibration tasks use different surface alphabets while preserving exact obstruction isomorphism.

## 10. Prospective transfer test

After both repair rules are promoted, freeze two untouched future tasks:

- one new Family-C surface realization;
- one new Family-T surface realization.

For each future task:

1. certify its current-language obstruction without consulting future outcomes;
2. compute its exact obstruction fingerprint;
3. match the promoted rule;
4. choose the retained repair strategy with zero portfolio search;
5. synthesize a new task-specific object capability inside that chosen repair family;
6. verify, attack, replay, admit, and prospectively evaluate the new capability normally.

The future capability must be newly synthesized. Reusing the exact earlier object capability does not satisfy V3.

Required future counters:

```text
portfolio_search_calls = 0
competitor_strategy_calls = 0
selected_strategy_calls = 1
```

Object-level candidate search inside the selected strategy is counted separately and may be nonzero.

## 11. Causal ablations and negative controls

V3 is not green without all of the following controls.

### Repair-rule ablation

Ablating a promoted repair rule must restore the cold portfolio-search path on the corresponding future task.

The eventual object-level answer may still be rediscovered; what must disappear is the meta-level search saving.

### Wrong-fingerprint control

A rule for Family C must not select the Family T strategy, and vice versa.

### Stale authority/verifier control

Changing authority or verifier identity invalidates otherwise matching repair memory.

### Sham rule control

A forged rule with a matching surface label but wrong fingerprint or portfolio digest is rejected.

### Incomplete obstruction control

A partial current-language search cannot produce a transferable obstruction fingerprint or trigger meta-growth.

### Portfolio-budget control

If only part of the frozen repair portfolio is explored and no solution is found, the route remains `UNKNOWN_SEARCH`, not `NAMED_META_OBSTRUCTION`.

### Choice control

A deliberately tied bounded fixture with two indistinguishable equally ranked repairs must remain `UNKNOWN_CHOICE` until external consequence breaks the tie.

### Object-capability ablation

Normal V2 transitive object-capability ablation remains unchanged and must still work after the meta layer is added.

## 12. Exact persistence

Add `MetaSnapshot` containing:

```text
object_state_text
meta_memory_text
meta_terminal_records
portfolio_digest
authority_snapshot
```

Cold restart must reconstruct the exact same object-state digest, meta-memory digest, active repair rules, and capability graph without invoking repair strategies or fixture adapters.

## 13. Closure certificate

V3 emits a bounded meta-growth closure certificate only when every frozen obligation is terminal and replayable.

Success status:

```text
CLOSED_BOUNDED_META_GROWTH_V3
```

Required terminal evidence includes:

- two cold acquisition episodes;
- two independent calibration episodes;
- two promoted repair rules selecting different strategy classes;
- two prospective future transfers with zero repair-portfolio search;
- exact meta restart;
- repair-rule ablation restoring cold search;
- wrong-fingerprint, stale-authority/verifier, sham-rule, incomplete-search, portfolio-budget, and `UNKNOWN_CHOICE` controls;
- inherited V2 qualification still green.

Expected executable verdict:

```text
PASS_VERIFIED_META_GROWTH_V3
```

## 14. Core modules

Provisional module boundaries:

```text
realitygraph/obstruction_fingerprint.py
    exact finite canonical obstruction encoding

realitygraph/repair_strategy.py
    RepairStrategy protocol and frozen portfolio types

realitygraph/meta_memory.py
    RepairRule, promotion, revocation, canonical persistence

realitygraph/meta_executor.py
    generic obstruction -> memory lookup / portfolio evaluation -> V2 executor loop

realitygraph/meta_snapshot.py
    exact object + meta-memory restart

realitygraph/fixtures/meta_growth_v3.py
    bounded acquisition/calibration/future fixtures only

verified_meta_growth_v3.py
    sealed qualification runner
```

The existing `developmental_executor.py` remains generation-generic and must not gain meta-fixture imports or strategy-name dispatch.

## 15. Test gates

The implementation must include focused tests proving:

- fingerprint invariance under allowed surface relabeling;
- fingerprint inequality for non-isomorphic obstruction geometry;
- cold portfolio selection through one generic meta executor;
- distinct winning repair classes across the two acquisition families;
- candidate rule creation after acquisition;
- promotion only after independent calibration agreement;
- exact meta-memory restart;
- future rule hit before strategy materialization;
- zero future portfolio search and zero competitor calls;
- new future object capability is synthesized and verified;
- repair-rule ablation restores cold portfolio search;
- stale/mismatched/sham rules cannot apply;
- partial obstruction and partial portfolio search stay `UNKNOWN_SEARCH`;
- tied repairs stay `UNKNOWN_CHOICE`;
- inherited V2 tests remain green;
- source-level meta executor contains no fixture imports, Family-C/Family-T names, or strategy-ID dispatch.

## 16. Evidence discipline

The sealed runner writes a canonical JSON summary and CI log artifact containing:

```text
acquisition fingerprints
calibration fingerprints
promoted repair rule IDs
selected strategy IDs
cold portfolio call counts
future portfolio call counts
object-level candidate search counts
future capability IDs
rule-ablation call counts
meta snapshot digest
closure certificate digest
claim boundary
```

CI fails unless the exact verdict and all required gates are present.

## 17. Explicit non-claims

A green V3 does **not** establish:

- open-ended or unbounded self-development;
- autonomous invention of arbitrary new substrate families;
- universal obstruction classification;
- transfer across non-isomorphic obstruction geometry;
- learned ultimate verifier or authority;
- optimal repair-strategy selection outside the frozen portfolio;
- designerless objective generation;
- that every expressive obstruction admits a repair in the declared portfolio.

The warranted claim is narrower:

> **Within a declared finite repair portfolio and exact finite obstruction canonicalizer, RealityGraph can learn a verified mapping from obstruction geometry to repair family, promote that mapping through independent evidence, and use it prospectively to avoid re-searching competing repair families while still verifying the newly synthesized task-specific capability through the existing developmental kernel.**

## 18. Success criterion

V3 is complete only if all of the following hold together:

```text
certified obstruction
  -> exact fingerprint
  -> cold repair-family search
  -> verified winning developmental move
  -> independent calibration
  -> promoted repair rule
  -> new isomorphic future obstruction
  -> direct repair-family selection
  -> new task-specific capability
  -> ordinary V2 verify / attack / replay / admit
  -> zero future portfolio search
  -> causal ablation restores cold meta search
```

That is the bounded first qualification of **verified learning of how to grow**.
