from __future__ import annotations

from dataclasses import dataclass

from .capability_graph import CapabilityGraph
from .memory_graph import MemoryGraphV2, MemoryRevocation
from .meta_executor import MetaGrowthResult, MetaGrowthSpec, execute_meta_growth
from .meta_memory import MetaMemory


@dataclass(frozen=True)
class CompiledPresent:
    """Canonical QCKN active present.

    This is the retained state allowed to alter future execution. Historical
    episodes remain outside it in the causal ledger / developmental evidence.
    """

    memory: MemoryGraphV2

    @classmethod
    def compile(
        cls,
        capability_graph: CapabilityGraph,
        meta_memory: MetaMemory,
    ) -> "CompiledPresent":
        memory = MemoryGraphV2.from_capability_graph(capability_graph).merge(
            MemoryGraphV2.from_meta_memory(meta_memory)
        )
        return cls(memory)

    @property
    def digest(self) -> str:
        return self.memory.digest

    def text(self) -> str:
        return self.memory.text()

    @classmethod
    def parse(cls, text: str) -> "CompiledPresent":
        return cls(MemoryGraphV2.parse(text))

    def restart(self) -> "CompiledPresent":
        restarted = self.parse(self.text())
        if restarted.text() != self.text() or restarted.digest != self.digest:
            raise ValueError("compiled present restart is not exact")
        return restarted

    @property
    def capability_graph(self) -> CapabilityGraph:
        return self.memory.to_capability_graph()

    @property
    def meta_memory(self) -> MetaMemory:
        return self.memory.to_meta_memory()

    def execute_future_meta(
        self,
        object_state,
        spec: MetaGrowthSpec,
    ) -> MetaGrowthResult:
        """Run future meta execution using only promoted active memory."""

        return execute_meta_growth(object_state, self.meta_memory, spec)

    def revoke_capability(
        self,
        capability_id: str,
        *,
        provenance: str = "",
    ) -> "CompiledPresent":
        return CompiledPresent(
            self.memory.merge(
                MemoryGraphV2(
                    revocations=(
                        MemoryRevocation(
                            "capability",
                            capability_id,
                            provenance,
                        ),
                    )
                )
            )
        )

    def revoke_repair_rule(
        self,
        rule_id: str,
        *,
        provenance: str = "",
    ) -> "CompiledPresent":
        return CompiledPresent(
            self.memory.merge(
                MemoryGraphV2(
                    revocations=(
                        MemoryRevocation(
                            "repair_rule",
                            rule_id,
                            provenance,
                        ),
                    )
                )
            )
        )
