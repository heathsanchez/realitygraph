# MG2 Memory Graph design

## Status

Approved architectural direction. This document defines the first implementation milestone for a canonical typed `.mg` active-memory format without changing the existing verified claims or developmental executors.

## Purpose

RealityGraph currently has three distinct active-memory representations:

1. `MG1` / `realitygraph.mg.MG`: tiny canonical law memory.
2. `CapabilityGraph`: typed executable verified capabilities with dependencies and revocation.
3. `MetaMemory`: developmental repair rules learned from obstruction classes, including acquisition/calibration history.

The repository already distinguishes immutable causal history from cognition: the ledger records what happened; `.mg` is the compressed consequential present. MG2 makes that boundary explicit by representing the active parts of all three memory layers in one canonical typed Memory Graph.

The target is:

```text
causal ledger / raw episodes / search traces
                  |
                  | compress earned consequential state
                  v
             Memory Graph (.mg / MG2)
                  |
          +-------+--------+
          |                |
          v                v
   object capability   developmental rule
          |                |
          +-------+--------+
                  v
            future execution
```

MG2 is not a history database and is not a replacement for the causal ledger.

## Design principles

### 1. History is not cognition

Raw acquisition/calibration episodes, candidate search traces, failed alternatives, and event history remain outside `.mg`. MG2 stores only earned state needed to alter future behavior.

### 2. Additive migration

`MG1` remains fully supported and unchanged. MG2 is introduced alongside it. Existing demos, tests, and qualification claims must continue to run without rewriting their executors.

### 3. Exact canonical restart

For every valid MG2 value `M`:

```text
parse(text(M)) == M
text(parse(text(M))) == text(M)
```

Canonical text must be deterministic and independent of insertion order.

### 4. Preserve current trust boundaries

Capability and developmental records retain their authority identity, verifier identity, provenance/evidence lineage, interface boundary, and revocation semantics. MG2 does not promote or weaken any claim.

### 5. No silent identity conflict

MG2 merge is content-strict. If two records have the same typed identity but different payloads, merge fails explicitly. It does not use last-write-wins and does not silently rename a conflict.

### 6. Active memory first

The first milestone serializes the present state. It does not redesign RealityGraph's developmental executor, search policies, verifier authority, or event ledger.

## Proposed module

Add:

```text
realitygraph/memory_graph.py
```

This module owns MG2 records, canonical serialization, merge behavior, and adapters to existing memory forms.

`realitygraph/mg.py` continues to own legacy MG1.

## Canonical representation

MG2 uses canonical JSON text with a fixed top-level schema. RealityGraph already has canonical JSON/digest machinery in the developmental stack, so this minimizes new parser surface and makes round-trip equality straightforward.

Conceptual shape:

```json
{
  "version": "MG2",
  "laws": [],
  "capabilities": [],
  "repair_rules": [],
  "revocations": []
}
```

The serialized form is one canonical JSON object plus a trailing newline. Arrays are sorted by stable typed identity before serialization. Object keys use the repository's canonical JSON ordering.

MG2 intentionally does not contain `episodes`, search traces, raw candidate portfolios, or full causal history.

## Typed records

### MemoryLaw

A lossless MG2 representation of an MG1 law:

```text
law_id
expr
scope
provenance
verifier_id
```

`verifier_id` comes from the MG1 memory header when importing MG1. MG2 does not infer a verifier when none was recorded.

### FiniteCapability

MG2 serializes the existing `FiniteCapability` model directly rather than introducing a competing capability type. The retained fields therefore remain:

```text
capability_id
input_type
output_type
semantics
guard_inputs
certificate_id
dependencies
authority_snapshot
verifier_id
provenance_ids
cost
```

This preserves executable semantics and the existing typed composition boundary.

### RepairRule

MG2 serializes promoted developmental `RepairRule` values using their existing fields:

```text
rule_id
obstruction_fingerprint
strategy_id
strategy_version
portfolio_digest
authority_snapshot
verifier_id
interface_digest
source_episode_digests
source_episode_phases
status
selection_cost
ablation_handle
```

Only `PROMOTED` repair rules are part of the normal active-memory projection. Candidate rules are not earned structure and stay outside MG2. A revoked rule may be represented by a revocation record rather than as an active repair rule.

