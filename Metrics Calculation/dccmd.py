#!/usr/bin/env python3
"""
dccmd_by_file_k2.py — per-file DCCMD for fixed c' = 2.0
========================================================
Depth(story) = longest simple path (service-to-service hops) reachable
               from ANY service that the story touches directly.

DCCMD(c') = 1 − MAD / (MAD + c'),  where MAD = median(|di − median(di)|)

Outputs:
  - dccmd_by_file_k2.csv        (wide format: one row per file, column DCCMD)
  - dccmd_by_file_k2_long.csv   (optional long format with --long)

Usage:
  python dccmd_by_file_k2.py /path/to/folder [--long]
"""

import json, sys, argparse, csv
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
from statistics import median

L1 = "1_structural_static"
L3 = "3_business_use_cases"

def cli():
    p = argparse.ArgumentParser(description="Per-file DCCMD with fixed c'=2.0")
    p.add_argument("folder", help="folder containing decomposition *.json files")
    p.add_argument("--wide-csv", default="dccmd_by_file.csv",
                   help="output CSV path (wide format)")
    p.add_argument("--long-csv", default="dccmd_by_file_k2_long.csv",
                   help="output CSV path (long format)")
    p.add_argument("--long", action="store_true",
                   help="also write the long-format CSV")
    return p.parse_args()

def longest_path(start, adj):
    @lru_cache(maxsize=None)
    def dfs(node, seen):
        best = 0
        for nxt in adj[node]:
            if nxt not in seen:
                best = max(best, 1 + dfs(nxt, seen | {nxt}))
        return best
    return dfs(start, frozenset({start}))

def depths_for_file(jf: Path):
    try:
        data = json.loads(jf.read_text())
        struct = data[L1]
        bus    = data[L3]
    except (json.JSONDecodeError, KeyError):
        return None, None

    # class → service map
    cls2svc = {n["id"]: svc
               for svc, nodes in struct["decomposition"].items()
               for n in nodes}
    services = sorted(struct["decomposition"].keys())

    # service-level adjacency (cross-service only)
    adj = {s: set() for s in services}
    for e in struct.get("links", []):
        s_src = cls2svc.get(e.get("source"))
        s_dst = cls2svc.get(e.get("target"))
        if s_src and s_dst and s_src != s_dst:
            adj[s_src].add(s_dst)

    # story → starting services (original "USE CASE" filter)
    story2svcs = defaultdict(set)
    for e in bus.get("links", []):
        story = e.get("source", "")
        if isinstance(story, str) and "USE CASE" in story.upper():
            svc = cls2svc.get(e.get("target"))
            if svc:
                story2svcs[story].add(svc)

    if not story2svcs:
        return None, len(services)

    # per-story depth = longest path from any touched service
    depths = []
    for svcs in story2svcs.values():
        best = 0
        for s in svcs:
            best = max(best, longest_path(s, adj))
        depths.append(best)

    return depths, len(services)

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
        depths, svc_cnt = depths_for_file(jf)
        if not depths:
            rows.append({
                "file": jf.name,
                "stories": "NA",
                "svc": svc_cnt or "NA",
                "medDepth": "NA",
                "MADraw": "NA",
                "DCCMD": "NA",
            })
            continue

        med = median(depths)
        mad_raw = median(abs(d - med) for d in depths)
        dccmd = 1 - (mad_raw / (mad_raw + 2))

        rows.append({
            "file": jf.name,
            "stories": len(depths),
            "svc": svc_cnt,
            "medDepth": f"{med:.6f}",
            "MADraw": f"{mad_raw:.6f}",
            "DCCMD": f"{dccmd:.6f}",
        })

    # ---- write wide CSV ----
    wide_fields = ["file","DCCMD", "stories", "svc", "medDepth", "MADraw"]
    with open(args.wide_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=wide_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in wide_fields})
    print(f"Wrote per-file wide CSV: {args.wide_csv}")

if __name__ == "__main__":
    main()
