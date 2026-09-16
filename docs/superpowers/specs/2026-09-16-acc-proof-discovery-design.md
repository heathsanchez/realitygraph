# ACC Proof Discovery v1 — Design

Date: 2026-09-16

## Objective

Use the official SAIR Andrews–Curtis (ACC) verifier/data as an exact truth oracle and adapt RealityGraph's retained-capability machinery to discover reusable, prospective AC structure that can graduate from Discovery-track replay evidence into a Proof-track partial theorem or Lean formalization.

The first goal is **not** to claim the Andrews–Curtis conjecture. It is to determine whether verified move structure learned only from the 424 public certified training presentations can produce exact, reusable capabilities that transfer prospectively to held-out Miller–Schupp presentations, especially the 550 open MS-1190 cases represented in the scored pool.

## Frozen external truth source

Pin the official repository:

- `SAIRcompetition/Andrews-Curtis`
- commit `a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`
- ordinary move spec `ac-r2-v1`
- move-spec hash `sha256:e13f57d82b5db1a79c1bd9d5ee1f6665ac4d96a634a3656ea20c0ada82e07643`
- Lean 4 `4.29.1`
- Mathlib `5e932f97dd25535344f80f9dd8da3aab83df0fe6`

All certificates must replay under the official reference semantics. No inferred or approximate move semantics may be used for promotion.

## Why this target is unusually strong

The official release provides:

- 424 unscored certified Miller–Schupp training presentations with exact move sequences;
- a full MS-1190 metadata denominator with 424 certified, 216 uncertified, and 550 open rows;
- all 550 open MS-1190 presentations in the scored pool;
- exact integer-encoded relators and frozen verifier semantics;
- a Proof Track that explicitly accepts partial results and Lean formalizations.

This gives a clean prospective test: learn only from certified material, freeze the acquired capabilities, then measure whether those capabilities apply to later/open presentations without consulting solution labels or hidden answers.

## Approaches considered

### A. Direct leaderboard search

Run increasingly strong beam/best-first search over the scored pool.

Pros: immediate Discovery-track utility.

Cons: weak test of the RealityGraph/MSI thesis; successes remain isolated paths and do not naturally produce mathematics.

### B. Verifier-gated capability mining — selected

Replay known training solutions, record exact intermediate states, extract recurring move macros and structural guards, retain only capabilities whose applicability can be decided from the current presentation alone, then test them prospectively on held-out/open MS cases.

Pros: directly reuses RealityGraph's verify → retain → restart → ablate → reuse loop; can produce both shorter search and candidate general lemmas.

Cons: requires careful separation between heuristic observables and theorem-strength guards.

### C. Start directly in Lean theorem search

Attempt broad symbolic lemmas over `AC.Reachable` before mining computational regularities.

Pros: strongest end product if it works.

Cons: poorly targeted initially; risks spending proof effort on irrelevant families.

**Decision:** use B as the discovery engine, with Lean as the promotion gate for any general family claim.

## Architecture

### 1. Official ACC adapter

Add an ACC domain adapter that consumes only frozen public data from the pinned official commit.

Responsibilities:

- parse the 424 certified training instances;
- represent a state as the exact ordered pair of freely reduced relator words;
- expose the 14 ordinary AC moves by delegating to or cross-checking against the official verifier semantics;
- replay a move sequence and record every intermediate state;
- emit immutable hashes for source presentation, move sequence, and final certificate.

The adapter must not invent stronger equivalence classes. Free reduction is permitted because it is part of the official semantics. Relator swaps, cyclic rotations, inversions, automorphisms, or other quotienting may be used only as *features* unless a corresponding exact reachability lemma is proved.

### 2. Trajectory graph

For every certified training path, construct an exact graph:

`presentation state -> verified AC move -> presentation state`.

Record for each state only target-free observables, including:

- reduced relator length vector;
- total length;
- exponent-sum matrix / abelianization signature;
- first/last letters and cancellation opportunities;
- local subword signatures;
- Miller–Schupp source parameters when publicly available (`n`, `w_vector`).

Target distance, future moves, final success, and any scored-pool outcome are forbidden as applicability inputs.

### 3. Capability miner

Mine recurring verified subsequences of moves as candidate capabilities.

A retained capability is:

`guard(current presentation) -> fixed verified move macro -> exact resulting state relation`.

Initial candidate classes:

1. repeated contiguous move macros of length 2–8;
2. macros whose net effect consistently reduces a structural residual after a temporary expansion;
3. parameterized Miller–Schupp motifs indexed by simple source features such as `n` and `w_vector` shape;
4. inverse-equivalent macro pairs, retained separately until their equivalence is proved.