The source episode digests are retained as evidence lineage, but the raw `RepairEpisode` bodies are not.

### Revocation

MG2 needs explicit revocation state because removing a capability or repair rule from an active list alone would allow stale memory to reintroduce it during merge.

A minimal revocation record is:

```text
target_kind   # capability | repair_rule | law
target_id
provenance    # optional existing evidence/authority handle; empty is allowed for legacy adapters
```

The first milestone does not invent causal evidence that existing structures do not contain.

## MemoryGraphV2

Conceptual API:

```python
@dataclass(frozen=True)
class MemoryGraphV2:
    laws: tuple[MemoryLaw, ...] = ()
    capabilities: tuple[FiniteCapability, ...] = ()
    repair_rules: tuple[RepairRule, ...] = ()
    revocations: tuple[MemoryRevocation, ...] = ()

    def text(self) -> str: ...

    @classmethod
    def parse(cls, text: str) -> "MemoryGraphV2": ...

    @property
    def digest(self) -> str: ...

    def merge(self, other: "MemoryGraphV2") -> "MemoryGraphV2": ...
```

Construction validates:

- unique IDs within each typed namespace;
- no duplicate revocation identity;
- capability dependency validity when projected as a capability graph;
- promoted-only active repair rules;
- canonical enum/status values;
- no active record that is simultaneously revoked in the same graph.

The four typed namespaces remain distinct, so a law and capability may share a textual ID without collision.

## Adapters

### MG1 -> MG2

```python
MemoryGraphV2.from_mg1(memory: MG)
```

Imports all legacy laws and preserves the MG1 verifier header per law.

### MG2 -> MG1

```python
memory.to_mg1()
```

This is a deliberately narrow projection. It succeeds only when projecting the law layer is lossless: all selected laws must have one compatible verifier identity. Capability, repair-rule, and revocation records are not silently discarded by a whole-memory conversion; callers must explicitly request a law-only projection if non-law records exist.

### CapabilityGraph -> MG2

```python
MemoryGraphV2.from_capability_graph(graph: CapabilityGraph)
```

Imports every capability and converts `revoked_ids` into capability revocation records.

### MG2 -> CapabilityGraph

```python
memory.to_capability_graph()
```

Reconstructs the capability layer and its revocations exactly. Other MG2 record types remain present in memory but are not part of this typed projection.

### MetaMemory -> MG2

```python
MemoryGraphV2.from_meta_memory(memory: MetaMemory, promoted_only=True)
```

The default imports only promoted rules. Candidate rules and raw episode bodies are not active memory.

If revoked rules are explicitly requested, they become revocation records rather than active rules.

### MG2 -> MetaMemory active projection

```python
memory.to_meta_memory()
```

Returns a `MetaMemory` sufficient for rule matching and future reuse, containing the retained repair rules but no reconstructed raw episodes. It must not fabricate episode bodies. The active projection is behaviorally equivalent for future rule lookup, not byte-identical to the original historical `MetaMemory`.

## Merge semantics

MG2 merge is deterministic, commutative, associative, and idempotent for non-conflicting memories.

For each typed record identity:

- absent + present -> present;
- identical + identical -> identical;
- same identity + different payload -> explicit merge conflict.

Revocation is monotone at the active-memory layer: if either side revokes an identity, the merged active view treats it as revoked. A conflicting payload is still reported rather than hidden by revocation.

No last-write-wins behavior is allowed.

## Relationship to capability composition

MG2 does not implement a second composition engine. `FiniteCapability` and `compose_capabilities` remain authoritative.

MG2 exposes a `CapabilityGraph` projection. A composed capability is admitted to MG2 only after it already satisfies the existing capability constructor and verification boundary.

This keeps memory serialization separate from semantic capability construction.

## Relationship to the causal ledger

The causal ledger remains the source of immutable history and concurrent evidence. MG2 is a materialized, compressed active view.

Conceptually:

```text
event DAG
  -> merge evidence
  -> verify consequence
  -> promote/revoke earned structure
  -> compress
  -> MG2
```

A future MG2 can carry stronger causal handles, but the first implementation must not duplicate the event DAG or claim that MG2 alone reconstructs complete history.

