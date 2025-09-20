#!/usr/bin/env python3
"""
cmod_by_file.py
---------------------------------------------------------------
Scan every *.json in a folder (1_structural_static layer) and write
a single CSV with per-file Code Modularity (CMod).

Per-partition Cluster Factor:
    CF_i = 2*μ_i / (2*μ_i + Σ_j ε_ij + ε_ji)
  where μ_i  = #internal edges inside partition i (count, not weight)
        ε_ij = sum of weights of edges from i to j (cross-partition only)

Per-file CMod = mean(CF_i) over partitions with at least one edge
(CF_i = 1.0 if only internal edges; partitions with zero edges are ignored).

Usage:
  python cmod_by_file.py /path/to/folder --csv cmod_by_file.csv
"""

import json, sys, argparse, csv
from pathlib import Path
from collections import defaultdict
from typing import Optional

LAYER_KEY = "1_structural_static"

# ── CLI ────────────────────────────────────────────────────────────────
def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Per-file Code Modularity (CMod) to CSV")
    p.add_argument("folder", help="Folder that holds *.json decompositions")
    p.add_argument("--csv", default="cmod_by_file.csv",
                   help="Output CSV path (default: cmod_by_file.csv)")
    return p.parse_args()

# ── compute CMod for ONE file ─────────────────────────────────────────
def cmod_for_file(jpath: Path) -> Optional[float]:
    try:
        data  = json.loads(jpath.read_text())
        layer = data[LAYER_KEY]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    decomp = layer.get("decomposition", {})
    links  = layer.get("links", [])

    # node → partition map
    node2part = {n["id"]: p for p, arr in decomp.items() for n in arr}

    internal = defaultdict(int)    # P → #internal edges (count)
    outgoing = defaultdict(float)  # P → Σ weights of edges leaving P
    incoming = defaultdict(float)  # P → Σ weights of edges entering P

    for e in links:
        src = e.get("source")
        dst = e.get("target")
        if src is None or dst is None:
            continue
        p_src = node2part.get(src)
        p_dst = node2part.get(dst)
        if p_src is None or p_dst is None:
            continue
        w = float(e.get("weight", 1.0))
        if p_src == p_dst:
            internal[p_src] += 1
        else:
            outgoing[p_src] += w
            incoming[p_dst] += w

    # per-partition CF and file-level mean
    cf_vals = []
    for p in decomp.keys():
        intra = internal.get(p, 0)
        ext_w = outgoing.get(p, 0.0) + incoming.get(p, 0.0)  # ε_ij + ε_ji

        if ext_w == 0 and intra == 0:
            cf = None  # edgeless partition -> ignore
        elif ext_w == 0:
            cf = 1.0
        else:
            cf = (2 * intra) / (2 * intra + ext_w)

        if cf is not None:
            cf_vals.append(cf)

    return (sum(cf_vals) / len(cf_vals)) if cf_vals else None

# ── batch driver ───────────────────────────────────────────────────────
def main():
    args  = cli()
    root  = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"ERROR: {root} is not a directory")

    files = sorted(root.glob("*.json"))
    if not files:
        sys.exit("No .json files found in folder.")

    rows = []
    for jf in files:
        cmod = cmod_for_file(jf)
        rows.append((jf.name, f"{cmod:.4f}" if cmod is not None else "NA"))

    with open(args.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "CMod"])
        for row in rows:
            w.writerow(row)

    print(f"Wrote file-level CMod CSV: {args.csv}")

if __name__ == "__main__":
    main()
