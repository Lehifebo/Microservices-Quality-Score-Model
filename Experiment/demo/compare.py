from itertools import combinations
from pathlib import Path
from datetime import datetime
import csv
import random

# --- Show description ---
desc_path = Path("description.txt")
if desc_path.exists():
    with open(desc_path, "r", encoding="utf-8") as f:
        print(f.read())
else:
    print("⚠️ 'description.txt' not found. Continuing without description.")

input("\nPress Enter to start...")

# --- Setup ---
svg_folder = Path("svgs")
svg_files = sorted(svg_folder.glob("*.svg"))

if len(svg_files) < 2:
    print("❌ Need at least 2 SVG files in 'svgs/' folder.")
    exit(1)

# Generate all unique unordered pairs
pairs = list(combinations(svg_files, 2))
random.seed(42)
random.shuffle(pairs)

# Start session log
with open("votes.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([f"\n--- Session started ---", datetime.now().isoformat()])

# --- Rank architectural criteria ---
criteria = ["Performance", "Reliability", "Maintainability", "Flexibility"]
print("\nPlease rank Performance, Reliability, Maintainability, Flexibility from most to least important, with regards to the application (1 = most important, 4 = least important):")

rankings = {}
for crit in criteria:
    while True:
        try:
            rank = int(input(f"Rank for {crit}: "))
            if 1 <= rank <= 4 and rank not in rankings.values():
                rankings[crit] = rank
                break
            else:
                print("❌ Invalid rank. Use unique numbers between 1 and 4.")
        except ValueError:
            print("❌ Please enter a valid integer.")

# Save criteria rankings to session
with open("votes.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["\n--- Criteria ranking ---"])
    for crit, rank in sorted(rankings.items(), key=lambda x: x[1]):
        writer.writerow([crit, rank])

# Match loop
with open("votes.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["\n--- Matches ---"])
    writer.writerow(["\nCandidate 1, Candidate 2, Winner"])

for i, (svg1, svg2) in enumerate(pairs, 1):
    id1 = svg_files.index(svg1) + 1
    id2 = svg_files.index(svg2) + 1

    print("\n" + "="*50)
    print(f"Match {i} of {len(pairs)}: {id1} vs {id2}")
    print(f"Vote by entering: {id1} or {id2}")
    print("="*50)

    while True:
        vote = input("Your vote: ").strip()
        if vote in {str(id1), str(id2)}:
            with open("votes.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([svg1.name, svg2.name, vote])
            print(f"✔️ Saved vote for {vote}")
            break
        else:
            print("❌ Invalid input. Please enter one of the two numbers.")

# End session log
with open("votes.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([f"--- Session ended ---", datetime.now().isoformat()])

print("\n✅ All matches completed.")
