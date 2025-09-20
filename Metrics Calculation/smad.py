#!/usr/bin/env python3
"""
smad_by_file.py
=====================================================================
Compute per-file SMAD value for K = 7 for every *.json
decomposition in a folder (layer = 1_structural_static).

For each file:
  sizes     = service sizes
  medSize   = median(sizes)
  MAD_raw   = median(|size - medSize|)
  SMAD_c7   = 1 − MAD_raw / (MAD_raw + 7)
  c'        = median(size)  (reported as medSize)

Outputs:
  - smad_by_file.csv        (wide format: one row per file, column SMAD_c7)
  - smad_by_file_long.csv   (optional long format with --long)

Usage:
  python smad_by_file.py /path/to/folder [--long]
"""

import json, sys, argparse, csv
from pathlib import Path
from statistics import median

LAYER_KEY = "1_structural_static"

def cli():
    p = argparse.ArgumentParser(description="Per-file SMAD (K=7)")
    p.add_argument("folder", help="folder with *.json decompositions")
    p.add_argument("--wide-csv", default="smad_by_file.csv",
                   help="output CSV path (wide format)")
    p.add_argument("--long-csv", default="smad_by_file_long.csv",
                   help="output CSV path (long format)")
    p.add_argument("--long", action="store_true",
                   help="also write the long-format CSV")
    return p.parse_args()

def analyze_file(jfile: Path):
    """Return dict with per-file stats and SMAD for K=7 or None if unreadable/empty."""
    try:
        data  = json.loads(jfile.read_text())
        layer = data[LAYER_KEY]
        decomp = layer.get("decomposition", {})
        if not isinstance(decomp, dict):
            return None
        sizes = [len(nodes) for nodes in decomp.values()]
        if not sizes:
            return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    med_size = median(sizes)
    mad_raw  = median(abs(sz - med_size) for sz in sizes)
    smad  = 1 - mad_raw / (mad_raw + 7)

    return {
        "file": jfile.name,
        "services": len(sizes),
        "MAD_raw": mad_raw,
        "medSize": med_size,   # <- this is c'
        "min": min(sizes),
        "max": max(sizes),
        "SMAD": smad
    }

def main():
    args = cli()
    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"{root} is not a directory")

    files = sorted(root.glob("*.json"))
    if not files:
        sys.exit("No *.json files found.")

    rows = []
    for jf in files:
        res = analyze_file(jf)
        if res is None:
            # record an NA row so you can see which files failed
            rows.append({
                "file": jf.name,
                "services": "NA",
                "MAD_raw": "NA",
                "medSize": "NA",
                "min": "NA",
                "max": "NA",
                "SMAD_c7": "NA"
            })
        else:
            rows.append(res)

    # ---- write wide CSV ----
    wide_fields = ["file", "SMAD","services", "MAD_raw", "medSize", "min", "max"]
    with open(args.wide_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=wide_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in wide_fields})

    print(f"Wrote per-file wide CSV: {args.wide_csv}")

if __name__ == "__main__":
    main()
