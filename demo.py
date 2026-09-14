from pathlib import Path

from realitygraph import Kernel, Ledger, MG
from realitygraph.graph_coloring import GraphColoring, odd_wheel_with_leaves


def main():
    memory_path = Path("memory.mg")
    ledger_path = Path("ledger.jsonl")

    memory = MG(verifier=GraphColoring.verifier_name)
    ledger = Ledger()
    kernel = Kernel(memory, ledger, kernel_id="demo")
    domain = GraphColoring()

    a = odd_wheel_with_leaves(7, 6, 20260915, "A")
    first = kernel.solve(domain, a)

    memory.save(memory_path)
    ledger_path.write_text(ledger.jsonl())

    b = odd_wheel_with_leaves(9, 7, 20260916, "B")
    second = kernel.solve(domain, b)

    print("REALITYGRAPH / VERIFIED LEARNING DEMO")
    print("------------------------------------")
    print(f"first problem:  {len(a.vertices)} vertices")
    print(f"3-color search: {first.search_nodes} nodes")
    print(f"residual:       {first.residual}")
    print(f"learned:        {first.learned}")
    print(f"ledger event:   {first.ledger_event}")
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
    print(f"ledger events:    {len(ledger.events)}")
    print(f"ledger digest:    {ledger.digest()}")


if __name__ == "__main__":
    main()
