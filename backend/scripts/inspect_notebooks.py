import json
import os

def inspect_nb(nb_path):
    print("=" * 60)
    print("INSPECTING:", nb_path)
    print("=" * 60)
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    print(f"Total cells: {len(nb.get('cells', []))}")
    for i, cell in enumerate(nb.get("cells", [])):
        cell_type = cell.get("cell_type")
        source = "".join(cell.get("source", []))
        if cell_type == "code":
            lines = [l for l in source.split("\n") if l.strip()]
            print(f"\n--- Cell [{i}] CODE ({len(lines)} lines) ---")
            for l in lines[:8]:
                print("   ", l[:120])
            if len(lines) > 8:
                print(f"    ... [{len(lines)-8} more lines]")
        elif cell_type == "markdown":
            headers = [l for l in source.split("\n") if l.strip().startswith("#")]
            if headers:
                print(f"\n--- Cell [{i}] MD: {' | '.join(headers[:3])} ---")

if __name__ == "__main__":
    inspect_nb("models/Adaptive_Quiz_Model.ipynb")
    print("\n\n")
    inspect_nb("models/CogniTrace_Adaptive_Quiz_Model_Training_and_Inference.ipynb")
