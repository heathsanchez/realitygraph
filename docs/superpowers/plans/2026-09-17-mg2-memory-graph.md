# MG2 Memory Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical typed `MG2` active-memory format that unifies legacy laws, executable capabilities, promoted developmental repair rules, and revocations while preserving MG1 compatibility and the existing `verified-meta-growth-v3` prospective behavior.

**Architecture:** Add `realitygraph/memory_graph.py` as a serialization/adaptation layer over the existing authoritative types `MG`/`Law`, `FiniteCapability`/`CapabilityGraph`, and `RepairRule`/`MetaMemory`. MG2 stores the compressed consequential present only; raw episodes and causal history remain outside `.mg`. The first milestone proves canonical restart, strict merge/revocation behavior, lossless object-capability projection, behaviorally sufficient promoted-rule projection, and unchanged meta-growth future behavior after one combined MG2 restart.

**Tech Stack:** Python 3.12, frozen dataclasses, `canonical_json`/`canonical_digest` from `realitygraph.developmental_types`, pytest/unittest, existing RealityGraph developmental executors and frozen meta-growth fixtures.

**Spec:** `docs/superpowers/specs/2026-09-17-mg2-memory-graph-design.md`

## Global Constraints

- `MG1` remains fully supported and unchanged.
- Existing executors are not rewritten in this milestone.
- MG2 stores active consequential state, not raw acquisition/calibration episodes, search traces, or the causal event DAG.
- `MemoryGraphV2.parse(MemoryGraphV2.text())` must restart exactly and canonically.
- Record ordering must not affect MG2 text or digest.
- Existing authority, verifier, interface, certificate, provenance/evidence, dependency, cost, and ablation identities must be preserved.
- Same typed identity with different payload is always an explicit `MemoryGraphConflict`, including revocation records with different provenance.
- `FiniteCapability`, `CapabilityGraph`, `RepairRule`, and `MetaMemory` remain semantically authoritative.
- Candidate repair rules are never admitted to MG2 active memory.
- MG2 never fabricates `RepairEpisode` bodies.
- A revocation tombstone may exist without the corresponding record so that merging with stale memory cannot re-activate it.
- A stored record may coexist with its revocation tombstone; the active projection excludes it.
- No scientific claim is strengthened merely because storage is unified.

---

## File Structure

**Create**

- `realitygraph/memory_graph.py` — MG2 record types, canonical serialization, validation, adapters, merge, active views, and revocation.
- `tests/test_memory_graph_v2.py` — unit and adapter tests.
- `tests/test_memory_graph_v2_integration.py` — combined object+meta restart and ablation qualification.

**Modify**

- `realitygraph/__init__.py` — public MG2 exports.
- `README.md` — document the MG1/MG2/ledger boundary.

**Must remain semantically unchanged**

- `realitygraph/mg.py`
- `realitygraph/capability.py`
- `realitygraph/capability_graph.py`
- `realitygraph/meta_memory.py`
- `realitygraph/meta_executor.py`
- `realitygraph/developmental_executor.py`
- `verified_meta_growth_v3.py`

---

### Task 1: Canonical MG2 core

**Files:**
- Create: `realitygraph/memory_graph.py`
- Create: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Consumes: `FiniteCapability`, `CapabilityGraph`, `RepairRule`, `RepairRuleStatus`, `canonical_json`, `canonical_digest`.
- Produces:
  - `MemoryGraphConflict`
  - `MemoryLaw`
  - `MemoryRevocation`
  - `MemoryGraphV2`
  - `MemoryGraphV2.text() -> str`
  - `MemoryGraphV2.parse(text: str) -> MemoryGraphV2`
  - `MemoryGraphV2.digest -> str`

- [ ] **Step 1: Write the failing core tests**

Create `tests/test_memory_graph_v2.py` with these shared fixtures and tests:

