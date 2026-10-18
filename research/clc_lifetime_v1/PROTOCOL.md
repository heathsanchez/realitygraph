# Finite CLC lifetime reauthentication V1

Baseline: 7d876da93a007933e3ff9c4894e01cb00e77ff9b. Research-only branch.

Objective: After an actual cold restart, revalidate the exact persisted capability, oracle, CLC claim, Lean source identity, Lean version, and receipt before granting FLASH execution authority. A stored receipt or hash alone never authorizes a capability.

Fixed tests: intact replay accepted only after a fresh Lean check; altered claim, oracle, executable semantics, authority, receipt, source identity, or absent Lean fail closed; revocation disables dependent capability; restoration requires a fresh authenticated admission; alternate support remains viable. Include native original tests and preserve negative results.

Nonclaims: no external-source authentication, no general semantic CLC proof, no G2 cross-domain transfer, no baseline superiority. Report UNKNOWN_ENVIRONMENT separately from false mathematics.
