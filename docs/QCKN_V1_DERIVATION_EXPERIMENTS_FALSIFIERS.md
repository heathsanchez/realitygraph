# QCKN V1 — Derivation, Experiments, and Falsifiers

**Status:** Historical and explanatory companion to the normative V1 documents  
**Purpose:** Record why the V1 architecture has the shape it does, what evidence forced each abstraction, and which tempting stronger claims were falsified

## 1. How to read this document

This is not the normative QCK specification and it is not the operator manual.

It is the **derivation record**.

The repository chain did not begin with the final architecture. It repeatedly proposed a stronger or simpler interpretation, attacked it, found a residual, and compressed the surviving structure into a smaller invariant.

The final V1 architecture is best understood as the result of that sequence.

The overall lineage is:

\[
\boxed{
\text{finite consequential distinction}
\to
\text{behavioural quotient}
\to
\text{developmental residual}
\to
\text{verified repair}
\to
\text{retained capability}
\to
\text{compiled developmental present}
}
\]

The most important historical fact is:

> **Negative results shaped the constitution as much as positive theorems did.**

---

# Part I — The MSI discovery lineage

## 2. Seed: minimal sufficient interface

The original Minimal-Sufficient-Interface repository began from a deliberately tiny question:

> If only protected consequences matter, which distinctions between states must survive?

For a set of protected continuations B, the finite relational kernel is:

\[
x\,E_B\,y
\iff
\forall c\in B,\;c(x)=c(y).
\]

Equivalently:

\[
E_B=\bigcap_{c\in B}K_c.
\]

Adding a verified separator refines the current relation by meet:

\[
E_{t+1}=E_t\wedge K_t.
\]

This produced the first compression:

> Consequential learning can be represented as monotone refinement of sameness.

The early exhaustive finite tests established:

- order independence of verified distinctions;
- idempotence of repeated evidence;
- convergence under finite strict refinement;
- reconstruction from a relation-only alphabet;
- a meet-semilattice abstraction independent of one concrete state encoding.

This was the first indication that the reusable object was not a task-specific heuristic but an algebra of justified distinction.

---

## 3. First major falsifier: local silence is not sufficiency

A tempting early stopping rule was:

> If the next available continuation does not separate any currently merged pair, the representation is sufficient.

The Lean falsifier showed this is false.

A locally silent continuation does not imply that every allowed continuation is silent.

The corrected completeness boundary became:

\[
\neg\operatorname{Residual}(B,T)
\iff
E_B=E_T
\]

only when B is compared against the full protected target family T under the declared completeness boundary.

This single falsifier became one of the permanent constitutional rules:

\[
\boxed{
\text{local silence}\not\Rightarrow\text{global sufficiency}
}
\]

and later reappeared as:

\[
\boxed{
\text{incomplete search}\not\Rightarrow\text{expressivity failure}.
}
\]

---

## 4. Behavioural congruence

The next question was whether protected equivalence remains lawful under reachable actions.

For an action monoid M acting on X with protected observation v:

\[
x\sim_*y
\iff
\forall m\in M,\quad
v(m\cdot x)=v(m\cdot y).
\]

The Lean development proved that \(\sim_*\) is the greatest reachable-action-invariant equivalence contained in the observational kernel.

Every reachable action descends to the quotient, preserving identity and composition.

This established the first fully compositional interpretation:

> A minimal sufficient interface is not just a partition; it is the maximal behavioural congruence compatible with protected consequence.

Finite recovery results then showed that, given a complete finite continuation list, repeatedly adding genuine separators reaches that exact behavioural quotient.

The key change in perspective was from:

~~~text
collect useful observations
~~~

to:

~~~text
compute the coarsest state on which all admitted future behavior remains well-defined
~~~

That perspective becomes QCK Core later.

---

## 5. Typed behavioural congruence

The monoid setting was then lifted to typed continuations in a small category.

For typed morphisms \(f:X\to Y\):

\[
x\sim_X y
\iff
\forall Y,\forall f:X\to Y,\quad
v_Y(f(x))=v_Y(f(y)).
\]

The objectwise minimal sufficient interfaces assemble functorially:

\[
Q(f)([x])=[f(x]).
\]

This established:

- typed quotient dynamics;
- identity preservation;
- composition preservation;
- object-relative consequence.

This mattered because later developmental systems would not live in one homogeneous state space.

---

## 6. Developmental continuation category

The next step allowed the accessible continuation family itself to grow.

