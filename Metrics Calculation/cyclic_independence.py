#!/usr/bin/env python3
"""
cyclic_independence_csv.py
====================================================================
Cyclic Independence (CiD) for every *.json file in a directory.
Writes results to a CSV (like the other metrics scripts).

CiD = 1 − ( # unordered service-pairs that have traffic BOTH directions )
           -------------------------------------------------------------
                   total # unordered service-pairs  [ N·(N−1)/2 ]

• Layer fixed to "1_structural_static". Change LAYER_KEY to use another.
• A “partition” = ANY key that appears in the 'decomposition' object.
• Only edges whose source-class and target-class belong to DIFFERENT
  partitions are considered.
--------------------------------------------------------------------
Usage:

    python cyclic_independence_csv.py /path/to/folder --csv cid_by_file.csv
"""

import argparse, json, sys, csv
from pathlib import Path
from itertools import combinations

LAYER_KEY = "1_structural_static"  # change if needed


# ── CLI ------------------------------------------------------------------
def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch Cyclic-Independence (CiD) to CSV")
    p.add_argument("folder", help="Directory containing decomposition JSON files")
    p.add_argument("--csv", default="cid_by_file.csv", help="Output CSV path")
    return p.parse_args()


# ── CiD for ONE file -----------------------------------------------------
def cid_for_file(jpath: Path):
    """
    Return dict with:
      file, partitions, cyclic_pairs, total_pairs, CiD
    or None if the file is unreadable / missing the layer.
    """
    try:
        data = json.loads(jpath.read_text())
        layer = data[LAYER_KEY]
    except (json.JSONDecodeError, KeyError):
        return None

    decomp = layer.get("decomposition", {})
    links  = layer.get("links", [])

    # Every key in decomposition IS a partition
    parts = sorted(decomp.keys())
    n = len(parts)
    total_pairs = n * (n - 1) // 2

    if n <= 1:
        return {
            "file": jpath.name,
            "partitions": n,
            "cyclic_pairs": 0,
            "total_pairs": total_pairs,
            "CiD": 1.0,
        }

    # node → partition map
    node2part = {n["id"]: p for p, lst in decomp.items() for n in lst}

    # directed dependency sets: P → {Q1, Q2, …}
    dep_out = {p: set() for p in parts}

    for e in links:
        src, dst = e.get("source"), e.get("target")
        p_src = node2part.get(src)
        p_dst = node2part.get(dst)
        if p_src is None or p_dst is None or p_src == p_dst:
            continue  # skip edges from/to unknown or same-partition nodes
        dep_out[p_src].add(p_dst)

    # count unordered cyclic pairs
    cyclic = sum(1 for p, q in combinations(parts, 2)
                 if q in dep_out[p] and p in dep_out[q])

    cid = 1 - (cyclic / total_pairs) if total_pairs > 0 else 1.0

    return {
        "file": jpath.name,
        "partitions": n,
        "cyclic_pairs": cyclic,
        "total_pairs": total_pairs,
        "CiD": cid,
    }


# ── Batch driver ---------------------------------------------------------
def main() -> None:
    args = cli()
    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"ERROR: {root} is not a directory")

    json_files = sorted(root.glob("*.json"))
    if not json_files:
        sys.exit("No .json files found in folder.")

    rows = []
    for jf in json_files:
        res = cid_for_file(jf)
        if res is None:
            rows.append({
                "file": jf.name,
                "partitions": "NA",
                "cyclic_pairs": "NA",
                "total_pairs": "NA",
                "CiD": "NA",
            })
        else:
            rows.append({
                "file": res["file"],
                "partitions": res["partitions"],
                "cyclic_pairs": res["cyclic_pairs"],
                "total_pairs": res["total_pairs"],
                "CiD": f'{res["CiD"]:.4f}',
            })

    fields = ["file","CiD", "partitions", "cyclic_pairs", "total_pairs" ]
    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

    print(f"Wrote CiD CSV: {args.csv}")


if __name__ == "__main__":
    main()
