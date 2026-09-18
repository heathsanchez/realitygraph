# QCKN V1 — Operator's Handbook

**Audience:** human operators, research agents, domain-adapter authors, reviewers  
**Status:** Practical V1 handbook derived from the frozen QCK/QCKN architecture

## 1. What this handbook is for

Use this handbook when you are applying QCKN to a real problem.

The goal is not to force every project into one implementation. The goal is to preserve the developmental invariants that the frozen V1 stack established:

1. define what consequences matter;
2. distinguish search failure from structural failure;
3. make the smallest warranted change;
4. verify independently;
5. retain only earned structure;
6. preserve causal history separately from active memory;
7. restart from the compiled present;
8. test whether the retained lesson actually changes future cost or reach.

The short operating law is:

\[
\boxed{
\text{observe}
\to
\text{residual}
\to
\text{intervene}
\to
\text{verify}
\to
\text{promote}
\to
\text{compile}
\to
\text{reuse}
}
\]

with:

\[
\boxed{
\text{revoke / ablate}
\to
\text{cold path returns}
}
\]

where a causal compounding claim is being made.

---

## 2. Before you start a new domain

Do not begin with architecture.

Begin with the consequence contract.

Write down, explicitly:

- What are the situations/states?
- What observations or outcomes are protected?
- What continuations/actions are admitted?
- Which authority decides whether a candidate is correct?
- What counts as a complete search?
- What is the resource envelope?
- What costs matter?
- What future optionality is declared?
- Which evidence is allowed to trigger promotion?
- What would falsify the intended transfer or compounding claim?

If you cannot answer these, the problem is not ready for QCKN promotion logic.

### Minimum domain-adapter contract

Aim to expose:

~~~text
observe(state, action) -> evidence
propose(state, residual) -> candidate
verify(candidate, contract) -> certificate / counterexample
cost(candidate or intervention) -> prospective cost
counterexample(failure) -> typed residual
promote(verified candidate) -> causal event
~~~

The adapter may use richer domain-specific types internally.

---

## 3. Step 1 — Define protected consequences

QCKN is consequence-first.

Do not ask:

> What representation should I use?

Ask:

> Which distinctions must remain available because some protected continuation can expose them?

For finite/discrete tasks, a practical starting point is a set of protected continuations or tests.

For Lean/proof work, the protected consequence may be exact kernel acceptance.

For software optimization, it may be extensional output equivalence plus a performance objective.

For ARC, it may be exact task consequences under declared observations and interactions.

For robotics, it may be a set of state-estimation/control consequences verified in simulation or hardware.

For empirical science, it may be a sealed predictive or causal consequence under a declared protocol.

### Operator rule

Never retain a distinction merely because it is easy to name.

Retain it because a protected consequence requires it.

---

## 4. Step 2 — Establish the current representation

Identify the current active interface or quotient.

Ask:

- Which states are presently treated as equivalent?
- What information is currently erased?
- Which capabilities already act lawfully on that representation?
- Which current distinctions are ACTIVE?
- Which are RESERVE?
- Which are only PROVENANCE?

If using the finite MSI adapter, materialize the current partition.

If using the QCK linear setting, identify the representation map q and its kernel.

If there is no explicit representation yet, use the domain's current operational state as the initial interface. Do not invent a “minimal” representation without evidence.

---

## 5. Step 3 — Push until consequence collides

QCKN development is residual-driven.

Run the current system under the declared contract.

A useful failure is one that can be stated as a typed incompatibility, for example:

- two currently merged states require different protected futures;
- a proposed action exposes an erased distinction;
- the complete current grammar cannot realize a required consequence;
- a certificate fails independent replay;
- requested recovery is impossible from the retained state;
- an implementation diverges from a valid formal contract;
- a repair portfolio is exhausted under its declared completeness boundary.

Do not convert ordinary implementation bugs or timeouts into structural residuals unless the evidence warrants it.

---

## 6. Step 4 — Classify the outcome honestly

