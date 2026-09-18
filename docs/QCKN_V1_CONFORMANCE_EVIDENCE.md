# QCKN V1 — Conformance and Evidence Profile

**Status:** Normative reference profile  
**Purpose:** Define what it means for an implementation or release to claim QCK/QCKN V1 conformance  
**Reference release:** heathsanchez/realitygraph at qckn-v1-frozen

## 1. Scope

This profile turns the V1 architecture into a checkable contract.

It does not claim that every conforming implementation must use the same codebase. It defines the minimum semantic, protocol, and evidence obligations required to use the labels:

- QCK V1 conformant;
- QCKN V1 adapter conformant;
- QCKN V1 runtime conformant;
- QCKN V1 full reference conformant.

Normative words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate V1 conformance requirements.

---

## 2. Canonical terminology

### QCK

**Quantitative Consequential Kernel**

The formal mathematical constitution governing:

- consequential equivalence / canonical nullspace;
- canonical quotient;
- sufficient representations;
- certified operation descent;
- new-context defect;
- finite-dimensional presentation;
- quantitative operation defect;
- snapshot and maintained reserve;
- active/reserve block dynamics;
- typed epistemic outcomes.

### QCKN

The developmental architecture and protocol built around QCK judgments.

### Authority

The independent checker that determines whether a proposed capability/repair has earned promotion under the declared contract.

### Ledger

Immutable causal history/evidence.

### CompiledPresent

Canonical active consequential state allowed to alter future execution.

### MG2

The V1 typed Memory Graph serialization used by the reference CompiledPresent.

---

## 3. Reference frozen artifacts

### 3.1 QCK constitutional surface

Repository:

**heathsanchez/Minimal-Sufficient-Interface**

Frozen branch:

**qck-v1-frozen**

Qualified commit:

**fc112771bd0a24e40e31e4eaef61ca0442103dd4**

QCK Core source blob:

**b9b1921c49c9947a02009be124286cfe3c723cb4**

Lean toolchain:

**v4.35.0-rc2**

Mathlib:

**44ba35c6daa9d69aff8fed9fff9bbde17ded774d**

### 3.2 QCKN downstream adapter/MDA surface

Repository:

**heathsanchez/Minimal-Sufficient-Interface**

Frozen branch:

**qckn-adapter-v1-frozen**

Commit:

**51ea5ab8121099173bc8d4edb6c83a5bcb7f3fb1**

### 3.3 QCKN runtime/release surface

Repository:

**heathsanchez/realitygraph**

Frozen branch:

**qckn-v1-frozen**

Commit:

**527cb7df1d931be53a61b1523abeaae20501af27**

Unified release workflow:

**QCKN v1 release**

Reference green run:

**35317971830**

Reference closure certificate:

**cd3ba3738b5f7cb13855e138496cc4644bae93718249dad728c12eb3cfda7fd3**

---

## 4. Conformance levels

## 4.1 Level A — QCK V1 constitutional conformance

An implementation claiming QCK V1 constitutional conformance MUST preserve the meaning of the frozen theorem surface.

At minimum it MUST support the equivalents of:

- contextual continuation composition;
- context-stable nullspace/equivalence;
- canonical quotient or equivalent canonical sufficient replacement;
- induced actions and observation;
- all-continuation substitution;
- sufficient-representation universal property;
- operation kernel stability;
- operation descent iff kernel stability for the corresponding setting;
- explicit defect witness on failure;
- quantitative defect in the finite-linear profile;
- snapshot reserve;
- maintained reserve;
- active/reserve compatibility;
- typed public outcome vocabulary.

A non-linear/discrete implementation MAY realize the same semantics through finite equivalence relations rather than linear quotient spaces, but MUST clearly identify itself as an adapter/profile rather than claiming the exact linear theorem surface.

A conforming implementation MUST NOT redefine QCK semantic meanings inside its developmental policy layer.

---

## 4.2 Level B — QCKN adapter/MDA conformance

