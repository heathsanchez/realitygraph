# QCKN Real Multidomain Flash V3 — Hardware-Closed Qualification

Authoritative RealityGraph run:
https://github.com/heathsanchez/realitygraph/actions/runs/35412565786

Artifact:
`10574464801`

Artifact digest:
`sha256:fab68e77237ac50ed06bf75caf1af1d6f5913e2358473fbf8ae632b1d83f6e82`

## Result

V3 closes the sole declared authority residual left by V2.

The shared developmental meta-capability remains independently supported by
exactly four real domains:

- SAIR / MathGraph / OpenRouter
- ARC3
- Lean-kernel diagnostic routing
- finite GPU-kernel IR optimization

The common operation is:

```text
verified consequence
→ compile durable state
→ restart
→ reuse before reacquisition
→ ablation restores the prior work
```

GPU hardware is **not** counted as a fifth independent developmental-learning
domain. Instead it is a destination promotion of two already-earned GPU-IR
capabilities.

## Measured hardware authority

The imported hardware certificate is pinned to:

- Runpod / NVIDIA GeForce RTX 4090
- artifact `10574349230`
- digest
  `sha256:b386f11d3af43d20722bb10d5cce37726a9909df79f0b4d042655cf968801873`

Bit-exact `int32` correctness held for both promoted transformations.

Measured medians over 60 repetitions after 12 warmups:

| Transformation | Cold | Promoted | Speedup |
| --- | ---: | ---: | ---: |
| adjacent affine fusion | 0.038112 ms | 0.025568 ms | **1.4906×** |
| identity removal | 0.038768 ms | 0.024576 ms | **1.5775×** |

The hardware residual:

`res:gpu-hardware:promote-ir-capability`

is settled by destination-local evidence:

`gpu-hardware:v1:rtx4090-triton-promotion`

## Event bus

The authority-gated bus now has exactly **5** active cross-domain edges:

1. SAIR → developmental meta-capability
2. ARC3 → developmental meta-capability
3. Lean kernel → developmental meta-capability
4. GPU IR → developmental meta-capability
5. GPU IR → GPU hardware measured-performance capability

The fifth edge is the first explicitly licensed content-level bridge in this
stack. Its source content is exactly:

`remove-identity-and-fuse-affine`

and its destination consequence is exactly:

`rtx4090-triton:fuse-affine+remove-identity`

Its certificate is bound to the measured hardware artifact digest.

All unrelated literal content remains unbridged.

## Residual closure

All five declared authority residuals in this initial qualification are now:

`SETTLED`

The qualification explicitly checks:

- four-domain meta-capability preserved;
- measured hardware run green;
- both hardware speed gates > 1.05×;
- destination-local hardware settlement;
- exactly four developmental meta edges;
- exactly one GPU-IR → GPU-hardware edge;
- zero unrelated literal-content edges;
- direct content controls remain type mismatches;
- heterogeneous avoided-cost units remain typed;
- scalarization remains rejected.

Markers:

```text
PASS_GPU_HARDWARE_RESIDUAL_CLOSED
PASS_EXACT_GPU_IR_TO_HARDWARE_BRIDGE
PASS_QCKN_REAL_MULTIDOMAIN_FLASH_V3
```

## Resource cleanup

The temporary Runpod endpoint was explicitly deleted after qualification.

Cleanup run:
https://github.com/heathsanchez/test/actions/runs/35412396698

Runpod returned HTTP **204**.

## Claim boundary

V3 establishes closure only for the **declared authority residuals in this
initial five-domain qualification**.

It does not establish universal Flash, universal GPU optimization, arbitrary
cross-domain semantic transfer, complete Lean Arena coverage, private SAIR
performance, or open-ended autonomous research.

The meaningful structural result is narrower:

> A shared developmental operation can be promoted across domains only where
> independent authority supports it, while domain content remains scoped unless
> an exact bridge certificate licenses a concrete destination consequence.