Use the strongest type justified by the evidence, not the type that would make development convenient.

### CertifiedSubstitution

Use when the proposed operation respects the current representation.

Typical next action: COMPILE.

### NewContextDefect

Use when a proposed operation exposes a distinction the current representation erased.

Typical licensed actions include SPLIT, EXPAND, RESTRUCTURE, CONSTRUCT, VERIFY.

### ReserveRequired

Use when current compression would destroy declared future optionality.

Typical actions: EXPAND or RESTRUCTURE.

### RecoveryUnavailable

Use when the requested distinction cannot be reconstructed from current retained state.

Typical actions: CONSTRUCT, RESTRUCTURE, EXPAND.

### ImplementationMismatch

Use when theory/contract is sound but code does not realize it.

Typical actions: RESTRUCTURE, VERIFY, REVOKE.

### CertificateInvalid

Use when purported evidence fails checking.

Typical actions: REVOKE, VERIFY.

### OutOfScope

Use when the request lies outside the contract.

Typical actions: EXPAND contract or construct a new supported path.

### Unknown

Use when the evidence is insufficient.

Typical actions: VERIFY or CONSTRUCT more evidence.

---

## 7. Step 5 — Preserve operational uncertainty

RealityGraph distinguishes several operational unknowns.

### UNKNOWN_SEARCH

Search is incomplete.

Do not call this expressivity failure.

### UNKNOWN_CHOICE

Several verified candidates remain tied.

Do not choose one and report uniqueness.

### UNKNOWN_EXPRESSIVITY

Use only when complete current-language search plus a replayable no-resolution certificate establishes the boundary.

### NAMED_OBSTRUCTION

Use only relative to the exact frozen language/portfolio/resource contract that was exhaustively checked.

### Operator rule

If you are unsure whether you have a structural failure or an incomplete search, you have an incomplete search.

---

## 8. Step 6 — Ask MDA for the smallest warranted move

MDA is not a semantic theorem. It is policy constrained by semantics.

List the interventions licensed by the outcome.

Then score them by prospective cost.

Possible cost components include:

- search calls;
- verifier calls;
- interactions;
- wall time;
- memory footprint;
- active representation dimension;
- proof support count;
- engineering complexity;
- recovery burden;
- risk of invalidating dependent capabilities.

Choose the cheapest licensed option under the declared cost function.

Do not hard-wire “defect means split.” Sometimes EXPAND, CONSTRUCT, or VERIFY is cheaper and better justified.

---

## 9. Step 7 — Generate a candidate repair

The proposer may be:

- deterministic search;
- heuristic search;
- an LLM;
- a human;
- another agent;
- an existing capability;
- a composition of verified capabilities.

The proposer is not trusted.

Store proposal metadata if useful for audit, but do not allow it to enter active memory merely because it was generated.

---

## 10. Step 8 — Verify independently

Before promotion, verify against the declared authority.

### Formal proof

Use Lean/kernel acceptance or another proof checker.

### Finite exact system

Use exhaustive enumeration.

### Software behavior

Use exact/reference output checks on the declared workload plus regression/attack gates.

### Empirical model

Use frozen split/group/sealed protocols. Do not upgrade empirical zero-failure evidence into logical certainty.

### Robotics/simulation

Use the declared simulator/hardware protocol and preserve environment boundaries.

### Operator checklist before promotion

- Is the verifier independent of the proposer?
- Is the authority identity recorded?
- Is the verifier version/snapshot recorded?
- Is the contract exact?
- Is the search/completeness claim scoped correctly?
- Are resource bounds recorded?
- Did the candidate survive the required attack/held-out checks?
- Are ties still ties?
- Is there any stale evidence?

If any answer is unclear, do not promote.

---

## 11. Step 9 — Promote causally

Promotion creates a causal ledger event.

For a capability, retain at least:

- capability identity;
- semantics/behavior;
- type boundary;
- guard inputs or applicability boundary;
- certificate;
- dependencies;
- authority snapshot;
- verifier identity;
- provenance IDs;
- cost.