```python
from dataclasses import replace

import pytest

from realitygraph.capability import FiniteCapability
from realitygraph.memory_graph import (
    MemoryGraphConflict,
    MemoryGraphV2,
    MemoryLaw,
    MemoryRevocation,
)
from realitygraph.meta_memory import RepairRule, RepairRuleStatus


def sample_capability(capability_id: str = "cap-a", dependencies=()) -> FiniteCapability:
    return FiniteCapability(
        capability_id=capability_id,
        input_type="bit",
        output_type="bit",
        semantics=(("0", "1"), ("1", "0")),
        guard_inputs=("0", "1"),
        certificate_id=f"cert-{capability_id}",
        dependencies=tuple(dependencies),
        authority_snapshot="authority-a",
        verifier_id="verifier-a",
        provenance_ids=(f"prov-{capability_id}",),
        cost=3,
    )


def sample_rule(rule_id: str = "repair-rule-a") -> RepairRule:
    return RepairRule(
        rule_id=rule_id,
        obstruction_fingerprint="fp-a",
        strategy_id="add_observable",
        strategy_version="v1",
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
        revocations=(MemoryRevocation("law", "old-law", "prov-revoke"),),
    )
    restarted = MemoryGraphV2.parse(memory.text())
    assert restarted == memory
    assert restarted.text() == memory.text()


def test_record_order_does_not_change_text_or_digest():
    laws = (
        MemoryLaw("law-b", "b", "scope-b", "prov-b", "verifier-a"),
        MemoryLaw("law-a", "a", "scope-a", "prov-a", "verifier-a"),
    )
    left = MemoryGraphV2(laws=laws)
    right = MemoryGraphV2(laws=tuple(reversed(laws)))
    assert left.text() == right.text()
    assert left.digest == right.digest


def test_candidate_repair_rule_is_not_valid_active_memory():
    candidate = replace(sample_rule(), status=RepairRuleStatus.CANDIDATE)
    with pytest.raises(ValueError, match="PROMOTED"):
        MemoryGraphV2(repair_rules=(candidate,))


def test_duplicate_typed_id_is_rejected():
    with pytest.raises(ValueError, match="duplicate MG2 law"):
        MemoryGraphV2(
            laws=(
                MemoryLaw("same", "x", "*", "", "v"),
                MemoryLaw("same", "x", "*", "", "v"),
            )
        )
```

- [ ] **Step 2: Run the tests and verify red state**

Run:

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: import/collection failure because `realitygraph.memory_graph` does not exist.

- [ ] **Step 3: Implement the MG2 core types and canonical payloads**

Create `realitygraph/memory_graph.py` beginning with:

