# MG2 Memory Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical typed `MG2` active-memory format that unifies legacy laws, executable capabilities, promoted developmental repair rules, and revocations while preserving MG1 compatibility and the existing `verified-meta-growth-v3` future behavior.

**Architecture:** Introduce `realitygraph/memory_graph.py` as a serialization/adaptation layer over the existing authoritative domain types (`MG`/`Law`, `FiniteCapability`/`CapabilityGraph`, `RepairRule`/`MetaMemory`). MG2 stores only compressed consequential present-state objects; raw episodes and causal history remain outside `.mg`. The first milestone proves exact canonical restart, deterministic merge/revocation behavior, lossless projections to existing runtime views, and unchanged prospective behavior in the current meta-growth qualification.

**Tech Stack:** Python 3.12, frozen dataclasses, canonical JSON/digest helpers from `realitygraph.developmental_types`, existing RealityGraph unit tests/pytest, existing qualification executors.

**Spec:** `docs/superpowers/specs/2026-09-17-mg2-memory-graph-design.md`

## Global Constraints

- `MG1` remains fully supported and unchanged.
- Existing demos, tests, and qualification claims must continue to run without rewriting their executors.
- MG2 stores active consequential state only; raw acquisition/calibration episodes, candidate traces, and event history remain outside `.mg`.
- Canonical serialization must be deterministic and insertion-order independent.
- Exact MG2 restart must satisfy `parse(text(M)) == M` and `text(parse(text(M))) == text(M)`.
- Existing authority identity, verifier identity, provenance/evidence lineage, interface boundaries, and revocation semantics must be preserved.
- Same typed identity with different payload is an explicit merge conflict; never last-write-wins and never silent renaming.
- `FiniteCapability`, `CapabilityGraph`, `RepairRule`, and `MetaMemory` remain semantically authoritative; MG2 must not create competing execution/composition semantics.
- Normal MetaMemory projection imports only promoted repair rules; candidate rules remain outside active memory.
- MG2 must never fabricate raw `RepairEpisode` bodies.
- No stronger scientific claim is created by storage unification.

---

## File Structure

**Create**

- `realitygraph/memory_graph.py` — MG2 record types, canonical serialization, validation, merge, revocation-aware active views, and adapters.
- `tests/test_memory_graph_v2.py` — unit and adapter tests.
- `tests/test_memory_graph_v2_integration.py` — meta-growth restart/ablation integration tests.

**Modify**

- `realitygraph/__init__.py` — export MG2 public types after behavior is proven.
- `README.md` — document MG2 as the canonical typed active-memory direction without changing scientific claims.

**Do not semantically rewrite in milestone 1**

- `realitygraph/mg.py`
- `realitygraph/capability.py`
- `realitygraph/capability_graph.py`
- `realitygraph/meta_memory.py`
- `realitygraph/meta_executor.py`
- `realitygraph/developmental_executor.py`
- `verified_meta_growth_v3.py`

---

### Task 1: Define canonical MG2 records and exact round-trip serialization

**Files:**
- Create: `realitygraph/memory_graph.py`
- Create: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Consumes: `realitygraph.developmental_types.canonical_digest`, `realitygraph.developmental_types.canonical_json`, `realitygraph.mg.Law`, `realitygraph.capability.FiniteCapability`, `realitygraph.meta_memory.RepairRule`, `RepairRuleStatus`.
- Produces:
  - `MemoryLaw`
  - `MemoryRevocation`
  - `MemoryGraphV2`
  - `MemoryGraphConflict`
  - `MemoryGraphV2.text() -> str`
  - `MemoryGraphV2.parse(text: str) -> MemoryGraphV2`
  - `MemoryGraphV2.digest -> str`

- [ ] **Step 1: Write failing tests for empty graph, record round trips, ordering, and digest stability**

Add to `tests/test_memory_graph_v2.py`:

```python
from realitygraph.capability import FiniteCapability
from realitygraph.memory_graph import (
    MemoryGraphV2,
    MemoryLaw,
    MemoryRevocation,
)
from realitygraph.meta_memory import RepairRule, RepairRuleStatus


def sample_capability(capability_id: str = "cap-a") -> FiniteCapability:
    return FiniteCapability(
        capability_id=capability_id,
        input_type="bit",
        output_type="bit",
        semantics=(("0", "1"), ("1", "0")),
        guard_inputs=("0", "1"),
        certificate_id="cert-a",
        dependencies=(),
        authority_snapshot="authority-a",
        verifier_id="verifier-a",
        provenance_ids=("prov-a",),
        cost=3,
    )


def sample_rule(rule_id: str = "repair-rule-a") -> RepairRule:
    return RepairRule(
        rule_id=rule_id,
        obstruction_fingerprint="fp-a",
        strategy_id="add_observable",
        strategy_version="strategy-v1",
        portfolio_digest="portfolio-a",
        authority_snapshot="authority-a",
        verifier_id="verifier-a",
        interface_digest="interface-a",
        source_episode_digests=("episode-a", "episode-b"),
        source_episode_phases=("ACQUISITION", "CALIBRATION"),
        status=RepairRuleStatus.PROMOTED,
        selection_cost=7,
        ablation_handle="ablate-a",
    )


def test_empty_mg2_round_trip_is_exact():
    memory = MemoryGraphV2()
    restarted = MemoryGraphV2.parse(memory.text())
    assert restarted == memory
    assert restarted.text() == memory.text()
    assert restarted.digest == memory.digest


def test_mg2_round_trip_preserves_all_record_types():
    memory = MemoryGraphV2(
        laws=(MemoryLaw("law-a", "x=y", "*", "prov-law", "verifier-a"),),
        capabilities=(sample_capability(),),
        repair_rules=(sample_rule(),),
        revocations=(MemoryRevocation("law", "law-old", "prov-revoke"),),
    )
    restarted = MemoryGraphV2.parse(memory.text())
    assert restarted == memory
    assert restarted.text() == memory.text()


def test_canonical_text_is_insertion_order_independent():
    laws = (
        MemoryLaw("law-b", "b", "scope-b", "prov-b", "verifier-a"),
        MemoryLaw("law-a", "a", "scope-a", "prov-a", "verifier-a"),
    )
    a = MemoryGraphV2(laws=laws)
    b = MemoryGraphV2(laws=tuple(reversed(laws)))
    assert a.text() == b.text()
    assert a.digest == b.digest
```

- [ ] **Step 2: Run tests to verify they fail because MG2 does not exist**

Run:

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: collection/import failure for `realitygraph.memory_graph`.

- [ ] **Step 3: Implement minimal canonical MG2 records and parser**

Create `realitygraph/memory_graph.py` with these concrete public types and payload contracts:

```python
from __future__ import annotations

import json
from dataclasses import dataclass

from .capability import FiniteCapability
from .developmental_types import canonical_digest, canonical_json
from .meta_memory import RepairRule, RepairRuleStatus


class MemoryGraphConflict(ValueError):
    pass


@dataclass(frozen=True)
class MemoryLaw:
    law_id: str
    expr: str
    scope: str = "*"
    provenance: str = ""
    verifier_id: str = ""

    def payload(self) -> dict[str, object]:
        return {
            "law_id": self.law_id,
            "expr": self.expr,
            "scope": self.scope,
            "provenance": self.provenance,
            "verifier_id": self.verifier_id,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "MemoryLaw":
        return cls(
            law_id=str(payload["law_id"]),
            expr=str(payload["expr"]),
            scope=str(payload["scope"]),
            provenance=str(payload["provenance"]),
            verifier_id=str(payload["verifier_id"]),
        )


@dataclass(frozen=True)
class MemoryRevocation:
    target_kind: str
    target_id: str
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.target_kind not in {"law", "capability", "repair_rule"}:
            raise ValueError("unsupported MG2 revocation target kind")
        if not self.target_id:
            raise ValueError("MG2 revocation requires target id")

    @property
    def identity(self) -> tuple[str, str]:
        return (self.target_kind, self.target_id)

    def payload(self) -> dict[str, object]:
        return {
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "provenance": self.provenance,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "MemoryRevocation":
        return cls(
            target_kind=str(payload["target_kind"]),
            target_id=str(payload["target_id"]),
            provenance=str(payload["provenance"]),
        )
```

Use helper payload converters for the existing domain types rather than adding methods to those files:

```python
def _capability_payload(cap: FiniteCapability) -> dict[str, object]:
    return {
        "capability_id": cap.capability_id,
        "input_type": cap.input_type,
        "output_type": cap.output_type,
        "semantics": [list(row) for row in cap.semantics],
        "guard_inputs": list(cap.guard_inputs),
        "certificate_id": cap.certificate_id,
        "dependencies": list(cap.dependencies),
        "authority_snapshot": cap.authority_snapshot,
        "verifier_id": cap.verifier_id,
        "provenance_ids": list(cap.provenance_ids),
        "cost": cap.cost,
    }


def _capability_from_payload(payload: dict[str, object]) -> FiniteCapability:
    return FiniteCapability(
        capability_id=str(payload["capability_id"]),
        input_type=str(payload["input_type"]),
        output_type=str(payload["output_type"]),
        semantics=tuple((str(a), str(b)) for a, b in payload["semantics"]),
        guard_inputs=tuple(str(x) for x in payload["guard_inputs"]),
        certificate_id=str(payload["certificate_id"]),
        dependencies=tuple(str(x) for x in payload["dependencies"]),
        authority_snapshot=str(payload["authority_snapshot"]),
        verifier_id=str(payload["verifier_id"]),
        provenance_ids=tuple(str(x) for x in payload["provenance_ids"]),
        cost=int(payload["cost"]),
    )
```

