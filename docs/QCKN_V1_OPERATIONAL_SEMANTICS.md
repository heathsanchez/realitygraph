# QCKN V1 — Operational Semantics and Protocol

**Status:** Normative V1 developmental specification  
**Reference runtime:** RealityGraph on qckn-v1-frozen  
**Reference release commit:** 527cb7df1d931be53a61b1523abeaae20501af27

## 1. Purpose

QCKN is the developmental system built around the **Quantitative Consequential Kernel (QCK)**.

QCK determines what consequential substitution, defect, and reserve are mathematically warranted. QCKN specifies how a developmental system:

- observes a consequential mismatch;
- preserves its epistemic type;
- chooses a licensed intervention;
- independently verifies the result;
- records the result causally;
- compiles earned structure into the active present;
- restarts from that present;
- reuses verified capability without replaying discovery;
- revokes or ablates retained structure when evidence changes.

The central operating principle is:

> **Search may speculate. Memory may not.**

QCKN is therefore not a generic learning loop. It is a protocol for **warranted developmental state change**.

---

## 2. Canonical architecture

V1 is most compactly organized into four planes.

### 2.1 Consequence semantics

Owned by MSI/QCK.

Questions:

- Which distinctions matter?
- What may be identified?
- Does a new operation descend through the current representation?
- What reserve is required for declared future optionality?

### 2.2 Developmental control

Owned by typed outcomes, MDA, domain policy, and independent authority.

Questions:

- What kind of residual is present?
- Which interventions are licensed?
- Which licensed intervention is cheapest under the declared prospective cost?
- Has the proposed change been independently verified?

### 2.3 Developmental memory

Owned by the causal Ledger and CompiledPresent/MG2.

Questions:

- What happened, and what did each change causally observe?
- What earned structure is allowed to alter future execution?
- Can the causal past be safely compressed to the active present?
- What revocations must survive merge and restart?

### 2.4 Domain realization

Examples include Lean kernels, theorem discovery, ARC, robotics, software optimization, finite synthesis, and empirical science.

A domain adapter should expose, as far as practical:

~~~text
observe
propose
verify
cost
counterexample
promote
~~~

Domain-specific search and authority stay below this interface. Developmental semantics stay shared.

---

## 3. Developmental state

The canonical QCKN V1 state is:

\[
\Sigma=(\Gamma,\mathcal L,\mathcal P)
\]

where:

- \(\Gamma\) is the declared consequence and authority contract;
- \(\mathcal L\) is the immutable causal evidence ledger;
- \(\mathcal P\) is the compiled consequential present.

Transient search state is intentionally not part of the canonical retained state.

### 3.1 Contract Γ

A contract names enough information to interpret evidence, including as applicable:

- protected consequences;
- current representation/interface;
- admitted action or constructor family;
- verifier/authority identity;
- closure or search completeness boundary;
- resource envelope;
- declared future obligations;
- cost semantics;
- interface/version digest.

A result is always relative to a contract. QCKN does not promote context-free claims.

### 3.2 Ledger L

The ledger is history/evidence.

It is an immutable content-addressed causal DAG. Each event records parents, operation, target, kernel/producer, and payload.

The ledger answers:

> What was observed, promoted, superseded, or revoked, and what did that event causally know?

### 3.3 Compiled present P

The compiled present is cognition/runtime state.

It contains only earned structure allowed to alter future execution, currently represented by MG2 and exposed through CompiledPresent.

The present may include:

- active verified capabilities;
- promoted repair rules;
- active laws;
- revocation facts;
- authority/verifier handles;
- dependencies;
- provenance pointers;
- costs.

It intentionally excludes raw episodes, failed search traces, full candidate portfolios, and general causal history.

---

## 4. State discipline: ACTIVE / RESERVE / PROVENANCE

QCKN distinguishes three roles.

### ACTIVE

Required for present consequence-preserving execution.

### RESERVE

Not required for present execution, but justified by declared future optionality.

### PROVENANCE

Evidence explaining why a substitution, promotion, or intervention is warranted.

The distinction is normative:

\[
\boxed{
\text{ACTIVE}\neq\text{RESERVE}\neq\text{PROVENANCE}
}
\]

In particular:

> Provenance is not recoverability.

A proof that forgetting was safe does not reconstruct the forgotten state.

