import json, shutil
from pathlib import Path

out = Path("frontend/public/data")
all_data = []

spain = json.load(open(out / "consumption.json", encoding="utf-8"))
all_data.extend(spain)
print(f"Spain: {len(spain)}")

for f in sorted(out.glob("consumption_*.json")):
    data = json.load(open(f, encoding="utf-8"))
    all_data.extend(data)
    print(f"  {f.name}: {len(data)}")

merged_path = out / "consumption.json"
json.dump(all_data, open(merged_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
print(f"\nMerged: {len(all_data)} records, {merged_path.stat().st_size:,}B")

shutil.copy(merged_path, Path("data/processed/public/consumption.json"))
print("Copied to processed/public/")

# Check DHD consistency
yr_dhd = {}
for r in all_data:
    yr = r.get("year", 0)
    dhd = r.get("dhd")
    if dhd is None: continue
    if yr not in yr_dhd: yr_dhd[yr] = []
    yr_dhd[yr].append(dhd)

print("\nDHD by year:")
for yr in sorted(yr_dhd.keys()):
    vals = yr_dhd[yr]
    print(f"  {yr}: {len(vals)} records, avg={sum(vals)/len(vals):.2f}, range={min(vals):.1f}-{max(vals):.1f}")

# Check total records by sector
sectors = {}
for r in all_data:
    s = r.get("sector", "?")
    sectors[s] = sectors.get(s, 0) + 1
print(f"\nSectors: {sectors}")