For repair rules, serialize `rule.payload()` and restore through `RepairRule.from_payload()`.

Define `MemoryGraphV2` with a canonical constructor boundary:

```python
@dataclass(frozen=True)
class MemoryGraphV2:
    laws: tuple[MemoryLaw, ...] = ()
    capabilities: tuple[FiniteCapability, ...] = ()
    repair_rules: tuple[RepairRule, ...] = ()
    revocations: tuple[MemoryRevocation, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "laws", tuple(sorted(self.laws, key=lambda x: x.law_id)))
        object.__setattr__(self, "capabilities", tuple(sorted(self.capabilities, key=lambda x: x.capability_id)))
        object.__setattr__(self, "repair_rules", tuple(sorted(self.repair_rules, key=lambda x: x.rule_id)))
        object.__setattr__(self, "revocations", tuple(sorted(self.revocations, key=lambda x: x.identity)))
        self._validate()

    def payload(self) -> dict[str, object]:
        return {
            "version": "MG2",
            "laws": [law.payload() for law in self.laws],
            "capabilities": [_capability_payload(cap) for cap in self.capabilities],
            "repair_rules": [rule.payload() for rule in self.repair_rules],
            "revocations": [item.payload() for item in self.revocations],
        }

    def text(self) -> str:
        return canonical_json(self.payload()) + "\n"

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="memory-graph-v2:")

    @classmethod
    def parse(cls, text: str) -> "MemoryGraphV2":
        payload = json.loads(text)
        if payload.get("version") != "MG2":
            raise ValueError("unsupported Memory Graph version")
        memory = cls(
            laws=tuple(MemoryLaw.from_payload(row) for row in payload["laws"]),
            capabilities=tuple(_capability_from_payload(row) for row in payload["capabilities"]),
            repair_rules=tuple(RepairRule.from_payload(row) for row in payload["repair_rules"]),
            revocations=tuple(MemoryRevocation.from_payload(row) for row in payload["revocations"]),
        )
        if memory.text() != text:
            raise ValueError("non-canonical MG2 memory")
        return memory
```

Validation in `_validate()` must reject duplicate IDs within a typed namespace, duplicate revocation identities, non-promoted active repair rules, active records simultaneously revoked, and malformed capability dependency graphs. Reuse `CapabilityGraph(self.capabilities, revoked_ids=...)` for dependency-cycle/missing-dependency validation once Task 2 adds the adapter import.

- [ ] **Step 4: Run the MG2 unit tests**

Run:

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: the initial round-trip/canonical-order tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2.py
git commit -m "feat: add canonical MG2 memory graph core"
```

---

### Task 2: Add MG1 and CapabilityGraph adapters with exact revocation behavior

**Files:**
- Modify: `realitygraph/memory_graph.py`
- Modify: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Consumes: Task 1 `MemoryGraphV2`, legacy `MG`/`Law`, `CapabilityGraph`.
- Produces:
  - `MemoryGraphV2.from_mg1(memory: MG) -> MemoryGraphV2`
  - `MemoryGraphV2.to_mg1(*, law_only: bool = False) -> MG`
  - `MemoryGraphV2.from_capability_graph(graph: CapabilityGraph) -> MemoryGraphV2`
  - `MemoryGraphV2.to_capability_graph() -> CapabilityGraph`
  - `MemoryGraphV2.active_laws`
  - `MemoryGraphV2.active_capabilities`

- [ ] **Step 1: Write failing adapter tests**

Add:

```python
import pytest

from realitygraph.capability_graph import CapabilityGraph
from realitygraph.mg import Law, MG


def test_mg1_round_trip_is_exact_for_law_only_memory():
    original = MG(
        "verifier-a",
        (
            Law("law-b", "expr-b", "scope-b", "prov-b"),
            Law("law-a", "expr-a", "scope-a", "prov-a"),
        ),
    )
    mg2 = MemoryGraphV2.from_mg1(original)
    restored = mg2.to_mg1()
    assert restored.text() == original.text()


def test_whole_memory_to_mg1_refuses_to_drop_non_law_records():
    memory = MemoryGraphV2(
        laws=(MemoryLaw("law-a", "x", "*", "", "verifier-a"),),
        capabilities=(sample_capability(),),
    )
    with pytest.raises(ValueError, match="non-law"):
        memory.to_mg1()