For developmental stage S:

\[
x\sim_X^S y
\iff
\forall f:X\to Y,\quad
S(f)\Rightarrow v_Y(f(x))=v_Y(f(y)).
\]

The structural law is:

\[
S\subseteq T
\Longrightarrow
\sim_X^T\subseteq\sim_X^S.
\]

Expanding executable futures can only refine the consequential interface.

This gives the basic developmental arrow:

\[
\boxed{
\text{new executable continuation}
\to
\text{new protected distinction}
\to
\text{finer quotient}.
}
\]

It also revealed a subtle but permanent distinction:

> The representation can change because capability changes.

That becomes the basis for QCK new-context defect.

---

## 7. Closure-relative capability: a crucial type correction

A strong developmental claim initially risked conflating two different events:

1. a target becomes newly reachable under the executable closure;
2. a syntactic form becomes newly expressible in the raw constructor language.

Finite counterexamples showed:

\[
\boxed{
\text{strict reachability growth}
\not\Rightarrow
\text{strict formability growth}.
}
\]

An operation can already be syntactically formable but only become useful/reachable after a previous capability changes the executable regime or representation.

This forced a permanent separation between:

- representation;
- raw constructor language;
- executable closure;
- resource-bounded reachability.

The final QCKN architecture keeps these distinct.

---

## 8. Capability-induced refinement and autonomous discovery

A sequence of three-state exhaustive experiments then joined capability acquisition to quotient refinement and later capability.

A controlled bridge established examples of:

\[
O_1
\to
\text{new separator}
\to
Q_1
\to
\text{new reachable }O_2.
\]

The reported census found:

- 1,944 strict capability-induced interface refinements;
- 744 full causal witnesses.

The stronger autonomous experiment removed the predefined O2 from the search procedure.

With a frozen candidate language and blind search order, acquiring O1 could change the executable closure and representation, after which the unchanged search discovered an emergent nonprimitive O2.

Reported results:

- 1,872 strict refinements;
- 220 autonomous post-refinement discovery witnesses.

Then endogenous O1 genesis removed the supplied-O1 assumption as well.

A verifier-visible residual drove search over the frozen transformation language.

Reported result:

- 36 residual worlds;
- 648 residual-driven O1 geneses;
- all 648 realized the full residual → O1 → separator → refined quotient → expanded closure → autonomous O2 chain.

This established the first bounded causal developmental loop.

---

## 9. Compositional closure and its falsifier

A natural conjecture was that one-step continuation families might already reveal the full behavioural quotient.

The three-state/two-generator census supported that locally, but the stronger four-state test falsified any universal version.

Across 4,096 four-state / one-generator worlds:

- 576 required proper composite separators.

This produced another permanent rule:

\[
\boxed{
\text{primitive consequences may be insufficient;}
\quad
\text{composite futures matter.}
}
\]

The corresponding Lean theorem identifies the endpoint:

\[
E_\infty
=
\bigcap_{f\in G^*}\ker(v\circ f).
\]

So QCK later quantifies over all finite words rather than a one-step horizon.

---

## 10. Counterexample-driven composition discovery

The next experiments removed pre-supplied composite separators.

Given only primitive actions and a verifier-returned merged pair, the learner searched words in the primitive language.

Reported results:

- all 576 four-state worlds requiring a proper composite were recovered;
- in a 65,536-world two-primitive census, 23,808 required composite discovery;
- 13,056 required a learned word using both primitive symbols;
- zero reported recovery/congruence failures in the declared census.

This supported the idea:

> A residual can guide construction, not just diagnosis.

That later becomes the CONSTRUCT intervention.

---

## 11. Constructor-law discovery

The system was then denied the correct composition law.

A finite hypothesis family included:

- sequential composition;
- reversed composition;
- left/right projection;
- pointwise alternatives.

The verifier returned concrete execution counterexamples.

Across all 5,832 three-state/two-primitive worlds:

- 4,704 uniquely identified sequential composition;
- 1,128 retained syntactic ambiguity;
- 0 had harmful ambiguity;
- all surviving ambiguous laws were extensionally identical to sequential composition on the reachable subalgebra.

This gave another key distinction:

\[
\boxed{
\text{syntactic uniqueness}
\neq
\text{behavioural uniqueness}.
}
\]

QCKN therefore prefers behavioural identity under protected consequences over arbitrary syntax identity.

---

## 12. Grammar-driven constructor genesis

