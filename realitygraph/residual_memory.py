from __future__ import annotations

import base64
import json

from .mg import Law, MG
from .residual import CompiledResidualModel
from .predictive import ThresholdRule
from .transfer_memory import transfer_scope


PREFIX = "compiled-residual-v1:"


def residual_to_law(
    source_hashes: tuple[tuple[str, str], ...],
    model: CompiledResidualModel,
    *,
    parent_law_id: str,
    provenance: str,
) -> Law:
    payload = {
        "parent_law_id": parent_law_id,
        "rules": [
            {"probe": rule.probe_name, "threshold": rule.threshold}
            for rule in model.rules
        ],
        "corrections": [
            [list(signature), delta, support]
            for signature, delta, support in model.corrections
        ],
        "min_support": model.min_support,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    scope = transfer_scope(source_hashes)
    ident = f"residual-{scope}-{provenance[:10]}"
    return Law(ident, PREFIX + encoded, scope, provenance)


def _payload(law: Law) -> dict:
    if not law.expr.startswith(PREFIX):
        raise ValueError("law is not a compiled residual model")
    encoded = law.expr[len(PREFIX):]
    padded = encoded + "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode()).decode())


def residual_parent_law_id(law: Law) -> str:
    return str(_payload(law)["parent_law_id"])


def law_to_residual_model(
    law: Law,
    probe_names: tuple[str, ...],
) -> CompiledResidualModel:
    payload = _payload(law)
    index = {name: i for i, name in enumerate(probe_names)}

    rules = []
    for item in payload["rules"]:
        name = str(item["probe"])
        if name not in index:
            raise ValueError(f"compiled residual probe is absent: {name}")
        rules.append(
            ThresholdRule(index[name], name, float(item["threshold"]))
        )

    corrections = []
    for signature, delta, support in payload["corrections"]:
        corrections.append(
            (
                tuple(int(bit) for bit in signature),
                float(delta),
                int(support),
            )
        )

    return CompiledResidualModel(
        tuple(rules),
        tuple(corrections),
        min_support=int(payload["min_support"]),
    )


def add_residual_to_memory(memory: MG, law: Law) -> MG:
    out = MG(memory.verifier, memory.laws.values())
    out.add(law)
    return out


def applicable_residual_laws(
    memory: MG,
    source_hashes: tuple[tuple[str, str], ...],
    probe_names: tuple[str, ...],
) -> tuple[Law, ...]:
    scope = transfer_scope(source_hashes)
    out = []
    for law in memory.laws.values():
        if law.scope != scope or not law.expr.startswith(PREFIX):
            continue
        parent = residual_parent_law_id(law)
        if parent not in memory.laws:
            continue
        try:
            law_to_residual_model(law, probe_names)
        except (KeyError, ValueError):
            continue
        out.append(law)
    return tuple(sorted(out, key=lambda item: item.id))
