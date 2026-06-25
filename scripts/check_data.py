import json
d = json.load(open("frontend/public/data/consumption.json", encoding="utf-8"))
print(f"Total: {len(d)}")

atc = [r for r in d if r.get("sector") == "Recetas SNS ATC"]
hosp = [r for r in d if r.get("sector") == "Hospitalario"]

print(f"\n=== ATC Records ({len(atc)}) ===")
dhds = [r["dhd"] for r in atc if r.get("dhd") is not None]
packs = [r["packages"] for r in atc if r.get("packages") is not None]
with_atc = [r for r in atc if r.get("atc_code")]
with_drug = [r for r in atc if r.get("drug_name")]
print(f"DHD values: {len(dhds)}, min={min(dhds):.2f}, max={max(dhds):.2f}, avg={sum(dhds)/len(dhds):.2f}")
print(f"Packages: {len(packs)}")
print(f"Has ATC code: {len(with_atc)}, Has drug_name: {len(with_drug)}")

print("\nATC samples:")
for r in atc[:8]:
    print(f"  y={r['year']} m={r.get('month')} atc={str(r.get('atc_code',''))[:12]} drug={str(r.get('drug_name',''))[:30]} dhd={r.get('dhd')} packages={r.get('packages')}")

# Check for bad drug names
bad_names = [r for r in atc if str(r.get("drug_name","")).upper().strip() in ["CODIGO", "CÓDIGO", "GRUPO ATC1", "TOTAL", "SUBTOTAL"]]
print(f"\nBad drug names: {len(bad_names)}")

# Year distribution
yrs = {}
for r in d:
    yr = r.get("year", 0)
    yrs[yr] = yrs.get(yr, 0) + 1
print(f"\nYear distribution:")
for y, c in sorted(yrs.items()):
    print(f"  {y}: {c}")

# Hospital samples
print(f"\n=== Hospital Records ({len(hosp)}) ===")
hpacks = [r["packages"] for r in hosp if r.get("packages") is not None]
hdhds = [r["dhd"] for r in hosp if r.get("dhd") is not None]
print(f"Packages: {len(hpacks)}, DHD: {len(hdhds)}")
for r in hosp[:5]:
    print(f"  y={r['year']} m={r.get('month')} geo={r.get('geography')} packs={r.get('packages')} dhd={r.get('dhd')}")
