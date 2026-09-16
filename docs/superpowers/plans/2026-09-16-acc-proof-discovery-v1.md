# ACC Proof Discovery v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an exact, verifier-gated Andrews–Curtis adapter and prospective capability-mining experiment that learns only from the 424 public certified Miller–Schupp paths and tests frozen capabilities on untouched/open presentations.

**Architecture:** Keep official SAIR semantics as an immutable external oracle pinned to commit `a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`. `realitygraph.acc` provides exact local state/replay primitives; replay and mining scripts consume the official training JSON at runtime; capability records are deterministic JSON with exact restart; a GitHub Actions workflow fetches the pinned official repository and runs the authoritative checks.

**Tech Stack:** Python 3 standard library, pytest/unittest-compatible tests, GitHub Actions, official SAIR Python verifier.

**Spec:** `docs/superpowers/specs/2026-09-16-acc-proof-discovery-design.md`

## Global Constraints

- Official repository: `SAIRcompetition/Andrews-Curtis` at commit `a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`.
- Ordinary move spec: `ac-r2-v1`, hash `sha256:e13f57d82b5db1a79c1bd9d5ee1f6665ac4d96a634a3656ea20c0ada82e07643`.
- Promotion uses exact ordered relator states with official free reduction only.
- Applicability guards may use current/source structure only; no future move, target distance, hidden verdict, or scored outcome.
- No global AC claim from finite evidence.
- No PR until the experiment is green and reviewed.

---

### Task 1: Exact ACC state adapter

**Files:**
- Create: `realitygraph/acc.py`
- Create: `tests/test_acc.py`

**Interfaces:**
- Produces: `free_reduce(word)`, `invert(word)`, `apply_move(state, move)`, `replay(state, moves)`, `state_observables(state)`, `state_hash(state)`, `sequence_hash(moves)`.

- [ ] **Step 1: Write failing tests** for free reduction, the official illustrative move `3` on `((1,2),(2,))`, and replay of `ms-train-0001` to `((1,), (2,))`.
- [ ] **Step 2: Run** `python -m pytest tests/test_acc.py -q` and require failure because `realitygraph.acc` is absent.
- [ ] **Step 3: Implement** the minimal exact semantics matching official `core.py` move IDs 0–13.
- [ ] **Step 4: Run** `python -m pytest tests/test_acc.py -q` and require all tests pass.
- [ ] **Step 5: Commit** adapter and tests.

### Task 2: Replay all public certified trajectories

**Files:**
- Create: `acc_training_replay.py`
- Extend: `tests/test_acc.py`

**Interfaces:**
- Consumes: official `competition/examples/training_424.json`.
- Produces: newline-delimited trajectory records plus summary JSON with exact endpoint/replay counts.

- [ ] **Step 1: Add a failing parser/replay-summary test** using a two-instance fixture.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement** loading, replay, exact target assertion, per-state observables, source/sequence hashes, and deterministic output.
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: In CI, require exactly `424/424` training certificates reach `((1,), (2,))` and cross-check each path with the official verifier.

### Task 3: Frozen guarded macro bank

**Files:**
- Create: `acc_capability_miner.py`
- Create: `tests/test_acc_capability.py`

**Interfaces:**
- Consumes: replay trajectories.
- Produces: canonical JSON capability bank. Each capability contains `macro`, `guard`, `support`, `examples`, and deterministic ID/hash.

- [ ] **Step 1: Add failing tests** showing repeated length-2..8 macros are grouped only when the current-state guard matches, and a mismatching state is not applicable.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement** target-free guard signatures from reduced lengths, exponent-sum matrix, boundary letters, and local cancellation flags; mine recurring macros; retain only zero-counterexample guards above configured support.
- [ ] **Step 4: Add exact serialize/restart test** and require byte-identical canonical JSON.
- [ ] **Step 5: Verify GREEN and commit.**

### Task 4: Prospective split, ablation, and open-MS transfer

**Files:**
- Create: `acc_prospective_transfer.py`
- Create: `.github/workflows/acc-proof-discovery-v1.yml`
- Create: `tests/test_acc_transfer.py`

**Interfaces:**
- Consumes: official training JSON, `ms1190_metadata.csv`, official verifier, frozen capability bank.
- Produces: `acc-proof-discovery-summary.json`, candidate submission lines for any newly solved open MS cases, and explicit ablation metrics.

- [ ] **Step 1: Add failing deterministic-split and lineage-ablation tests.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement** presentation-level deterministic Phase A/Phase B split, mine on Phase A only, freeze/restart bank, evaluate untouched Phase B, then delete the bank and require warm-only gains disappear.
- [ ] **Step 4: Only if Phase B is green, reconstruct public `open` MS presentations from `n,w_vector`, apply the frozen bank/search, and send any complete paths through the pinned official verifier.
- [ ] **Step 5: Workflow checks out the official repo at the frozen SHA, verifies the move-spec hash, runs tests, replays 424/424, runs prospective evaluation, and uploads the summary/artifacts.
- [ ] **Step 6: Inspect the workflow result. Do not promote an open-case solution or Proof-track claim unless the official verifier accepts it and the evidence level is stated accurately.**
