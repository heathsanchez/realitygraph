# QCKN v1 release gate

This branch is the first single qualification surface for the bounded QCKN stack.

It pins two independently qualified repositories:

- QCK/QCKN contract source: `heathsanchez/Minimal-Sufficient-Interface`
  at `51ea5ab8121099173bc8d4edb6c83a5bcb7f3fb1`.
- Frozen constitutional QCK theorem surface: ancestor
  `fc112771bd0a24e40e31e4eaef61ca0442103dd4`.
- RealityGraph runtime release candidate: this branch, descended from the green
  `qckn-end-to-end-v1` commit
  `3d78e57afd08c33bd844676f766d023cdc5b65da`.

The release gate deliberately re-runs all load-bearing boundaries rather than
trusting documentation alone:

1. verifies the frozen QCK theorem surface is unchanged;
2. re-runs the finite QCK adapter and typed MDA tests;
3. rebuilds and audits bounded QCK v1 in Lean against pinned Mathlib;
4. exercises the cross-repository path
   `QCK defect -> MDA -> CertifiedSubstitution -> COMPILE -> causal promotion -> CompiledPresent`;
5. re-runs causal-history compression and end-to-end zero-search reuse;
6. re-runs `verified_meta_growth_v3.py` from the causal-ledger compiled present.

The bounded claim remains exactly that: this is a qualified developmental
substitution/retention loop over the declared finite settings and controls. It
does not claim open-ended autonomous development, universal transfer, or
unbounded representation invention.
