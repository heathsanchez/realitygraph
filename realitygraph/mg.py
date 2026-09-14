from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Law:
    id: str
    expr: str
    scope: str = "*"
    provenance: str = ""

    def line(self) -> str:
        tail = f"@{self.scope}" if self.scope else ""
        tail += f"#{self.provenance}" if self.provenance else ""
        return f"+{self.id}:{self.expr}{tail}"


class MG:
    """Tiny canonical active-memory format."""

    def __init__(self, verifier: str = "", laws: Iterable[Law] = ()):
        self.verifier = verifier
        self.laws = {law.id: law for law in laws}

    @classmethod
    def parse(cls, text: str) -> "MG":
        verifier = ""
        laws: list[Law] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines and lines[0] != "MG1":
            raise ValueError("unsupported .mg version")
        for line in lines[1:]:
            if line.startswith("v:"):
                verifier = line[2:]
            elif line.startswith("+"):
                ident, rest = line[1:].split(":", 1)
                provenance = ""
                if "#" in rest:
                    rest, provenance = rest.rsplit("#", 1)
                scope = "*"
                if "@" in rest:
                    rest, scope = rest.rsplit("@", 1)
                laws.append(Law(ident, rest, scope, provenance))
        return cls(verifier, laws)

    @classmethod
    def load(cls, path: str | Path) -> "MG":
        p = Path(path)
        return cls.parse(p.read_text()) if p.exists() else cls()

    def add(self, law: Law) -> None:
        self.laws[law.id] = law

    def merge(self, other: "MG") -> "MG":
        out = MG(self.verifier or other.verifier, self.laws.values())
        for law in other.laws.values():
            old = out.laws.get(law.id)
            if old is None:
                out.add(law)
            elif old != law:
                suffix = law.provenance[:8] or "foreign"
                out.add(Law(f"{law.id}~{suffix}", law.expr, law.scope, law.provenance))
        return out

    def text(self) -> str:
        lines = ["MG1"]
        if self.verifier:
            lines.append(f"v:{self.verifier}")
        lines.extend(self.laws[k].line() for k in sorted(self.laws))
        return "\n".join(lines) + "\n"

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.text())