A QCKN adapter implementation MUST:

1. map domain-specific equivalence/substitution checks onto QCK-aligned outcomes;
2. preserve CertifiedSubstitution versus NewContextDefect;
3. preserve the broader V1 typed outcomes where applicable;
4. preserve semantic classification separately from intervention selection;
5. expose only interventions licensed by the typed outcome;
6. select among licensed interventions through an explicit policy/cost layer.

The frozen reference MDA intervention vocabulary is:

- SPLIT;
- MERGE;
- EXPAND;
- REVOKE;
- CONSTRUCT;
- VERIFY;
- RESTRUCTURE;
- COMPILE.

The adapter MUST NOT silently upgrade incomplete search into an expressivity defect.

---

## 4.3 Level C — QCKN runtime conformance

A QCKN V1 runtime MUST implement the following trust and memory boundaries.

### Proposal boundary

Proposal MUST NOT equal promotion.

### Authority boundary

Promotion MUST require independent verification under a declared authority and contract.

### Causal history

Promotions/revocations MUST be recordable as immutable causal events or an equivalent structure preserving concurrency semantics.

### Active memory

Runtime active state MUST be separable from raw historical evidence.

### Exact restart

The compiled active state MUST support deterministic restart preserving active semantics.

### Revocation

Revocation MUST survive restart/merge and MUST prevent stale active reintroduction.

### Conflict preservation

Same-identity conflicting active payloads MUST NOT be silently resolved by last-write-wins.

### Dependency semantics

Dependent capabilities MUST become inactive when required ancestors are revoked/ablated.

### Unknown preservation

Incomplete search/tied choice MUST remain explicit rather than being forced into success/failure.

---

## 4.4 Level D — QCKN V1 full reference conformance

A full reference-conformant release MUST satisfy Levels A, B, and C and MUST reproduce the V1 load-bearing release gates or equivalent checks.

The reference release additionally demonstrates:

- QCK rebuild and axiom audit;
- frozen downstream adapter/MDA tests;
- executable cross-repository QCK → MDA → promotion → CompiledPresent bridge;
- causal ledger → CompiledPresent compilation;
- exact restart;
- future zero-search reuse;
- targeted revocation restoring cold search;
- stale/wrong/sham control rejection;
- bounded meta-growth closure.

---

## 5. QCK theorem-surface obligations

The frozen QCK Core public surface includes, by name in the reference implementation:

- wordMap;
- wordMap_append;
- contextNullspace;
- mem_contextNullspace_iff;
- contextNullspace_invariant;
- Canonical;
- canonicalMap;
- reducedAction;
- reducedObservation;
- canonicalMap_wordMap;
- allWordSubstitution;
- Sufficient;
- ker_le_contextNullspace;
- canonicalFactor;
- canonicalFactor_surjective;
- Certificate;
- Certificate.comp;
- KernelStable;
- descendedOperation;
- operation_descends_iff;
- operation_defect_witness.

FiniteLinear additionally includes the qualified families for:

- future observable closure;
- closure stabilization;
- annihilator characterization;
- finitePresentation;
- finite presentation kernel/surjectivity;
- canonical finite-dimensional equivalence;
- rank minimality;
- stacked operation map;
- operation defect;
- positive defect witness;
- snapshot reserve;
- maintained reserve;
- reserve update;
- active/maintained block law;
- fixed-vocabulary rank modularity/submodularity;
- generated-context non-submodularity counterexample.

API V1 additionally exposes:

- CertifiedSubstitution;
- NewContextDefect;
- ReserveRequired;
- RecoveryUnavailable;
- ImplementationMismatch;
- CertificateInvalid;
- OutOfScope;
- Unknown;
- Outcome;
- OperationAssessment;
- assessOperation.

Equivalent names are permitted in independent implementations, but semantic meaning MUST match.

---

## 6. Lean proof integrity profile

The reference QCK V1 qualification MUST reject QCK-owned use of:

