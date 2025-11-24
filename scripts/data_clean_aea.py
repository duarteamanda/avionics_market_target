import re
import pandas as pd

file_path = "data/processed/aea/AEA_RepairList2025-2026.csv"
df = pd.read_csv(file_path)

#Data cleaning and standardisation
def clean_company(name):
    if pd.isna(name):
        return name
    name = name.strip()
    name = re.sub(r'\bIncorporated\b', 'Inc', name, flags=re.IGNORECASE)
    name = re.sub(r'\bInc\.\b', 'Inc', name, flags=re.IGNORECASE)
    name = name.replace('.', '')
    name = name.replace(',', '')
    name = re.sub(r'\s+', ' ', name)
    return name

df['company'] = df['company'].apply(clean_company)
df.to_csv(file_path, index=False)

print("Cleaning done! File overwritten at:", file_path)
