from __future__ import annotations

from dataclasses import dataclass

from .mg import Law, MG
from .transfer_memory import PREFIX, law_to_model, transfer_scope


@dataclass(frozen=True)
class CapabilityMatch:
    law_id: str
    scope: str
    provenance: str


def exact_restart(text: str) -> MG:
    """Parse serialized active memory and require byte-for-byte canonical replay."""
    restarted = MG.parse(text)
    if restarted.text() != text:
        raise AssertionError("serialized capability memory did not restart exactly")
    return restarted


def applicable_transfer_capabilities(
    memory: MG,
    source_hashes: tuple[tuple[str, str], ...],
    probe_names: tuple[str, ...],
) -> tuple[CapabilityMatch, ...]:
    """Return compiled transfer laws applicable from source/schema information only.

    No labels, targets, verdicts, or future outcomes are consulted. A law is
    applicable iff its frozen source scope matches and it can be reconstructed
    against the presented probe schema.
    """
    scope = transfer_scope(source_hashes)
    matches = []
    for law in memory.laws.values():
        if law.scope != scope or not law.expr.startswith(PREFIX):
            continue
        try:
            law_to_model(law, probe_names)
        except (KeyError, ValueError):
            continue
        matches.append(CapabilityMatch(law.id, law.scope, law.provenance))
    return tuple(sorted(matches, key=lambda item: item.law_id))


def ablate_capability(memory: MG, law_id: str) -> MG:
    """Delete one retained lineage while preserving every other active law."""
    return MG(
        memory.verifier,
        (law for ident, law in memory.laws.items() if ident != law_id),
    )


def only_law(memory: MG, match: CapabilityMatch) -> Law:
    law = memory.laws.get(match.law_id)
    if law is None:
        raise ValueError(f"capability disappeared from memory: {match.law_id}")
    return law
