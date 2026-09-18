# QCKN Flash Kernel V1

## Purpose

This branch turns the earlier Flash Closure and continuation-relative quotient
experiments into one small live developmental runtime.

The object being qualified is not a solver or a multi-agent workflow. It is a
shared consequence graph whose state may be changed by independently admitted:

- verified capabilities;
- exact obstructions;
- protected future continuations;
- explicit revocations.

Workers remain outside the trust boundary. They may propose candidate edges, but
only admitted evidence changes shared developmental state.

## Kernel

The runtime wraps the frozen `FlashClosure` and `FutureQuotient` kernels.

Every admitted event triggers closure until no further cheap structural change is
available:

```text
verified event
→ prune exact refuted routes
→ derive lawful compositions
→ discharge every newly solved live obligation
→ cancel redundant workers / remaining candidate search
→ repeat to fixed point
```

Protected future continuations separately induce the present quotient:

```text
present states
/ equality under every currently protected future consequence
```

Adding a verified separator may split the present; revoking that future may merge
it again.

## Frozen four-lens qualification

The finite qualification uses four abstract developmental lenses named:

- theorem
- ARC
- kernel
- GPU

These labels do **not** assert arbitrary semantic transfer between those real
domains. In the fixture they share one explicitly declared typed contract, which
lets us test whether one global runtime behaves differently from four siloed
pipelines.

There are 12 live obligations total: three per lens. Each begins with an
eight-candidate frozen search portfolio, so the initial future search market is
96 candidate attempts.

Two verified capabilities are discovered in different lenses:

```text
f : X → Y
g : Y → Z
```

Neither one can settle any live `X → Z` obligation alone.

The shared graph has a verified composition rule:

```text
g ∘ f = h : X → Z
```

The qualification also admits one exact negative separator whose fingerprint is
present in every compatible candidate portfolio.

## Controls

### Independent pipelines

The theorem pipeline sees only `f`. The GPU pipeline sees only `g`. The ARC
pipeline sees the negative separator. Because the pipelines do not share live
state:

- no pipeline contains both `f` and `g`;
- `h` cannot be generated;
- only the three ARC-local occurrences of the bad route are pruned;
- 93 candidate attempts remain represented.

With the fixed acquisition costs of `f=4` and `g=5`, the siloed system represents
102 total units of acquisition plus remaining portfolio work.

### Global Flash

The same evidence enters one shared graph.

The exact negative separator first propagates laterally across all 12 compatible
obligations and removes 12 future candidate attempts.

When `g` arrives after `f`, closure derives `h`. In the same recursive closure:

- `h` discharges all 12 live obligations;
- every live worker is cancelled;
- the remaining 84 candidate attempts disappear;
- the total 96-entry search market has been eliminated.

The only paid capability acquisition is still 9 units.

### Sham

A valid but irrelevant `X → Q` capability is admitted. It changes no protected
obligation, generates no composition, and removes no search.

### Ablation

After global closure, revoking `f` invalidates the dependent `h` and reopens all
12 obligations in one flash. The previously admitted obstruction remains valid,
so exactly 84 candidate attempts return rather than the original 96.

This supplies a causal control for the compounding path.

## Future determines present

The same runtime also keeps an ARC-lens finite future quotient.

A first protected continuation gives:

```text
{a,b} | {c}
```

A second protected future distinguishes `a` from `b`, forcing:

```text
{a} | {b} | {c}
```

Revoking that future merges the present back to:

```text
{a,b} | {c}
```

The different provenance histories of `a` and `b` never by themselves justify a
present distinction.

## Intended claim

A green V1 qualification establishes, inside one exact finite fixture, that:

1. informative failure can become globally reusable negative capital;
2. capabilities discovered in different live lenses can compose before their
   originating workers finish unrelated search;
3. recursive closure can eliminate work in every compatible live obligation;
4. protected futures can determine the minimal present quotient;
5. revocation propagates through dependency structure and reopens work;
6. irrelevant verified artifacts do not alter protected state.

The developmental state, rather than any worker, is the persistent object.

## Claim boundary

This is an **exact finite architectural qualification**. The four lens names are
fixtures sharing a declared typed contract. It does not prove that theorem
proving, ARC, Lean-kernel engineering, GPU optimization, robotics, or any other
real domains share arbitrary transferable content.

It also does not establish open-ended autonomous research, universal experiment
selection, universal optimality of the developmental-value score, or an
unbounded intelligence theorem.

The next meaningful test is to attach real independently verified adapters from
multiple domains to this same runtime and measure whether genuine destination
authority supports any lateral transfer or only shared developmental machinery.

## Run

```bash
python -m unittest tests.test_flash_kernel_v1 -v
python qckn_flash_kernel_v1.py
```

A qualified run ends with:

```text
PASS_FLASH_GLOBAL_FAILURE_CAPITAL
PASS_FLASH_RECURSIVE_COMPOSITION
PASS_FLASH_FUTURE_DEFINES_PRESENT
PASS_FLASH_ABLATION_REOPENS
PASS_QCKN_FLASH_KERNEL_V1
```


## Observed qualification

GitHub Actions run:
https://github.com/heathsanchez/realitygraph/actions/runs/35404921798

All five dedicated tests and all five qualification markers passed.

Observed frozen metrics:

- initial candidate search market: **96**
- global informative-failure pruning: **12**
- remaining search after obstruction: **84**
- composed capability generated after cross-lens evidence: **h**
- obligations discharged by the flash: **12 / 12**
- flash radius: **12**
- candidate search eliminated at the fixed point: **96 / 96**
- open workers after closure: **0**
- represented independent-pipeline total cost: **102**
- Flash acquisition cost: **9**
- represented reduction in the frozen fixture: **91.18%**
- targeted ablation reopened: **12 / 12**
- pending search restored after ablation: **84**

The negative-capital event itself required two closure iterations and changed all
12 compatible live obligations. The later `g` admission generated `h` by
composition and recursively discharged the full live set.

The present-state quotient also followed the protected-future control exactly:

```text
{a,b,c}
→ {a,b} | {c}
→ {a} | {b} | {c}
→ revoke future-2
→ {a,b} | {c}
```

The branch therefore qualifies the intended architectural mechanism, subject to
the finite-fixture claim boundary above.
