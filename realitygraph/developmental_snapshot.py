from __future__ import annotations

import json
from dataclasses import dataclass

from .developmental_state import DevelopmentalState
from .developmental_types import canonical_digest, canonical_json


@dataclass(frozen=True)
class DevelopmentalSnapshot:
    state_text: str
    state_digest: str
    grammar_digest: str
    active_capability_ids: tuple[str, ...]
    admitted_delta_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.state_text or not self.state_digest or not self.grammar_digest:
            raise ValueError("developmental snapshot requires state and grammar evidence")
        if len(self.active_capability_ids) != len(set(self.active_capability_ids)):
            raise ValueError("snapshot active capability IDs must be unique")
        if len(self.admitted_delta_ids) != len(set(self.admitted_delta_ids)):
            raise ValueError("snapshot delta IDs must be unique")

    @classmethod
    def from_state(cls, state: DevelopmentalState) -> "DevelopmentalSnapshot":
        return cls(
            state_text=state.to_text(),
            state_digest=state.digest,
            grammar_digest=state.grammar.digest,
            active_capability_ids=state.capability_graph.active_ids(),
            admitted_delta_ids=tuple(delta.delta_id for delta in state.admitted_deltas),
        )

    def payload(self) -> dict[str, object]:
        return {
            "state_text": self.state_text,
            "state_digest": self.state_digest,
            "grammar_digest": self.grammar_digest,
            "active_capability_ids": list(self.active_capability_ids),
            "admitted_delta_ids": list(self.admitted_delta_ids),
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="developmental-snapshot-v2:")

    def to_text(self) -> str:
        return canonical_json({"version": "developmental-snapshot-v2", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "DevelopmentalSnapshot":
        payload = json.loads(text)
        if payload.pop("version", None) != "developmental-snapshot-v2":
            raise ValueError("unsupported developmental snapshot version")
        snapshot = cls(
            state_text=str(payload["state_text"]),
            state_digest=str(payload["state_digest"]),
            grammar_digest=str(payload["grammar_digest"]),
            active_capability_ids=tuple(str(x) for x in payload.get("active_capability_ids", ())),
            admitted_delta_ids=tuple(str(x) for x in payload.get("admitted_delta_ids", ())),
        )
        if snapshot.to_text() != text:
            raise ValueError("non-canonical developmental snapshot serialization")
        return snapshot

    def restore(self) -> DevelopmentalState:
        state = DevelopmentalState.from_text(self.state_text)
        if state.digest != self.state_digest:
            raise ValueError("snapshot state digest mismatch")
        if state.grammar.digest != self.grammar_digest:
            raise ValueError("snapshot grammar digest mismatch")
        if state.capability_graph.active_ids() != self.active_capability_ids:
            raise ValueError("snapshot active capability set mismatch")
        if tuple(delta.delta_id for delta in state.admitted_deltas) != self.admitted_delta_ids:
            raise ValueError("snapshot grammar delta set mismatch")
        return state
