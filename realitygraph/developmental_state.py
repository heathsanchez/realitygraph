from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .capability import FiniteCapability
from .capability_graph import CapabilityGraph
from .developmental_types import canonical_digest, canonical_json
from .grammar import Grammar, GrammarDelta


@dataclass(frozen=True)
class TerminalRecord:
    generation_id: str
    obligation_id: str
    route: str
    evidence_digest: str
    retained_capability_id: str | None = None
    admitted_delta_id: str | None = None

    def __post_init__(self) -> None:
        if not self.generation_id or not self.obligation_id or not self.route:
            raise ValueError("terminal record requires generation, obligation, and route")
        if not self.evidence_digest:
            raise ValueError("terminal record requires evidence digest")

    def payload(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "obligation_id": self.obligation_id,
            "route": self.route,
            "evidence_digest": self.evidence_digest,
            "retained_capability_id": self.retained_capability_id,
            "admitted_delta_id": self.admitted_delta_id,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TerminalRecord":
        retained = payload.get("retained_capability_id")
        delta = payload.get("admitted_delta_id")
        return cls(
            generation_id=str(payload["generation_id"]),
            obligation_id=str(payload["obligation_id"]),
            route=str(payload["route"]),
            evidence_digest=str(payload["evidence_digest"]),
            retained_capability_id=None if retained is None else str(retained),
            admitted_delta_id=None if delta is None else str(delta),
        )


def _capability_payload(capability: FiniteCapability) -> dict[str, Any]:
    return {
        "capability_id": capability.capability_id,
        "input_type": capability.input_type,
        "output_type": capability.output_type,
        "semantics": [list(item) for item in sorted(capability.semantic_table.items())],
        "guard_inputs": list(capability.guard_inputs),
        "certificate_id": capability.certificate_id,
        "dependencies": list(capability.dependencies),
        "authority_snapshot": capability.authority_snapshot,
        "verifier_id": capability.verifier_id,
        "provenance_ids": list(capability.provenance_ids),
        "cost": capability.cost,
    }


def _capability_from_payload(payload: dict[str, Any]) -> FiniteCapability:
    return FiniteCapability(
        capability_id=str(payload["capability_id"]),
        input_type=str(payload["input_type"]),
        output_type=str(payload["output_type"]),
        semantics=tuple((str(a), str(b)) for a, b in payload["semantics"]),
        guard_inputs=tuple(str(x) for x in payload.get("guard_inputs", ())),
        certificate_id=str(payload["certificate_id"]),
        dependencies=tuple(str(x) for x in payload.get("dependencies", ())),
        authority_snapshot=str(payload["authority_snapshot"]),
        verifier_id=str(payload["verifier_id"]),
        provenance_ids=tuple(str(x) for x in payload.get("provenance_ids", ())),
        cost=int(payload["cost"]),
    )


@dataclass(frozen=True)
class DevelopmentalState:
    generation_index: int
    grammar: Grammar
    capability_graph: CapabilityGraph
    admitted_deltas: tuple[GrammarDelta, ...]
    terminal_records: tuple[TerminalRecord, ...]
    authority_snapshot: str
    protected_consequence_digest: str
    provenance_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.generation_index < 0:
            raise ValueError("generation index must be non-negative")
        if not self.authority_snapshot or not self.protected_consequence_digest:
            raise ValueError("developmental state requires authority and protected consequence digest")
        if len(self.provenance_ids) != len(set(self.provenance_ids)):
            raise ValueError("state provenance IDs must be unique")
        active_delta_ids = [delta.delta_id for delta in self.admitted_deltas]
        if len(active_delta_ids) != len(set(active_delta_ids)):
            raise ValueError("state grammar deltas must be unique")

    @classmethod
    def empty(
        cls,
        authority_snapshot: str,
        protected_consequence_digest: str,
    ) -> "DevelopmentalState":
        return cls(
            generation_index=0,
            grammar=Grammar(()),
            capability_graph=CapabilityGraph(()),
            admitted_deltas=(),
            terminal_records=(),
            authority_snapshot=authority_snapshot,
            protected_consequence_digest=protected_consequence_digest,
            provenance_ids=(),
        )

    def payload(self) -> dict[str, Any]:
        return {
            "generation_index": self.generation_index,
            "grammar": json.loads(self.grammar.text()),
            "capability_graph": {
                "capabilities": [
                    _capability_payload(capability)
                    for capability in sorted(
                        self.capability_graph.capabilities,
                        key=lambda item: item.capability_id,
                    )
                ],
                "revoked_ids": list(self.capability_graph.revoked_ids),
            },
            "admitted_deltas": [
                json.loads(delta.text()) for delta in self.admitted_deltas
            ],
            "terminal_records": [record.payload() for record in self.terminal_records],
            "authority_snapshot": self.authority_snapshot,
            "protected_consequence_digest": self.protected_consequence_digest,
            "provenance_ids": list(self.provenance_ids),
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="developmental-state-v2:")

    def to_text(self) -> str:
        return canonical_json({"version": "developmental-state-v2", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "DevelopmentalState":
        payload = json.loads(text)
        if payload.pop("version", None) != "developmental-state-v2":
            raise ValueError("unsupported developmental state version")

        grammar_text = canonical_json(payload["grammar"]) + "\n"
        grammar = Grammar.from_text(grammar_text)

        graph_payload = payload["capability_graph"]
        graph = CapabilityGraph(
            tuple(
                _capability_from_payload(row)
                for row in graph_payload.get("capabilities", ())
            ),
            tuple(str(x) for x in graph_payload.get("revoked_ids", ())),
        )

        deltas = tuple(
            GrammarDelta.from_text(canonical_json(row) + "\n")
            for row in payload.get("admitted_deltas", ())
        )
        records = tuple(
            TerminalRecord.from_payload(row)
            for row in payload.get("terminal_records", ())
        )
        state = cls(
            generation_index=int(payload["generation_index"]),
            grammar=grammar,
            capability_graph=graph,
            admitted_deltas=deltas,
            terminal_records=records,
            authority_snapshot=str(payload["authority_snapshot"]),
            protected_consequence_digest=str(payload["protected_consequence_digest"]),
            provenance_ids=tuple(str(x) for x in payload.get("provenance_ids", ())),
        )
        if state.to_text() != text:
            raise ValueError("non-canonical developmental state serialization")
        return state

    def with_generation(
        self,
        *,
        grammar: Grammar,
        capability_graph: CapabilityGraph,
        admitted_delta: GrammarDelta | None,
        terminal_record: TerminalRecord,
        provenance_ids: tuple[str, ...] = (),
    ) -> "DevelopmentalState":
        deltas = self.admitted_deltas + (() if admitted_delta is None else (admitted_delta,))
        provenance = tuple(dict.fromkeys((*self.provenance_ids, *provenance_ids)))
        return DevelopmentalState(
            generation_index=self.generation_index + 1,
            grammar=grammar,
            capability_graph=capability_graph,
            admitted_deltas=deltas,
            terminal_records=self.terminal_records + (terminal_record,),
            authority_snapshot=self.authority_snapshot,
            protected_consequence_digest=self.protected_consequence_digest,
            provenance_ids=provenance,
        )