- sorry;
- admit;
- local axiom declarations;
- local constant declarations used as proof placeholders;
- unsafe shortcuts in the qualified source surface.

The reference axiom audit permits only Lean foundational dependencies reported as:

- propext;
- Classical.choice;
- Quot.sound.

No QCK-local axiom declaration is part of the frozen constitutional surface.

A release claiming exact reference conformance SHOULD reproduce this audit against the pinned Lean/Mathlib environment.

---

## 7. Frozen QCK qualification evidence

Reference bounded QCK V1 qualification:

- run: **35306672847**
- commit: **fc112771bd0a24e40e31e4eaef61ca0442103dd4**
- result: GREEN

The release verified:

- pinned environment;
- QCK source build;
- API interface;
- FiniteLinear interface;
- placeholder rejection;
- axiom audit;
- compilation of every QCK-owned Lean source.

---

## 8. Frozen adapter/MDA qualification evidence

Reference downstream migration run:

- run: **35307981087**
- commit: **51ea5ab8121099173bc8d4edb6c83a5bcb7f3fb1**
- result: GREEN

It verified:

1. frozen QCK theorem surface is unchanged from the constitutional commit;
2. finite QCK adapter tests pass;
3. typed MDA policy tests pass.

A conforming adapter SHOULD provide an equivalent invariant preventing policy-layer edits from mutating the constitutional theorem surface.

---

## 9. Memory Graph conformance

The reference MG2 active-memory schema contains:

- laws;
- capabilities;
- promoted repair rules;
- revocations.

### 9.1 Canonical serialization

For every valid active memory M:

~~~text
parse(text(M)) == M
text(parse(text(M))) == text(M)
~~~

Insertion order MUST NOT change canonical text.

### 9.2 Typed identity

IDs are scoped by typed namespace.

A law and capability MAY share textual IDs.

Two records in the same typed namespace with the same identity but different payloads MUST cause explicit conflict.

### 9.3 Promoted-only repair memory

Candidate repair rules MUST NOT enter ordinary active MG2 memory.

### 9.4 No fabricated history

Restoring active MetaMemory from MG2 MUST NOT fabricate raw acquisition/calibration episodes.

### 9.5 Revocation

A revocation record MUST survive merge and active projection.

### 9.6 Capability graph validity

Capability dependencies MUST exist and MUST be acyclic.

---

## 10. Causal ledger conformance

The reference ledger uses immutable content-addressed events with explicit parents.

An equivalent implementation MUST preserve the following semantics.

### 10.1 Concurrent merge

Concurrent events are merged without destructive overwrite.

### 10.2 Causal revoke

A revocation removes only versions it causally observed.

Concurrent unseen versions survive.

### 10.3 Causal supersession

A later causally-descended promotion may supersede an earlier version.

### 10.4 Compilation refusal

If causal history cannot be represented faithfully at identity-level active memory, compilation MUST fail explicitly.

At minimum, V1 reference semantics refuse:

- concurrent same-identity different payload;
- revocation killing only a subset of concurrent same-identity promotions.

---

## 11. Capability conformance

A retained finite capability MUST include enough information to determine:

- identity;
- input/output type;
- executable semantics;
- applicability/guard boundary;
- certificate;
- dependencies;
- authority snapshot;
- verifier identity;
- provenance;
- cost.

Composition MUST use the authoritative capability composition layer.

MG2 or serialization code MUST NOT independently invent new composition semantics.

---

## 12. Repair-rule conformance

A promoted repair rule MUST be bound to enough exact context to prevent accidental over-transfer.

The reference V1 rule binds:

- obstruction fingerprint;
- strategy identity/version;
- portfolio digest;
- authority snapshot;
- verifier identity;
- interface digest;
- source episode lineage;
- selection cost;
- ablation handle.

A future rule hit MUST reject stale or mismatched:

- fingerprint;
- portfolio;
- authority;
- verifier;
- interface;
- strategy version/applicability.

---

## 13. Developmental uncertainty conformance

