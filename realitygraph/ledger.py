from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .mg import Law, MG


@dataclass(frozen=True)
class Event:
    """One immutable causal change.

    Event identity is content-addressed. Parents encode what this event had
    observed, so concurrency is represented rather than guessed from clocks.
    """

    parents: tuple[str, ...]
    kernel: str
    op: str
    target: str
    payload: tuple[tuple[str, str], ...] = ()

    @property
    def id(self) -> str:
        body = {
            "parents": list(self.parents),
            "kernel": self.kernel,
            "op": self.op,
            "target": self.target,
            "payload": list(self.payload),
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    @classmethod
    def add(cls, law: Law, kernel: str, parents: Iterable[str] = ()) -> "Event":
        return cls(
            tuple(sorted(set(parents))),
            kernel,
            "add",
            law.id,
            tuple(sorted({
                "expr": law.expr,
                "scope": law.scope,
                "provenance": law.provenance,
            }.items())),
        )

    @classmethod
    def revoke(
        cls,
        target: str,
        kernel: str,
        parents: Iterable[str] = (),
        reason: str = "",
    ) -> "Event":
        payload = (("reason", reason),) if reason else ()
        return cls(tuple(sorted(set(parents))), kernel, "revoke", target, payload)

    def law(self) -> Law:
        if self.op != "add":
            raise ValueError("event does not contain a law")
        data = dict(self.payload)
        return Law(self.target, data["expr"], data.get("scope", "*"), data.get("provenance", ""))


class Ledger:
    """Immutable-event causal DAG with deterministic union merge.

    The ledger is evidence/history. MG is the compressed live projection.
    """

    def __init__(self, events: Iterable[Event] = ()):
        self.events: dict[str, Event] = {}
        for event in events:
            self._insert(event)

    def _insert(self, event: Event) -> Event:
        old = self.events.get(event.id)
        if old is not None and old != event:
            raise ValueError("content-address collision")
        self.events[event.id] = event
        return event

    @property
    def heads(self) -> tuple[str, ...]:
        parents = {p for event in self.events.values() for p in event.parents}
        return tuple(sorted(set(self.events) - parents))

    def append_add(
        self,
        law: Law,
        kernel: str,
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.add(law, kernel, self.heads if parents is None else parents)
        return self._insert(event)

    def append_revoke(
        self,
        target: str,
        kernel: str,
        reason: str = "",
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.revoke(target, kernel, self.heads if parents is None else parents, reason)
        return self._insert(event)

    def merge(self, other: "Ledger") -> "Ledger":
        return Ledger((*self.events.values(), *other.events.values()))

    def contains(self, ancestor: str, descendant: str) -> bool:
        """True iff ancestor causally precedes descendant."""
        if ancestor == descendant:
            return True
        seen: set[str] = set()
        stack = [descendant]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            event = self.events.get(current)
            if event is None:
                continue
            if ancestor in event.parents:
                return True
            stack.extend(event.parents)
        return False

    def _maximal_adds(self, target: str) -> list[Event]:
        adds = [e for e in self.events.values() if e.op == "add" and e.target == target]
        revokes = [e for e in self.events.values() if e.op == "revoke" and e.target == target]

        # A revoke removes only versions it causally observed. Concurrent adds live.
        live = [
            add
            for add in adds
            if not any(self.contains(add.id, revoke.id) for revoke in revokes)
        ]

        # A causally later add supersedes an earlier version. Concurrent versions
        # remain side-by-side until consequence resolves them.
        return [
            add
            for add in live
            if not any(
                add.id != later.id and self.contains(add.id, later.id)
                for later in live
            )
        ]

    def materialize(self, verifier: str = "") -> MG:
        laws: list[Law] = []
        targets = sorted({e.target for e in self.events.values() if e.op == "add"})
        for target in targets:
            versions = self._maximal_adds(target)
            unique: dict[tuple[str, str, str], Event] = {}
            for event in versions:
                law = event.law()
                unique[(law.expr, law.scope, law.provenance)] = event

            ordered = sorted(unique.values(), key=lambda e: e.id)
            for i, event in enumerate(ordered):
                law = event.law()
                if len(ordered) == 1:
                    laws.append(law)
                else:
                    # Conflict is explicit but non-destructive.
                    laws.append(
                        Law(
                            f"{target}~{event.id[:8]}",
                            law.expr,
                            law.scope,
                            law.provenance or event.id[:12],
                        )
                    )
        return MG(verifier, laws)

    def digest(self) -> str:
        ids = "\n".join(sorted(self.events))
        return hashlib.sha256(ids.encode()).hexdigest()[:16]

    def jsonl(self) -> str:
        rows = []
        for event_id in sorted(self.events):
            event = self.events[event_id]
            row = asdict(event)
            row["id"] = event_id
            row["parents"] = list(event.parents)
            row["payload"] = dict(event.payload)
            rows.append(json.dumps(row, sort_keys=True, separators=(",", ":")))
        return "\n".join(rows) + ("\n" if rows else "")