QCK V1 fully formalizes snapshot and maintained reserve in the finite-linear setting. Runtime reserve management in QCKN V1 is only partially realized. A conforming V1 implementation must therefore not claim that every formal reserve construction is already represented operationally by MG2.

---

## 5. Epistemic outcome vocabulary

The public QCK-aligned outcome vocabulary is:

- CertifiedSubstitution
- NewContextDefect
- ReserveRequired
- RecoveryUnavailable
- ImplementationMismatch
- CertificateInvalid
- OutOfScope
- Unknown

RealityGraph also has operational result kinds such as:

- AUTHORIZED
- COMPILED
- REFUTED
- UNKNOWN_IDENTITY
- UNKNOWN_CHOICE
- UNKNOWN_SEARCH
- UNKNOWN_EXPRESSIVITY
- NAMED_OBSTRUCTION

These are related but **not identical layers**.

Normative rule:

> QCK semantic classification, developmental route, and MDA intervention are distinct types and must not be collapsed into one enum merely for convenience.

---

## 6. Core judgments

For exposition, QCKN V1 uses the following judgment forms.

### 6.1 Sufficiency

\[
\Gamma\vdash q\;\mathsf{sufficient}
\]

means the representation q preserves all protected consequences in the declared contract.

### 6.2 Operation descent

\[
\Gamma;q\vdash A\Downarrow
\]

means A is certified to descend through q.

This corresponds to CertifiedSubstitution.

### 6.3 Operation defect

\[
\Gamma;q\vdash A\Uparrow w
\]

means A exposes a distinction erased by q, with witness w.

This corresponds to NewContextDefect.

### 6.4 Residual

\[
\Gamma;\Sigma\vdash \rho
\]

means the current state has a verifier-grounded unresolved obligation \(\rho\).

A timeout or empty search result is not automatically a residual of structural insufficiency.

### 6.5 Licensed intervention

\[
\rho\rightsquigarrow\mathcal I
\]

means outcome \(\rho\) licenses intervention set \(\mathcal I\).

### 6.6 Verified promotion

\[
\Gamma\vdash c\;\mathsf{verified}
\]

means independent authority has checked the candidate against the declared protected consequences.

### 6.7 Causal compilation

\[
\mathcal L\Downarrow\mathcal P
\]

means the representable active consequences of the ledger can be compiled into a canonical present without silently erasing unresolved causal distinctions.

---

## 7. Residual licensing

QCKN V1 preserves a strict distinction between kinds of uncertainty.

### 7.1 UNKNOWN_SEARCH

Search is incomplete or budget-limited.

It does **not** license the claim that the current language is insufficient.

### 7.2 UNKNOWN_CHOICE

More than one admissible verified option remains tied under the current ordering.

It does **not** license arbitrary tie breaking as a semantic fact.

### 7.3 UNKNOWN_EXPRESSIVITY

A structural expressivity claim requires an exact residual certificate tied to:

- the relevant obligation;
- the current language snapshot;
- completeness of the declared search/closure;
- replayable no-resolution evidence.

Only then may grammar/language expansion be licensed.

### 7.4 NAMED_OBSTRUCTION

A complete checked regime has no successful repair in the declared portfolio or language.

The obstruction is relative to that exact regime. It is not a universal impossibility result.

---

## 8. MDA intervention semantics

MDA means **Minimum Developmental Action**.

MDA receives a typed outcome and chooses only among interventions licensed by that type.

Canonical V1 interventions are:

- SPLIT
- MERGE
- EXPAND
- REVOKE
- CONSTRUCT
- VERIFY
- RESTRUCTURE
- COMPILE

The frozen Python policy uses the following admissible sets.

### CertifiedSubstitution

\[
\{\mathsf{COMPILE}\}
\]

### NewContextDefect

\[
\{
\mathsf{SPLIT},
\mathsf{EXPAND},
\mathsf{RESTRUCTURE},
\mathsf{CONSTRUCT},
\mathsf{VERIFY}
\}
\]

### ReserveRequired

\[
\{
\mathsf{EXPAND},
\mathsf{RESTRUCTURE}
\}
\]

### RecoveryUnavailable

\[
\{
\mathsf{CONSTRUCT},
\mathsf{RESTRUCTURE},
\mathsf{EXPAND}
\}
\]

