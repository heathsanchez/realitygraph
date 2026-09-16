# P vs NP developmental closure V1

## Verdict

`FINITE_SIGNAL`, with an exact new representation theorem but no asymptotic
compression result.

The run discovered and checked an exact behavioral quotient for free-fanout
NAND DAGs.  It does **not** prove a superpolynomial lower bound, `P != NP`, or
an escape from relativization, algebrization, or Natural Proofs.

The swarm proposed the retained candidate manually.  Each generation's lower
substrate contains one frozen candidate, so this run does not claim autonomous
or exhaustive invariant-language discovery.

## Representation genesis

The old singleton recurrence predicts that three-input XOR costs three gates.
Exact enumeration gives four because its two final-gate parents cannot coexist
after two gates.  Pairwise joint availability repairs that example, but is not
recursively closed:

```text
J(3,5) = J(3,7) = J(5,7) = 2
J(3,5,7) = 3
```

Adding `J3`, then `J4`, would create an unbounded arity ladder.  The minimum
missing distinction is provenance: which distinct non-input behaviours must
coexist to produce a function.

For each Boolean function `f`, let `P(f)` be the inclusion-minimal sets of
non-input semantic gate outputs occurring in a normalized NAND DAG that makes
`f` available.  Then

```text
J(S) = min | union_f B_f |, where each B_f is in P(f).
```

This factorizes arbitrary-order coavailability into per-function antichains.

## Why the equality is exact

For the lower bound, take any normalized DAG making every `f` in `S`
available.  Its semantic support contains some minimal `B_f` for each `f`, so
the selected union has size at most the DAG's gate count.

For the upper bound, choose one support `B_f` for every requested function and
concatenate their witness DAGs.  Free fan-out allows an existing equal
behaviour to be reused; a gate whose output behaviour is already present is
skipped.  The resulting normalized DAG has exactly the distinct non-input
behaviours in the union.  The two inequalities coincide.

The antichains are also the bounded least fixed point

```text
P(x_i) = { empty-set }

P(f) = Min_subset {                         (for non-input f)
  {f} union B_g union B_h
  : NAND(g,h)=f, B_g in P(g), B_h in P(h)
}.
```

This removes circuit syntax, topological ordering, wire identity, and duplicate
semantic gates while preserving every exact DAG-size consequence.

## Exact evidence

- Singleton relaxation predicts XOR size `3`; exact size is `4`.
- The smallest fixed-arity obstruction has all three pair costs `2` but triple
  cost `3`.
- Through three inputs and four gates, `1,501` cumulative available-set states
  contract to `345` minimal singleton supports.
- All `17,296` triples of individually reachable three-input functions at
  budget three were checked.  The support quotient correctly certified all
  `16,303` unavailable triples with zero classification errors.
- Fixed-point antichains equal independently extracted state antichains on the
  retained finite universes.

## Developmental execution

The unchanged generic executor runs three generations:

1. singleton costs -> pairwise joint coavailability;
2. fixed-arity failure -> provenance-support antichains;
3. support union -> a symbolic direct-NAND family rule.

The capability dependency chain is explicit.  Ancestor removal transitively
invalidates descendants.  The sealed future query and answer are absent from
the admitted constructor and its attack set.  After exact restart, the retained
G3 parameterized evaluator applies the retained support-union rule to compute
the cost of six distinct NAND outputs on six inputs with zero circuit-enumerator
calls and zero grammar-search calls.  The query is `UNKNOWN` before G3, and
removing either G2 or G3 restores `UNKNOWN`.  A separate direct semantic oracle
checks the returned value.

This is a causal bounded reuse check, but the future family is structurally
simple: its outputs each require one distinct gate.  It is not strong enough to
upgrade the overall result beyond `FINITE_SIGNAL`.

## Exact residual

The quotient is exact but not known to be small.  A function may have
exponentially many incomparable minimum supports.  The highest-information
next experiment is therefore not another `J_k`: search for a compositional
domination preorder strictly stronger than subset inclusion, accepting a
contraction only when exhaustive verification finds zero lost consequences.

The construction is semantic and relativizing in character.  No
nonalgebrizing ingredient or asymptotic Natural-Proof analysis has been
established.

## Replay

```bash
python -m pytest tests/test_pvsnp_developmental_closure_v1.py -q
python pvsnp_developmental_closure_v1.py
```
