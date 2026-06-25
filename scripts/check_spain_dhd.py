import json
d = json.load(open("frontend/public/data/consumption.json", encoding="utf-8"))

# Spain DHD
sp = [r for r in d if r.get("geography") == "Spain" and r.get("dhd") is not None]
print(f"Spain with DHD: {len(sp)}")
vals = [r["dhd"] for r in sp]
print(f"DHD: min={min(vals):.1f} max={max(vals):.1f} avg={sum(vals)/len(vals):.1f}")

big = [r for r in sp if r["dhd"] > 100]
print(f"DHD >100: {len(big)}")
if big:
    for r in big[:10]:
        print(f"  BIG: y={r['year']} atc={r.get('atc_code')} dhd={r['dhd']:.0f} ddd={r.get('ddd')} sector={r.get('sector')} geo={r.get('geography')}")

# Check if there's a dedicated Spain record with BIG DHD
huge = [r for r in sp if r["dhd"] > 1000]
print(f"\nDHD >1000: {len(huge)}")
if huge:
    for r in huge[:10]:
        print(f"  HUGE: y={r['year']} atc={r.get('atc_code')} dhd={r['dhd']:.0f} ddd={r.get('ddd')} packages={r.get('packages')} sector={r.get('sector')}")

# Check year distribution for Spain
yrs = {}
for r in sp:
    yr = r["year"]
    yrs[yr] = yrs.get(yr, 0) + 1
print(f"\nSpain years: {dict(sorted(yrs.items()))}")

# Check all sectors
sectors = {}
for r in d:
    s = r.get("sector", "?")
    sectors[s] = sectors.get(s, 0) + 1
print(f"\nSectors: {sectors}")

# Check RECORDS with sector "Hospitalario" that have DHD (shouldn't exist)
hosp_dhd = [r for r in d if r.get("sector") == "Hospitalario" and r.get("dhd") is not None]
print(f"\nHospital with DHD: {len(hosp_dhd)}")

# Check if there's "Extrahospitalario" data 
extra = [r for r in d if r.get("sector") == "Extrahospitalario"]
print(f"Extrahospitalario: {len(extra)}")
if extra:
    for r in extra[:3]:
        print(f"  y={r['year']} geo={r['geography']} dhd={r.get('dhd')} atc={r.get('atc_code')}")
