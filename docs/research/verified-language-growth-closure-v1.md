# Verified Language-Growth Closure v1 — Evidence Record

Date: 2026-09-17
Branch: `verified-language-growth-closure-v1`
Base: `capability-selective-representation-v4`
Authoritative run: `35132132212`
Head tested by the authoritative run: `d2d2434ab809cc6ac6654b17eac9d89b7ee2fc44`
Evidence artifact: `10461723097`
Artifact SHA-256 (zip): `2f379095d76c8ee08ed31a09f7e4750eebd007164cd36c69902ca8088bb82799`
Closure certificate digest: `2425d88379ab2f842983a729e259551c6b4f20f5d734b8151950be91d6eab0c2`

## Verdict

```text
PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1
CLOSURE CLOSED_BOUNDED
```

The authoritative workflow ran the focused new test modules, the full regression suite, the sealed qualification executable, explicit JSON assertions on the scientific verdict and closure status, and uploaded the resulting summary/log artifact.

Full regression result:

```text
Ran 70 tests in 2.233s
OK
```

## What was qualified

This qualification tests a bounded two-generation developmental loop in which language growth is permitted only after separate old-language completeness and no-resolution certificates exist.

The generic core introduced by this branch includes:

- typed developmental results and exact residual certificates;
- separate completeness and no-resolution evidence for `UNKNOWN_EXPRESSIVITY`;
- deterministic finite grammar semantics and extensional quotienting;
- replayable `GrammarDelta` admission and ablation;
- typed finite capabilities and verified composition;
- dependency-DAG validation and transitive ablation;
- bounded exhaustive counterexample attack;
- constitutional residual routing;
- replayable `CLOSED_BOUNDED` closure certificates.

No Parkinson- or Andrews–Curtis-specific module is imported by the generic core.

## Generation 1 — earned observer

The frozen old observer language is the complete four-function Boolean language of `x` lifted over `(x,y)`:

```text
0000
1111
0011
1100
```

The protected obligation requires signature:

```text
0110
```

The old class is exhaustively complete for its declared `x`-only substrate and the required separator is extensionally absent.

Only after those two facts are certified does growth become legal. The lower declared substrate contains atoms `0`, `1`, `x`, `y` and NAND composition. Search is ordered by compositional depth; the selected earned constructor is:

```text
G1 = nand-d3-0110
signature = 0110
grammar candidate checks = 10
future search calls = 0
```

The selected constructor is extensionally novel relative to the complete old language, independently truth-table verified, serialized/restarted exactly, composed with a separately verified bit-to-label capability, exhaustively attacked over the complete declared carrier, reused with zero grammar search on later inputs, and causally ablated.

A useful debugging result occurred during construction: an earlier fixture counted raw expression-tree NAND occurrences and therefore failed to find the standard shared-subexpression construction inside the declared bound. The qualification was corrected to use the actually declared resource — compositional depth — rather than merely increasing a failed search budget. Under that exact substrate, the observer appears at depth 3.

## Generation 2 — earned stateful observer using G1

The second generation is not a re-run of the first search. Its residual is different: histories share the same present pair while requiring different outcomes based on prior earned G1 output.

The old G2 observation class exhausts all 16 stateless Boolean denotations of the present pair. Because the designated histories have the same present, this complete stateless class cannot separate the histories.

Only after that stateless completeness and no-resolution pair is certified does G2 expand into the declared generic two-state Moore-machine substrate. Its input signal is explicitly the retained G1 constructor.

The selected constructor is:

```text
G2 = fsm-t1000-o01
constructor dependency = nand-d3-0110
grammar candidate checks = 3
future search calls = 0
```

The G2 capability also explicitly depends on the G1 capability. The qualification verifies:

- exact G2 restart;
- zero-search later reuse;
- exhaustive finite attack survival;
- G1 ablation transitively invalidates G2;
- G2-only ablation leaves G1 active.

This is the recursive edge: an earned constructor from generation 1 becomes part of the lawful substrate from which generation 2 can be formed.

## Scientific gates

Every gate below passed in the authoritative run:

```text
g1_old_language_complete
g1_old_language_no_resolution
g1_extensional_novelty
g1_independently_verified
g1_restart_exact
g1_future_reuse_zero_search
g1_composition_verified
g1_attack_survives
g1_ablation_restores_old_limit
g2_stateless_language_complete
g2_stateless_no_resolution
g2_stateful_novelty
g2_depends_on_g1
g2_restart_exact
g2_future_reuse_zero_search
g2_attack_survives
g1_ablation_invalidates_g2
g2_only_ablation_preserves_g1
unknown_search_blocks_growth
unknown_choice_preserved
stale_certificate_rejected
sham_extension_rejected
closed_bounded
```

The runner printed each gate as `=1` and then emitted the exact PASS verdict.

## Constitutional controls

The qualification intentionally protects the distinctions that matter to the developmental kernel:

- budget exhaustion routes to `UNKNOWN_SEARCH`; it cannot manufacture `UNKNOWN_EXPRESSIVITY`;
- `UNKNOWN_CHOICE` preserves multiple lawful alternatives when separating evidence is absent;
- stale or authority-mismatched certificates cannot license growth;
- extensionally duplicate candidates cannot count as language growth;
- a sham non-separator cannot be admitted merely because a proposer emits it;
- dependency cycles and missing dependencies are rejected;
- `CLOSED_BOUNDED` requires exact terminal manifest coverage, replayability, and restart/ablation evidence for every structural admission.

## Exact bounded claim

The warranted claim is:

> Given the frozen finite carriers, old languages, lower substrates, verifier authority, protected consequences, attack spaces and resource envelopes used by this qualification, RealityGraph can distinguish ordinary search insufficiency from certified expressive insufficiency; synthesize and admit a minimal extensionally novel verified constructor; retain, compose, restart, attack and causally ablate it; then use that earned constructor as an explicit dependency of a later verified language-growth generation; and emit a replayable `CLOSED_BOUNDED` certificate for the declared manifest.

## Explicit nonclaims

This result does **not** establish:

- open-ended or universal closure;
- unbounded recursive self-development;
- autonomous invention of a lowest-level substrate;
- a universal least repair when multiple lawful repairs exist;
- universal correctness from survival of a bounded attack;
- optimal language-growth search;
- autonomous choice of ultimate values or verifier authority.

The result is deliberately finite and constitutional: growth occurs only when exact evidence licenses it, and the system preserves `UNKNOWN` when it has not earned the right to change itself.
