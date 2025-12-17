import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

aircraft_data = 'data/processed/faa/master.csv'
dealer_data = 'data/processed/aea/AEA_RepairList2025-2026.csv'
output_file = 'data/processed/us_dealer_opportunities.csv'

aircraft_df = pd.read_csv(aircraft_data)
repair_store_df = pd.read_csv(dealer_data)

shapes_states = "data/shapes/states_provinces/cb_2018_us_state_5m.shp"
states = gpd.read_file(shapes_states)

# US filter
aircraft_df = aircraft_df[aircraft_df['COUNTRY'] == 'US']
repair_store_df = repair_store_df[repair_store_df['country'] == 'United States']

print("Total US aircraft records:", len(aircraft_df))
print("Total US dealer records:", len(repair_store_df))
print("Total empty 'STATE' in FAA Records:", aircraft_df['STATE'].isna().sum())
print("Total empty 'state/territory/regions' in AEA records:", repair_store_df['state/territory/regions'].isna().sum())

repair_store_df.columns = repair_store_df.columns.str.strip()

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

repair_store_df['standard_state'] = repair_store_df['state/territory/regions'].map(standard_state)
missing_states = repair_store_df[repair_store_df['standard_state'].isna()]
print(missing_states[['state/territory/regions']])

# Count repair stores per state
coverage = repair_store_df['standard_state'].value_counts().reset_index()
coverage.columns = ['state', 'repair_store_count']

# Count aircraft per state
faa_counts = aircraft_df['STATE'].value_counts().reset_index()
faa_counts.columns = ['state', 'num_aircraft']

# Combine aircraf and repair stores per state
combined = pd.merge(faa_counts, coverage, on='state', how='left')
combined['repair_store_count'] = combined['repair_store_count'].fillna(0)
combined['dealers_per_aircraft'] = combined['repair_store_count'] / combined['num_aircraft'] * 1000

# Count Ratio
combined_nonzero = combined[combined['repair_store_count'] > 0].copy()

print(combined.sort_values('dealers_per_aircraft', ascending=False))
print(combined_nonzero.sort_values('dealers_per_aircraft', ascending=False))

ak_count = combined.loc[combined['state'] == 'AK', 'dealers_per_aircraft'].values[0] if 'AK' in combined['state'].values else 0
hi_count = combined.loc[combined['state'] == 'HI', 'dealers_per_aircraft'].values[0] if 'HI' in combined['state'].values else 0

# Merge shapefile with dealers per aircraft
df_main = states.merge(combined, left_on='STUSPS', right_on='state', how='left').fillna(0)

total_repair_stores_after = combined['repair_store_count'].sum()
print("Total repair stores after merge:", total_repair_stores_after)

missing_states = repair_store_df[repair_store_df['standard_state'].isna()]
print(missing_states[['state/territory/regions']])
print("Number of stores without mapping:", len(missing_states))

# Continents List
continental_states = [
    'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'ID', 'IL', 'IN',
    'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV',
    'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN',
    'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
]
df_plot = df_main[df_main['STUSPS'].isin(continental_states)].copy()

# Highlight states with less ratio cover (less dealers per aircraft total)
cmap = plt.cm.Reds_r
norm = plt.Normalize(vmin=df_plot['dealers_per_aircraft'].min(), vmax=df_plot['dealers_per_aircraft'].max())
df_plot['color'] = df_plot['dealers_per_aircraft'].apply(lambda x: mcolors.to_hex(cmap(norm(x))))

# Plot
fig, ax = plt.subplots(1, 1, figsize=(17,12))
df_plot.plot(color=df_plot['color'], linewidth=0.8, ax=ax, edgecolor='0.8')

sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm._A = []
cbar = fig.colorbar(sm, ax=ax)
cbar.set_label('Dealers per Aircraft')

for idx, row in df_plot.iterrows():
    plt.annotate(text=row['STUSPS'], xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
                 ha='center', va='center', fontsize=8)

ax.axis('off')
ax.set_title('US States: Dealer Coverage Ratio', fontsize=24)

fig.text(
    0.5, 0.05,
    f'Alaska (AK): {ak_count:.2f}, Hawaii (HI): {hi_count:.2f}. Territories not included in map'
    f'\nValues show number of dealers per 1,000 aircraft based on FAA Repair Store List',
    ha='center',
    fontsize=10,
)

plt.show()

## Create dealer_opportunities CSV
# Make a copy of the repair list
dealer_opportunities = repair_store_df.copy()

# Exclude US territories
exclude_territories = ['PUERTO RICO', 'GUAM', 'U.S. VIRGIN ISLANDS', 'AMERICAN SAMOA', 'NORTHERN MARIANA ISLANDS']
dealer_opportunities = dealer_opportunities[~dealer_opportunities['state/territory/regions'].str.upper().isin(exclude_territories)]

# Merge with the combined state data to get dealers_per_aircraft for each dealer
dealer_opportunities = dealer_opportunities.merge(
    combined[['state', 'dealers_per_aircraft']],
    left_on='standard_state',
    right_on='state',
    how='left'
)

# Fill missing values with 0 (for states without aircraft data)
dealer_opportunities['dealers_per_aircraft'] = dealer_opportunities['dealers_per_aircraft'].fillna(0)

# Define priority levels based on dealers_per_aircraft ratio
def assign_priority(x):
    if x <= 1:
        return 'Very High'
    elif x <= 2:
        return 'High'
    elif x <= 3:
        return 'Medium'
    elif x <= 5:
        return 'Low'
    else:
        return 'Very Low'

dealer_opportunities['priority_level'] = dealer_opportunities['dealers_per_aircraft'].apply(assign_priority)

# Drop unwanted columns
columns_to_keep = [col for col in repair_store_df.columns] + ['priority_level']

# Reorder so priority_level is the first column
cols = ['priority_level'] + [col for col in dealer_opportunities.columns if col != 'priority_level']
dealer_opportunities = dealer_opportunities[cols]

# Drop unwanted columns
dealer_opportunities = dealer_opportunities.drop(columns=[
    'country', 'continent', 'dealers_per_aircraft', 'standard_state', 'state'], errors='ignore')

# Save CSV
dealer_opportunities.to_csv(output_file, index=False)
print(f"CSV created at {output_file}")
print(len(dealer_opportunities))