import pandas as pd
from pathlib import Path

files = list(Path("data/raw/atc_xlsx").glob("*.xlsx"))
print(f"Files found: {len(files)}")

if not files:
    print("No files found!")
    exit()

f = files[0]
print(f"\n=== {f.name} ===")

# Read without headers to see raw structure
df = pd.read_excel(str(f), header=None)
print(f"Shape: {df.shape}")
print(f"\nAll rows (first 20):")
for i in range(min(20, len(df))):
    row = [str(v)[:40] for v in df.iloc[i].values if str(v) != "nan"]
    print(f"  {i}: {row}")

# Read second file too
f2 = files[50] if len(files) > 50 else files[-1]
print(f"\n=== {f2.name} ===")
df2 = pd.read_excel(str(f2), header=None)
print(f"Shape: {df2.shape}")
for i in range(min(15, len(df2))):
    row = [str(v)[:40] for v in df2.iloc[i].values if str(v) != "nan"]
    print(f"  {i}: {row}")
