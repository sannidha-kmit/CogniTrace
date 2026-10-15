import json

def inspect_first():
    with open("models/Adaptive_Quiz_Model.ipynb", "r", encoding="utf-8") as f:
        nb = json.load(f)
    print("Total cells in Adaptive_Quiz_Model.ipynb:", len(nb.get("cells", [])))
    for i, cell in enumerate(nb.get("cells", [])):
        cell_type = cell.get("cell_type")
        source = "".join(cell.get("source", []))
        lines = [l for l in source.split("\n") if l.strip()]
        print(f"\n--- Cell [{i}] {cell_type.upper()} ({len(lines)} lines) ---")
        for l in lines[:6]:
            print("   ", l[:120])
        if len(lines) > 6:
            print(f"    ... [{len(lines)-6} more lines]")

if __name__ == "__main__":
    inspect_first()
