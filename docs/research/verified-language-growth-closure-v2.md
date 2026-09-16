# Verified Language-Growth Closure V2 — Evidence Record

Date: 2026-09-17

## Authoritative qualification

- Branch: `verified-language-growth-closure-v2`
- Qualification head: `ac5c7d9537c96afcca949aab424d9955e726aaaa`
- GitHub Actions run: `35137364208`
- Job: `104932971679`
- Run conclusion: `success`
- Full repository suite: `91/91` tests passed
- Scientific verdict: `PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2`
- Closure status: `CLOSED_BOUNDED_DEPTH3`
- Machine closure status: `CLOSED_BOUNDED`
- Qualification depth: `3`
- Closure certificate digest: `db788441c3774501d2181812591b3ca152102be8985b3ce482b74dc881f9f59d`
- Evidence artifact: `10463946158` (`verified-language-growth-closure-v2-evidence`)
- Evidence artifact files:
  - `verified-language-growth-closure-v2-summary.json`
  - `verified-language-growth-closure-v2.log`

## What changed from V1

V1 proved a real verified recursive edge from G1 to G2, but the two generations were still individually orchestrated by fixture-specific builders.

V2 removes that orchestration objection. All three growth stages are executed through the same public transition:

```text
realitygraph.developmental_executor.execute_generation(state, spec)
```

The executor contains no fixture import and no branch on G1/G2/G3 identity or constructor names. Generation-specific content is confined to frozen `GenerationSpec` adapters and finite data.

The generic executor owns the consequential protocol:

```text
validate frozen boundary
-> attempt current language
-> distinguish incomplete search from exact no-resolution
-> require Complete + NoResolution before structural growth
-> build ResidualCertificate
-> enumerate declared lower substrate
-> apply verified grammar admission gates
-> compile retained capability
-> validate dependency DAG
-> exact snapshot/restart
-> exhaustive bounded attack
-> sealed future zero-search reuse
-> emit canonical GenerationTrace
-> return changed DevelopmentalState
```

## Three-generation result

### G1 — Boolean observer language growth

- Admitted constructor: `nand-d3-0110`
- Explicit capability dependencies: none
- Grammar search checks before admission: `10`
- Future grammar search calls: `0`
- Complete old language: yes
- Separate no-resolution certificate: yes
- Extensional novelty: yes
- Exact restart: yes
- Exhaustive attack: `SURVIVE`

The current language was the complete four Boolean functions of `x`. The lower substrate was `{0,1,x,y}` plus canonical NAND composition. The executor earned the parity observer rather than receiving XOR as a primitive constructor.

### G2 — stateful observer growth

- Admitted constructor: `fsm-t1000-o01`
- Explicit capability dependency: `nand-d3-0110`
- Grammar search checks before admission: `3`
- Future grammar search calls: `0`
- Complete declared stateless language: yes
- Separate no-resolution certificate: yes
- Extensional novelty: yes
- Exact restart: yes
- Exhaustive attack: `SURVIVE`

G2 consumes the G1 capability as an earned input signal. The resulting stateful observer is therefore not merely later in time; it has an explicit causal dependency on the earlier verified growth.

### G3 — three-state temporal observer growth

- Admitted constructor: `g3-s3-t021101-o010`
- Explicit capability dependency: `fsm-t1000-o01`
- Grammar search checks before admission: `187`
- Future grammar search calls: `0`
- Frozen sequence carrier: all binary sequences of lengths `0..4` (`31` sequences)
- Complete two-state raw machine space: `64`
- Complete three-state raw machine space: `5,832`
- Exact two-state no-resolution: yes
- Three-state extensional novelty: yes
- Exact restart: yes
- Exhaustive attack: `SURVIVE`

The protected target is the finite-state property `1 iff the signal sequence has contained two consecutive 1 values`.

The qualification first exhausted all `64` binary-input two-state Moore machines and proved that none realizes the target on the complete frozen carrier. Only after that exact no-resolution result was structural growth licensed. The lower three-state substrate was then exhaustively generated from all `5,832` raw machines and quotient-reduced extensionally. The admitted three-state observer explicitly depends on G2.