```python
from __future__ import annotations

import json
from dataclasses import dataclass

from .capability import FiniteCapability
from .capability_graph import CapabilityGraph
from .developmental_types import canonical_digest, canonical_json
from .meta_memory import MetaMemory, RepairRule, RepairRuleStatus
from .mg import Law, MG


class MemoryGraphConflict(ValueError):
    """Raised when one typed MG2 identity has incompatible payloads."""


@dataclass(frozen=True)
class MemoryLaw:
    law_id: str
    expr: str
    scope: str = "*"
    provenance: str = ""
    verifier_id: str = ""

    def __post_init__(self) -> None:
        if not self.law_id:
            raise ValueError("MG2 law requires law_id")

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
            raise ValueError("MG2 revocation requires target_id")

    @property
    def identity(self) -> tuple[str, str]:
        return self.target_kind, self.target_id

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

Use explicit converters for the existing capability type:

```python
def _capability_payload(capability: FiniteCapability) -> dict[str, object]:
    return {
        "capability_id": capability.capability_id,
        "input_type": capability.input_type,
        "output_type": capability.output_type,
        "semantics": [list(row) for row in capability.semantics],
        "guard_inputs": list(capability.guard_inputs),
        "certificate_id": capability.certificate_id,
        "dependencies": list(capability.dependencies),
        "authority_snapshot": capability.authority_snapshot,
        "verifier_id": capability.verifier_id,
        "provenance_ids": list(capability.provenance_ids),
        "cost": capability.cost,
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

Implement the container:

```python
@dataclass(frozen=True)
class MemoryGraphV2:
    laws: tuple[MemoryLaw, ...] = ()
    capabilities: tuple[FiniteCapability, ...] = ()
    repair_rules: tuple[RepairRule, ...] = ()
    revocations: tuple[MemoryRevocation, ...] = ()

    def __post_init__(self) -> None:
        self._reject_duplicate_ids()
        if any(rule.status is not RepairRuleStatus.PROMOTED for rule in self.repair_rules):
            raise ValueError("MG2 active repair rules must be PROMOTED")
        object.__setattr__(self, "laws", tuple(sorted(self.laws, key=lambda item: item.law_id)))
        object.__setattr__(
            self,
            "capabilities",
            tuple(sorted(self.capabilities, key=lambda item: item.capability_id)),
        )
        object.__setattr__(
            self,
            "repair_rules",
            tuple(sorted(self.repair_rules, key=lambda item: item.rule_id)),
        )
        object.__setattr__(
            self,
            "revocations",
            tuple(sorted(self.revocations, key=lambda item: item.identity)),
        )
        known_caps = {cap.capability_id for cap in self.capabilities}
        revoked_known_caps = tuple(
            row.target_id
            for row in self.revocations
            if row.target_kind == "capability" and row.target_id in known_caps
        )
        CapabilityGraph(self.capabilities, revoked_known_caps)

    def _reject_duplicate_ids(self) -> None:
        def reject(kind: str, values) -> None:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate MG2 {kind} identity")

        reject("law", [item.law_id for item in self.laws])
        reject("capability", [item.capability_id for item in self.capabilities])
        reject("repair rule", [item.rule_id for item in self.repair_rules])
        reject("revocation", [item.identity for item in self.revocations])

    def payload(self) -> dict[str, object]:
        return {
            "version": "MG2",
            "laws": [item.payload() for item in self.laws],
            "capabilities": [_capability_payload(item) for item in self.capabilities],
            "repair_rules": [item.payload() for item in self.repair_rules],
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
            capabilities=tuple(
                _capability_from_payload(row) for row in payload["capabilities"]
            ),
            repair_rules=tuple(
                RepairRule.from_payload(row) for row in payload["repair_rules"]
            ),
            revocations=tuple(
                MemoryRevocation.from_payload(row) for row in payload["revocations"]
            ),
        )
        if memory.text() != text:
            raise ValueError("non-canonical MG2 memory")
        return memory
```

The constructor intentionally allows tombstones whose target is absent and allows a stored record to coexist with a tombstone; active projections added in Task 2/3 decide what is live.

- [ ] **Step 4: Run the core tests and verify green state**

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2.py
git commit -m "feat: add canonical MG2 memory graph core"
```

---

### Task 2: MG1 and CapabilityGraph adapters

**Files:**
- Modify: `realitygraph/memory_graph.py`
- Modify: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Produces:
  - `MemoryGraphV2.from_mg1(memory: MG) -> MemoryGraphV2`
  - `MemoryGraphV2.to_mg1(*, law_only: bool = False) -> MG`
  - `MemoryGraphV2.from_capability_graph(graph: CapabilityGraph) -> MemoryGraphV2`
  - `MemoryGraphV2.to_capability_graph() -> CapabilityGraph`
  - `MemoryGraphV2.active_laws`
  - `MemoryGraphV2.active_capabilities`

- [ ] **Step 1: Add failing adapter tests**

Append:

```python
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.mg import Law, MG


def test_mg1_to_mg2_to_mg1_is_exact_for_law_only_memory():
    original = MG(
        "verifier-a",
        (
            Law("law-b", "expr-b", "scope-b", "prov-b"),
            Law("law-a", "expr-a", "scope-a", "prov-a"),
        ),
    )
    restored = MemoryGraphV2.from_mg1(original).to_mg1()
    assert restored.text() == original.text()


def test_whole_memory_to_mg1_refuses_silent_non_law_loss():
    memory = MemoryGraphV2(
        laws=(MemoryLaw("law-a", "x", "*", "", "verifier-a"),),
        capabilities=(sample_capability(),),
    )
    with pytest.raises(ValueError, match="non-law"):
        memory.to_mg1()


def test_capability_graph_round_trip_preserves_revocation_and_active_ids():
    parent = sample_capability("parent")
    child = sample_capability("child", dependencies=("parent",))
    original = CapabilityGraph((parent, child), revoked_ids=("parent",))
    restored = MemoryGraphV2.from_capability_graph(original).to_capability_graph()
    assert restored.capabilities == original.capabilities
    assert restored.revoked_ids == original.revoked_ids
    assert restored.active_ids() == ()


def test_capability_revocation_tombstone_survives_without_local_record():
    memory = MemoryGraphV2(
        revocations=(MemoryRevocation("capability", "remote-cap", "remote-ablation"),)
    )
    restarted = MemoryGraphV2.parse(memory.text())
    assert restarted.revocations == memory.revocations
```

- [ ] **Step 2: Run focused tests and verify red state**

```bash
python -m pytest -q tests/test_memory_graph_v2.py -k 'mg1 or capability_graph or tombstone'
```

Expected: failures because adapter methods do not exist.

- [ ] **Step 3: Implement law and capability active views/adapters**

Add to `MemoryGraphV2`:

```python
@property
def active_laws(self) -> tuple[MemoryLaw, ...]:
    revoked = {
        row.target_id for row in self.revocations if row.target_kind == "law"
    }
    return tuple(item for item in self.laws if item.law_id not in revoked)


@property
def active_capabilities(self) -> tuple[FiniteCapability, ...]:
    graph = self.to_capability_graph()
    active = set(graph.active_ids())
    return tuple(
        item for item in self.capabilities if item.capability_id in active
    )


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
        raise ValueError(
            "MG2 contains non-law active-memory records; request law_only projection"
        )
    laws = self.active_laws
    verifiers = {item.verifier_id for item in laws}
    if len(verifiers) > 1:
        raise ValueError("MG2 law layer has incompatible verifier identities")
    verifier = next(iter(verifiers), "")
    return MG(
        verifier,
        tuple(
            Law(item.law_id, item.expr, item.scope, item.provenance)
            for item in laws
        ),
    )


@classmethod
def from_capability_graph(cls, graph: CapabilityGraph) -> "MemoryGraphV2":
    return cls(
        capabilities=graph.capabilities,
        revocations=tuple(
            MemoryRevocation("capability", ident)
            for ident in graph.revoked_ids
        ),
    )


def to_capability_graph(self) -> CapabilityGraph:
    known = {item.capability_id for item in self.capabilities}
    revoked = tuple(
        row.target_id
        for row in self.revocations
        if row.target_kind == "capability" and row.target_id in known
    )
    return CapabilityGraph(self.capabilities, tuple(sorted(revoked)))
```

`to_mg1(law_only=True)` is the explicit lossy projection for callers that knowingly discard MG2-only layers; whole-memory conversion must otherwise fail rather than silently drop them.

- [ ] **Step 4: Run MG2 adapter tests**

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: PASS.

- [ ] **Step 5: Run existing capability/developmental regression tests**

```bash
python -m pytest -q \
  tests/test_capability_algebra.py \
  tests/test_developmental_state.py \
  tests/test_developmental_executor.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2.py
git commit -m "feat: bridge MG1 and capability graph into MG2"
```

---

### Task 3: Promoted MetaMemory, strict merge, and revocation

**Files:**
- Modify: `realitygraph/memory_graph.py`
- Modify: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Produces:
  - `MemoryGraphV2.from_meta_memory(memory: MetaMemory, *, promoted_only: bool = True) -> MemoryGraphV2`
  - `MemoryGraphV2.to_meta_memory() -> MetaMemory`
  - `MemoryGraphV2.active_repair_rules`
  - `MemoryGraphV2.merge(other: MemoryGraphV2) -> MemoryGraphV2`
  - `MemoryGraphV2.revoke(target_kind: str, target_id: str, *, provenance: str = "") -> MemoryGraphV2`
  - `MemoryGraphV2.from_active_state(capability_graph, meta_memory) -> MemoryGraphV2`
  - `MemoryGraphV2.active_state() -> tuple[CapabilityGraph, MetaMemory]`

- [ ] **Step 1: Add failing MetaMemory and merge tests**

Append:

```python
from realitygraph.meta_memory import MetaMemory, RepairEpisode, RepairPhase


def promoted_meta_memory() -> MetaMemory:
    common = dict(
        obstruction_fingerprint="fp-promoted",
        strategy_id="add_observable",
        strategy_version="v1",
        portfolio_digest="portfolio-a",
        authority_snapshot="authority-a",
        verifier_id="verifier-a",
        interface_digest="interface-a",
        selection_cost=5,
    )
    memory = MetaMemory.empty()
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


def test_promoted_meta_projection_preserves_lookup_without_episode_bodies():
    original = promoted_meta_memory()
    mg2 = MemoryGraphV2.from_meta_memory(original)
    restored = mg2.to_meta_memory()
    rule = next(item for item in original.rules if item.status is RepairRuleStatus.PROMOTED)
    assert restored.episodes == ()
    assert restored.promoted_match(
        obstruction_fingerprint=rule.obstruction_fingerprint,
        portfolio_digest=rule.portfolio_digest,
        authority_snapshot=rule.authority_snapshot,
        verifier_id=rule.verifier_id,
        interface_digest=rule.interface_digest,
    ) == rule


def test_candidate_meta_rule_is_excluded_by_default():
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
    memory = MetaMemory.empty().record_success(
        RepairEpisode(
            episode_id="only-acq",
            phase=RepairPhase.ACQUISITION,
            object_evidence_digest="candidate-evidence",
            **common,
        )
    )
    assert MemoryGraphV2.from_meta_memory(memory).repair_rules == ()


def test_merge_is_idempotent_commutative_and_associative_when_compatible():
    a = MemoryGraphV2(laws=(MemoryLaw("a", "a", "*", "", "v"),))
    b = MemoryGraphV2(capabilities=(sample_capability("b"),))
    c = MemoryGraphV2(repair_rules=(sample_rule("c"),))
    assert a.merge(a) == a
    assert a.merge(b) == b.merge(a)
    assert a.merge(b).merge(c) == a.merge(b.merge(c))


def test_merge_rejects_same_typed_identity_with_different_payload():
    left = MemoryGraphV2(laws=(MemoryLaw("law-a", "x", "*", "", "v"),))
    right = MemoryGraphV2(laws=(MemoryLaw("law-a", "y", "*", "", "v"),))
    with pytest.raises(MemoryGraphConflict, match="law:law-a"):
        left.merge(right)


def test_merge_rejects_revocation_identity_with_different_provenance():
    left = MemoryGraphV2(
        revocations=(MemoryRevocation("capability", "cap-a", "evidence-a"),)
    )
    right = MemoryGraphV2(
        revocations=(MemoryRevocation("capability", "cap-a", "evidence-b"),)
    )
    with pytest.raises(MemoryGraphConflict, match="revocation"):
        left.merge(right)


def test_revocation_is_monotone_when_merged_with_stale_live_memory():
    live = MemoryGraphV2(capabilities=(sample_capability("cap-a"),))
    tombstone = MemoryGraphV2(
        revocations=(MemoryRevocation("capability", "cap-a", "ablation-a"),)
    )
    merged = live.merge(tombstone)
    assert merged.to_capability_graph().active_ids() == ()
    assert merged.capabilities == live.capabilities
```

- [ ] **Step 2: Run focused tests and verify red state**

```bash
python -m pytest -q tests/test_memory_graph_v2.py -k 'meta or merge or revocation'
```

Expected: failures for missing methods.

- [ ] **Step 3: Implement promoted repair-rule projection**

Add:

```python
@property
def active_repair_rules(self) -> tuple[RepairRule, ...]:
    revoked = {
        row.target_id
        for row in self.revocations
        if row.target_kind == "repair_rule"
    }
    return tuple(
        item for item in self.repair_rules if item.rule_id not in revoked
    )


@classmethod
def from_meta_memory(
    cls,
    memory: MetaMemory,
    *,
    promoted_only: bool = True,
) -> "MemoryGraphV2":
    if not promoted_only and any(
        item.status is RepairRuleStatus.CANDIDATE for item in memory.rules
    ):
        raise ValueError("MG2 active memory cannot import candidate repair rules")
    rules = tuple(
        item
        for item in memory.rules
        if item.status is RepairRuleStatus.PROMOTED
    )
    revocations = tuple(
        MemoryRevocation("repair_rule", item.rule_id, item.ablation_handle)
        for item in memory.rules
        if item.status is RepairRuleStatus.REVOKED
    )
    return cls(repair_rules=rules, revocations=revocations)


def to_meta_memory(self) -> MetaMemory:
    return MetaMemory(rules=self.active_repair_rules, episodes=())
```

This is intentionally a future-execution projection. It preserves promoted matching but cannot reconstruct historical episode bodies.

- [ ] **Step 4: Implement strict typed merge and revocation**

Add:

```python
def _merge_by_identity(kind: str, left, right, key):
    merged = {key(item): item for item in left}
    for item in right:
        ident = key(item)
        previous = merged.get(ident)
        if previous is None:
            merged[ident] = item
        elif previous != item:
            raise MemoryGraphConflict(f"conflicting MG2 {kind}:{ident}")
    return tuple(merged[ident] for ident in sorted(merged))
```

Then:

```python
def merge(self, other: "MemoryGraphV2") -> "MemoryGraphV2":
    return MemoryGraphV2(
        laws=_merge_by_identity(
            "law", self.laws, other.laws, lambda item: item.law_id
        ),
        capabilities=_merge_by_identity(
            "capability",
            self.capabilities,
            other.capabilities,
            lambda item: item.capability_id,
        ),
        repair_rules=_merge_by_identity(
            "repair_rule",
            self.repair_rules,
            other.repair_rules,
            lambda item: item.rule_id,
        ),
        revocations=_merge_by_identity(
            "revocation",
            self.revocations,
            other.revocations,
            lambda item: item.identity,
        ),
    )


def revoke(
    self,
    target_kind: str,
    target_id: str,
    *,
    provenance: str = "",
) -> "MemoryGraphV2":
    return self.merge(
        MemoryGraphV2(
            revocations=(MemoryRevocation(target_kind, target_id, provenance),)
        )
    )


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

- [ ] **Step 5: Run MG2 unit/adapter tests**

```bash
python -m pytest -q tests/test_memory_graph_v2.py
```

Expected: PASS.

- [ ] **Step 6: Run existing meta/developmental regression tests**

```bash
python -m pytest -q \
  tests/test_meta_executor.py \
  tests/test_developmental_state.py \
  tests/test_developmental_executor.py \
  tests/test_capability_algebra.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add realitygraph/memory_graph.py tests/test_memory_graph_v2.py
git commit -m "feat: unify promoted developmental memory in MG2"
```

---

### Task 4: Combined MG2 restart qualification against meta-growth V3

**Files:**
- Create: `tests/test_memory_graph_v2_integration.py`

**Interfaces:**
- Consumes: frozen V3 fixtures, `execute_meta_growth`, `MemoryGraphV2`, `dataclasses.replace`.
- Produces: a direct proof that one MG2 can carry both calibration object capabilities plus promoted meta rules, restart canonically, and preserve sealed-future rule reuse and ablation behavior.

- [ ] **Step 1: Write the failing combined-restart integration test**

Create `tests/test_memory_graph_v2_integration.py`:

```python
from dataclasses import replace

from realitygraph.fixtures.meta_growth_v3 import (
    ADD_FINITE_MEMORY_2,
    ADD_OBSERVABLE,
    FAMILY_C,
    FAMILY_T,
    make_episode,
)
from realitygraph.memory_graph import MemoryGraphV2
from realitygraph.meta_executor import execute_meta_growth
from realitygraph.meta_memory import MetaMemory, RepairPhase


def build_calibrated_state():
    memory = MetaMemory.empty()

    c_acq_bundle = make_episode(FAMILY_C, "acquisition", RepairPhase.ACQUISITION)
    c_acq = execute_meta_growth(c_acq_bundle.state, memory, c_acq_bundle.spec)
    memory = c_acq.meta_memory

    t_acq_bundle = make_episode(FAMILY_T, "acquisition", RepairPhase.ACQUISITION)
    t_acq = execute_meta_growth(t_acq_bundle.state, memory, t_acq_bundle.spec)
    memory = t_acq.meta_memory

    c_cal_bundle = make_episode(FAMILY_C, "calibration", RepairPhase.CALIBRATION)
    c_cal = execute_meta_growth(c_cal_bundle.state, memory, c_cal_bundle.spec)
    memory = c_cal.meta_memory

    t_cal_bundle = make_episode(FAMILY_T, "calibration", RepairPhase.CALIBRATION)
    t_cal = execute_meta_growth(t_cal_bundle.state, memory, t_cal_bundle.spec)
    memory = t_cal.meta_memory

    return c_cal, t_cal, memory


def combined_mg2_after_calibration():
    c_cal, t_cal, memory = build_calibrated_state()
    combined = MemoryGraphV2.from_capability_graph(
        c_cal.object_state.capability_graph
    ).merge(
        MemoryGraphV2.from_capability_graph(t_cal.object_state.capability_graph)
    ).merge(
        MemoryGraphV2.from_meta_memory(memory)
    )
    return c_cal, t_cal, memory, MemoryGraphV2.parse(combined.text())


def test_combined_mg2_restart_preserves_both_future_rule_hits():
    c_cal, t_cal, memory, restarted = combined_mg2_after_calibration()
    restarted_graph, restarted_meta = restarted.active_state()

    expected_ids = {
        c_cal.selected_generation.capability.capability_id,
        t_cal.selected_generation.capability.capability_id,
    }
    assert expected_ids.issubset(set(restarted_graph.active_ids()))
    assert restarted_meta.episodes == ()

    for family in (FAMILY_C, FAMILY_T):
        future_bundle = make_episode(family, "future", RepairPhase.FUTURE)
        future_state = replace(
            future_bundle.state,
            capability_graph=restarted_graph,
        )
        result = execute_meta_growth(
            future_state,
            restarted_meta,
            future_bundle.spec,
        )
        assert result.rule_hit
        assert result.portfolio_search_calls == 0
        assert result.competitor_strategy_calls == 0
        assert result.selected_generation is not None
        assert result.selected_generation.future is not None
        assert result.selected_generation.future.grammar_search_calls == 0
        assert result.selected_generation.future.passed
```

The existing V3 fixture creates family-specific seed states. The integration test deliberately replaces only their `capability_graph` with the combined restarted graph; it does not transplant grammar, terminal records, or other task-specific state.

- [ ] **Step 2: Run the integration test and verify red state**

```bash
python -m pytest -q tests/test_memory_graph_v2_integration.py -vv
```

Expected: failure until MG2 adapters are complete enough for the combined restart.

- [ ] **Step 3: Add repair-rule ablation checks to the integration test**

Append:

```python
def test_mg2_repair_rule_revocation_restores_cold_portfolio_search():
    _, _, _, restarted = combined_mg2_after_calibration()
    restarted_graph, _ = restarted.active_state()

    cases = (
        (FAMILY_C, ADD_OBSERVABLE),
        (FAMILY_T, ADD_FINITE_MEMORY_2),
    )
    for family, strategy_id in cases:
        rule = next(
            item for item in restarted.active_repair_rules
            if item.strategy_id == strategy_id
        )
        ablated = restarted.revoke(
            "repair_rule",
            rule.rule_id,
            provenance=rule.ablation_handle,
        )
        _, ablated_meta = ablated.active_state()
        future_bundle = make_episode(family, "future", RepairPhase.FUTURE)
        future_state = replace(
            future_bundle.state,
            capability_graph=restarted_graph,
        )
        result = execute_meta_growth(
            future_state,
            ablated_meta,
            future_bundle.spec,
        )
        assert not result.rule_hit
        assert result.portfolio_search_calls > 0
        assert result.selected_strategy_id == strategy_id
```

- [ ] **Step 4: Add object-capability revocation check**

Append:

```python
def test_mg2_capability_revocation_uses_existing_dependency_semantics():
    c_cal, _, _, restarted = combined_mg2_after_calibration()
    capability_id = c_cal.selected_generation.capability.capability_id
    ablated = restarted.revoke(
        "capability",
        capability_id,
        provenance="integration-capability-ablation",
    )
    graph = ablated.to_capability_graph()
    assert capability_id not in graph.active_ids()
```

Transitive dependency behavior is already covered by the parent/child unit test from Task 2 and remains delegated to `CapabilityGraph.active_ids()`.

- [ ] **Step 5: Run integration tests**

```bash
python -m pytest -q tests/test_memory_graph_v2_integration.py -vv
```

Expected: PASS.

- [ ] **Step 6: Run the authoritative existing V3 qualification unchanged**

```bash
python verified_meta_growth_v3.py
```

Expected output contains:

```text
PASS_VERIFIED_META_GROWTH_V3
CLOSED_BOUNDED_META_GROWTH_V3
```

`verified_meta_growth_v3.py` must have no diff.

- [ ] **Step 7: Commit Task 4**

```bash
git add tests/test_memory_graph_v2_integration.py
git commit -m "test: qualify combined MG2 restart against meta growth"
```

---

### Task 5: Public exports, README boundary, and full verification

**Files:**
- Modify: `realitygraph/__init__.py`
- Modify: `README.md`
- Modify: `tests/test_memory_graph_v2.py`

**Interfaces:**
- Produces public imports:
  - `MemoryGraphConflict`
  - `MemoryGraphV2`
  - `MemoryLaw`
  - `MemoryRevocation`

- [ ] **Step 1: Add a failing public-export test**

Append:

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

- [ ] **Step 2: Run export test and verify red state**

```bash
python -m pytest -q tests/test_memory_graph_v2.py::test_mg2_public_exports_are_available
```

Expected: import failure.

- [ ] **Step 3: Export the four MG2 public types**

In `realitygraph/__init__.py`, add:

```python
from .memory_graph import (
    MemoryGraphConflict,
    MemoryGraphV2,
    MemoryLaw,
    MemoryRevocation,
)
```

Add these exact names to the existing `__all__` list:

```python
    "MemoryGraphConflict",
    "MemoryGraphV2",
    "MemoryLaw",
    "MemoryRevocation",
```

- [ ] **Step 4: Add the MG2 section next to the existing Ledger/.mg section in README**

Use this text:

```markdown
### MG2 typed active memory

`MG1` remains the tiny canonical law-memory format. MG2 extends `.mg` into one
typed active Memory Graph that can carry legacy laws, verified finite
capabilities, promoted developmental repair rules, and explicit revocations.
Raw episodes, candidate search traces, and causal history remain in the ledger.

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
or causal ledger. It is a canonical restartable representation of active state
that those components have already earned.
```

Do not add open-ended self-development, universal-transfer, or ontology-invention claims.

- [ ] **Step 5: Run focused MG2 tests**

```bash
python -m pytest -q \
  tests/test_memory_graph_v2.py \
  tests/test_memory_graph_v2_integration.py
```

Expected: PASS.

- [ ] **Step 6: Run full pytest regression**

```bash
python -m pytest -q
```

Expected: zero failures.

- [ ] **Step 7: Run unittest discovery because the repository README requires it**

```bash
python -m unittest discover -s tests -v
```

Expected: zero failures/errors.

- [ ] **Step 8: Re-run the two developmental qualifications nearest the MG2 boundary**

```bash
python verified_language_growth_closure_v2.py
python verified_meta_growth_v3.py
```

Expected: their existing green verdicts, including `PASS_VERIFIED_META_GROWTH_V3` and `CLOSED_BOUNDED_META_GROWTH_V3`.

- [ ] **Step 9: Verify branch scope**

```bash
git diff --name-only verified-meta-growth-v3...HEAD
```

The only implementation/documentation paths allowed in this milestone are:

```text
README.md
docs/superpowers/specs/2026-09-17-mg2-memory-graph-design.md
docs/superpowers/plans/2026-09-17-mg2-memory-graph.md
realitygraph/__init__.py
realitygraph/memory_graph.py
tests/test_memory_graph_v2.py
tests/test_memory_graph_v2_integration.py
```

Also verify the protected executor files have no diff:

```bash
git diff --exit-code verified-meta-growth-v3...HEAD -- \
  realitygraph/mg.py \
  realitygraph/capability.py \
  realitygraph/capability_graph.py \
  realitygraph/meta_memory.py \
  realitygraph/meta_executor.py \
  realitygraph/developmental_executor.py \
  verified_meta_growth_v3.py
```

Expected: exit code 0.

- [ ] **Step 10: Commit Task 5**

```bash
git add README.md realitygraph/__init__.py tests/test_memory_graph_v2.py
git commit -m "docs: expose MG2 as canonical typed active memory"
```

---

## Final Verification Checklist

Fresh evidence is required before any completion claim:

- [ ] `python -m pytest -q tests/test_memory_graph_v2.py tests/test_memory_graph_v2_integration.py`
- [ ] `python -m pytest -q`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `python verified_language_growth_closure_v2.py`
- [ ] `python verified_meta_growth_v3.py`
- [ ] MG1 law-only round trip is byte-identical via `MG.text()`.
- [ ] MG2 parse/text restart is exact and digest-stable.
- [ ] CapabilityGraph round trip preserves capabilities, revocations, and `active_ids()` behavior.
- [ ] Promoted repair-rule lookup survives MG2 restart with `MetaMemory.episodes == ()`.
- [ ] Candidate repair rules never enter MG2 active memory.
- [ ] Strict same-identity/different-payload conflicts raise `MemoryGraphConflict` for laws, capabilities, repair rules, and revocations.
- [ ] Repair-rule tombstone restores cold portfolio search in the V3 integration test.
- [ ] Capability revocation delegates to existing `CapabilityGraph` dependency/ablation behavior.
- [ ] `verified_meta_growth_v3.py` and existing semantic core files remain unchanged.
- [ ] No stronger scientific claim appears in README or code comments.
- [ ] Final diff contains only milestone-1 paths.