The hand-written law menu was then removed.

The learner received only the generative syntax:

\[
t ::= x\mid F(t)\mid G(t).
\]

Sequential composition appears as a generated term rather than a named candidate.

Across 729 ordered primitive pairs:

- 558 had a unique surviving constructor syntax;
- 171 had only operationally equivalent syntactic ambiguity;
- 0 harmful ambiguity;
- 3,626 verifier counterexamples;
- at most 7 per world;
- zero identity-law failures;
- zero associativity failures.

The deterministic shortest retained term was F(G(x)) in 728/729 worlds; the remaining world was operationally trivial.

The positive lesson was strong:

> Verifier residuals can drive constructor genesis.

But that claim was then attacked.

---

## 13. Adversarial break of constructor-genesis overclaim

Adversarial tests showed that a broad statement like:

> residuals always reveal the right constructor

was too strong.

The work had to be fortified with explicit boundaries around:

- grammar completeness;
- verifier horizon;
- contextual verification;
- no-uniform-lookahead counterexamples;
- no-retraction properties.

This is historically important.

The final system does not say:

> failure implies invent a constructor.

It says:

> only typed evidence under a declared complete boundary may license structural expansion.

That is exactly why RealityGraph later distinguishes UNKNOWN_SEARCH from UNKNOWN_EXPRESSIVITY.

---

## 14. Greedy selection falsifier

Immediate pair-split gain looked attractive as a universal next-step criterion.

It was cardinality-optimal over all tested binary 4×4 worlds.

But a 5×4 counterexample showed it is not a theorem.

Dynamic programming established that optimal next-step value is residual-relative.

Permanent lesson:

\[
\boxed{
\text{local split gain}
\not\Rightarrow
\text{globally optimal developmental action}.
}
\]

This becomes part of the rationale for MDA and explicit prospective cost.

---

# Part II — Concrete representation development

## 15. Arithmetic representation genesis

Arithmetic experiments moved beyond abstract finite carriers.

Verified causal conflicts rejected naive most-significant-first local addition.

Residuals forced a positional dependency order, after which a two-state latent interface became sufficient for exact local composition.

Across positional bases 2 through 16, the same two-state behavioural structure was independently recovered.

For widths 2, 3, 10, 32 and 128, the reported result was that exactly \(n-1\) verifier counterexamples recovered the precedence chain:

\[
0\to1\to\cdots\to n-1.
\]

This was important because it showed:

- verified failure can change processing order;
- representation and dependency structure may both need development;
- the useful retained object can be a latent interface, not a literal observation.

It also produced no-fixed-delay and granularity ambiguity boundaries, preventing overclaiming one universal encoding.

---

## 16. Verified interface compilation

A resource-bounded Boolean synthesis experiment then tested whether a verified behavioural program could become a new constructor.

Starting from variables and NAND only:

- verifier residuals isolated minimum representatives for protected half-adder outputs;
- those representatives were promoted as unit-cost constructors;
- minimum full-adder formula cost changed from 20 to 6;
- matched sham and exact-ablation arms remained at 20 under budget 6.

The full-adder outputs were then promoted and recursively reused.

Python exhausted widths 4 and 6; Lean independently certified the frozen constructions and enumerations.

The result is deliberately typed:

> 20 → 6 is promoted-constructor description cost, not reduced fully expanded NAND-gate complexity.

That distinction is an early form of the later QCKN rule:

> Always state what cost measure actually changed.

---

## 17. Blind recursive cross-grammar genesis

A stronger experiment removed the named intermediate interface and dependence on one syntax.

Three independently specified complete Boolean grammars searched anonymous two-behaviour libraries.

The sealed later arithmetic task was excluded before selection.

Reported held-out description-cost reductions were 53.2%–62.5%.

On the sealed full-adder task:

- WARM reached cost 6 in every grammar;
- COLD and controls remained at 20/29.

The retained interface was then promoted across widths 2, 4 and 8.

At each generation:

- residual elimination recovered the two-block composition;
- WARM used two calls;
- ancestor ablation required at least four;
- structural carry-edge interventions were predicted;
- Python exhausted the eight-bit census;
- Lean independently certified frozen programs and additional census/edge checks.

This is one of the clearest predecessors of the final “compiled present changes future reach” claim.

---

# Part III — Consequential development becomes typed

## 18. Consequential core

The repository then consolidated many experiments into an explicit developmental state.

A state was represented conceptually as:

