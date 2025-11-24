import pandas as pd
import os
import re

# Paths
aea_path = "data/processed/aea/AEA_RepairList2025-2026.csv"
faa_path = "data/processed/faa/FAA_Repair_Station.csv"
output_path = "data/processed/dealer_opportunities.csv"

os.makedirs("data/processed", exist_ok=True)

# Read CSVs
aea = pd.read_csv(aea_path, dtype=str)
faa = pd.read_csv(faa_path, dtype=str)

# Required columns
required_aea_cols = ["company", "city/suburb", "address"]
required_faa_cols = ["Agency Name", "City", "Address Line 1"]

for col in required_aea_cols:
    if col not in aea.columns:
        raise ValueError(f"Missing column in AEA file: {col}")

for col in required_faa_cols:
    if col not in faa.columns:
        raise ValueError(f"Missing column in FAA file: {col}")

# Cleaning function: remove LLC, LIMITED, CORP, LTDA, & , - , . , , and normalize spaces
def clean_text_for_merge(text):
    if pd.isna(text):
        return ""
    text = text.lower().strip()
    # Remove LLC, LIMITED, CORP, LTDA at the end
    text = re.sub(r'\b(llc|limited|corp|ltda)\b$', '', text, flags=re.IGNORECASE)
    # Remove & - . ,
    text = re.sub(r'[&\-\.,]', '', text)
    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Merge by cleaned name + cleaned city
merged = pd.merge(
    faa,
    aea,
    left_on=[faa["Agency Name"].map(clean_text_for_merge), faa["City"].map(clean_text_for_merge)],
    right_on=[aea["company"].map(clean_text_for_merge), aea["city/suburb"].map(clean_text_for_merge)],
    how="left",
    indicator=True
)

# MATCH_BY_CITY = name + city
merged["MATCH_BY_CITY"] = merged["_merge"].apply(lambda x: "YES" if x == "both" else "NO")

# Dictionary for company -> address from AEA
aea_address_dict = {clean_text_for_merge(r["company"]): clean_text_for_merge(r["address"]) for _, r in aea.iterrows()}

# MATCH_BY_ADDRESS = name matches + address matches (when city doesn't)
merged["MATCH_BY_ADDRESS"] = ""
no_city_match_idx = merged[merged["MATCH_BY_CITY"] == "NO"].index
for idx in no_city_match_idx:
    row = merged.loc[idx]
    company_key = clean_text_for_merge(row["Agency Name"])
    faa_address = clean_text_for_merge(row["Address Line 1"])
    aea_address = aea_address_dict.get(company_key, "")
    if company_key in aea_address_dict and faa_address == aea_address:
        merged.at[idx, "MATCH_BY_ADDRESS"] = "YES"

# MATCH_BY_NAME_ONLY = name matches, but neither city nor address match
merged["MATCH_BY_NAME_ONLY"] = ""
for idx in no_city_match_idx:
    row = merged.loc[idx]
    company_key = clean_text_for_merge(row["Agency Name"])
    faa_address = clean_text_for_merge(row["Address Line 1"])
    aea_address = aea_address_dict.get(company_key, "")
    city_match = clean_text_for_merge(row["City"]) == clean_text_for_merge(row["city/suburb"]) if pd.notna(row["city/suburb"]) else False
    address_match = faa_address == aea_address
    if company_key in aea_address_dict and not city_match and not address_match:
        merged.at[idx, "MATCH_BY_NAME_ONLY"] = "YES"

# Save final CSV
final = merged[["Agency Name", "City", "Address Line 1", "MATCH_BY_CITY", "MATCH_BY_ADDRESS", "MATCH_BY_NAME_ONLY"]]
final.to_csv(output_path, index=False)
print(f"File saved as: {output_path}")

# Counts
total_city = (merged["MATCH_BY_CITY"] == "YES").sum()
total_address = (merged["MATCH_BY_ADDRESS"] == "YES").sum()
total_name_only = (merged["MATCH_BY_NAME_ONLY"] == "YES").sum()
total_overall_matches = total_city + total_address + total_name_only
total_no_match = len(faa) - total_overall_matches
total_aea = len(aea)
total_faa = len(faa)

# Summary
print(f"Total companies in AEA: {total_aea}")
print(f"Total companies in FAA: {total_faa}")

print(f"Total matching name + city or suburb: {total_city}")
print(f"Total matching name + address : {total_address}")
print(f"Total matching name only: {total_name_only}")
print(f"Total matches overall: {total_overall_matches}")
print(f"Total NO MATCH: {total_no_match}")

