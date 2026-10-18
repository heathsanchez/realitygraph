# Factory policy inheritance — qualified training result

Protocol frozen at commit `38b37118b51ecfd07fb623ae966dc785699aeab4`. The only source patch is the sentinel-based default inheritance in the two cattrs dict-unstructuring factories, on cattrs base `b3fb197563bd784adcbe7a385bf7d414a9c82829` with exact author tests at `ff4682ad7a6d180feed4a527f8e5059afeb02432`.

## Native evidence

- Qualified run: https://github.com/heathsanchez/realitygraph/actions/runs/39169033098
- Artifact: 12151384788; SHA-256 `0a9c1edff00045d03bb84c9d38a128fa47e515a0b0271fb3a4d4b8ce58e501a3`
- Original source SHA-256 `a26bdab4fe32cdd3fb25f0b9ca4127d0eeb6778e92828fe549c8ed28e78797eb`
- Candidate source SHA-256 `7984d50ad61db13b118b1956b0a269741b54cb57a32c1b7cac13c48ae218661d`
- Baseline: 2 protected cases, 2 failures, 0 errors.
- Patched protected test: twice, 2 passes per run.
- Both changed author-test files: 220 tests, 0 failures, 0 errors, 15 skipped.
- Physical source withdrawal: 2 failures restored.
- Byte-identical candidate restoration: 2 protected passes, 0 errors.

Scientific state: **WARRANTED_BOUNDED_FACTORY_POLICY_INHERITANCE_TRAINING**. This demonstrates a successful native repair and causal withdrawal/restoration on cattrs, but not cross-source generalization. The generic policy-inheritance rule is a CANDIDATE for transfer, not WARRANTED across factories or repositories.

Held-out future: UNSELECTED. Prospective G2: UNKNOWN. No held-out source inspected or tested.
