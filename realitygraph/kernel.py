from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .mg import Law, MG


@dataclass
class SolveResult:
    consequence: Any
    witness: Any
    search_nodes: int
    reused_memory: bool
    residual: str
    learned: str | None = None


class Kernel:
    """Construct -> verify -> residual -> minimal repair -> compress -> reuse."""

    def __init__(self, memory: MG):
        self.memory = memory

    def solve(self, domain, problem) -> SolveResult:
        for law in self.memory.laws.values():
            match = domain.match_law(problem, law)
            if match is not None:
                consequence, witness = domain.finish_from_law(problem, law, match)
                if not domain.verify(problem, consequence, witness):
                    raise AssertionError("memory-produced consequence failed verifier")
                return SolveResult(consequence, witness, 0, True, "compiled law matched")

        candidate, search = domain.construct(problem)
        verdict = domain.verify_candidate(problem, candidate)
        if verdict.accepted:
            return SolveResult(verdict.consequence, candidate, search, False, "accepted directly")

        residual = domain.localize(problem, verdict)
        repair = domain.minimal_repair(problem, residual)
        if repair is not None:
            expr, scope, evidence = repair
            prov = hashlib.sha256(evidence.encode()).hexdigest()[:12]
            law = Law(domain.law_id(expr), expr, scope, prov)
            self.memory.add(law)
            consequence, witness = domain.finish_from_law(problem, law, residual)
            if not domain.verify(problem, consequence, witness):
                raise AssertionError("learned consequence failed verifier")
            return SolveResult(consequence, witness, search, False, residual.summary, law.line())

        return SolveResult(verdict.consequence, candidate, search, False, residual.summary)
