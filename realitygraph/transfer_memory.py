from __future__ import annotations

import base64
import hashlib
import json

from .mg import Law, MG
from .predictive import CompiledPredictiveModel, ThresholdRule


PREFIX = "compiled-predictive-v1:"


def transfer_scope(source_hashes: tuple[tuple[str, str], ...]) -> str:
    body = "|".join(f"{url}={digest}" for url, digest in source_hashes)
    return hashlib.sha256(("transfer|" + body).encode()).hexdigest()[:20]


def model_to_law(
    source_hashes: tuple[tuple[str, str], ...],
    model: CompiledPredictiveModel,
    *,
    provenance: str,
) -> Law:
    payload = {
        "rules": [
            {"probe": rule.probe_name, "threshold": rule.threshold}
            for rule in model.rules
        ],
        "decoder": [
            [list(signature), probability, support]
            for signature, probability, support in model.decoder
        ],
        "fallback": model.fallback_probability,
        "min_support": model.min_support,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    scope = transfer_scope(source_hashes)
    return Law(
        f"transfer-{scope}",
        PREFIX + encoded,
        scope,
        provenance,
    )


def law_to_model(law: Law, probe_names: tuple[str, ...]) -> CompiledPredictiveModel:
    if not law.expr.startswith(PREFIX):
        raise ValueError("law is not a compiled predictive model")
    encoded = law.expr[len(PREFIX):]
    padded = encoded + "=" * (-len(encoded) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    index = {name: i for i, name in enumerate(probe_names)}

    rules = []
    for item in payload["rules"]:
        name = str(item["probe"])
        if name not in index:
            raise ValueError(f"compiled probe is absent from future world: {name}")
        rules.append(ThresholdRule(index[name], name, float(item["threshold"])))

    decoder = []
    for signature, probability, support in payload["decoder"]:
        decoder.append(
            (tuple(int(bit) for bit in signature), float(probability), int(support))
        )

    return CompiledPredictiveModel(
        tuple(rules),
        tuple(decoder),
        float(payload["fallback"]),
        min_support=int(payload["min_support"]),
    )


def model_memory(law: Law) -> MG:
    return MG("sealed-natural-group-transfer-v1", (law,))


def model_from_memory(
    memory: MG,
    source_hashes: tuple[tuple[str, str], ...],
    probe_names: tuple[str, ...],
) -> CompiledPredictiveModel:
    scope = transfer_scope(source_hashes)
    laws = [law for law in memory.laws.values() if law.scope == scope]
    if len(laws) != 1:
        raise ValueError("memory does not contain exactly one compiled transfer law")
    return law_to_model(laws[0], probe_names)