def test_capability_graph_round_trip_preserves_revocation_and_active_ids():
    parent = sample_capability("parent")
    child = FiniteCapability(
        capability_id="child",
        input_type="bit",
        output_type="bit",
        semantics=(("0", "0"), ("1", "1")),
        guard_inputs=("0", "1"),
        certificate_id="cert-child",
        dependencies=("parent",),
        authority_snapshot="authority-a",
        verifier_id="verifier-a",
        provenance_ids=("prov-child",),
        cost=4,
    )
    original = CapabilityGraph((parent, child), revoked_ids=("parent",))
    restored = MemoryGraphV2.from_capability_graph(original).to_capability_graph()
    assert restored.capabilities == original.capabilities
    assert restored.revoked_ids == original.revoked_ids
    assert restored.active_ids() == original.active_ids() == ()
```

- [ ] **Step 2: Run focused tests and confirm failure**

```bash
python -m pytest -q \
  tests/test_memory_graph_v2.py::test_mg1_round_trip_is_exact_for_law_only_memory \
  tests/test_memory_graph_v2.py::test_capability_graph_round_trip_preserves_revocation_and_active_ids
```

Expected: failure because adapters are not implemented.

- [ ] **Step 3: Implement the adapters and active views**

Add imports:

```python
from .capability_graph import CapabilityGraph
from .mg import Law, MG
```

Implement MG1 conversion:

```python
@classmethod
def from_mg1(cls, memory: MG) -> "MemoryGraphV2":
    return cls(
        laws=tuple(
            MemoryLaw(
                law_id=law.id,
                expr=law.expr,
                scope=law.scope,
                provenance=law.provenance,
                verifier_id=memory.verifier,
            )
            for law in memory.laws.values()
        )
    )


def to_mg1(self, *, law_only: bool = False) -> MG:
    if not law_only and (self.capabilities or self.repair_rules or self.revocations):
        raise ValueError("MG2 contains non-law records; request explicit law-only projection")
    active = self.active_laws
    verifiers = {law.verifier_id for law in active}
    if len(verifiers) > 1:
        raise ValueError("MG2 law layer contains incompatible verifier identities")
    verifier = next(iter(verifiers), "")
    return MG(
        verifier,
        tuple(Law(law.law_id, law.expr, law.scope, law.provenance) for law in active),
    )
```

Implement capability conversion:

```python
@classmethod
def from_capability_graph(cls, graph: CapabilityGraph) -> "MemoryGraphV2":
    return cls(
        capabilities=graph.capabilities,
        revocations=tuple(
            MemoryRevocation("capability", capability_id)
            for capability_id in graph.revoked_ids
        ),
    )


def to_capability_graph(self) -> CapabilityGraph:
    revoked = tuple(
        item.target_id
        for item in self.revocations
        if item.target_kind == "capability"
    )
    return CapabilityGraph(self.capabilities, revoked)
```

Add active views that filter revocations without deleting underlying records:

```python
@property
def active_laws(self) -> tuple[MemoryLaw, ...]:
    revoked = {r.target_id for r in self.revocations if r.target_kind == "law"}
    return tuple(law for law in self.laws if law.law_id not in revoked)

@property
def active_capabilities(self) -> tuple[FiniteCapability, ...]:
    revoked = {r.target_id for r in self.revocations if r.target_kind == "capability"}
    graph = CapabilityGraph(self.capabilities, tuple(sorted(revoked)))
    active = set(graph.active_ids())
    return tuple(cap for cap in self.capabilities if cap.capability_id in active)
```

Adjust validation so a stored record may be revoked; the *active view* must exclude it. The spec requires revocation persistence, not rejection of stored+revoked state. Reject only duplicate revocation identities and revocations pointing to a missing target when the target kind is capability or repair rule and MG2 is meant to be self-contained. Legacy law tombstones may target an absent old law to prevent reintroduction during merge.

- [ ] **Step 4: Run all MG2 unit tests**

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: PASS.

- [ ] **Step 5: Run existing MG1 and capability tests**

Discover exact filenames, then run the relevant existing tests plus:

```bash
python -m pytest -q tests -k 'mg or capability_graph or capability'
```

Expected: no regressions.

- [ ] **Step 6: Commit Task 2**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2.py
git commit -m "feat: bridge MG1 and capability graph into MG2"
```

---

### Task 3: Add promoted MetaMemory projection, deterministic merge, and revocation semantics

**Files:**
- Modify: `realitygraph/memory_graph.py`
- Modify: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Consumes: `MetaMemory`, `RepairRuleStatus`, Task 1/2 MG2 core.
- Produces:
  - `MemoryGraphV2.from_meta_memory(memory: MetaMemory, *, promoted_only: bool = True) -> MemoryGraphV2`
  - `MemoryGraphV2.to_meta_memory() -> MetaMemory`
  - `MemoryGraphV2.active_repair_rules`
  - `MemoryGraphV2.merge(other: MemoryGraphV2) -> MemoryGraphV2`
  - `MemoryGraphV2.revoke(target_kind: str, target_id: str, provenance: str = "") -> MemoryGraphV2`

