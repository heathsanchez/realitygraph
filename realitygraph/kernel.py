from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .ledger import Ledger
from .mg import Law, MG


@dataclass
class SolveResult:
    consequence: Any
    witness: Any
    search_nodes: int
    reused_memory: bool
    residual: str
    learned: str | None = None
    ledger_event: str | None = None


class Kernel:
    """MOVE -> COLLIDE -> SHIFT -> KEEP -> REPEAT."""

    def __init__(
        self,
        memory: MG,
        ledger: Ledger | None = None,
        kernel_id: str = "kernel",
    ):
        self.memory = memory
        self.ledger = ledger
        self.kernel_id = kernel_id

        if self.ledger is not None:
            if not self.ledger.events and self.memory.laws:
                for law in self.memory.laws.values():
                    self.ledger.append_add(law, "bootstrap", parents=())
            self.sync_from_ledger()

    def sync_from_ledger(self) -> None:
        if self.ledger is None:
            return
        live = self.ledger.materialize(self.memory.verifier)
        self.memory.laws = live.laws

    def _keep(self, law: Law) -> str | None:
        if self.ledger is None:
            self.memory.add(law)
            return None
        event = self.ledger.append_add(law, self.kernel_id)
        self.sync_from_ledger()
        return event.id

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
            consequence, witness = domain.finish_from_law(problem, law, residual)

            if not domain.verify(problem, consequence, witness):
                raise AssertionError("proposed learned consequence failed verifier")

            event_id = self._keep(law)
            return SolveResult(
                consequence,
                witness,
                search,
                False,
                residual.summary,
                law.line(),
                event_id,
            )

        return SolveResult(verdict.consequence, candidate, search, False, residual.summary)