\[
S=(X,E,C,V,P)
\]

with:

- carrier/domain X;
- active representation E;
- executable language C;
- certification relation V;
- provenance P.

Later code also tracked a version space H and developmental policy D.

The important move was to refuse one unconstrained “Repair” type.

Residuals and repairs became typed.

Residual examples:

- PairResidual;
- ClosureResidual;
- AcquisitionResidual.

Repair examples:

- RefineRepresentation;
- ReplaceVersionSpace;
- ExtendLanguage;
- UpdatePolicy;
- CoupledRepair.

This enforced:

> different developmental failures are not semantically interchangeable.

A timeout cannot masquerade as ClosureResidual.

A representation refinement cannot masquerade as a language extension.

A policy update is not the same event as changing the quotient.

This type discipline survives into QCKN V1.

---

## 19. Residual-specific certification and provenance

Certification was then bound to the exact state/residual that motivated the repair.

A repair had to be:

- conservative under its type;
- attached to the correct residual;
- verified to resolve that residual;
- compiled with provenance.

Exact ablation could restore the prior state when no unrelated changes intervened.

This produced the causal pattern:

\[
\boxed{
\text{residual}
\to
\text{certified repair}
\to
\text{compiled change}
\to
\text{provenance}
\to
\text{ablation}.
}
\]

That pattern later becomes ledger promotion + revocation.

---

## 20. Minimal repair and regime genesis

The MSI capstone work proved and tested stronger bounded statements about least verifier-licensed repairs and residual-induced regime changes.

The research programme explicitly separated:

- repair;
- minimality;
- uniqueness up to behavioural equivalence;
- conservative extension;
- quotient effect;
- capability gain;
- causal ablation;
- presentation invariance;
- recursive composability.

It also documented the stronger open targets:

- minimality in richer regimes;
- endogenous specification genesis;
- categorical organization discovered rather than assumed.

These stronger goals were not silently imported into V1.

V1 instead freezes the pieces actually established.

---

## 21. Failure-generated consequence and consequence-distinction duality

The lineage then explored a deeper duality:

- protected consequences determine which distinctions must exist;
- residual distinctions reveal missing consequence structure.

This culminated in a consequence-distinction Galois-style core and fixed-point/diagnostic results.

Historically this matters because it shifts the interpretation of failure.

A failure is not merely a negative score.

It can be evidence specifying **which distinction the current representation lacks**.

That idea is foundational to QCK new-context defect and to the QCKN instruction:

> Turn RED into the smallest reusable separator possible.

---

# Part IV — QCK: constitutional compression

## 22. Why QCK was needed

By September 2026, MSI contained:

- relational kernels;
- behavioural congruence;
- typed/category formulations;
- developmental categories;
- finite exhaustive experiments;
- typed residuals/repairs;
- reserve/recovery ideas;
- compounding experiments.

The repository had enough evidence, but too many partially overlapping semantic forms.

QCK was the compression step.

The design goal was:

> Find the smallest formal kernel that the surrounding developmental machinery can depend on without carrying the accidental shape of every experiment.

QCK means:

**Quantitative Consequential Kernel**

---

## 23. QCK Core

QCK Core chose a quotient-first linear operational formulation.

For actions S and observation C:

\[
N_{\mathcal C}
=
\bigcap_w\ker(C\circ S_w).
\]

Canonical state:

\[
V/N_{\mathcal C}.
\]

Core proves:

- invariance;
- induced actions;
- induced observation;
- all-word substitution;
- universal sufficiency property;
- certificate composition;
- operation descent;
- defect witness.

This replaced many local notions with one constitutional criterion:

\[
\boxed{
A(\ker q)\subseteq\ker q.
}
\]

If this holds, the operation descends.

If not, QCK returns a witness that the new operation exposes a forgotten distinction.

This is the clean semantic center of V1.

---

## 24. QCK FiniteLinear

FiniteLinear then made the kernel executable and quantitative.

It formalized:

- dual future-observable closure;
- stabilization;
- annihilator equality;
- finite presentation;
- rank minimality;
- operation defect;
- snapshot reserve;
- maintained reserve;
- exact reserve attainment;
- reserve self-update;
- active/reserve block dynamics;
- fixed-vocabulary submodularity;
- capability-generated context non-submodularity.

This was a second important compression:

> Representation cost is not only “number of current distinctions”; future optionality can impose a quantifiable reserve obligation.

It also produced another falsifier:

