import pandas as pd
import re
import os

input_path = "data/raw/faa/Repair Station Contacts with Ratings (Download).csv"
output_path = "data/processed/faa/FAA_Repair_Station.csv"

df = pd.read_csv(input_path, dtype=str)

def clean_company(company_name):
    if pd.isna(company_name):
        return company_name

    name = company_name.strip()
    name = re.sub(r'\bIncorporated\b', 'Inc', name, flags=re.IGNORECASE)
    name = re.sub(r'\bInc\.\b', 'Inc', name, flags=re.IGNORECASE)
    name = name.replace('.', '').replace(',', '')
    name = re.sub(r'\s+', ' ', name)
    return name

df["Agency Name"] = df["Agency Name"].apply(clean_company)

df.to_csv(output_path, index=False)
print(f"Cleaned file saved to: {output_path}")