For a repair rule, retain at least:

- obstruction fingerprint;
- strategy identity/version;
- portfolio digest;
- authority snapshot;
- verifier identity;
- interface digest;
- evidence lineage;
- selection cost;
- ablation handle.

### Important

Acquisition can produce candidate developmental knowledge.

Promotion requires the protocol's promotion evidence.

In V1 meta-growth, repair rules require independent calibration before promotion.

---

## 12. Step 10 — Compile history into the present

The ledger is not the hot path.

Compile earned active state into CompiledPresent/MG2.

The compiled present should contain only what is allowed to change future execution.

Do not stuff raw history into active memory merely because it might be useful someday.

### Compilation refusal is valid

If the ledger contains:

- concurrent same-identity conflicting payloads; or
- a revocation that killed only some concurrent versions,

then identity-level MG2 cannot safely represent the situation.

Compilation should fail explicitly.

Resolve the causal conflict first.

Do not use last-write-wins.

---

## 13. Step 11 — Restart exactly

A promoted lesson is not operationally real until restart preserves it.

Require:

~~~text
parse(text(P)) == P
digest(parse(text(P))) == digest(P)
~~~

Then rerun the future task from the restarted present.

Do not allow hidden process memory, raw episode objects, or unpersisted caches to carry the result.

The point is to prove that the compiled present itself contains the earned lesson.

---

## 14. Step 12 — Measure future advantage

A compounding claim needs a cost comparison.

Useful measurements include:

- grammar search calls;
- portfolio search calls;
- competitor strategy calls;
- theorem support search;
- interactions;
- hypothesis scans;
- internal predictions;
- synthesis cost;
- runtime;
- active representation rank;
- number of candidate representations;
- verifier calls;
- retained state size.

The strongest pattern is:

~~~text
COLD
WARM
RAW_HISTORY
SHAM
ANCESTOR_ABLATION
~~~

### COLD

No retained lesson.

### WARM

Starts only from promoted compiled state.

### RAW_HISTORY

Gets history without the compiled causal abstraction.

### SHAM

Gets similarly shaped but causally irrelevant retained state.

### ANCESTOR_ABLATION

Exact relevant retained ancestor is removed.

A causal compounding claim is strongest when WARM improves and the matched controls do not.

---

## 15. Step 13 — Ablate the claimed lesson

If you say:

> this retained lesson caused the future advantage

then remove it.

For a repair rule, targeted revocation should restore the cold repair-search path.

For a capability dependency chain, ancestor ablation should transitively invalidate descendants.

If removal changes nothing, the claimed retained object may not be causally responsible.

Turn that into a residual and re-minimize.

---

## 16. Step 14 — Re-minimize

V1 contains the mathematical machinery for safe forgetting, but automatic runtime re-minimization is not yet fully generalized.

Still, operators should challenge retained structure manually.

For every active item ask:

1. Does any current protected consequence require it?
2. Does any declared future require it as reserve?
3. Is it only provenance?
4. Can another promoted capability subsume it?
5. Does removal change any protected outcome?
6. Does removal break recoverability that the contract promises?

If no protected present/future consequence depends on it, move it out of ACTIVE.

Do not accumulate intelligence as permanent clutter.

---

## 17. How to treat RED

RED is often the most valuable result in QCKN.

Immediately ask:

> What is the smallest reusable fact this RED proves?

Prefer, in order:

1. explicit separator;
2. typed residual;
3. counterexample;
4. obstruction fingerprint;
5. failed contract boundary;
6. resource lower bound;
7. recovery obstruction;
8. certificate invalidation.

Avoid retaining only prose like “approach failed.”

### Good RED

“States x and y are identified by q, but A sends them to outputs separated by protected consequence c.”

### Weak RED

“Model was worse.”

The first can drive future development. The second usually cannot.

---

## 18. New language or representation growth

Do not expand representation/grammar because search got difficult.

Require an exact reason.

For grammar/language growth, the reference developmental stack requires:

1. complete current-language enumeration under the declared bound;
2. a separate no-resolution certificate;
3. an obligation tied to the exact state/language snapshot.

Only then route to EXPAND.

This rule exists because incomplete search repeatedly masquerades as “need a new representation” in exploratory work.

---

## 19. Capability composition

Composition is powerful but dangerous if treated as free.

When composing A and B:

1. build the composition using the authoritative capability algebra;
2. record dependencies;
3. verify the composition independently;
4. promote only after verification;
5. add it to the causal ledger;
6. compile;
7. challenge whether A, B, or intermediate representation structure still needs to remain ACTIVE.

The goal is not “more capabilities stored.”

The goal is:

\[
\boxed{
\text{more verified future consequence per unit active structure and acquisition cost}
}
\]

---

## 20. Repair-rule reuse

A promoted repair rule is not “whenever something looks similar, use this strategy.”

Reuse requires exact boundary checks.

Verify:

- obstruction fingerprint;
- portfolio digest;
- authority snapshot;
- verifier identity;
- interface digest;
- strategy version;
- applicability.

If any mismatch occurs, fall back to cold portfolio search or the appropriate Unknown route.

Do not weaken matching to increase apparent transfer.

---

## 21. Active memory versus history

Keep this mental model:

~~~text
Ledger
  = what happened
  = evidence
  = concurrent causal truth
  = potentially large

CompiledPresent
  = what may affect the next decision
  = promoted capabilities/rules
  = revocations
  = canonical restart state
  = intentionally small
~~~

When debugging, do not “fix” a missing active capability by loading the whole ledger into cognition.

Instead ask why the promotion/compiler boundary did not retain it.

---

## 22. Working in GitHub repositories

For QCKN V1 and descendants:

- frozen V1 branches are immutable;
- new development happens on new branches;
- small meaningful slices get their own commits;
- each semantic slice should have a focused CI gate;
- RED gates should fail for the intended scientific reason;
- do not weaken a gate merely to turn it green;
- freeze important green milestones;
- record exact commit/run/certificate identities.

### Frozen V1 roots

Minimal-Sufficient-Interface:

- qck-v1-frozen
- qckn-adapter-v1-frozen

RealityGraph:

- qckn-v1-frozen

Do not develop V2 by editing these branches.

---

## 23. End-to-end worked example

The frozen cross-repository QCKN test is the shortest reference example.

### Initial condition

A finite interface identifies two states under the current protected basis.

A proposed action maps those states to images with different protected consequences.

### QCK assessment

Result:

**NewContextDefect**

The current representation is insufficient for the new operation.

### MDA

Under the test cost model, EXPAND is the cheapest licensed intervention.

### Context expansion

Add the required continuation/observation.

Reassess the same operation.

Result:

**CertifiedSubstitution**

### MDA

CertifiedSubstitution licenses:

**COMPILE**

### Promotion

Construct the verified finite capability with certificate/authority/provenance metadata.

Write a causal promotion event.

### Compile

Ledger materializes to CompiledPresent.

### Restart

Serialized active present is parsed exactly.

### Reuse

The promoted capability executes from the restarted capability graph.

This example proves the architectural bridge:

\[
\boxed{
\text{QCK meaning}
\to
\text{MDA policy}
\to
\text{causal promotion}
\to
\text{compiled runtime}
}
\]

---

## 24. Verified meta-growth worked example

V1 also contains a higher-order example.

Two obstruction families are used:

- observation collision → add_observable;
- temporal collision → add_finite_memory_2.

### Acquisition

Cold portfolio search finds a successful repair family.

Only a candidate meta-rule is created.

### Calibration

Independent matching episode selects the same repair family.

Rule becomes PROMOTED.

### Compile/restart

Promoted object capabilities and repair rules are written causally, compiled to MG2, and restarted exactly.

### Future

An untouched future obstruction with the same exact fingerprint boundary hits the promoted rule.

Observed future costs:

- portfolio search = 0;
- competitor strategy calls = 0;
- future grammar search = 0.