### ImplementationMismatch

\[
\{
\mathsf{RESTRUCTURE},
\mathsf{VERIFY},
\mathsf{REVOKE}
\}
\]

### CertificateInvalid

\[
\{
\mathsf{REVOKE},
\mathsf{VERIFY}
\}
\]

### OutOfScope

\[
\{
\mathsf{EXPAND},
\mathsf{CONSTRUCT}
\}
\]

### Unknown

\[
\{
\mathsf{VERIFY},
\mathsf{CONSTRUCT}
\}
\]

MDA then chooses:

\[
I^*
=
\arg\min_{I\in\mathcal I}
\operatorname{prospectiveCost}(I).
\]

The cost function belongs to developmental policy. It is not part of QCK semantics.

---

## 9. Developmental transition rules

The following rules are the normative operational skeleton.

### 9.1 OBSERVE

A domain interaction produces consequence evidence.

~~~text
current state
   + action / construction
   + verifier-visible outcome
→ evidence
~~~

No retained state changes merely because a proposer produced a candidate.

### 9.2 CLASSIFY

Evidence is converted into the strongest justified typed outcome or operational residual.

The classifier must preserve uncertainty. Incomplete evidence must remain Unknown/UNKNOWN_SEARCH rather than being upgraded to structural impossibility.

### 9.3 ROUTE

Operational residuals are routed constitutionally.

The reference developmental core routes:

- terminal authorized/compiled/refuted/named-obstruction results → TERMINAL;
- unknown identity → SPLIT;
- unknown choice → EVIDENCE;
- unknown search → SEARCH;
- certified unknown expressivity → EXPAND.

EXPAND requires the exact residual certificate; a digest or obligation mismatch is a hard error.

### 9.4 SELECT

MDA chooses the cheapest licensed intervention.

Selection is deterministic for equal cost by declared order in the reference implementation, but this tie-breaking is policy, not semantics.

### 9.5 PROPOSE

Search, an LLM, a human, another agent, or a prior compiled capability may propose a repair/capability.

A proposal is untrusted.

### 9.6 VERIFY

Independent authority checks the proposed consequence contract.

Possible authorities include:

- Lean or another proof kernel;
- exhaustive finite checking;
- exact arithmetic;
- benchmark equivalence;
- simulation;
- sealed empirical evaluation;
- physical experiment.

Verification must be scoped to the contract actually checked.

### 9.7 ATTACK

Where the domain supports it, promoted candidates should survive the declared adversarial or exhaustive attack regime.

Passing one nominal case is not equivalent to passing the frozen attack surface.

### 9.8 PROMOTE

Only independently verified structure may enter causal developmental memory as promoted capability or promoted repair rule.

Acquisition evidence alone is not always enough. V1 meta-growth requires independent calibration before a repair rule becomes PROMOTED.

### 9.9 LEDGER

Promotion or revocation is written as a causal event.

Parents identify what the event had observed.

This prevents wall-clock order from pretending to be causal order.

### 9.10 COMPILE

Representable earned history is projected into CompiledPresent.

Compilation may fail if doing so would erase unresolved causal distinctions.

### 9.11 RESTART

The compiled present must support exact canonical round trip:

~~~text
parse(text(P)) == P
text(parse(text(P))) == text(P)
~~~

The reference CompiledPresent additionally checks digest equality.

### 9.12 REUSE

Future execution may use active promoted rules/capabilities from the compiled present.

V1 demonstrates future rule reuse with:

- zero repair-portfolio search;
- zero competitor strategy calls;
- zero future object-level grammar search;

while still independently verifying the new task-specific capability.

### 9.13 REVOKE

A capability/rule may be causally revoked.

Revocation is retained in the active memory layer so stale merge cannot silently reintroduce the revoked identity.

### 9.14 ABLATE

Ablation removes a retained contribution in a controlled counterfactual arm.

A causal claim of compounding should, where practical, require that exact ablation restores the cold path or removes the claimed later reach.

---

## 10. Promotion rule

The promotion rule can be summarized as:

\[
\frac{
c\;\mathsf{proposed}
\qquad
E\models_{\mathcal A,\Gamma}c
}{
\mathcal L
\longrightarrow
\mathcal L+\mathsf{promote}(c,E)
}
\]

