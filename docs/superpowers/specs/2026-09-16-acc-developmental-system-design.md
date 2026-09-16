# ACC Developmental System v1 — Design

## Goal

Build one coherent Andrews–Curtis developmental system that preserves the already-verified ACC baseline, learns **which representation/action generator to invoke from residual evidence**, promotes only exact verifier-backed improvements, and freezes before the 550 historically open Miller–Schupp cases are touched by the scientific evaluation.

The system must support two independent outputs:

1. **Discovery lane:** produce officially replayable primitive AC move sequences for previously unsolved presentations.
2. **Proof lane:** turn recurring parameterized structure into Lean theorems in the pinned official SAIR environment.

No claim of solving an open case or proving a theorem may be made without the corresponding official verifier/kernel gate.

## Existing verified starting point

Base branch: `acc-consequence-closure-v1` at `e06d53d08163d145d2541a4bb2da48de3f6b7722`.

This base retains:

- exact official `ac-r2-v1` semantics;
- 424/424 certified training replay and official-verifier compatibility;
- prospective guarded macro reuse;
- exact consequence closure;
- exact AC-realizable orbit closure;
- explicit bridges between native Miller–Schupp representatives and scored representatives;
- ablation/restart controls.

Evidence already established on the exact-state closure experiment:

- 297 acquisition / 127 held-out;
- 6,392 retained solved states;
- 71/127 cold vs 103/127 closure-assisted at budget 100;
- 32 warm-only, 0 cold-only;
- exact restart and zero ablation mismatches;
- full 424-proof closure: 8,408 states;
- open-MS attack: 0/550 at budget 3,000.

The 0/550 result is treated as a **representation/action-language residual**, not as justification for merely increasing search budget.

## Existing work that must be integrated, not reimplemented

### ACC exact-tail/source work

Import from `acc-exact-tail-v1` / `acc-proof-discovery-v1`:

- `acc_exact_tail.py` and its tests as an explicit legacy baseline/control;
- `acc_source_transfer.py`;
- `acc_ms_recurrence.py`;
- `tests/test_acc_exact_tail.py`;
- `tests/test_acc_ms_recurrence.py`;
- `docs/research/acc-ms-centralizer-recurrence.md`.

The exact-tail branch is downstream of `acc-proof-discovery-v1`, so importing from `acc-exact-tail-v1` covers both the tail and the recurrence/source-transfer additions.

### Discovered Miller–Schupp recurrence

Preserve the exact five-move macro:

`N_REDUCTION_MACRO = (6, 2, 9, 3, 7)`

for the parameterized presentation `P(n,w)`, with the exact symbolic boundary

`w^-1 y w = y`.

This recurrence is not a heuristic search feature. It is a candidate **symbolic capability generator**: when its guard is proved, it maps an entire parameter family `P(n+1,w)` to `P(n,w)` by legal AC moves.

### RealityGraph developmental machinery to port semantically

Do not copy OpenML-specific implementation details. Port the protocol from:

- `capability-generator-transfer-v2` — learn a generator family that rescues failed capabilities prospectively;
- `capability-generator-controller-transfer-v3` — learn when to invoke the generator rather than applying it unconditionally;
- `capability-selective-representation-v4` — maintain a frozen portfolio of representations and select locally before verifier gating;
- `baseline-residual-consequence` — learn only corrections to the baseline residual and delete distinctions that do not earn their place;
- `meta-100x-v1` — recursively compile the policy across sealed generations.

## Core architecture

### 1. Immutable truth layer

`realitygraph.acc` and the pinned official SAIR verifier remain the only semantic authorities.

Every generated action, macro, recurrence, substitution move, bridge, or tail must compile to a sequence of the 14 official primitive move IDs. Generated high-level operations are never accepted as equivalences on their own.

A candidate solution is valid only if:

1. local replay reaches the exact ordered official target;
2. the official SAIR verifier accepts the primitive sequence;
3. the sequence respects official move/path limits.

### 2. Baseline capability field

The baseline for all prospective comparisons is the strongest already-verified combination available before the tested future exists:

- primitive best-first search;
- existing guarded macros/start macros;
- exact solved-state tails;
- exact orbit-closed solved-state tails;
- previously promoted symbolic recurrences.

New generators are evaluated as **residual corrections to this baseline**. A new layer must not silently remove a baseline success.

### 3. ACC representation/action-generator portfolio

Create a common generator interface. Each generator consumes only the current presentation, frozen source knowledge, and baseline search diagnostics. It emits zero or more candidates together with their primitive expansion and provenance.

