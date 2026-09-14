from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations

from .mg import Law


@dataclass(frozen=True)
class Graph:
    vertices: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]


@dataclass
class Verdict:
    accepted: bool
    consequence: str


@dataclass
class Residual:
    vertices: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    summary: str


class GraphColoring:
    verifier_name = "proper_k_coloring"

    def construct(self, graph: Graph):
        coloring, nodes = self._color(graph.vertices, graph.edges, 3)
        return coloring, nodes

    def verify_candidate(self, graph: Graph, coloring):
        if coloring is not None and self._verify_coloring(graph, coloring, 3):
            return Verdict(True, "chi<=3")
        return Verdict(False, "not-3-colored")

    def verify(self, graph: Graph, consequence: str, witness) -> bool:
        if consequence != "chi=4":
            return False
        return self._find_odd_wheel(graph) is not None and self._verify_coloring(graph, witness, 4)

    def localize(self, graph: Graph, verdict: Verdict) -> Residual:
        verts = list(graph.vertices)
        changed = True
        while changed:
            changed = False
            for v in list(verts):
                trial = [x for x in verts if x != v]
                edges = self._induced(graph.edges, trial)
                coloring, _ = self._color(tuple(trial), tuple(edges), 3)
                if coloring is None:
                    verts = trial
                    changed = True
                    break
        edges = tuple(self._induced(graph.edges, verts))
        return Residual(tuple(verts), edges, f"minimal non-3-colorable core: {len(verts)} vertices")

    def minimal_repair(self, graph: Graph, residual: Residual):
        core = Graph(residual.vertices, residual.edges)
        if not self._recognize_odd_wheel(core):
            return None
        evidence = repr((sorted(residual.vertices), sorted(residual.edges)))
        return "hub(oddcycle)->chi>=4", "finite-simple", evidence

    def law_id(self, expr: str) -> str:
        return "ow" if expr == "hub(oddcycle)->chi>=4" else "law"

    def match_law(self, graph: Graph, law: Law):
        if law.expr != "hub(oddcycle)->chi>=4":
            return None
        return self._find_odd_wheel(graph)

    def finish_from_law(self, graph: Graph, law: Law, match):
        coloring, _ = self._color(graph.vertices, graph.edges, 4)
        if coloring is None:
            raise AssertionError("expected a 4-coloring witness")
        return "chi=4", coloring

    @staticmethod
    def _induced(edges, vertices):
        v = set(vertices)
        return [e for e in edges if e[0] in v and e[1] in v]

    @staticmethod
    def _verify_coloring(graph: Graph, coloring, k: int) -> bool:
        if coloring is None or set(coloring) != set(graph.vertices):
            return False
        if any(not (0 <= coloring[v] < k) for v in graph.vertices):
            return False
        return all(coloring[a] != coloring[b] for a, b in graph.edges)

    @staticmethod
    def _color(vertices, edges, k: int):
        adj = {v: set() for v in vertices}
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
        colors = {}
        nodes = 0

        def choose():
            uncolored = [v for v in vertices if v not in colors]
            if not uncolored:
                return None
            return max(uncolored, key=lambda v: (
                len({colors[n] for n in adj[v] if n in colors}), len(adj[v])
            ))

        def search():
            nonlocal nodes
            nodes += 1
            if len(colors) == len(vertices):
                return dict(colors)
            v = choose()
            forbidden = {colors[n] for n in adj[v] if n in colors}
            for c in range(k):
                if c in forbidden:
                    continue
                colors[v] = c
                found = search()
                if found is not None:
                    return found
                del colors[v]
            return None

        return search(), nodes

    @staticmethod
    def _recognize_odd_wheel(graph: Graph):
        n = len(graph.vertices)
        adj = {v: set() for v in graph.vertices}
        for a, b in graph.edges:
            adj[a].add(b)
            adj[b].add(a)
        for hub in graph.vertices:
            if len(adj[hub]) != n - 1:
                continue
            rim = [v for v in graph.vertices if v != hub]
            rimset = set(rim)
            if len(rim) < 3 or len(rim) % 2 == 0:
                continue
            if not all(len(adj[v] & rimset) == 2 for v in rim):
                continue
            seen, stack = {rim[0]}, [rim[0]]
            while stack:
                x = stack.pop()
                for y in adj[x] & rimset:
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
            if len(seen) == len(rim):
                return {"hub": hub, "rim": tuple(rim)}
        return None

    def _find_odd_wheel(self, graph: Graph):
        adj = {v: set() for v in graph.vertices}
        for a, b in graph.edges:
            adj[a].add(b)
            adj[b].add(a)
        for hub in graph.vertices:
            nbrs = tuple(adj[hub])
            for size in range(3, len(nbrs) + 1, 2):
                for rim in combinations(nbrs, size):
                    verts = (hub,) + rim
                    sub = Graph(verts, tuple(self._induced(graph.edges, verts)))
                    match = self._recognize_odd_wheel(sub)
                    if match:
                        return match
        return None


def odd_wheel_with_leaves(rim_n: int, leaves: int, seed: int, prefix: str) -> Graph:
    if rim_n < 3 or rim_n % 2 == 0:
        raise ValueError("rim_n must be odd and >= 3")
    rng = random.Random(seed)
    rim = [f"{prefix}{i}" for i in range(rim_n)]
    hub = f"{prefix}H"
    edges = set()
    for i, v in enumerate(rim):
        edges.add(tuple(sorted((v, rim[(i + 1) % rim_n]))))
        edges.add(tuple(sorted((hub, v))))
    vertices = rim + [hub]
    for i in range(leaves):
        leaf = f"{prefix}L{i}"
        vertices.append(leaf)
        edges.add(tuple(sorted((leaf, rng.choice(rim + [hub])))))
    rng.shuffle(vertices)
    return Graph(tuple(vertices), tuple(sorted(edges)))