Promotion requires:

- exact replay on every supporting training occurrence;
- deterministic guard from current/source structure only;
- a minimum support threshold;
- no counterexample among training states matching the guard;
- serialization into RealityGraph memory and byte-exact restart.

### 4. Prospective split

Do not randomly split individual states from the same known proof.

Split by natural presentation groups before mining. Phase A contains only certified source presentations. Freeze the capability bank. Phase B evaluates untouched certified presentations grouped by Miller–Schupp parameters so no trajectory from the held-out presentation was seen during acquisition.

Primary prospective metrics:

- number of held-out presentations where at least one frozen capability applies;
- exact replay success rate of applicable capabilities;
- reduction in cold search expansions to first solution under the same search budget;
- solution-length delta;
- number of genuinely new presentations solved only after capability reuse;
- zero-search transfer events, where retained capabilities alone reach a solved residual.

Ablation must delete the retained lineage and restore the cold baseline.

### 5. Open MS-1190 transfer

Only after the held-out certified test is frozen and green, apply the same capability bank to the 550 public `open` MS-1190 rows.

The experiment may use public `n` and `w_vector` metadata and reconstruct the official presentation exactly, but may not use unpublished solutions or verdicts.

For every newly solved open presentation:

1. produce a move list;
2. replay it through the pinned official verifier;
3. record path length, peak relator length, work, and certificate hash;
4. retain the solution only if the official verifier accepts it.

This is Discovery-track evidence, not yet a Proof-track theorem.

### 6. Proof-candidate extraction

Cluster successful transferred capabilities by exact guard and symbolic effect. A cluster becomes a proof candidate only when its guard can be stated independently of the finite training set.

Candidate output shape:

`For all parameters satisfying guard G, presentation P(parameters) is AC-reachable to Q(parameters)`.

The preferred first theorem is a nontrivial Miller–Schupp subfamily or a reusable reachability lemma, not the whole conjecture.

### 7. Lean promotion

Create a separate Lean file importing the official `AC` statement. Formalize only candidates already supported by exact replay evidence.

Promotion levels:

- L0: verified finite move path only;
- L1: parameterized executable generator with independent replay checks;
- L2: Lean theorem showing the macro/family is `AC.Reachable` for all parameters satisfying a stated guard;
- L3: Proof-track-ready partial theorem with a precise description of what remains open.

No Proof-track claim may skip directly from finite experiments to L2/L3.

## Files planned

- `realitygraph/acc.py` — exact ACC domain/state adapter
- `acc_training_replay.py` — replay and trajectory extraction
- `acc_capability_miner.py` — guarded macro discovery/retention
- `acc_prospective_transfer.py` — frozen held-out and open-MS transfer experiment
- `tests/test_acc.py` — reducer/move/replay/gating tests
- `.github/workflows/acc-proof-discovery-v1.yml` — pinned reproducible run
- later, only if evidence warrants it: `lean/ACCProofCandidate.lean`

## Test strategy

1. Reproduce the official sample `ms-train-0160` path exactly.
2. Replay all 424 certified AC training paths; require 424/424 accepted and matching endpoint `(x,y)`.
3. Cross-check local state transitions against official verifier golden vectors and sample receipts.
4. Negative controls: mutate a move, reorder a path, or violate a guard and require rejection/non-promotion.
5. Serialize and restart the capability bank; require byte-exact canonical replay.
6. Run prospective held-out evaluation with acquisition data frozen before targets are inspected.
7. Run lineage ablation and require the warm-only gain to disappear.
8. Only then run the frozen bank against open MS-1190 presentations.
9. Any proposed general theorem gets an independent Lean check against the pinned official `AC.lean` environment.

## Success criteria for v1

The first experiment is successful if all of the following hold:

- official replay compatibility is exact;
- the 424 known certificates reproduce cleanly;
- at least one retained capability transfers to an untouched certified presentation under a target-free guard;
- the transferred capability measurably reduces cold search or solves a residual with zero reacquisition search;
- exact restart succeeds;
- lineage ablation removes the benefit;
- no claim stronger than the evidence is made.

A stronger v1 result is at least one previously open MS-1190 presentation solved by the frozen capability system and accepted by the official verifier.

The Proof-track milestone is later: at least one exact, nontrivial general reachability lemma derived from those recurring capabilities and independently checked in Lean.

## Non-goals

- claiming AC or Stable AC globally from finite data;
- treating heuristic graph similarity as mathematical equivalence;
- using scored outcomes to choose applicability guards;
- optimizing leaderboard path length before establishing exact transfer;
- hiding unsuccessful transfer cases.