Initial portfolio:

#### G0 — Exact-tail generator

Lookup exact solved states and append the shortest verified suffix. Existing implementation is retained as a control.

#### G1 — Orbit-tail generator

Match an AC-realizable cyclic/inverse/swap representative, prepend the exact bridge to the stored representative, then append its verified suffix.

#### G2 — Parameter-recurrence generator

Recognize parameterized Miller–Schupp structure and apply proved/prospectively certified recurrence schemas such as `(6,2,9,3,7)` only when their symbolic guard is satisfied.

This generator is permitted to emit repeated applications of a recurrence, but each application is expanded to primitive moves and replayed.

#### G3 — Structural macro generator

Mine trajectory fragments without the old requirement that every retained macro reduce total relator length immediately. Candidate fragments may temporarily increase length. Promotion depends on sealed prospective rescue, not local monotonicity.

Fragments are parameterized where possible by source structure rather than stored as exact trajectories.

#### G4 — Substitution/Nielsen supermove generator

Generate a high-level substitution candidate representing rotations/conjugations followed by multiplication, then compile it to ordinary AC moves before search/verifier use.

The implementation may use ACSolverX only as prior-art/reference for the transformation family; the RealityGraph implementation must independently expand and verify every candidate under official SAIR semantics.

No JAX truncation semantics or finite-buffer equality may be treated as group equality.

### 4. Residual descriptor

Introduce `ACCResidual` as a target-free description of why the frozen baseline did not close within its budget.

Minimum fields:

- source family metadata available from the public input (`n`, `|w|`, reduced `w` signature);
- relator lengths and exponent-sum matrix;
- initial heuristic tuple;
- best heuristic tuple reached;
- minimum total relator length reached;
- depth of best state;
- whether/when the search first entered an existing macro-capability state;
- number of capability-state expansions;
- exact/orbit-tail near-hit statistics that do not require a target solution;
- plateau length / number of expansions since last strict structural improvement;
- fraction of generated successors rejected only by `max_total`;
- search budget consumed.

No field may encode whether the presentation is known solvable, the withheld certified move sequence, or any later official outcome.

### 5. Generator learner

On development data only, evaluate each frozen generator family as an augmentation to the baseline.

Generator ranking is lexicographic:

1. number of baseline failures rescued;
2. verified solve improvement;
3. negative number of baseline successes harmed;
4. official-verifier acceptance count;
5. expansion reduction on cases solved by both;
6. lower generator/search cost;
7. deterministic generator ID tie-break.

A generator is promotable only if it produces at least one verifier-backed rescue and zero unaccounted semantic failures.

### 6. Residual-conditioned controller

Learn a small deterministic controller that decides whether to invoke a promoted generator from `ACCResidual` only.

The first controller language is deliberately small:

- conjunctions of threshold/equality predicates over residual fields;
- a default action of `retain baseline`;
- one selected generator ID or a small ordered generator portfolio.

The controller is calibrated on data distinct from generator-learning data. It is compared against:

- baseline only;
- unconditional generator use;
- exhaustive use of every generator.

Promotion gates:

- held-out verified solves are no worse than baseline;
- baseline successes harmed = 0;
- verifier failures are no worse than exhaustive/unconditional alternatives;
- search cost is strictly below exhaustive portfolio search;
- controller serialization/restart is byte-exact;
- controller ablation returns the exact baseline result.

### 7. Selective `UNKNOWN` semantics

If the controller has no certified basis for choosing a generator, it must leave the baseline unchanged. Unsupported regions are `UNKNOWN`, never inferred equivalences.

A generated symbolic schema can be promoted beyond its finite calibration region only when its guard is proved algebraically/Lean-checked. Otherwise it remains a bounded empirical search capability.

### 8. Sealed scientific protocol

The 424 certified SAIR presentations are the only source of supervision for the scientific development run.

Use a deterministic family-level three-way split so members of the same structural family cannot leak arbitrarily across stages:

- **Acquisition:** learn baseline memory and candidate generator schemas;
- **Controller calibration:** choose invocation rules and generator ordering;
- **Future:** untouched prospective evaluation.

Primary split unit is exact reduced `w_vector` family. Where a family contains multiple `n`, larger `n` is held later than smaller `n`; singleton families are allocated by deterministic hash.

The manifest and split digest are frozen before any future evaluation.

The 550 historically open rows must not be loaded by the scientific workflow until:

1. generator portfolio is frozen;
2. controller is frozen;
3. all future gates pass;
4. serialized policy hash is printed.