- [ ] **Step 1: Write failing tests for MetaMemory behavior and merge laws**

Add:

```python
from realitygraph.meta_memory import MetaMemory, RepairEpisode, RepairPhase


def promoted_meta_memory() -> MetaMemory:
    memory = MetaMemory.empty()
    common = dict(
        obstruction_fingerprint="fp-a",
        strategy_id="add_observable",
        strategy_version="strategy-v1",
        portfolio_digest="portfolio-a",
        authority_snapshot="authority-a",
        verifier_id="verifier-a",
        interface_digest="interface-a",
        selection_cost=5,
    )
    memory = memory.record_success(
        RepairEpisode(
            episode_id="acq",
            phase=RepairPhase.ACQUISITION,
            object_evidence_digest="evidence-acq",
            **common,
        )
    )
    memory = memory.record_success(
        RepairEpisode(
            episode_id="cal",
            phase=RepairPhase.CALIBRATION,
            object_evidence_digest="evidence-cal",
            **common,
        )
    )
    return memory


def test_promoted_meta_memory_projection_preserves_rule_lookup_without_episodes():
    original = promoted_meta_memory()
    mg2 = MemoryGraphV2.from_meta_memory(original)
    restored = mg2.to_meta_memory()
    rule = original.rules[0]
    assert restored.episodes == ()
    assert restored.promoted_match(
        obstruction_fingerprint=rule.obstruction_fingerprint,
        portfolio_digest=rule.portfolio_digest,
        authority_snapshot=rule.authority_snapshot,
        verifier_id=rule.verifier_id,
        interface_digest=rule.interface_digest,
    ) == rule


def test_candidate_rule_is_not_imported_by_default():
    common = dict(
        obstruction_fingerprint="fp-candidate",
        strategy_id="candidate-strategy",
        strategy_version="v1",
        portfolio_digest="portfolio",
        authority_snapshot="authority",
        verifier_id="verifier",
        interface_digest="interface",
        selection_cost=1,
    )
    candidate = MetaMemory.empty().record_success(
        RepairEpisode(
            episode_id="only-acq",
            phase=RepairPhase.ACQUISITION,
            object_evidence_digest="candidate-evidence",
            **common,
        )
    )
    assert MemoryGraphV2.from_meta_memory(candidate).repair_rules == ()


def test_merge_is_commutative_associative_and_idempotent_for_compatible_memory():
    a = MemoryGraphV2(laws=(MemoryLaw("a", "a", "*", "", "v"),))
    b = MemoryGraphV2(capabilities=(sample_capability("b"),))
    c = MemoryGraphV2(repair_rules=(sample_rule("c"),))
    assert a.merge(a) == a
    assert a.merge(b) == b.merge(a)
    assert a.merge(b).merge(c) == a.merge(b.merge(c))


def test_merge_rejects_same_typed_id_with_different_payload():
    a = MemoryGraphV2(laws=(MemoryLaw("law-a", "x", "*", "", "v"),))
    b = MemoryGraphV2(laws=(MemoryLaw("law-a", "y", "*", "", "v"),))
    with pytest.raises(MemoryGraphConflict, match="law:law-a"):
        a.merge(b)


def test_revocation_is_monotone_across_merge():
    live = MemoryGraphV2(capabilities=(sample_capability("cap-a"),))
    revoked = live.revoke("capability", "cap-a", provenance="ablation")
    merged = live.merge(revoked)
    assert merged.to_capability_graph().active_ids() == ()
    assert ("capability", "cap-a") in {item.identity for item in merged.revocations}
```

- [ ] **Step 2: Run focused tests and confirm they fail**

```bash
python -m pytest -q tests/test_memory_graph_v2.py -k 'meta_memory or merge or revocation'
```

Expected: failures for missing methods.

- [ ] **Step 3: Implement MetaMemory adapters**

Import `MetaMemory` and implement:

```python
@classmethod
def from_meta_memory(
    cls,
    memory: MetaMemory,
    *,
    promoted_only: bool = True,
) -> "MemoryGraphV2":
    rules = tuple(
        rule
        for rule in memory.rules
        if (not promoted_only or rule.status is RepairRuleStatus.PROMOTED)
        and rule.status is not RepairRuleStatus.REVOKED
    )
    revocations = tuple(
        MemoryRevocation("repair_rule", rule.rule_id, rule.ablation_handle)
        for rule in memory.rules
        if rule.status is RepairRuleStatus.REVOKED
    )
    return cls(repair_rules=rules, revocations=revocations)


@property
def active_repair_rules(self) -> tuple[RepairRule, ...]:
    revoked = {r.target_id for r in self.revocations if r.target_kind == "repair_rule"}
    return tuple(rule for rule in self.repair_rules if rule.rule_id not in revoked)


def to_meta_memory(self) -> MetaMemory:
    return MetaMemory(rules=self.active_repair_rules, episodes=())
```