\[
\boxed{
\text{fixed-vocabulary submodularity}
\not\Rightarrow
\text{developmental diminishing returns}.
}
\]

Capability combinations can expose distinctions that neither exposes alone.

This warns against additive value assumptions in V2.

---

## 25. QCK API

QCK API then stabilized the boundary between mathematics and control:

- CertifiedSubstitution;
- NewContextDefect;
- ReserveRequired;
- RecoveryUnavailable;
- ImplementationMismatch;
- CertificateInvalid;
- OutOfScope;
- Unknown.

This is one of the decisive architectural moves.

Instead of allowing downstream code to infer meaning from arbitrary failures, QCK exports typed epistemic states.

The downstream MDA layer then chooses interventions without changing semantic meaning.

---

# Part V — RealityGraph becomes the developmental runtime

## 26. Early RealityGraph: MOVE → COLLIDE → SHIFT → KEEP → REPEAT

RealityGraph began with a compact operational kernel:

~~~text
MOVE
→ COLLIDE
→ SHIFT
→ KEEP
→ REPEAT
~~~

- Move: take a useful construction/action.
- Collide: meet independently grounded consequence.
- Shift: change only what the collision warrants.
- Keep: retain what changes future reach.
- Repeat: start from the changed present.

This was the runtime analogue of MSI's verified refinement principle.

---

## 27. Causal ledger

Very early in RealityGraph, KEEP was routed through an immutable causal event ledger.

The key semantics were:

- content-addressed events;
- explicit parents;
- deterministic union merge;
- concurrent edits preserved;
- revoke only what was causally observed;
- no last-write-wins truth.

This became one of the deepest architectural decisions:

\[
\boxed{
\text{causal history}
\neq
\text{active cognition}.
}
\]

The ledger records what happened.

A later compiled memory decides what should affect the future.

---

## 28. Consequence fields and “compute once”

RealityGraph then explored a different but related optimization:

> Evaluate the counterfactual consequence field once, then quotient/reuse it instead of repeatedly recomputing the same predictions.

In blind finite meta-world experiments:

- hypotheses × actions were evaluated once;
- a joint separating batch was selected;
- the batch was verified;
- the batch was compiled;
- future worlds in the same declared family skipped experiment design and hypothesis scanning.

The field demo reported a 257× reduction in internal identification predictions for a fresh world inheriting a verified separator.

The important transferable principle was not the exact factor.

It was:

\[
\boxed{
\text{verified discrimination can be compiled off the repeated search path}.
}
\]

This becomes the operational interpretation of “never pay twice.”

---

## 29. Real measured and grouped data

RealityGraph also tested consequence-specific compression on measured datasets and predictive settings.

These experiments were carefully bounded.

Examples included:

- exact finite dataset quotienting;
- target-specific feature/probe retention;
- sealed groups;
- zero-failure evidence bounds;
- categorical sets and numeric intervals;
- natural-group transfer diagnostics;
- leakage versus transfer consequence types.

The negative lesson was as important as the positive one:

> Empirical stability is not logical certainty.

Hence the final architecture distinguishes proof certificates from empirical evidence and requires claim language to match authority strength.

---

## 30. Cross-domain transfer and its limits

The MSI evidence map summarized a major lesson:

Different domains retain different products.

Examples:

- arithmetic: causal precedence + latent state;
- finite MSI: query policy or separator structure;
- interface compilation: extensional programs as constructors;
- Lean: verified proof substrate;
- ARC: observation basis and residual history.

The transferable invariant is not one universal representation.

It is the developmental law:

\[
\boxed{
\text{verified failure}
\to
\text{residual}
\to
\text{justified distinction/construction}
\to
\text{retention}
\to
\text{changed future reach/search}.
}
\]

This prevents QCKN from claiming a universal transferable ontology.

---

## 31. ARC transfer falsifiers

ARC provided a particularly valuable series of negative transfer tests.

Within an episode, residual history changed later query selection and could improve closure.

But progressively stronger cross-episode inherited query-policy hypotheses failed causal identity.

The final residual-conditioned comparison reported:

| arm | exact target | queries |
| --- | ---: | ---: |
| WARM residual-conditioned | yes | 7 |
| COLD | yes | 6 |
| RAW_HISTORY | yes | 5 |
| SHAM | yes | 7 |
| ANCESTOR_ABLATION | yes | 6 |

Thus:

