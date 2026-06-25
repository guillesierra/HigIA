import json
from pathlib import Path

d = json.loads(Path("data/processed/aemps/latest_normalized.json").read_text(encoding="utf-8"))
alerts = [r for r in d if r.get("record_type") == "safety_alert"]
print(f"Total alerts: {len(alerts)}")

for i, r in enumerate(alerts[:15]):
    print(f"\n=== Alert {i+1} ===")
    print(f"Title: {str(r.get('title',''))[:120]}")
    print(f"Date: {r.get('date')}")
    print(f"Ingredients: {r.get('possible_active_ingredients',[])}")
    raw = str(r.get("raw_text", ""))
    summary = str(r.get("summary", ""))
    print(f"Summary: {summary[:200]}")
    # Show first 300 chars of raw text
    print(f"Raw text start: {raw[:300]}")
