from __future__ import annotations

import json
from dataclasses import dataclass

from .developmental_state import DevelopmentalState
from .developmental_types import canonical_digest, canonical_json
from .meta_memory import MetaMemory


@dataclass(frozen=True)
class MetaSnapshot:
    object_state_text: str
    object_state_digest: str
    meta_memory_text: str
    meta_memory_digest: str
    portfolio_digest: str
    authority_snapshot: str

    def __post_init__(self) -> None:
        if not self.object_state_text or not self.object_state_digest:
            raise ValueError("meta snapshot requires object state text and digest")
        if not self.meta_memory_text or not self.meta_memory_digest:
            raise ValueError("meta snapshot requires meta memory text and digest")
        if not self.portfolio_digest or not self.authority_snapshot:
            raise ValueError("meta snapshot requires portfolio and authority identity")

        state = DevelopmentalState.from_text(self.object_state_text)
        memory = MetaMemory.from_text(self.meta_memory_text)
        if state.digest != self.object_state_digest:
            raise ValueError("meta snapshot object state digest mismatch")
        if memory.digest != self.meta_memory_digest:
            raise ValueError("meta snapshot memory digest mismatch")
        if state.authority_snapshot != self.authority_snapshot:
            raise ValueError("meta snapshot authority mismatch")

    @classmethod
    def from_present(
        cls,
        object_state: DevelopmentalState,
        meta_memory: MetaMemory,
        *,
        portfolio_digest: str,
        authority_snapshot: str,
    ) -> "MetaSnapshot":
        if object_state.authority_snapshot != authority_snapshot:
            raise ValueError("cannot snapshot object state under different authority")
        if not portfolio_digest:
            raise ValueError("cannot snapshot without portfolio identity")
        return cls(
            object_state_text=object_state.to_text(),
            object_state_digest=object_state.digest,
            meta_memory_text=meta_memory.text(),
            meta_memory_digest=meta_memory.digest,
            portfolio_digest=str(portfolio_digest),
            authority_snapshot=str(authority_snapshot),
        )

    def payload(self) -> dict[str, object]:
        return {
            "object_state_text": self.object_state_text,
            "object_state_digest": self.object_state_digest,
            "meta_memory_text": self.meta_memory_text,
            "meta_memory_digest": self.meta_memory_digest,
            "portfolio_digest": self.portfolio_digest,
            "authority_snapshot": self.authority_snapshot,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="meta-snapshot-v3:")

    def text(self) -> str:
        return canonical_json({"version": "meta-snapshot-v3", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "MetaSnapshot":
        payload = json.loads(text)
        if payload.pop("version", None) != "meta-snapshot-v3":
            raise ValueError("unsupported meta snapshot version")
        snapshot = cls(
            object_state_text=str(payload["object_state_text"]),
            object_state_digest=str(payload["object_state_digest"]),
            meta_memory_text=str(payload["meta_memory_text"]),
            meta_memory_digest=str(payload["meta_memory_digest"]),
            portfolio_digest=str(payload["portfolio_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
        )
        if snapshot.text() != text:
            raise ValueError("non-canonical meta snapshot")
        return snapshot

    def restore(self) -> tuple[DevelopmentalState, MetaMemory]:
        state = DevelopmentalState.from_text(self.object_state_text)
        memory = MetaMemory.from_text(self.meta_memory_text)
        if state.digest != self.object_state_digest:
            raise ValueError("meta snapshot restore changed object state digest")
        if memory.digest != self.meta_memory_digest:
            raise ValueError("meta snapshot restore changed meta memory digest")
        if state.authority_snapshot != self.authority_snapshot:
            raise ValueError("meta snapshot restore authority mismatch")
        return state, memory