\[
\boxed{
\text{within-episode developmental value}
\not\Rightarrow
\text{cross-episode transferable query-policy identity}.
}
\]

This failure redirected the programme upward:

> The transferable object may be the generator of an observation language, not a ranking over already fixed observations.

That is exactly the kind of RED→new-level residual QCKN is meant to preserve.

---

# Part VI — Verified recursive development

## 32. Verified language-growth closure V1

RealityGraph then formalized a strict license for grammar growth.

The old language may grow only after:

1. complete enumeration of the declared current language;
2. an independent no-resolution certificate;
3. an exact obligation/language snapshot.

UNKNOWN_SEARCH cannot expand grammar.

UNKNOWN_CHOICE remains unresolved.

Generation 1:

- exhausted the old Boolean observer language;
- certified parity not expressible there;
- searched a declared NAND substrate;
- admitted the smallest verified extension found by compositional depth.

Generation 2:

- exhausted the current stateless denotations;
- certified the required history-sensitive distinction absent;
- admitted a verified two-state Moore-machine observer dependent on G1.

Ablation restored the previous frontier.

Green verdict:

**PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1**

Status:

**CLOSED_BOUNDED**

This is the origin of the constitutional residual routing used later.

---

## 33. Generic recursive executor V2

V2 moved the developmental loop itself into reusable machinery.

G1, G2, and G3 were produced by the same generic execute_generation transition.

The qualified chain was:

~~~text
nand-d3-0110
    -> fsm-t1000-o01
    -> g3-s3-t021101-o010
~~~

Every generation required:

- complete current-language evidence;
- separate no-resolution certificate;
- verified admission;
- exact restart;
- bounded attack;
- zero future grammar search on reuse.

G3 strengthened the expressivity step:

- all 64 binary-input two-state Moore machines were exhausted;
- none realized the target property;
- only then was the three-state substrate searched.

Transitive dependency ablations were verified.

Green verdict:

**PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2**

Status:

**CLOSED_BOUNDED_DEPTH3**

This established that the developmental transition itself could be generic across several generations.

---

## 34. Verified meta-growth V3

The next question was whether the system could retain not only an object capability, but a verified rule about **how to repair a class of obstruction**.

Two different obstruction families were used:

- observation collision → add_observable;
- temporal collision → add_finite_memory_2.

The protocol required:

1. exact obstruction fingerprint;
2. cold repair-family search;
3. successful verified repair;
4. acquisition creates only a candidate rule;
5. independent calibration;
6. promotion;
7. future isomorphic obstruction;
8. direct repair-family selection;
9. new task-specific capability still independently verified;
10. targeted rule ablation restores cold repair search.

The future path achieved:

- zero repair-portfolio search;
- zero competitor strategy calls;
- zero future object grammar search.

Wrong fingerprints, stale authority/verifier identities, sham portfolio identity, incomplete search, partial portfolio, and tied repairs were rejected or preserved as Unknown.

Green verdict:

**PASS_VERIFIED_META_GROWTH_V3**

Status:

**CLOSED_BOUNDED_META_GROWTH_V3**

This is the bounded first qualification of:

> verified learning of how to grow.

---

# Part VII — Memory is compressed into a present

## 35. MG2

At this point RealityGraph had several active memory forms:

- MG1 laws;
- CapabilityGraph;
- MetaMemory.

The MG2 design unified active memory without rewriting history or semantics.

The design principle was explicit:

\[
\boxed{
\text{history is not cognition}.
}
\]

MG2 stores:

- active laws;
- verified capabilities;
- promoted repair rules;
- revocations.

It excludes:

- raw episodes;
- candidate traces;
- full search portfolios;
- causal event history.

It introduced strict same-ID conflict detection, deterministic canonical serialization, exact restart, and promoted-only repair memory.

This was not merely a storage refactor.

It established the active-memory boundary that the rest of QCKN could rely on.

---

## 36. CompiledPresent

CompiledPresent wrapped MG2 as the canonical active runtime state.

It exposes:

- exact text/digest restart;
- capability graph projection;
- active meta-memory projection;
- future meta execution;
- capability/rule revocation.

The verified meta-growth qualification was then rewired to run through CompiledPresent rather than sidecar memory.

The same future behavior survived restart.

This closed the gap between:

> retained experimental evidence

and:

> actual state used by the next execution.

---

## 37. Causal history → compiled present

The next step connected the immutable ledger to the active present.

Ledger events were extended to carry:

