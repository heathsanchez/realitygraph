# QCKN Flash Closure V1 — qualification checkpoint

**Status:** PASS on the exact finite falsification harness. This is an
architectural result, not a claim that arbitrary research domains obtain the
same savings.

Branch: `qckn-flash-closure-v1`

Qualified commit: `7e2faa1682a92e94518b225642d2d85e7c93e973`

Qualification run: `35403517434`

## What changed

Flash is now an executable shared-state transition, not a generational
metaphor.

An independently verified capability or exact separating obstruction is
admitted to one shared graph. Admission immediately runs consequence closure to
a fixed point:

1. prune globally refuted candidate occurrences under matching typed contracts;
2. derive independently re-certified compositions;
3. discharge every compatible live obligation;
4. cancel the remaining search attached to discharged obligations;
5. repeat until no consequential change remains.

Revocation runs the same mechanism in reverse: invalidated causal dependents
reopen, while unrelated discharged obligations remain closed.

The same runtime also contains a future-defined present quotient. Present
states are equivalent exactly when the currently protected verified
continuations give them the same future signature. Adding a verified future may
split the present quotient; revoking a protected future may merge it again.
Historical provenance alone never separates states.

## Positive exact fixture

Ten live obligations were active simultaneously across source, target and six
game-labelled domains.

Independent search:

- search calls: 108
- wall rounds: 16

Flash:

- search calls: 54
- wall rounds: 7
- search calls avoided: 54
- search reduction: 50%
- wall rounds avoided: 9
- cancelled future search occurrences: 82
- all 10 obligations discharged

The first verified decoder capability flashed to two obligations.

The later verified parity capability immediately:

- discharged eight obligations;
- composed with the decoder;
- generated a new independently verified pair-label capability;
- propagated that composite to all six game-labelled obligations;
- cancelled their now-useless remaining searches.

No generation boundary was required.

## Failure capital control

Four independent obligations each had the same frozen four-candidate search
portfolio.

Independent search cost: 16 calls.

Under Flash, each exact counterexample became a typed obstruction and
immediately pruned the same bad candidate from the other live obligations.

Result:

- Flash search calls: 4
- search calls avoided: 12
- wall rounds: 1
- three exact obstructions retained
- nine future candidate occurrences pruned
- all four obligations discharged

Thus informative failure produced immediate lateral future-search reduction.

## Controls

All gates passed:

- sham capability cannot mutate shared state;
- admission order yields the same compiled present;
- composition is independently re-certified;
- revoking parity reopens exactly its eight causal dependents;
- unrelated decoder obligations remain discharged;
- future continuations require matching authority/verifier;
- differing histories do not force a present distinction;
- a newly protected future splits a previously merged present class;
- revoking that future merges the class again.

## Claim boundary

This establishes that the proposed Flash semantics are executable and can
strictly reduce search on a controlled exact multi-obligation system.

It does not establish that raw cross-domain transfer is always beneficial.
ARC3 Global Flash V2 already supplied a useful separator: unrestricted shared
proposal evidence underperformed the market-local scheduler despite beating the
sequential baseline. The real-domain repair therefore keeps exact authority
destination-local and is being tested separately.

The architectural statement justified by this checkpoint is:

> Verified capability and verified failure can be admitted asynchronously into
> one shared consequence graph, propagated immediately to every compatible live
> obligation, composed and re-closed to a fixed point, with obsolete work
> cancelled before further acquisition; protected future continuations can
> simultaneously determine the minimum valid present quotient.