where:

- c is the candidate;
- E is independent evidence;
- \(\mathcal A\) is the authority identity;
- \(\Gamma\) is the checked contract.

Normative consequences:

1. proposal identity is not authority identity;
2. stale authority snapshots invalidate reuse;
3. stale verifier identity invalidates reuse;
4. sham portfolio/interface identity invalidates reuse;
5. promotion evidence must be replayable enough for the declared claim.

---

## 11. Capability semantics

The reference FiniteCapability contains:

- capability_id;
- input_type;
- output_type;
- finite semantics table;
- guard inputs;
- certificate_id;
- dependencies;
- authority snapshot;
- verifier identity;
- provenance IDs;
- cost.

Capabilities may compose only through the authoritative capability algebra.

MG2 does not implement a second composition engine.

Dependencies matter causally:

- ablating an ancestor invalidates dependent descendants;
- ablating a descendant need not invalidate its ancestors.

The reference graph enforces dependency existence and acyclicity.

---

## 12. Repair-rule semantics

A promoted RepairRule records a verified relationship between an exact obstruction fingerprint and a repair strategy family.

Important fields include:

- obstruction fingerprint;
- strategy identity/version;
- repair portfolio digest;
- authority snapshot;
- verifier identity;
- interface digest;
- source episode digests/phases;
- selection cost;
- ablation handle.

V1 promotion discipline:

1. acquisition may create a candidate rule;
2. independent calibration is required for promotion;
3. future exact matches may select the repair family without searching competitors;
4. the selected task-specific repair must still be constructed and independently verified;
5. wrong fingerprints, stale authority, stale verifier, and sham portfolio identity must not reuse the rule.

---

## 13. Obstruction fingerprints

Obstruction fingerprints are exact finite canonical encodings of declared structural residual geometry.

They are not universal semantic identities.

A V1 promoted rule may transfer only when its exact boundary matches:

- obstruction fingerprint;
- portfolio digest;
- authority snapshot;
- verifier identity;
- interface digest;
- strategy version/applicability.

Transfer outside this boundary is unlicensed.

---

## 14. Causal ledger semantics

Each ledger event is content-addressed by its causal payload.

### 14.1 Merge

Ledger merge is deterministic union of immutable events.

### 14.2 Causal containment

An event contains another when the latter is reachable through parent ancestry.

### 14.3 Revocation

A revocation kills only promoted versions it causally observed.

Concurrent unseen versions survive.

### 14.4 Supersession

A causally later promotion can supersede an earlier version.

Concurrent versions remain unresolved until evidence resolves them.

### 14.5 Conflict preservation

If concurrent same-identity active payloads disagree, compilation to identity-level MG2 must fail rather than silently select or rename a winner.

### 14.6 Mixed causal revocation

If a revocation kills only some concurrent versions of the same identity, compilation to identity-level MG2 must fail rather than collapse the distinction.

These refusal cases are part of V1 correctness, not implementation inconvenience.

---

## 15. CompiledPresent semantics

CompiledPresent is the canonical active runtime boundary.

The reference MG2 contains four typed namespaces:

- laws;
- capabilities;
- repair rules;
- revocations.

### 15.1 What enters

Only earned state required to alter future execution.

### 15.2 What stays out

- raw search traces;
- raw candidate portfolios;
- failed alternatives;
- historical acquisition/calibration episode bodies;
- full event DAG.

### 15.3 Merge

For compatible memories, merge is intended to be:

- commutative;
- associative;
- idempotent.

Same typed identity with different payload is an explicit conflict.

### 15.4 Revocation

Revocation is monotone in the active-memory view.

### 15.5 Projection

MG2 may project to:

- CapabilityGraph;
- active MetaMemory;
- legacy MG1 law layer where lossless.

A whole-memory downgrade to MG1 must not silently discard capability/rule/revocation state.

---

## 16. History versus cognition

This distinction is normative:

\[
\boxed{
\mathcal L=\text{history/evidence}
}
\]

\[
\boxed{
\mathcal P=\text{compiled consequential present}
}
\]

History may be large.

The active present should contain only what has earned causal relevance for future execution.

Therefore:

> A restart should not need to replay discovery merely to regain already verified capability.

This is the operational meaning of “never pay twice for a verified lesson.”

---