## First integration target: verified-meta-growth-v3

The first end-to-end proof of usefulness is the current `verified-meta-growth-v3` architecture.

The test will:

1. obtain the object-level `CapabilityGraph` used by the developmental state;
2. obtain the promoted repair rules from `MetaMemory`;
3. combine both into one `MemoryGraphV2`;
4. serialize and parse it exactly;
5. project the restarted MG2 back into the existing object/meta runtime views;
6. run the same untouched-future episodes through the existing executor;
7. require the same rule hits and the same future behavior, including zero repair-portfolio search and zero future grammar search where the existing qualification currently requires them;
8. ablate or revoke the corresponding MG2 record and require restoration of the cold path where the existing qualification currently establishes causality.

This test demonstrates unification of active memory without changing the executor or enlarging the claim boundary.

## Testing strategy

Implementation is test-driven.

### Unit tests

- MG2 empty round trip.
- Law round trip.
- Capability round trip.
- Repair-rule round trip.
- Revocation round trip.
- Canonical ordering independent of construction order.
- Digest stability across exact restart.
- Duplicate typed-ID rejection.
- Same-ID/different-payload merge conflict.
- Merge commutativity, idempotence, and associativity for compatible inputs.
- Active+revoked inconsistency rejection.

### Adapter tests

- MG1 -> MG2 -> MG1 exact for law-only memory.
- CapabilityGraph -> MG2 -> CapabilityGraph exact, including `active_ids()` and ablation behavior.
- Promoted MetaMemory -> MG2 -> active MetaMemory preserves `promoted_match` behavior.
- Candidate repair rules do not enter MG2 by default.
- No raw `RepairEpisode` body is fabricated on restore.

### Integration tests

- Combined object+meta MG2 restart preserves the existing `verified-meta-growth-v3` future route.
- Rule/capability revocation through the MG2 view restores the same cold-search or `UNKNOWN` behavior established by the existing ablations.
- Existing MG1 tests and current qualification tests stay green.

## Files expected in the first implementation

New:

```text
realitygraph/memory_graph.py
tests/test_memory_graph_v2.py
tests/test_memory_graph_v2_integration.py
```

Possibly modified only for exports/documentation:

```text
realitygraph/__init__.py
README.md
```

Existing `mg.py`, `capability.py`, `capability_graph.py`, `meta_memory.py`, and developmental executors should not require semantic rewrites in this milestone.

## Non-goals

The first MG2 milestone does not claim or implement:

- open-ended self-development;
- automatic ontology invention;
- automatic capability composition search;
- replacement of the causal ledger;
- replacement of the verifier/authority boundary;
- universal cross-domain transfer;
- migration of every historical branch artifact;
- a public package/network protocol;
- automatic garbage collection or MDL optimization over MG2;
- a MathGraph deployment layer.

Those can be evaluated after MG2 proves it can faithfully represent and restart the current active intelligence state.

## Acceptance criteria

MG2 is complete for this milestone only if all of the following hold:

1. Existing MG1 behavior is unchanged.
2. MG2 has deterministic canonical serialization and exact restart.
3. CapabilityGraph projection is lossless, including revocation/ablation behavior.
4. Promoted MetaMemory projection preserves future rule matching without storing or fabricating raw episodes.
5. A single MG2 value can contain the active object capability graph and promoted meta-developmental rules simultaneously.
6. The combined MG2 restart preserves the existing `verified-meta-growth-v3` prospective behavior on its frozen future episodes.
7. MG2 revocation or ablation restores the corresponding cold path in the integration test.
8. Conflicting identities fail explicitly rather than silently merging.
9. Existing repository tests and qualification claims remain green.
10. No stronger scientific claim is made merely because storage has been unified.

## Follow-on direction, not part of milestone 1

Once active-state unification is demonstrated, MG2 can become the common substrate on which RealityGraph performs memory minimization and higher-order compounding:

```text
experience
 -> verified consequence
 -> obstruction
 -> representation/capability
 -> MG2
 -> graph compression/composition
 -> cleaner residual
 -> next capability
 -> smaller/more powerful MG2
```

That is the point where Memory Graph becomes not merely a storage format but the canonical active state through which RealityGraph's developmental loop compounds.
