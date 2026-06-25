import json
from pathlib import Path

p = "data/processed/sanidad_real/latest_normalized.json"
d = json.load(open(p, encoding="utf-8"))

ccaa_data = {}
spain = []
for r in d:
    geo = r.get("geography", "")
    if geo == "Spain":
        spain.append(r)
    elif geo:
        if geo not in ccaa_data:
            ccaa_data[geo] = []
        ccaa_data[geo].append(r)

print(f"Spain: {len(spain)} records")

out = Path("frontend/public/data")
out.mkdir(parents=True, exist_ok=True)

# Save Spain
spain_path = out / "consumption.json"
with open(spain_path, "w", encoding="utf-8") as f:
    json.dump(spain, f, ensure_ascii=False, indent=2, default=str)
print(f"consumption.json: {len(spain)} records, {spain_path.stat().st_size:,}B")

for geo, recs in sorted(ccaa_data.items()):
    fname = f"consumption_{geo.replace(' ', '_')}.json"
    fpath = out / fname
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=2, default=str)
    print(f"  {fname}: {len(recs)} records, {fpath.stat().st_size:,}B")

# Also keep the full file in processed/ for DB rebuild
print(f"\nTotal: {len(spain) + sum(len(v) for v in ccaa_data.values())}")