The restored MetaMemory is intentionally an active projection; it must preserve `promoted_match` semantics but never reconstruct historical episodes.

- [ ] **Step 4: Implement strict deterministic merge and revoke**

Use one helper per typed namespace:

```python
def _merge_by_id(kind: str, left, right, key):
    merged = {key(item): item for item in left}
    for item in right:
        ident = key(item)
        old = merged.get(ident)
        if old is None:
            merged[ident] = item
        elif old != item:
            raise MemoryGraphConflict(f"conflicting MG2 {kind}:{ident}")
    return tuple(merged[key] for key in sorted(merged))
```

Implement:

```python
def merge(self, other: "MemoryGraphV2") -> "MemoryGraphV2":
    return MemoryGraphV2(
        laws=_merge_by_id("law", self.laws, other.laws, lambda x: x.law_id),
        capabilities=_merge_by_id(
            "capability", self.capabilities, other.capabilities, lambda x: x.capability_id
        ),
        repair_rules=_merge_by_id(
            "repair_rule", self.repair_rules, other.repair_rules, lambda x: x.rule_id
        ),
        revocations=_merge_by_id(
            "revocation", self.revocations, other.revocations, lambda x: x.identity
        ),
    )


def revoke(
    self,
    target_kind: str,
    target_id: str,
    *,
    provenance: str = "",
) -> "MemoryGraphV2":
    tombstone = MemoryRevocation(target_kind, target_id, provenance)
    return self.merge(MemoryGraphV2(revocations=(tombstone,)))
```

For revocation merge, same `(target_kind, target_id)` with different provenance must not be treated as a semantic payload conflict. Canonicalize the provenance deterministically: choose identical provenance when equal; if one is empty, retain the non-empty one; if both are non-empty and differ, combine them as a sorted `|`-joined string. Put this logic in a dedicated `_merge_revocations()` helper instead of `_merge_by_id()`.

- [ ] **Step 5: Run all MG2 tests**

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: PASS.

- [ ] **Step 6: Add explicit validation tests for malformed active memory**

Add tests that assert:

```python
def test_active_repair_rule_must_be_promoted():
    candidate = RepairRule(
        **{**sample_rule().payload(), "status": "CANDIDATE"}
    )
```

Do not construct `RepairRule` from a dict splat that violates enum typing; instead use `dataclasses.replace(sample_rule(), status=RepairRuleStatus.CANDIDATE)` and assert `MemoryGraphV2(repair_rules=(candidate,))` raises `ValueError`.

Also test duplicate IDs and capability dependency cycles/missing dependencies by constructing the invalid MG2 and requiring constructor failure.

- [ ] **Step 7: Commit Task 3**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2.py
git commit -m "feat: add developmental memory and merge semantics to MG2"
```

---

### Task 4: Prove one combined MG2 restart preserves verified-meta-growth-v3 behavior

**Files:**
- Create: `tests/test_memory_graph_v2_integration.py`
- Modify: `realitygraph/memory_graph.py` only if the integration test exposes a missing adapter needed by the approved spec.

**Interfaces:**
- Consumes: `MemoryGraphV2`, existing `MetaSnapshot`/meta-growth fixtures and executor, existing object-level developmental state/capability graph from `verified_meta_growth_v3` path.
- Produces: an integration test proving a single MG2 carries both active object capability state and promoted repair rules through exact restart and preserves prospective behavior.

- [ ] **Step 1: Inspect the exact fixture/runtime entry points used by `verified_meta_growth_v3.py`**

Read:

```text
verified_meta_growth_v3.py
realitygraph/fixtures/meta_growth_v3.py
realitygraph/meta_executor.py
realitygraph/developmental_state.py
realitygraph/meta_snapshot.py
```

Identify the object capability graph field on the state and the existing future bundle construction. Do not modify those files in this task.

- [ ] **Step 2: Write the failing combined-restart integration test**

The test should follow the existing qualification sequence rather than importing its final summary as truth:

```python
from realitygraph.fixtures.meta_growth_v3 import (
    FAMILY_C,
    FAMILY_T,
    make_episode,
)
from realitygraph.memory_graph import MemoryGraphV2
from realitygraph.meta_executor import execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase


