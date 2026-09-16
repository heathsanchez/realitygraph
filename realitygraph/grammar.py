from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .developmental_types import canonical_digest, canonical_json


@dataclass(frozen=True)
class FiniteConstructor:
    constructor_id: str
    input_type: str
    output_type: str
    semantics: tuple[tuple[str, str], ...]
    complexity: int
    dependencies: tuple[str, ...] = ()
    primitive_expansion: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.constructor_id or not self.input_type or not self.output_type:
            raise ValueError("constructor requires id and interface types")
        if self.complexity < 0:
            raise ValueError("constructor complexity must be non-negative")
        if not self.semantics:
            raise ValueError("constructor requires finite semantics")
        keys = [str(key) for key, _ in self.semantics]
        if len(keys) != len(set(keys)):
            raise ValueError("constructor semantic inputs must be unique")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("constructor dependencies must be unique")
        if self.constructor_id in self.dependencies:
            raise ValueError("constructor cannot depend on itself")

    @property
    def semantic_table(self) -> dict[str, str]:
        return {str(key): str(value) for key, value in self.semantics}

    @property
    def semantic_signature(self) -> str:
        return "".join(value for _, value in sorted(self.semantic_table.items()))

    @property
    def extensional_key(self) -> tuple[str, str, tuple[tuple[str, str], ...]]:
        return (
            self.input_type,
            self.output_type,
            tuple(sorted(self.semantic_table.items())),
        )

    def observe(self, value: str) -> str:
        try:
            return self.semantic_table[str(value)]
        except KeyError as exc:
            raise ValueError(f"input outside verified constructor carrier: {value}") from exc

    def payload(self) -> dict[str, Any]:
        return {
            "constructor_id": self.constructor_id,
            "input_type": self.input_type,
            "output_type": self.output_type,
            "semantics": [list(item) for item in sorted(self.semantic_table.items())],
            "complexity": self.complexity,
            "dependencies": list(self.dependencies),
            "primitive_expansion": list(self.primitive_expansion),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "FiniteConstructor":
        return cls(
            constructor_id=str(payload["constructor_id"]),
            input_type=str(payload["input_type"]),
            output_type=str(payload["output_type"]),
            semantics=tuple((str(a), str(b)) for a, b in payload["semantics"]),
            complexity=int(payload["complexity"]),
            dependencies=tuple(str(x) for x in payload.get("dependencies", ())),
            primitive_expansion=tuple(str(x) for x in payload.get("primitive_expansion", ())),
        )


@dataclass(frozen=True)
class Grammar:
    constructors: tuple[FiniteConstructor, ...]

    def __post_init__(self) -> None:
        ids = [constructor.constructor_id for constructor in self.constructors]
        if len(ids) != len(set(ids)):
            raise ValueError("grammar constructor IDs must be unique")
        available = set(ids)
        for constructor in self.constructors:
            missing = set(constructor.dependencies) - available
            if missing:
                raise ValueError(f"grammar has missing constructor dependencies: {sorted(missing)}")

    @property
    def constructor_map(self) -> dict[str, FiniteConstructor]:
        return {constructor.constructor_id: constructor for constructor in self.constructors}

    def payload(self) -> dict[str, Any]:
        return {
            "constructors": [
                constructor.payload()
                for constructor in sorted(self.constructors, key=lambda item: item.constructor_id)
            ]
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="finite-grammar-v1:")

    def text(self) -> str:
        return canonical_json({"version": "finite-grammar-v1", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "Grammar":
        payload = json.loads(text)
        if payload.pop("version", None) != "finite-grammar-v1":
            raise ValueError("unsupported grammar version")
        grammar = cls(tuple(FiniteConstructor.from_payload(row) for row in payload["constructors"]))
        if grammar.text() != text:
            raise ValueError("non-canonical grammar serialization")
        return grammar

    def extensional_classes(self) -> dict[tuple[str, str, tuple[tuple[str, str], ...]], tuple[str, ...]]:
        classes: dict[tuple[str, str, tuple[tuple[str, str], ...]], list[str]] = {}
        for constructor in self.constructors:
            classes.setdefault(constructor.extensional_key, []).append(constructor.constructor_id)
        return {key: tuple(sorted(values)) for key, values in classes.items()}

    def extensionally_contains(self, constructor: FiniteConstructor) -> bool:
        return constructor.extensional_key in self.extensional_classes()


@dataclass(frozen=True)
class GrammarDelta:
    parent_language_id: str
    child_language_id: str
    added_constructors: tuple[FiniteConstructor, ...]
    residual_digest: str
    authority_snapshot: str
    dependency_ids: tuple[str, ...]
    verifier_id: str
    provenance_ids: tuple[str, ...]
    ablation_handle: str

    def __post_init__(self) -> None:
        if not self.parent_language_id or not self.child_language_id:
            raise ValueError("grammar delta requires parent and child language IDs")
        if not self.added_constructors:
            raise ValueError("grammar delta must add at least one constructor")
        if not self.residual_digest or not self.authority_snapshot or not self.verifier_id:
            raise ValueError("grammar delta requires residual, authority, and verifier")
        if not self.ablation_handle:
            raise ValueError("grammar delta requires ablation handle")

    def payload(self) -> dict[str, Any]:
        return {
            "parent_language_id": self.parent_language_id,
            "child_language_id": self.child_language_id,
            "added_constructors": [item.payload() for item in self.added_constructors],
            "residual_digest": self.residual_digest,
            "authority_snapshot": self.authority_snapshot,
            "dependency_ids": list(self.dependency_ids),
            "verifier_id": self.verifier_id,
            "provenance_ids": list(self.provenance_ids),
            "ablation_handle": self.ablation_handle,
        }

    @property
    def delta_id(self) -> str:
        return canonical_digest(self.payload(), prefix="grammar-delta-v1:")

    def text(self) -> str:
        return canonical_json({"version": "grammar-delta-v1", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "GrammarDelta":
        payload = json.loads(text)
        if payload.pop("version", None) != "grammar-delta-v1":
            raise ValueError("unsupported grammar delta version")
        delta = cls(
            parent_language_id=str(payload["parent_language_id"]),
            child_language_id=str(payload["child_language_id"]),
            added_constructors=tuple(
                FiniteConstructor.from_payload(row) for row in payload["added_constructors"]
            ),
            residual_digest=str(payload["residual_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
            dependency_ids=tuple(str(x) for x in payload.get("dependency_ids", ())),
            verifier_id=str(payload["verifier_id"]),
            provenance_ids=tuple(str(x) for x in payload.get("provenance_ids", ())),
            ablation_handle=str(payload["ablation_handle"]),
        )
        if delta.text() != text:
            raise ValueError("non-canonical grammar delta serialization")
        return delta