After that point the policy may run once against the 550 and official verification records the result.

### 9. Deployment-adaptation lane

If the frozen scientific policy still yields 0/550, a separate workflow may inspect **unlabeled** open-case search residuals to improve competition performance.

That lane must be labeled `deployment-adaptation`, and its results must not be described as untouched prospective transfer on the 550.

Any capability created in this lane still requires primitive expansion and official verification. The scientific frozen-policy artifacts remain immutable.

### 10. Recursive capability compilation

After one generator/controller generation passes its sealed future gate, the next generation may use only:

- earlier acquisition/calibration data;
- previously frozen generator/controller policy;
- verified consequences produced before the next future partition exists.

Generation `k+1` must be frozen before its future is evaluated. The key metric is verified consequence per unit search relative to the parent generation, not raw model complexity.

A generation is retained only when it is no worse on verified coverage/harm and strictly improves at least one of:

- verified rescues;
- search expansions/cost;
- supported source scope.

### 11. Proof lane

Integrate the existing Miller–Schupp centralizer recurrence into the main branch as a separate theorem target.

The existing `acc-proof-theorem-v1` CI failure occurred during **building the official Lean environment**, before the candidate theorem was checked. Therefore the theorem is currently neither verified nor falsified.

The proof lane must:

1. reproduce the pinned official Lean environment using the repository's own documented toolchain rather than an unnecessary `lake update` that can drift/fail;
2. compile the official environment first with no candidate file;
3. add the recurrence theorem candidate only after the base environment is green;
4. prove a precise `AC.Reachable` statement for the recurrence under the centralizer guard;
5. keep the computational five-move witness as a cross-check, not as a substitute for Lean proof.

Failure of the Lean statement must not affect Discovery-track search correctness; the lanes share discovered structure but have independent truth gates.

## Data and artifact contracts

Freeze and upload:

- source/split manifest and SHA-256;
- generator portfolio JSON with provenance commits;
- controller JSON and byte-exact restart digest;
- retained exact/orbit tail bank digest;
- symbolic recurrence registry and guard status (`empirical` or `proved`);
- prospective comparison summary;
- ablation summary;
- open-550 candidate file containing only officially accepted solutions;
- official-verifier receipts;
- proof-lane Lean build log and theorem result.

Every accepted candidate must record lineage: baseline state → generator → generated high-level action → primitive move expansion → official receipt.

## Test strategy

Use TDD for every new unit.

Required unit tests:

- generator output expands to legal primitive moves;
- expansion replay equals the generator's claimed successor;
- recurrence guard positives/negatives;
- structural macros may worsen length but cannot bypass the verifier;
- residual descriptors never inspect target moves/outcomes;
- controller invokes only from frozen residual fields;
- controller ablation restores byte-for-byte baseline behavior;
- exact restart of portfolio/controller;
- orbit-tail bridge replay correctness;
- substitution supermove compilation equivalence on exhaustive small examples;
- family split is deterministic, disjoint, and future-sealed;
- open rows are inaccessible before freeze marker exists.

Required integration gates:

- 424/424 replay with local semantics;
- 424/424 official verifier;
- prospective future: baseline vs generated vs controlled vs exhaustive;
- zero harmed baseline successes for promoted controller;
- at least one prospective verifier-backed rescue before any new generator is promoted;
- official verification of every open-550 candidate;
- exact ablation of each retained generator/controller lineage.

## Success definitions

### Scientific success

A frozen generator/controller learned without future/open outcomes produces verifier-backed prospective improvement on untouched certified families while preserving baseline successes.

### Competition success

At least one of the 550 historically open MS presentations receives an officially accepted primitive move sequence.

### Proof-track success

At least one nontrivial parameterized recurrence/family statement discovered by the system is accepted by the pinned official Lean environment.

These are independent claims and must be reported separately.

## Explicit non-goals

- Do not claim the Andrews–Curtis conjecture.
- Do not equate finite empirical recurrence with a universal theorem.
- Do not hide high-level actions from the official verifier.
- Do not increase search budgets before testing representation/action changes.
- Do not use open-550 results to retroactively describe a policy as prospectively frozen.
- Do not merge to `main` or create an external PR as part of this experiment.

## Integration branch

Implementation branch: `acc-developmental-system-v1`.

It starts from `acc-consequence-closure-v1`, then deliberately imports the ACC-specific recurrence/exact-tail artifacts and implements the ACC-native generator/controller protocol. No wholesale merge of the OpenML branches is intended.