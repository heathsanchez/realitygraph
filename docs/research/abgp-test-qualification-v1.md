# ABGP Test Qualification V1 — Evidence Record

Status: **METHODOLOGICALLY QUALIFIED / NOT CONFIRMATORY EVIDENCE**

This record binds the pre-freeze qualification of the A/B/G/P experimental machinery on branch `abgp-preregistration-freeze-v1`. It does **not** report A/B/G/P confirmatory results. `ABGP-CONFIRM-v1` was not derived, inspected, or executed.

## Observed qualification run

- Qualification/workflow head: `2ae1b0a96ebcff97f3f003d734cb991feaceddd3`
- GitHub Actions run: `35183954190`
- Job: `105081887960`
- Run URL: `https://github.com/heathsanchez/realitygraph/actions/runs/35183954190`
- Result: `SUCCESS`
- Full regression: **200/200 tests passed**
- Qualification verdict: `QUALIFIED`
- Qualification fixtures: **21** total
  - planted positive: **4**
  - ordinary explanation: **13**
  - broken mechanics: **4**
- Every frozen fixture matched its expected scientific/validity outcome.
- Independent statistical-reference audit: `PASS`
- Pre-freeze power audit: `QUALIFIED`
- `confirmatory_namespace_used=false`
- `confirmatory_namespace_accessed=false`

The explicit CLI emitted:

```text
REALITYGRAPH / ABGP TEST QUALIFICATION V1
verdict QUALIFIED
fixtures 21
statistical_reference PASS
power_qualified 1
confirmatory_namespace_used 0
qualification_digest e1e01c892e1006bc68b507865a429a733a168cb3156e57815ba57dac6c6a9206
ABGP_QUALIFIED
```

## Qualification artifact

- Evidence artifact name: `abgp-dev-qual-v1-evidence`
- Artifact ID: `10481661109`
- Artifact ZIP SHA-256: `68177694b0eb6a03a393fdb6777a34d4979fa136a1fe03ce2e2fbfba6af52631`
- `abgp-qualification-summary.json` SHA-256: `4e69329d127381661cc6ce49fffdbecc5c84e621efe0ba7efdbbd43d81517bcf`
- Internal qualification digest: `e1e01c892e1006bc68b507865a429a733a168cb3156e57815ba57dac6c6a9206`

The uploaded evidence bundle also contains the DEV matrix and the independent-P episode-budget audit. The bundle contains DEV/QUAL evidence only.

## Frozen inferential units and power qualification

The qualification rule requires at least 0.80 power at the preregistered minimum meaningful effect throughout the declared nuisance envelope, using component alpha `0.0125`. Counts remain `REVIEW_PENDING`; this table records the present review candidate that passed qualification.

| Arm | Inferential unit / dependence handling | Candidate n | Effect floor | Nuisance envelope | Minimum qualified power |
|---|---|---:|---:|---|---:|
| A | independent acquisition → separately seeded sealed-future episode; same acquisition history/message for fixed-language Bayes; no future verifier/message | 4,096 episodes | 0.05 | paired discordance q = 0.05, 0.10, 0.25, 0.50, 0.75, 1.00 | **0.8252540787** |
| B | ordered acquisition→transfer world pair; 4 interventions nested inside the world; 12 ordered directions × 3 controls = 36 IUT components; dependence-agnostic union-bound guarantee | 1,015 worlds/direction = 12,180 units | 0.15 each component | paired discordance q = 0.15, 0.30, 0.50, 0.75, 1.00 | **0.8005982642** |
| G | independent world; one relevance-label exchange jointly across all nonzero doses; lower-dose signal set to zero for conservative power qualification | 421 worlds | 0.15 max-dose gap | max-dose discordance q = 0.15, 0.30, 0.50, 0.75, 1.00 | **0.8012420003** |
| P | independent acquisition → serialize → hard restart → fixed four-probe future episode; four probes collapse to one binary episode outcome and never inflate n | 4,096 episodes | 0.05 each primary baseline | paired discordance q = 0.05, 0.10, 0.25, 0.50, 0.75, 1.00 | **0.8252540787** |

For P, the full 4,096-independent-acquisition DEV/QUAL resource audit completed with 98,304 maximum acquisition candidate checks. The observed generation time on the GitHub runner was 0.669627 seconds; this runtime is a property of the finite qualification generator, not a claim about a future heavier acquisition implementation.

## Statistical implementation qualification

The scientific statistics were cross-checked against independent finite references rather than self-tested against the same implementation:

- exact McNemar/binomial reference cases: **45**
- Holm reference-grid cases: **625**
- legacy weighted-G exact-sign cases: **114**
- world-blocked G exhaustive-sign cases: **346**
- maximum absolute scientific/reference discrepancy: `2.7755575615628914e-17`

The world-blocked G reference enumerates one sign per world, so all dose contributions within a world change sign together. This independently checks the repeated-measures exchangeability implementation used by the hardened G analysis.

## What `QUALIFIED` means

`QUALIFIED` means the frozen DEV/QUAL challenge suite showed that the experimental machinery is internally capable of the distinctions the preregistration asks it to make:

- planted-positive worlds pass through the same scientific analyzers;
- named ordinary explanations such as fixed-language Bayesian carry-forward, target-side bisimulation, posterior-only persistence, sham structure, and global corruption do not falsely satisfy the stronger claims;
- deliberate protocol defects are classified `INVALID` rather than being misreported as scientific negatives;
- exact statistical implementations agree with independent references;
- the current review-candidate counts satisfy the pre-freeze power rule over the declared nuisance envelopes;
- replay is deterministic and the confirmatory namespace remains inaccessible.

It does **not** mean A, B, G, or P is true in the confirmatory experiment. The strongest scientific interpretation remains unavailable until a separately reviewed final lock is frozen and the one-shot confirmatory namespace is explicitly authorized.

## Current lock boundary

The design manifest and analysis plan remain `REVIEW_PENDING`, and `confirmatory_execution_enabled=false`. The review-lock builder cannot freeze or unlock confirmation. Any eventual frozen lock must bind, among other fields, the successful qualification status/digest, inferential-unit audit hashes, ordinary-explanation oracle hashes, bisimulation canonicalizer hashes, scientific-code hashes, resource budgets, and the confirmatory namespace identifier.

Any post-unlock change to thresholds, counts, inferential units, dependence structure, grammar independence, intervention classes, corruption schedule, information boundaries, source-distinctness, statistical tests, verdict semantics, or scientific code requires a new preregistration version and a new confirmatory namespace.