A representation-order bug was exposed during development: the target signature was initially constructed in length-first carrier order while `FiniteConstructor.semantic_signature` canonicalizes by lexicographically sorted semantic keys. The scientific two-state lower-bound test already passed, but the three-state witness comparison failed. The fix changed only signature encoding to the repository's canonical semantic-key order; it did not alter the carrier, target property, state counts, machine spaces, or resource bounds.

## Same-executor gates

All passed:

```text
same executor for G1/G2/G3                  PASS
executor has no fixture imports             PASS
executor has no generation/name dispatch    PASS
same GenerationTrace schema                 PASS
```

This is the principal V2 result: the recursive developmental loop is now reusable machinery rather than hand-written generation control flow.

## Restart and prospective reuse

Every generation serializes into canonical developmental state/snapshot form and restarts exactly before the next generation.

The final cold snapshot reconstructs:

- the exact grammar semantics;
- all three retained capabilities;
- the capability dependency graph;
- admitted grammar deltas;
- terminal records;
- authority/protected-consequence state;
- canonical state digest.

No generation candidate enumerator is needed for cold snapshot restoration.

After each capability is admitted and frozen, the designated future set is evaluated with:

```text
G1 future grammar search calls = 0
G2 future grammar search calls = 0
G3 future grammar search calls = 0
```

## Causal ablation

The active capability dependency chain is:

```text
G1 -> G2 -> G3
```

The exact ablation gates passed:

```text
ablate G1 -> G1 inactive, G2 inactive, G3 inactive
ablate G2 -> G1 active,   G2 inactive, G3 inactive
ablate G3 -> G1 active,   G2 active,   G3 inactive
```

This establishes that the downstream reach is causally dependent on the earned upstream capabilities, rather than merely correlated with their presence during discovery.

## Constitutional controls retained

V2 re-runs and preserves the V1 constitutional controls:

```text
UnknownSearch blocks structural growth          PASS
UnknownChoice remains unresolved without evidence PASS
stale certificate rejected                     PASS
sham extension rejected                        PASS
inherited V1 qualification remains green       PASS
```

In particular, a budget stop remains `UnknownSearch`; it cannot be reinterpreted as evidence that the current language is complete.

## Closure

The final closure audit includes:

- frozen initial-state and three `GenerationSpec` digests;
- three canonical `GenerationTrace` records;
- all admitted grammar deltas;
- active capability DAG;
- exact snapshot/restart evidence;
- complete bounded attack evidence;
- sealed future evidence;
- causal ablation evidence;
- preserved search/choice controls;
- replay digest.

The machine-readable closure remains `CLOSED_BOUNDED`; the human-facing qualification label is `CLOSED_BOUNDED_DEPTH3`.

## Exact claim boundary

This branch establishes a bounded finite result:

> Given an initial verified developmental state and a finite ordered sequence of frozen generation specifications, one generic RealityGraph developmental executor can repeatedly distinguish search incompleteness from certified expressive inadequacy; license structural growth only from complete no-resolution evidence; synthesize and independently verify extensionally novel language constructors; retain them with explicit causal dependencies; restart, attack, and prospectively reuse them; use earlier earned capabilities as substrate dependencies for later growth; preserve transitive invalidation under ancestor ablation; and produce a replayable bounded depth-three closure certificate without generation-specific control flow in the executor.

It does **not** establish:

- open-ended autonomous recursive improvement;
- unbounded generation count;
- autonomous invention of verifier authority or terminal values;
- a universal lowest substrate;
- universal optimal synthesis;
- universal cross-domain generality;
- universal correctness from bounded attack survival;
- closure outside the frozen manifests, finite carriers, declared substrates, verifier authority, and resource envelopes.

The correct scientific boundary is therefore:

```text
verified generic recursive developmental execution at bounded depth 3
!=
open-ended self-development
```