A new task-specific capability is still constructed and independently verified.

### Ablation

Targeted rule revocation restores cold portfolio search.

This is the reference pattern for “learn how to repair, but still verify each new repair.”

---

## 25. Debugging guide

### Symptom: warm path fails to reuse

Check:

1. fingerprint mismatch;
2. authority snapshot mismatch;
3. verifier mismatch;
4. portfolio digest mismatch;
5. interface digest mismatch;
6. strategy version mismatch;
7. rule was never independently promoted;
8. revocation exists;
9. dependency ancestor is inactive.

### Symptom: grammar expands too often

Check:

1. are UNKNOWN_SEARCH and UNKNOWN_EXPRESSIVITY conflated?
2. is completeness actually certified?
3. is the residual bound to the correct language snapshot?
4. is a timeout being treated as proof?

### Symptom: MG2 merge conflicts

Check:

1. same typed ID with different payload?
2. concurrent promotions?
3. mixed causal revocation?
4. stale duplicate identity?

Do not rename identities silently. Resolve the evidence.

### Symptom: active state keeps growing

Check:

1. no re-minimization;
2. provenance accidentally stored as ACTIVE;
3. reserve obligations not separated;
4. composed capability makes intermediates redundant;
5. revocations not propagated to active view.

### Symptom: transfer looks good but ablation also looks good

Likely the retained object is not causally responsible.

Check RAW_HISTORY and SHAM controls.

---

## 26. Promotion checklist

Before promoting any capability/rule:

- [ ] protected consequence contract is explicit;
- [ ] candidate is type-correct;
- [ ] independent authority checked it;
- [ ] authority identity/version recorded;
- [ ] verifier identity recorded;
- [ ] applicability/interface boundary recorded;
- [ ] dependencies recorded;
- [ ] relevant attack/held-out tests passed;
- [ ] no unresolved tie is being hidden;
- [ ] no incomplete search is being called exhaustive;
- [ ] cost semantics are explicit;
- [ ] provenance/evidence handles recorded;
- [ ] ablation handle exists where causal reuse will be claimed.

---

## 27. Compile checklist

Before producing CompiledPresent:

- [ ] all included repair rules are PROMOTED;
- [ ] capability dependencies exist and are acyclic;
- [ ] revocations are explicit;
- [ ] same-ID/different-payload conflicts are absent;
- [ ] no mixed causal revocation is being collapsed;
- [ ] raw episodes/search traces are excluded;
- [ ] serialization is canonical;
- [ ] restart preserves text and digest.

---

## 28. Release checklist

Before freezing a QCKN milestone:

- [ ] constitutional QCK surface unchanged unless intentionally versioned;
- [ ] adapter/MDA tests green;
- [ ] domain-specific authority checks green;
- [ ] cold/warm/control evidence recorded;
- [ ] exact restart green;
- [ ] causal ledger → compiled present green;
- [ ] ablation restores claimed cold behavior;
- [ ] stale/sham/wrong-boundary controls reject;
- [ ] Unknown routes remain preserved where evidence is incomplete;
- [ ] claim boundary written explicitly;
- [ ] exact commit, run, environment, and certificate recorded.

---

## 29. When not to use QCKN language

Do not describe a result as QCKN-certified merely because:

- an LLM suggested it;
- a benchmark improved once;
- a test suite passed without a declared authority boundary;
- a heuristic transferred;
- a cached artifact was reused;
- a representation got smaller;
- a search got faster.

The relevant question is:

> What protected consequence was checked, by what authority, under what contract, and what causal retained object changed the future path?

If that cannot be answered, use ordinary engineering/research language instead.

---

## 30. V1 operating motto

The repository lineage compresses to four operator rules:

\[
\boxed{
\begin{array}{l}
\textbf{Distinguish only when consequence forces it.}\\
\textbf{Compress whenever consequence permits it.}\\
\textbf{Verify before retaining.}\\
\textbf{Never pay twice for a verified lesson.}
\end{array}
}
\]