A conforming QCKN V1 runtime MUST preserve at least the following distinctions.

### UNKNOWN_SEARCH

Insufficient search completeness.

### UNKNOWN_CHOICE

Multiple surviving options not ordered by current evidence.

### UNKNOWN_EXPRESSIVITY

Current language proven insufficient under an exact completeness/no-resolution certificate.

### NAMED_OBSTRUCTION

Declared complete repair regime exhausted without success.

A runtime MUST NOT route UNKNOWN_SEARCH directly to grammar expansion.

A runtime MUST NOT resolve UNKNOWN_CHOICE merely by implementation order while claiming semantic uniqueness.

---

## 14. Reference developmental routing

The frozen RealityGraph developmental core routes:

- AUTHORIZED → TERMINAL
- COMPILED → TERMINAL
- REFUTED → TERMINAL
- NAMED_OBSTRUCTION → TERMINAL
- UNKNOWN_IDENTITY → SPLIT
- UNKNOWN_CHOICE → EVIDENCE
- UNKNOWN_SEARCH → SEARCH
- UNKNOWN_EXPRESSIVITY + matching certificate → EXPAND

For UNKNOWN_EXPRESSIVITY, certificate digest and obligation identity MUST match the result.

Equivalent routing is allowed if it preserves the same epistemic boundaries.

---

## 15. Reference MDA admissibility table

A full reference-conformant implementation SHOULD reproduce the frozen V1 admissibility relation.

| Outcome | Licensed interventions |
| --- | --- |
| CertifiedSubstitution | COMPILE |
| NewContextDefect | SPLIT, EXPAND, RESTRUCTURE, CONSTRUCT, VERIFY |
| ReserveRequired | EXPAND, RESTRUCTURE |
| RecoveryUnavailable | CONSTRUCT, RESTRUCTURE, EXPAND |
| ImplementationMismatch | RESTRUCTURE, VERIFY, REVOKE |
| CertificateInvalid | REVOKE, VERIFY |
| OutOfScope | EXPAND, CONSTRUCT |
| Unknown | VERIFY, CONSTRUCT |

The prospective cost model MAY vary.

Changing the admissibility relation constitutes a protocol version change unless justified as a compatible extension.

---

## 16. Exact restart evidence

Reference MG2 qualification:

- run: **35313208624**
- commit: **1ccc329a70604dba4615eb36e5a581f0d1dd095f**
- result: GREEN

Reference QCKN runtime qualification:

- run: **35313489441**
- commit: **1139747f341933149e0446b8d24162eb1bc34a06**
- result: GREEN

Reference CompiledPresent qualification:

- run: **35313797246**
- commit: **3e9fce1459b443db75c433f67139e003f51533cb**
- result: GREEN

These collectively established:

- canonical MG2 restart;
- object capability + promoted meta-rule combined present;
- history-free active projection;
- future reuse through restarted memory;
- ablation restoring cold path.

---

## 17. Causal compilation evidence

Reference causal present qualification:

- run: **35314111064**
- commit: **72c95db10543354e3ab64093f6c20ffb7a803390**
- result: GREEN

Required behaviors demonstrated:

- causal capability promotion compiles into active present;
- causal repair-rule promotion compiles into active present;
- causal rule revocation restores cold path;
- capability revocation disables active view while preserving record;
- concurrent same-ID conflicting payload is refused;
- mixed concurrent revocation is refused;
- legacy causal ledger semantics remain intact.

---

## 18. End-to-end developmental evidence

Reference end-to-end qualification:

- run: **35315590783**
- commit: **3d78e57afd08c33bd844676f766d023cdc5b65da**
- result: GREEN

It demonstrated:

\[
\text{learn}
\to
\text{verify}
\to
\text{promote}
\to
\text{causal ledger}
\to
\text{CompiledPresent}
\to
\text{restart}
\to
\text{zero-search reuse}.
\]

It also demonstrated:

\[
\text{causal revoke}
\to
\text{recompile}
\to
\text{cold search returns}.
\]

