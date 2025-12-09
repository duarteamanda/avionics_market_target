import os
import pandas as pd

# Paths
processed_dir = "data/processed"
os.makedirs(processed_dir, exist_ok=True)

raw_path = "data/raw/faa/MASTER.txt"
empty_state_csv = f"{processed_dir}/master_empty_state.csv"

# Load FAA Master and copy
df_original = pd.read_csv(raw_path, dtype=str)
df = df_original.copy()
print(f"Total records in raw file: {len(df)}")

# Standardise and clean address columns
address_cols = ['COUNTRY', 'STATE', 'CITY', 'STREET', 'STREET2', 'ZIP CODE', 'REGION']

for col in address_cols:
    df[col] = df[col].str.strip()
    df[col] = df[col].replace([r'^\s*$', r'(?i)^<unset>$', r'(?i)^NULL$'], pd.NA, regex=True)

# Drop data with no address information
df = df.dropna(subset=address_cols, how='all')
df = df[~df['TYPE AIRCRAFT'].isin(['7', '8'])]
print(f"Total records after dropping rows with no address: {len(df)}")

# Validate N-NUMBER as an unique number
unique_numbers = df['N-NUMBER'].nunique()
print(f"Unique N-NUMBERs: {unique_numbers}")

# Filter all rows with empty STATE
empty_state_all = df[df['STATE'].isna()].copy()
print(f"Total records with empty STATE (all countries): {len(empty_state_all)}")

# Export CSV
cols_to_export = ['N-NUMBER'] + address_cols
empty_state_all[cols_to_export].to_csv(empty_state_csv, index=False, na_rep='NA')
print(f"CSV exported for filling STATE: {empty_state_csv}")

