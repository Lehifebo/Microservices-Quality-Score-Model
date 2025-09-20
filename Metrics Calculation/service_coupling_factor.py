#!/usr/bin/env python3
"""
scf_by_file.py — write Service Coupling Factor (SCF) per *.json to CSV
======================================================================

SCF = external_edge_count / ( external_edge_count + service_count )
(note: current implementation below uses the same computation as your
original script: scf = sqrt( svc_count / (ext_edges + svc_count) ).)

Layer: fixed to '1_structural_static'. Change LAYER_KEY if needed.

Usage:
  python scf_by_file.py /path/to/folder --csv scf_by_file.csv
"""

import argparse, json, sys, math, csv
from pathlib import Path

LAYER_KEY = "1_structural_static"


# ─── CLI ────────────────────────────────────────────────────────────────
def cli():
    p = argparse.ArgumentParser(description="Per-file Service Coupling Factor (SCF) to CSV")
    p.add_argument("folder", help="Directory containing *.json decomposition files")
    p.add_argument("--csv", default="scf_by_file.csv", help="Output CSV path")
    return p.parse_args()


# ─── SCF for one file ───────────────────────────────────────────────────
def scf_for_file(jpath: Path):
    """
    Return dict with: file, services, external_edges, SCF
    or None on error/unreadable file.
    """
    try:
        data  = json.loads(jpath.read_text())
        block = data[LAYER_KEY]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    decomp = block.get("decomposition", {})
    links  = block.get("links", [])

    # every key is a service
    services = sorted(decomp.keys())
    svc_of = {n["id"]: s for s, lst in decomp.items() for n in lst}

    ext_edges = 0
    for e in links:
        src = e.get("source")
        dst = e.get("target")
        s_src = svc_of.get(src)
        s_dst = svc_of.get(dst)
        if s_src and s_dst and s_src != s_dst:
            ext_edges += 1  # directed edge counted once

    svc_count = len(services)
    denom = ext_edges + svc_count
    scf = 0.0 if denom == 0 else math.sqrt(svc_count / denom)  # matches your original script

    return {
        "file": jpath.name,
        "services": svc_count,
        "external_edges": ext_edges,
        "SCF": f"{scf:.4f}",
    }


# ─── Batch driver ───────────────────────────────────────────────────────
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
        res = scf_for_file(jf)
        if res is None:
            rows.append({"file": jf.name, "services": "NA", "external_edges": "NA", "SCF": "NA"})
        else:
            rows.append(res)

    with open(args.csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file","SCF", "services", "external_edges"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote SCF CSV: {args.csv}")


if __name__ == "__main__":
    main()