The final bounded meta-growth verdict remained:

**PASS_VERIFIED_META_GROWTH_V3**

---

## 19. Cross-repository conformance evidence

Reference cross-repo qualification:

- run: **35315966480**
- RealityGraph commit: **1c5b8aee89b5d40d3e063c8e217aad8b3361156c**
- pinned MSI/QCKN adapter commit: **51ea5ab8121099173bc8d4edb6c83a5bcb7f3fb1**
- result: GREEN

The executable path was:

\[
\text{QCK defect}
\to
\text{MDA EXPAND}
\to
\text{expanded context}
\to
\text{CertifiedSubstitution}
\to
\text{MDA COMPILE}
\to
\text{causal promotion}
\to
\text{CompiledPresent}.
\]

A full QCKN V1 claim SHOULD include an equivalent executable bridge from semantic classification to runtime retention.

---

## 20. Unified V1 release gate

Reference unified release:

- branch: **qckn-v1-release**
- final frozen branch: **qckn-v1-frozen**
- final commit: **527cb7df1d931be53a61b1523abeaae20501af27**
- run: **35317971830**
- conclusion: GREEN

The workflow rechecked:

1. frozen QCK theorem surface;
2. finite adapter;
3. typed MDA;
4. pinned Lean/Mathlib build;
5. placeholder rejection;
6. axiom audit;
7. cross-repository QCKN bridge;
8. causal compiled present;
9. end-to-end developmental tests;
10. bounded verified meta-growth.

This is the authoritative V1 integrated evidence point.

---

## 21. Reference closure certificate

The unified developmental release ended with:

**CLOSED_BOUNDED_META_GROWTH_V3**

Certificate:

**cd3ba3738b5f7cb13855e138496cc4644bae93718249dad728c12eb3cfda7fd3**

The reference runtime also printed:

**PASS_VERIFIED_META_GROWTH_V3**

A conforming derivative release MAY produce a different certificate when code/data/contracts differ, but MUST preserve the same evidence discipline if making the same bounded claim.

---

## 22. Mandatory causal-control pattern for compounding claims

If a release claims that retained structure causes future developmental advantage, it SHOULD include matched controls sufficient to exclude trivial caching or history effects.

The strongest V1-derived pattern is:

- COLD;
- WARM;
- RAW_HISTORY;
- SHAM;
- ANCESTOR_ABLATION.

At minimum, a causal compounding claim MUST include a relevant ablation demonstrating loss/restoration of the claimed advantage.

Without ablation, the release MAY report correlation/association but SHOULD NOT label the retained object as causally necessary.

---

## 23. Claim-language conformance

A V1-conformant release MAY claim, when supported by its evidence:

- bounded verified consequential substitution;
- canonical finite-linear sufficiency under a declared contract;
- typed residual-driven development;
- verified capability promotion;
- causal compiled active memory;
- exact restart;
- bounded zero-search reuse;
- causal ablation restoring a cold path;
- bounded learning of repair-family selection under an exact finite obstruction representation.

A V1-conformant release MUST NOT imply that V1 established:

- universal transfer;
- open-ended autonomous intelligence;
- arbitrary ontology invention;
- universal repair optimality;
- universal obstruction classification;
- learned ultimate authority;
- unbounded self-improvement;
- universal source-independent representation;
- general automatic implementation of every formal reserve theorem.

---

## 24. Versioning rules

### 24.1 Constitutional changes

Any change to the meaning of:

- consequential equivalence;
- canonical sufficiency;
- KernelStable;
- defect;
- reserve;
- public QCK outcome semantics

requires a new QCK constitutional version unless proven observationally identical to V1.

### 24.2 Protocol changes

Changes to:

- MDA admissibility;
- promotion conditions;
- causal merge/revocation semantics;
- active-memory conflict semantics;
- required authority boundary

require a QCKN protocol version update.

### 24.3 Compatible extensions

