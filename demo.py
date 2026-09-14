from pathlib import Path

from realitygraph import Kernel, MG
from realitygraph.graph_coloring import GraphColoring, odd_wheel_with_leaves


def main():
    memory_path = Path("memory.mg")
    memory = MG(verifier=GraphColoring.verifier_name)
    kernel = Kernel(memory)
    domain = GraphColoring()

    a = odd_wheel_with_leaves(7, 6, 20260915, "A")
    first = kernel.solve(domain, a)
    memory.save(memory_path)

    b = odd_wheel_with_leaves(9, 7, 20260916, "B")
    second = kernel.solve(domain, b)

    print("REALITYGRAPH / VERIFIED LEARNING DEMO")
    print("------------------------------------")
    print(f"first problem:  {len(a.vertices)} vertices")
    print(f"3-color search: {first.search_nodes} nodes")
    print(f"residual:       {first.residual}")
    print(f"learned:        {first.learned}")
    print(f"result:         {first.consequence}")
    print()
    print(f"fresh problem:  {len(b.vertices)} vertices")
    print(f"memory reused:  {second.reused_memory}")
    print(f"3-color search: {second.search_nodes} nodes")
    print(f"result:         {second.consequence}")
    print()
    print("memory.mg")
    print("---------")
    print(memory.text(), end="")
    print(f"canonical memory: {len(memory.text().encode())} bytes")


if __name__ == "__main__":
    main()
