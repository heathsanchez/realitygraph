# QCKN V2 Compounding Falsification Evidence

**Result:** `PASS` for the declared bounded finite fixture  
**Measured:** 2026-09-18  
**Frozen V1 base:** `527cb7df1d931be53a61b1523abeaae20501af27`  
**Measured implementation:** `edb647e004824a5a74579b3dc7b4ea6a5ad1ff4a`
**Frozen QCK dependency:** `51ea5ab8121099173bc8d4edb6c83a5bcb7f3fb1`  
**Toolchain:** Python 3.12.14, `unittest`, RealityGraph V1 finite capability/ledger/MG2 APIs

## Question

Can independently acquired verified capabilities be composed, independently
re-certified as a new standalone identity, compiled into a smaller active
present, and reused on a disjoint relabelled surface at lower acquisition-search
cost, with matched controls restoring the cold frontier?

The fixture freezes one acquisition-search unit for every generation and target
arm. Authority checks are reported separately and never folded into search.

## Measured developmental sequence

| Generation | Verified result | Acquisition search | Authority checks |
|---|---|---:|---:|
| G1 | `Pair -> Bit` parity from bounded NAND search | 10 | 4 |
| G2 | `Bit -> Label` decoder from the complete four-map portfolio | 3 | 7 |
| G3 | Standalone `Pair -> Label` after typed composition and re-certification | 0 | 8 |

The observed marginal acquisition sequence is therefore:

\[
10 > 3 > 0.
\]

G3's zero is not zero work. The dependency-bearing composite is checked over
all four source inputs, then the newly materialized dependency-free identity is
checked again over all four inputs. Those eight verification checks are exposed
above. Zero refers only to new acquisition search, consistently with G1 and G2.

G2 similarly reports five checks spent rejecting or accepting searched
proposals plus two checks on the separately identified promoted decoder. No
promotion check is hidden inside acquisition search.

The original dependent composite still names both parents. Only
`g3-standalone-parity-label-v2`, with certificate
`cert:g3-standalone-exhaustive-v2`, has no execution dependencies. Its
provenance names A, B, the dependent composition, and their certificates.

## Re-minimisation

| Measure | Before | After |
|---|---:|---:|
| ACTIVE capability records | 3 | 1 |
| ACTIVE declared cost | 8 | 4 |

The protected four-row `Pair -> Label` replay is identical before and after
contraction. Its digest is
`9d7d70a2f2ae2695b1752546f86c663d5b3aac66ce4ea798e4376c2c263b19dd`.

The contracted `CompiledPresent` is 747 bytes and restarts with exact text and
digest equality. Restart digest:
`97ee12c867cb3037fd1367daab4a6f102eb2c0bba058434c11e72ec7a9d8b78f`.

The active MG2 record contains only the standalone capability. The causal ledger
retains three promotion events, with digest `13dc88c0666ade11`, and the retention
decision retains eight provenance pointers. This is omission from ACTIVE, not
erasure of ancestry.

The primary contract declares no independent decoder recovery, so its RESERVE
count is zero. The matched negative contract declares that recovery and places
the decoder in RESERVE; an attempted removal raises `RecoveryUnavailable`.
This result validates the bounded deletion gate and role classification. It does
not claim a complete general implementation of snapshot or maintained reserve.

## Unseen relabelled transfer

Source inputs are `00, 01, 10, 11`. Target inputs are the disjoint surface
`aa, ab, ba, bb`, related only by the frozen carrier isomorphism. Every arm uses
the same complete 16-map target universe and exhaustive target authority.

| Arm | Target search | Authority checks | Compiled shortcut |
|---|---:|---:|---|
| COLD | 7 | 18 | no |
| WARM | 0 | 4 | yes |
| RAW_HISTORY | 7 | 18 | no |
| SHAM | 7 | 20 | no |
| ANCESTOR_ABLATION | 7 | 18 | no |

WARM begins only from the exact restarted contracted `CompiledPresent` and runs
no discovery search. COLD reaches the seventh member of the frozen complete
candidate order. Both reach the same exact target semantics under authority
`bounded-finite-authority-v1` and verifier `truth-table-exhaustive-v1`.

RAW_HISTORY receives the causal ledger but no active compiled capability and
therefore remains cold. SHAM is type-compatible and size-matched, pays its failed
authority check, and then remains cold. Removing the standalone compiled
capability restores the exact cold search cost of 7.

## Falsification gates

| Gate | Outcome |
|---|---|
| G1 search is exactly 10 | PASS |
| G2 search is exactly 3 | PASS |
| G3 acquisition search is exactly 0 | PASS |
| A, B, dependent composition, and standalone materialization meet their declared finite authorities | PASS |
| ACTIVE contracts 3 -> 1 | PASS |
| Protected source consequences are unchanged | PASS |
| Restart is exact and history-free | PASS |
| WARM search is below COLD | PASS |
| WARM and COLD have the same verified endpoint and authority boundary | PASS |
| RAW_HISTORY and SHAM do not receive the shortcut | PASS |
| Standalone ablation restores exact cold cost | PASS |
| Declared decoder recoverability prevents deletion | PASS |
| Frozen V1 regression suite remains green | PASS: 170 total tests, including the 158-test V1 baseline and 12 V2 tests |

Focused command:

```text
python -m unittest tests.test_qckn_v2_compounding_falsification -v
Ran 12 tests ... OK
```

Full regression command:

```text
PYTHONPATH="$PWD:/workspace/scratch/e453c7c0eddc/Minimal-Sufficient-Interface" \
  python -m unittest discover -s tests -p 'test_*.py' -q
Ran 170 tests in 14.777s ... OK
```

Canonical JSON evidence was 2,269 bytes with SHA-256
`97507c75144478aefd242f34675a48c0590590a79da9722f9368d452c356c763`.

Hosted GitHub Actions qualification also passed:

- branch commit: `77e5fef15762f98de90edd1713f650047fb5af74`;
- run: `35337879739` (`Success`, 1m 17s);
- job: `falsify` (`Success`, 36s);
- artifact: `qckn-v2-compounding-falsification-evidence`;
- artifact digest:
  `sha256:5c640d3831d8713f17462ad53b51c2908466c94046e657baec825b18d401f792`.

## Bounded conclusion

Within the declared finite capability spaces, exact structural transport,
authority boundary, and controls, independently acquired verified capabilities
can be composed and independently re-certified into a smaller compiled active
present that reduces acquisition search on unseen relabelled instances. The
raw-history, sham, and exact-ablation controls support causal attribution to the
compiled standalone capability.

This is evidence for bounded verified capability compounding in this fixture.
It is not evidence for universal transfer, open-ended self-improvement,
automatic ontology invention, universal composition optimality, or a complete
runtime realization of QCK maintained reserve.