def test_mg2_combined_restart_preserves_future_meta_growth_routes():
    memory = MetaMemory.empty()

    # Acquisition and calibration establish promoted rules exactly as the
    # existing qualification does.
    for family in (FAMILY_C, FAMILY_T):
        bundle = make_episode(family, "acquisition", RepairPhase.ACQUISITION)
        result = execute_meta_growth(bundle.state, memory, bundle.spec)
        memory = result.meta_memory

    last_result = None
    for family in (FAMILY_C, FAMILY_T):
        bundle = make_episode(family, "calibration", RepairPhase.CALIBRATION)
        last_result = execute_meta_growth(bundle.state, memory, bundle.spec)
        memory = last_result.meta_memory

    assert last_result is not None

    object_graph = last_result.object_state.capability_graph
    combined = MemoryGraphV2.from_capability_graph(object_graph).merge(
        MemoryGraphV2.from_meta_memory(memory)
    )
    restarted = MemoryGraphV2.parse(combined.text())

    restarted_graph = restarted.to_capability_graph()
    restarted_meta = restarted.to_meta_memory()

    for family in (FAMILY_C, FAMILY_T):
        future_bundle = make_episode(family, "future", RepairPhase.FUTURE)
        future_state = future_bundle.state.with_capability_graph(restarted_graph)
        result = execute_meta_growth(future_state, restarted_meta, future_bundle.spec)
        assert result.rule_hit
        assert result.portfolio_search_calls == 0
        assert result.competitor_strategy_calls == 0
        assert result.selected_generation is not None
        assert result.selected_generation.future is not None
        assert result.selected_generation.future.grammar_search_calls == 0
        assert result.selected_generation.future.passed
```

Use the *actual* state replacement API discovered in Step 1. If `DevelopmentalState` uses `dataclasses.replace` rather than a `with_capability_graph()` method, use `dataclasses.replace(future_bundle.state, capability_graph=restarted_graph)` in the final test. Do not invent a new state API just for this test.

- [ ] **Step 3: Run the integration test and verify it fails for a concrete missing bridge, not because the test copied the wrong runtime API**

```bash
python -m pytest -q tests/test_memory_graph_v2_integration.py -vv
```

Expected initial failure: either missing MG2 bridge behavior or an exact mismatch that identifies what the serializer/projection failed to preserve.

- [ ] **Step 4: Implement the minimum bridge needed for the exact existing runtime shape**

Allowed examples:

- preserve a capability graph revocation that the first adapter omitted;
- add `MemoryGraphV2.combine_active_state(capability_graph, meta_memory)` as a convenience constructor if the test otherwise repeats stable adapter composition;
- add a projection helper that returns `(CapabilityGraph, MetaMemory)`.

Do **not** move execution logic into MG2 and do not rewrite the meta executor.

If a convenience API is added, use this exact signature:

```python
@classmethod
def from_active_state(
    cls,
    capability_graph: CapabilityGraph,
    meta_memory: MetaMemory,
) -> "MemoryGraphV2":
    return cls.from_capability_graph(capability_graph).merge(
        cls.from_meta_memory(meta_memory)
    )


def active_state(self) -> tuple[CapabilityGraph, MetaMemory]:
    return self.to_capability_graph(), self.to_meta_memory()
```

- [ ] **Step 5: Add MG2 ablation/revocation integration checks**

Extend the integration test with the existing promoted rules:

```python
for rule in restarted.active_repair_rules:
    ablated_memory = restarted.revoke(
        "repair_rule",
        rule.rule_id,
        provenance=rule.ablation_handle,
    )
    _, ablated_meta = ablated_memory.active_state()
    # Select the future family whose fingerprint matches this rule using the
    # same fixture helper used in the qualification.
    result = execute_meta_growth(future_state, ablated_meta, future_bundle.spec)
    assert not result.rule_hit
    assert result.portfolio_search_calls > 0
```

Also revoke an ancestor object capability and assert that `to_capability_graph().active_ids()` transitively drops dependent descendants, matching existing `CapabilityGraph.ablate()` semantics.

- [ ] **Step 6: Run the integration tests**

```bash
python -m pytest -q tests/test_memory_graph_v2_integration.py -vv
```

Expected: PASS.

- [ ] **Step 7: Run the authoritative existing meta-growth qualification test/script**

Run the existing relevant unit test(s), then:

```bash
python verified_meta_growth_v3.py
```

Expected output includes:

```text
PASS_VERIFIED_META_GROWTH_V3
CLOSED_BOUNDED_META_GROWTH_V3
```

The script must be unmodified for this milestone.

- [ ] **Step 8: Commit Task 4**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2_integration.py
git commit -m "test: qualify combined MG2 restart against meta growth"
```

---

### Task 5: Export MG2, document the memory boundary, and run full regression verification

**Files:**
- Modify: `realitygraph/__init__.py`
- Modify: `README.md`
- Modify: `tests/test_memory_graph_v2.py` only if an export test is useful.

