# ABGP P Independent-Episode Budget / Power Audit

Date: 2026-09-17
Status: REVIEW_PENDING methodological audit; not confirmatory evidence
Confirmatory namespace accessed: NO

## Finding

The current DEV P harness acquires one synthetic `RetainedStructure`, serializes/restarts it once, and then evaluates many held-out future tasks under that same retained object. Therefore the future-task count is not the number of independent acquisition→restart→future episodes.

The stronger P claim requires the independent inferential unit to be an acquisition episode (or else the claim must be explicitly conditional on one fixed acquired object).

## Exact paired-Bernoulli power calculation

For the simplest design with exactly one scored future binary outcome per independent acquisition episode, keep the currently proposed preregistered parameters:

- effect floor: 0.05 absolute treatment-minus-control advantage;
- component alpha: 0.0125 (conservative four-arm Holm floor used by the current pre-freeze qualification audit);
- exact one-sided paired McNemar/binomial test;
- full feasible discordance envelope q ∈ {0.05, 0.10, 0.25, 0.50, 0.75, 1.00};
- target minimum power: 0.80 at every q in that envelope.

Under those rules, the minimum independent acquisition-episode count is approximately **3,820**. At the current round count of **4,096** independent episodes, the worst-case power is approximately **0.825**, attained at q=1.00.

Illustrative worst-case minimum power across the envelope:

| independent acquisition episodes | minimum power |
| ---: | ---: |
| 40 | 0.003 |
| 64 | 0.023 |
| 100 | 0.035 |
| 256 | 0.065 |
| 512 | 0.130 |
| 1,024 | 0.248 |
| 2,048 | 0.495 |
| 3,820 | 0.800 |
| 4,096 | 0.825 |

The worst case at large n is complete discordance (q=1.00), where a 5-point marginal advantage corresponds to only a modest directional imbalance among discordant pairs.

## Budget implication

This audit does **not** establish that ~3,820–4,096 independent acquisition episodes are affordable.

The current `acquire_dev_structure()` is a synthetic constant-time DEV constructor and is not a valid proxy for the cost of the strengthened confirmatory acquisition procedure. The review lock requires `resource_budgets`, but no final frozen resource budget exists yet.

Therefore P is currently blocked on one of two defensible designs:

1. **One future outcome per independent acquisition episode.** This preserves the exact paired-binary model and requires ~3,820 independent acquisitions under the current conservative power rule.
2. **Fixed nested futures per acquisition episode.** Then the future-task count must be preregistered, nested outcomes must be reduced to a frozen per-episode statistic, inference/randomization must occur at the acquisition-episode level, and power must be recomputed over a preregistered between-episode nuisance/variance envelope. Nested futures cannot be counted as independent units.

If neither design fits the frozen resource budget, the stronger cross-acquisition P claim is not presently feasible at the 0.05 effect floor under the current distribution-free paired-binary power criterion. The scientifically clean alternatives would be to weaken P to a conditional-on-acquired-object persistence claim or preregister a different hierarchical estimand/test before freeze; the effect floor should not be changed merely to make the existing budget pass.

## Required next evidence before P can be frozen

- implement or otherwise bound the actual strengthened acquisition procedure;
- measure its DEV-only resource cost without using any confirmatory seed/outcome;
- choose and freeze the number of independent acquisition episodes;
- if nested futures are used, freeze their count K and the per-episode aggregation rule;
- freeze the episode-level test and nuisance envelope;
- rerun the power audit under those final definitions;
- bind the resulting resource budget and acquisition implementation hash in the final lock.