- capability promotion/revocation;
- repair-rule promotion/revocation.

The compiler then materializes representable causal history into CompiledPresent.

Crucially, compilation refuses:

- concurrent same-identity conflicting payloads;
- mixed causal revocation where only some concurrent versions are killed.

This produced an important semantic principle:

\[
\boxed{
\operatorname{compile}:\mathcal L\rightharpoonup\mathcal P
}
\]

Compilation is a partial operation.

It is permitted only when the requested active projection can represent the causal distinctions faithfully.

This is one of the most mature ideas in the final V1 architecture.

---

## 38. End-to-end causal compounding

The verified meta-growth runner was then changed to construct its active state from the causal ledger itself.

The green end-to-end qualification demonstrated:

\[
\boxed{
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
}
\]

And:

\[
\boxed{
\text{causal revoke}
\to
\text{recompile}
\to
\text{cold search returns}.
}
\]

This moved QCKN beyond “cache reuse.”

The retained object is:

- verified;
- causally recorded;
- independently restartable;
- ablatable.

---

## 39. Cross-repository bridge

The final semantic/runtime gap was between:

- frozen QCK/MDA in Minimal-Sufficient-Interface; and
- RealityGraph runtime.

A cross-repository test exercised:

\[
\boxed{
\text{QCK defect}
\to
\text{MDA EXPAND}
\to
\text{expanded contract}
\to
\text{CertifiedSubstitution}
\to
\text{MDA COMPILE}
\to
\text{causal promotion}
\to
\text{CompiledPresent}.
}
\]

This proved that the final architecture was not merely a diagram connecting independently green repos.

The semantic boundary and runtime boundary were executable together.

---

## 40. Unified V1 release

The final release gate re-ran the complete load-bearing chain:

- frozen QCK theorem surface;
- finite QCK adapter;
- typed MDA;
- pinned Lean/Mathlib;
- proof-placeholder rejection;
- axiom audit;
- cross-repository bridge;
- causal compiled present;
- end-to-end developmental tests;
- verified meta-growth.

Reference release:

- RealityGraph commit: 527cb7df1d931be53a61b1523abeaae20501af27;
- run: 35317971830;
- result: GREEN;
- closure certificate:
  cd3ba3738b5f7cb13855e138496cc4644bae93718249dad728c12eb3cfda7fd3.

This is the point at which the exploratory lineage became a bounded released architecture.

---

# Part VIII — Falsifier register

## 41. Permanent negative laws

The following table summarizes the strongest “do not infer” lessons forced by the repo chain.

| Tempting inference | What broke it | V1 rule |
| --- | --- | --- |
| One silent test means the representation is sufficient | Lean/local-silence falsifier | Sufficiency is relative to the full declared continuation contract |
| One-step consequences always determine behavioural state | Four-state composite-separator census | Quantify over admitted finite continuation closure |
| Immediate split gain is globally optimal | 5×4 greedy counterexample | Selection is residual-relative and cost-sensitive |
| Reachability growth means new syntax was invented | Closure-relative capability witness | Distinguish formability from executable reach |
| Search found nothing, so language is insufficient | Finite search/completeness boundary | Incomplete search stays UNKNOWN_SEARCH |
| A generated constructor that works proves a universal constructor-genesis law | Adversarial grammar/verifier breaks | Structural growth requires explicit completeness and authority boundaries |
| Finer representation and larger language are the same development | Typed consequential-core work | Keep representation repair and capability/language repair distinct |
| Successful proposal deserves retention | Consequential certification and RealityGraph authority boundary | Proposal ≠ promotion |
| Provenance lets us recover deleted state | Reserve/recoverability analysis | Provenance ≠ recoverability |
| Any learned query policy should transfer | ARC source-distinct negatives | Transfer object is domain/residual-relative |
| Warm success proves causal compounding | RAW/SHAM/ablation controls | Require counterfactual controls for causal claims |
| Same label means same obstruction | V3 stale/sham/wrong-fingerprint controls | Bind reuse to exact fingerprint/portfolio/authority/interface |
| Partial repair search can identify the best repair | V3 partial-portfolio control | Partial portfolio stays UNKNOWN_SEARCH |
| Tied minimal repairs may be arbitrarily selected and called unique | V3 UNKNOWN_CHOICE control | Preserve unresolved choice |
| Historical evidence belongs in active memory | MG2 design | History ≠ cognition |
| Concurrent same-ID facts can be last-write-wins | Causal ledger compiler | Preserve conflict; compilation may refuse |
| Fixed-vocabulary diminishing returns extends to developmental context growth | QCK U/V counterexample | Generated context may be complementary/non-submodular |

