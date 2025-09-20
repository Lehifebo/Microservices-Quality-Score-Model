#!/usr/bin/env python3
"""
aggregate_metrics.py
===========================================================
Merge ALL *.csv in the *current folder* into one table:

    Project,Candidate,CiD,CMod,SCF,SMAD,DCCMD

Assumptions:
• CSVs have a 'file' column like "project_candidate.json".
• The metric value column is named after the metric (CiD, CMod, SCF, SMAD or SMAD_c7,
  DCCMD or DCCMD_c2.0). Wide SMAD/DCCMD variants are handled.

All metric values are rounded/formatted to **2 decimals** in the output.

Usage:
  python aggregate_metrics.py --out metrics_agg.csv
"""

import csv, re, sys, argparse
from pathlib import Path
from collections import defaultdict

METRIC_HEADERS = {
    "CiD":   ["CiD"],
    "CMod":  ["CMod", "overall_modularity", "overall_mod"],
    "SCF":   ["SCF"],
    "SMAD":  ["SMAD"],         
    "DCCMD": ["DCCMD"],        
}

def cli():
    p = argparse.ArgumentParser(description="Aggregate metric CSVs into one table (current folder).")
    p.add_argument("--out", default="metrics_agg.csv", help="Output CSV path")
    return p.parse_args()

def pick_metric(headers):
    """Return (metric_name, metric_col) from headers or (None,None)."""
    for metric, candidates in METRIC_HEADERS.items():
        for c in candidates:
            if c in headers:
                return metric, c
    for h in headers:
        if re.fullmatch(r"SMAD_c[\d.]+", h):
            return "SMAD", ("SMAD_c7" if "SMAD_c7" in headers else h)
    for h in headers:
        if re.fullmatch(r"DCCMD_c[\d.]+", h):
            return "DCCMD", ("DCCMD_c2.0" if "DCCMD_c2.0" in headers else h)
    return None, None

def parse_name(fname):
    """Return (project, candidate) from 'project_candidate.json'."""
    base = Path(fname).name
    stem = base[:-5] if base.endswith(".json") else Path(base).stem
    if "_" not in stem:
        return None, None
    proj, cand = stem.split("_", 1)
    return proj, cand

def fmt2(val: str) -> str:
    """Format numeric string to 2 decimals; keep 'NA' or empty as-is."""
    if val is None:
        return "NA"
    s = val.strip()
    if s == "" or s.upper() == "NA":
        return "NA"
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return s  # if it isn't numeric, leave it untouched

def main():
    args = cli()
    root = Path.cwd()
    out_path = (root / args.out).resolve()

    # (Project,Candidate) -> metrics
    agg = defaultdict(lambda: {"CiD":"NA","CMod":"NA","SCF":"NA","SMAD":"NA","DCCMD":"NA"})

    csv_files = sorted(root.glob("*.csv"))
    if not csv_files:
        sys.exit("No *.csv files found in current folder.")

    for csv_path in csv_files:
        if csv_path.resolve() == out_path:
            continue  # skip previous output if re-running

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if not headers or "file" not in headers:
                continue

            metric_name, metric_col = pick_metric(headers)
            if not metric_name:
                continue

            for row in reader:
                fname = (row.get("file") or "").strip()
                if not fname:
                    continue
                proj, cand = parse_name(fname)
                if not proj or not cand:
                    continue
                val = row.get(metric_col)
                agg[(proj, cand)][metric_name] = fmt2(val)

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Project","Candidate","CiD","CMod","SCF","SMAD","DCCMD"])
        for (proj, cand), m in sorted(agg.items()):
            w.writerow([proj, cand, m["CiD"], m["CMod"], m["SCF"], m["SMAD"], m["DCCMD"]])

    print(f"Wrote aggregated metrics (2 decimals): {out_path}")

if __name__ == "__main__":
    main()
