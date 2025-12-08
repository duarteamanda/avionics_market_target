import os
import pandas as pd

# Paths
processed_dir = "data/processed"
os.makedirs(processed_dir, exist_ok=True)

raw_path = "data/raw/faa/MASTER.txt"
empty_state_csv = f"{processed_dir}/master_empty_state.csv"

# Load FAA Master
df = pd.read_csv(raw_path, dtype=str)

# Cleaning address columns
address_cols = ['COUNTRY', 'STATE', 'CITY', 'STREET', 'STREET2', 'ZIP CODE']
for col in address_cols:
    df[col] = df[col].str.strip()
    df[col] = df[col].replace([r'^\s*$', r'(?i)^<unset>$', r'(?i)^NULL$'], pd.NA, regex=True)

df = df.dropna(subset=address_cols, how='all')

# Filter all rows with empty STATE
empty_state_all = df[df['STATE'].isna()].copy()
print(f"Total records with empty STATE (all countries): {len(empty_state_all)}")

# Export CSV
empty_state_all.to_csv(empty_state_csv, index=False, na_rep='NA')
print(f"CSV exported for filling STATE: {empty_state_csv}")