**Interfaces:**
- Consumes: fully passing Tasks 1–4.
- Produces: stable public imports for `MemoryGraphV2`, `MemoryLaw`, `MemoryRevocation`, `MemoryGraphConflict`; README description of MG1/MG2 boundary.

- [ ] **Step 1: Add a failing public-export test**

Add:

```python
def test_mg2_public_exports_are_available():
    from realitygraph import (
        MemoryGraphConflict,
        MemoryGraphV2,
        MemoryLaw,
        MemoryRevocation,
    )
    assert MemoryGraphV2 is not None
    assert MemoryLaw is not None
    assert MemoryRevocation is not None
    assert MemoryGraphConflict is not None
```

- [ ] **Step 2: Run it and verify failure**

```bash
python -m pytest -q tests/test_memory_graph_v2.py::test_mg2_public_exports_are_available
```

Expected: import failure until exports are added.

- [ ] **Step 3: Export MG2 types from `realitygraph/__init__.py`**

Add the exact imports:

```python
from .memory_graph import (
    MemoryGraphConflict,
    MemoryGraphV2,
    MemoryLaw,
    MemoryRevocation,
)
```

If the file maintains `__all__`, add these four names there as well.

- [ ] **Step 4: Update README without changing claim boundaries**

Add a concise section near `Ledger and .mg`:

```markdown
### MG2 typed active memory

`MG1` remains the tiny canonical law-memory format. The MG2 milestone extends
`.mg` into one typed active-memory graph that can carry legacy laws, verified
`FiniteCapability` objects, promoted developmental repair rules, and monotone
revocations while leaving raw episodes and causal history in the ledger.

```text
ledger / episodes / search history
              -> verify + compress
              -> MG2 consequential present
                   | laws
                   | capabilities
                   | promoted repair rules
                   | revocations
```

MG2 does not replace the verifier, capability executor, developmental executor,
or causal ledger. It is the canonical restartable representation of the active
state those components have already earned.
```

Do not add claims of open-ended self-improvement, universal transfer, autonomous ontology invention, or stronger scientific results.

- [ ] **Step 5: Run focused MG2 tests**

```bash
python -m pytest -q tests/test_memory_graph_v2.py tests/test_memory_graph_v2_integration.py
```

Expected: PASS.

- [ ] **Step 6: Run full repository tests**

```bash
python -m pytest -q
```

Expected: zero failures.

- [ ] **Step 7: Run the frozen qualifying demos required by README/branch scope**

At minimum run:

```bash
python verified_language_growth_closure_v2.py
python verified_meta_growth_v3.py
```

Expected outputs include their existing green verdicts; MG2 does not alter those scripts.

If the branch CI normally runs `python -m unittest discover -s tests -v`, run it too:

```bash
python -m unittest discover -s tests -v
```

Expected: zero failures/errors.

- [ ] **Step 8: Verify the final diff stays inside milestone 1**

Run:

```bash
git diff --stat verified-meta-growth-v3...HEAD
git diff --name-only verified-meta-growth-v3...HEAD
```

Expected implementation files are limited to:

```text
README.md
docs/superpowers/specs/2026-09-17-mg2-memory-graph-design.md
docs/superpowers/plans/2026-09-17-mg2-memory-graph.md
realitygraph/__init__.py
realitygraph/memory_graph.py
tests/test_memory_graph_v2.py
tests/test_memory_graph_v2_integration.py
```

If unrelated files appear, remove those changes before completion.

- [ ] **Step 9: Commit Task 5**

```bash
git add README.md realitygraph/__init__.py tests/test_memory_graph_v2.py
git commit -m "docs: expose MG2 as canonical typed active memory"
```

---

## Final Verification Checklist

Before claiming MG2 milestone completion, run fresh verification and record exact outputs:

- [ ] `python -m pytest -q tests/test_memory_graph_v2.py tests/test_memory_graph_v2_integration.py`
- [ ] `python -m pytest -q`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `python verified_language_growth_closure_v2.py`
- [ ] `python verified_meta_growth_v3.py`
- [ ] confirm exact MG2 serialize/parse restart in the integration test
- [ ] confirm MG1 round trip is unchanged
- [ ] confirm capability revocation transitively affects descendants exactly as `CapabilityGraph` does
- [ ] confirm promoted repair rule lookup works after MG2 restart with no fabricated `RepairEpisode` bodies
- [ ] confirm repair-rule revocation restores cold portfolio search
- [ ] confirm same-identity/different-payload merge raises `MemoryGraphConflict`
- [ ] confirm no scientific claim beyond the existing branch boundary was added
- [ ] inspect `git diff --name-only verified-meta-growth-v3...HEAD` for scope drift

Only after every required command is freshly green may the branch be described as complete.