These are not incidental caveats.

They are part of the architecture.

---

# Part IX — What the entire chain compresses to

## 42. Three strata

After the full lineage, the codebase is best understood as three strata.

### 42.1 Discovery lineage

MSI experiments, theorems, falsifiers, arithmetic, constructor genesis, cross-grammar compounding, ARC negatives, empirical transfer work.

Purpose:

> discover which developmental claims survive attack.

### 42.2 Constitutional kernel

QCK Core + FiniteLinear + API.

Purpose:

> state the surviving consequential semantics with the smallest formal surface.

### 42.3 Developmental machine

MDA + authority + typed residual routing + capability graph + obstruction fingerprinting + causal ledger + MG2/CompiledPresent.

Purpose:

> act on constitutional judgments, verify changes, retain them causally, and make them available to the next problem.

---

## 43. The invariant that survived everything

The strongest compression of the whole repository chain is:

> **Never introduce a distinction without consequential evidence; never erase one while a protected future can expose it; never retain a developmental change without independent verification; never replay discovery once its verified consequence has been safely compiled.**

Equivalently:

\[
\boxed{
\begin{array}{l}
\text{Distinguish only when consequence forces it.}\\
\text{Compress whenever consequence permits it.}\\
\text{Verify before retaining.}\\
\text{Never pay twice for a verified lesson.}
\end{array}
}
\]

---

# Part X — Evidence hierarchy at V1 freeze

## 44. What is established

The repository chain supports, with different authority strengths:

1. **Finite consequential refinement:** exact and exhaustive.
2. **Behavioural congruence and quotient dynamics:** machine-checked in Lean.
3. **Typed/developmental quotient structure:** machine-checked in bounded formal settings.
4. **Residual-driven constructor/capability genesis:** exhaustive finite evidence with explicit boundaries.
5. **Arithmetic representation development:** verifier-driven structural evidence across widths/bases.
6. **Verified interface compilation:** causal resource-frontier change with Python/Lean checking.
7. **Cross-grammar behavioural recovery:** bounded synthetic evidence.
8. **Source-distinct Lean proof-substrate compounding:** external formal-verifier evidence.
9. **ARC within-episode developmental value:** positive; cross-episode query-policy identity: falsified.
10. **RealityGraph active-memory compounding:** bounded exact restart/reuse/ablation.
11. **Verified repair-family meta-growth:** bounded exact finite obstruction/portfolio evidence.
12. **Cross-repository QCK→MDA→runtime bridge:** executable.
13. **Unified QCKN V1 release:** green.

---

## 45. What remains open

V1 does not close:

- universal minimal repair in arbitrary developmental regimes;
- general endogenous specification/objective genesis;
- general emergent category formation without ambient structure;
- natural-domain observation-language/meta-constructor transfer;
- general automatic active/reserve runtime minimization;
- open-ended capability composition;
- universal cross-domain transfer;
- unbounded self-development;
- learned ultimate verifier authority.

These are legitimate next questions precisely because V1 now keeps them outside the frozen claim.

---

## 46. Why V2 should not reopen V1

The lineage repeatedly improved by **moving uncertainty outward**, not by continually rewriting the deepest kernel.

Once a layer became stable, later experiments attacked the next boundary:

~~~text
state distinctions
→ action closure
→ typed continuations
→ language growth
→ constructor growth
→ developmental policy
→ meta-repair policy
→ active memory
→ causal compilation
~~~

The same discipline should govern V2.

V2 should test whether the frozen V1 machine yields measurable compounding on genuinely new work.

It should reopen QCK only if a concrete residual shows that the constitutional contract itself is insufficient.

---

## 47. Final historical interpretation

The repository chain began as a small theory of sufficient distinctions.

It ended V1 with a bounded machine for converting verified experience into a causally justified, restartable, smaller developmental present.

The path was not:

\[
\text{more abstraction}
\to
\text{more abstraction}
\to
\text{more abstraction}.
\]

It was:

\[
\boxed{
\text{proposal}
\to
\text{counterexample}
\to
\text{typed residual}
\to
\text{smaller invariant}
\to
\text{formalization}
\to
\text{runtime consolidation}.
}
\]

That pattern is itself the best example of the QCKN method.