New domain adapters, search strategies, cost models, authorities, evidence renderers, or storage transports MAY be added without changing V1 semantics if they preserve all normative boundaries.

---

## 25. Minimal machine-readable release manifest

A QCKN V1 release SHOULD publish a manifest containing at least:

~~~text
qck_version
qck_commit_or_artifact_digest
qckn_protocol_version
runtime_commit
authority_ids
verifier_ids
dependency_versions
qualification_run_ids
closure_certificate
claim_boundary
~~~

Where exact reproducibility matters, include:

- source hashes;
- data hashes;
- environment/toolchain pins;
- frozen portfolio/grammar digests;
- interface/contract digests.

---

## 26. Reference verification commands

The exact command surface may evolve, but the reference release profile re-runs the following classes of checks.

### QCK

~~~text
lake build QCK
lake env lean QCKFiniteLinearTest.lean
lake env lean QCKAPITest.lean
lake env lean QCKAxiomAudit.lean
~~~

### Adapter/MDA

~~~text
python -m unittest tests.test_qck_v1_finite_adapter -v
python -m unittest tests.test_qckn_mda -v
~~~

### Cross-repository bridge

~~~text
python -m unittest tests.test_qckn_cross_repo -v
~~~

### Causal compiled present

~~~text
python -m unittest \
  tests.test_compiled_present \
  tests.test_causal_compiled_present \
  tests.test_qckn_end_to_end -v
~~~

### Final bounded developmental qualification

~~~text
python verified_meta_growth_v3.py
~~~

A derivative implementation MAY replace these with equivalent tests, but MUST document how each normative obligation is covered.

---

## 27. Conformance checklist

### QCK constitution

- [ ] canonical consequence contract explicit;
- [ ] sufficient representation semantics preserved;
- [ ] operation descent/defect preserved;
- [ ] explicit witness on defect;
- [ ] reserve semantics preserved where claimed;
- [ ] typed API meanings preserved;
- [ ] no hidden local proof axioms in the claimed formal surface.

### Developmental control

- [ ] semantic type separate from policy action;
- [ ] incomplete search preserved as incomplete;
- [ ] intervention licensing explicit;
- [ ] prospective cost explicit;
- [ ] proposal separate from authority.

### Memory

- [ ] causal history separate from active memory;
- [ ] active memory canonical;
- [ ] exact restart;
- [ ] revocation survives restart/merge;
- [ ] conflicts fail explicitly;
- [ ] raw episodes not fabricated from compiled state.

### Causal claim

- [ ] warm advantage measured;
- [ ] relevant cold/control arm exists;
- [ ] targeted ablation removes advantage;
- [ ] verifier boundary unchanged between arms.

### Release

- [ ] exact commit/digest pinned;
- [ ] qualification run pinned;
- [ ] claim boundary included;
- [ ] closure certificate recorded where applicable.

---

## 28. Authoritative V1 evidence chain

The V1 reference evidence chain is:

\[
\boxed{
\begin{array}{l}
\text{QCK constitutional qualification}\\
\downarrow\\
\text{QCK adapter/MDA qualification}\\
\downarrow\\
\text{MG2 active-memory qualification}\\
\downarrow\\
\text{CompiledPresent qualification}\\
\downarrow\\
\text{causal history compilation}\\
\downarrow\\
\text{end-to-end developmental qualification}\\
\downarrow\\
\text{cross-repository semantic/runtime bridge}\\
\downarrow\\
\text{unified V1 release gate}
\end{array}
}
\]

The final integrated evidence point is:

**run 35317971830 — GREEN**

---

## 29. Canonical conformance statement

A release may state:

> **This implementation is QCKN V1 reference-conformant under the declared contract and evidence profile. It preserves the frozen Quantitative Consequential Kernel semantics, separates semantic classification from developmental policy, requires independent promotion authority, maintains causal history separately from compiled active memory, supports exact restart and explicit revocation, and has passed the documented V1 qualification gates.**

Only use this statement when the corresponding obligations are actually satisfied.
