import pandas as pd

aircraft_data = 'data/processed/faa/master.csv'
dealer_data = 'data/processed/aea/AEA_RepairList2025-2026.csv'

aircraft_df = pd.read_csv(aircraft_data)
repair_store_df = pd.read_csv(dealer_data)

# US filter
aircraft_df = aircraft_df[aircraft_df['COUNTRY'] == 'US']
repair_store_df = repair_store_df[repair_store_df['country'] == 'United States']

aircraft_df.to_csv('data/processed/faa_aircraft_population_us.csv', index=False)
repair_store_df.to_csv('data/processed/aea_repair_store_us.csv', index=False)

# Us states
standard_state = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA",
    "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM",
    "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY"
}

# Standardising
repair_store_df['state/territory/regions'] = (
    repair_store_df['state/territory/regions']
    .str.upper()
    .str.strip()
)

# Aplicar padronização
repair_store_df['standard_state'] = repair_store_df['state/territory/regions'].map(standard_state)

# Contar repair stores por estado
coverage = repair_store_df['standard_state'].value_counts().reset_index()
coverage.columns = ['state', 'repair_store_count']

# Contar aeronaves por estado (AJUSTE O NOME DA COLUNA SE NECESSÁRIO)
faa_counts = aircraft_df['STATE'].value_counts().reset_index()
faa_counts.columns = ['state', 'num_aircraft']

# Juntar
combined = pd.merge(faa_counts, coverage, on='state', how='left')

# Evitar NaN
combined['repair_store_count'] = combined['repair_store_count'].fillna(0)

# Calcular proporção
combined['dealers_per_aircraft'] = (
    combined['repair_store_count'] / combined['num_aircraft']
)

print(combined.sort_values('dealers_per_aircraft', ascending=False))

