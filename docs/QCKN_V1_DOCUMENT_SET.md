# QCK / QCKN V1 Document Set

This documentation set is the human-readable specification derived from the frozen V1 repositories. It does not modify the frozen constitutional or runtime branches.

## 1. QCK V1 — Quantitative Consequential Kernel

Normative mathematical constitution.

Repository: heathsanchez/Minimal-Sufficient-Interface  
Documentation branch: qck-v1-documentation  
Path: docs/QCK_V1_KERNEL_SPEC.md

Defines the canonical consequence contract, quotient, sufficiency, certified substitution, new-context defect, finite presentation, quantitative defect, reserve, active/reserve dynamics, and typed QCK API boundary.

## 2. QCKN V1 — Operational Semantics and Protocol

Path: docs/QCKN_V1_OPERATIONAL_SEMANTICS.md

Defines the developmental state, typed residual routing, MDA boundary, authority/promotion protocol, causal ledger, CompiledPresent, exact restart, reuse, revocation, and master transition.

## 3. QCKN V1 — Operator's Handbook

Path: docs/QCKN_V1_OPERATOR_HANDBOOK.md

Practical procedures for applying QCKN to a domain: defining contracts, classifying REDs, choosing interventions, verifying, promoting, compiling, restarting, measuring compounding, ablating, and releasing.

## 4. QCKN V1 — Conformance and Evidence Profile

Path: docs/QCKN_V1_CONFORMANCE_EVIDENCE.md

Defines V1 conformance levels, frozen commits, proof-integrity requirements, causal-memory requirements, restart/revocation semantics, qualification runs, closure certificate, claim language, and release checklist.

## 5. QCKN V1 — Derivation, Experiments, and Falsifiers

Path: docs/QCKN_V1_DERIVATION_EXPERIMENTS_FALSIFIERS.md

Explains how the architecture emerged from the MSI and RealityGraph research lineage, including the positive results and the falsifiers that forced the final boundaries.

---

## Canonical hierarchy

\[
\boxed{
\begin{array}{c}
\textbf{QCK V1 — Quantitative Consequential Kernel}\\
\text{what consequential substitution means}\\[3pt]
\downarrow\\[3pt]
\textbf{QCKN V1 — Operational Semantics \& Protocol}\\
\text{how verified developmental state changes}\\[3pt]
\downarrow\\[3pt]
\textbf{QCKN V1 — Operator's Handbook}\\
\text{how to run it}\\[3pt]
\downarrow\\[3pt]
\textbf{QCKN V1 — Conformance \& Evidence Profile}\\
\text{how to know an implementation obeys it}\\[3pt]
\downarrow\\[3pt]
\textbf{Reference Lean + runtime + CI evidence}
\end{array}
}
\]

The derivation/falsifier volume sits alongside this hierarchy and records why the rules have their present form.

## Frozen V1 roots

Minimal-Sufficient-Interface:

- qck-v1-frozen
- qckn-adapter-v1-frozen

RealityGraph:

- qckn-v1-frozen

The documentation branches are deliberately separate:

- qck-v1-documentation
- qckn-v1-documentation