## 17. Split and merge as representational moves

The repo lineage reveals two fundamental representational directions.

### SPLIT

A newly protected consequence exposes a distinction currently erased.

### MERGE

A distinction ceases to affect current or declared future consequences and can be removed from the active representation, unless justified as reserve.

The developmental machine should therefore alternate as evidence requires:

\[
\boxed{
\text{SPLIT when consequence forces it;}
\qquad
\text{MERGE when consequence permits it.}
}
\]

V1 formalizes the split side strongly and formalizes the mathematics needed for safe reserve/merging in QCK. Automatic runtime re-minimization is a V2 frontier.

---

## 18. Failure semantics

A RED result should be preserved at the strongest warranted type.

Preferred retained forms include:

- explicit separating pair;
- NewContextDefect witness;
- closure residual;
- named obstruction;
- obstruction fingerprint;
- counterexample;
- certificate invalidation;
- resource obstruction;
- recovery obstruction.

A failure should not be retained merely as “did not work” if a smaller reusable separator can be extracted.

---

## 19. Core non-inferences

A conforming operator or implementation must not make the following upgrades without evidence.

### Local silence → sufficiency

Invalid.

### Timeout → expressivity failure

Invalid.

### Empty candidate set under partial search → named obstruction

Invalid.

### Successful candidate → promoted memory

Invalid until independently verified.

### Candidate rule after acquisition → promoted repair rule

Invalid until independent calibration.

### Same label → same obstruction

Invalid unless exact fingerprint/interface/authority boundaries match.

### Provenance → recoverability

Invalid.

### Historical frequency → current authority

Invalid.

### Concurrent same-ID facts → last-write-wins

Invalid.

### Warm success → causal compounding

Invalid without matched cold/sham/raw/ablation evidence where the causal claim depends on retained structure.

---

## 20. Master transition

The QCKN V1 machine can be summarized as:

\[
(\Gamma,\mathcal L,\mathcal P)
\xrightarrow{
\text{observe}
}
\rho
\xrightarrow{
\text{classify}
}
o
\xrightarrow{
\text{MDA}
}
I
\xrightarrow{
\text{propose}
}
c
\xrightarrow{
\text{authority}
}
E
\xrightarrow{
\text{promote/revoke}
}
\mathcal L'
\xrightarrow{
\text{compile}
}
\mathcal P'.
\]

Then:

\[
\Sigma'=(\Gamma',\mathcal L',\mathcal P')
\]

becomes the starting state for the next problem.

The compounding claim is meaningful only if \(\mathcal P'\) changes future cost or reach and the matched ablation removes that advantage.

---

## 21. V1 demonstrated end-to-end path

The frozen cross-repository qualification demonstrates:

\[
\text{QCK defect}
\to
\text{MDA chooses EXPAND}
\to
\text{expanded context}
\to
\text{CertifiedSubstitution}
\to
\text{MDA chooses COMPILE}
\to
\text{causal promotion}
\to
\text{CompiledPresent}.
\]

The frozen RealityGraph developmental qualification additionally demonstrates:

\[
\text{cold acquisition}
\to
\text{independent calibration}
\to
\text{promoted repair rule}
\to
\text{causal ledger}
\to
\text{CompiledPresent}
\to
\text{exact restart}
\to
\text{future zero-search rule reuse}.
\]

Targeted causal revocation restores the cold portfolio-search path.

---

## 22. Claim boundary

QCKN V1 establishes a bounded verified developmental protocol over declared finite settings and exact trust boundaries.

It does **not** establish:

- universal transfer;
- open-ended autonomous development;
- arbitrary ontology invention;
- universal obstruction classification;
- universal repair optimality;
- learned ultimate verifier authority;
- unbounded self-improvement;
- general automatic garbage collection of representations;
- full runtime implementation of all QCK reserve mathematics.

The warranted V1 claim is:

> **Verified developmental products can be causally retained, compiled into a canonical active present, restarted exactly, and reused to change later bounded search/reach while preserving independent verification and restoring the cold path under targeted ablation.**

---

## 23. Canonical one-sentence definition

> **QCKN V1 is the operational protocol that turns QCK-classified consequential evidence into licensed intervention, independently verified promotion, causal memory, and a compressed active present that can be reused without replaying the discovery that earned it.**
