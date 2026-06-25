import json
from collections import Counter

d = json.load(open("frontend/public/data/consumption.json", encoding="utf-8"))

# Check what recetas SNS ATC records exist and their years
atc = [r for r in d if r.get("sector") == "Recetas SNS ATC"]
print(f"Recetas SNS ATC: {len(atc)}")
yrs = Counter(r["year"] for r in atc)
print(f"Years: {dict(sorted(yrs.items()))}")

# Check with atc_code
with_code = [r for r in atc if r.get("atc_code")]
print(f"With ATC code: {len(with_code)}")
yrs2 = Counter(r["year"] for r in with_code)
print(f"Years: {dict(sorted(yrs2.items()))}")

# Check Comunitario
com = [r for r in d if r.get("sector") == "Comunitario"]
print(f"\nComunitario: {len(com)}")
yrs3 = Counter(r["year"] for r in com)
print(f"Years: {dict(sorted(yrs3.items()))}")
# Check their geography_type
geo_types = Counter(r.get("geography_type") for r in com)
print(f"Geo types: {dict(geo_types)}")

# Count unique (geography, atc_code) pairs in Recetas SNS ATC
pairs = set()
for r in with_code:
    pairs.add((r["geography"], r["atc_code"]))
print(f"\nUnique (geo, atc) pairs: {len(pairs)}")
for p in sorted(pairs)[:20]:
    print(f"  {p[0]} | {p[1]}")
