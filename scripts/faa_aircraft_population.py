import os
import pandas as pd
import pycountry
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

# Create processed directories
processed_dir_faa = "data/processed/faa"
processed_dir_aea = "data/processed/aea"
os.makedirs(processed_dir_faa, exist_ok=True)
os.makedirs(processed_dir_aea, exist_ok=True)

# Paths
faa_raw_path = "data/raw/faa/MASTER.txt"
faa_clean_csv = f"{processed_dir_faa}/master.csv"

aea_raw_path = "data/processed/aea/AEA_RepairList2025-2026.csv"

# Shapefiles
shapes_country = "data/shapes/countries"
shapes_states = "data/shapes/states_provinces/cb_2018_us_state_5m.shp"

# Load FAA master raw data
df_faa = pd.read_csv(faa_raw_path, dtype=str)
print(f"FAA Total Aircraft Population: {len(df_faa)}")

df_aea = pd.read_csv(aea_raw_path, dtype=str)
print(f"AEA Total Repair Station: {len(df_aea)}")

## Clean, standardise, and save FAA aircraft population data
df_faa_clean = df_faa.copy()

# Remove Type Aircraft 7 (weight-shift-control) and 8 (powered parachute)
df_faa_clean = df_faa_clean[~df_faa_clean['TYPE AIRCRAFT'].isin(['7', '8'])]
print(f"Total Aircraft Population after dropping 7 & 8 as Type Aircraft: {len(df_faa_clean)}")

# Clean address columns
address_cols = ['COUNTRY', 'STATE', 'CITY', 'STREET', 'STREET2', 'ZIP CODE']
for col in address_cols:
    df_faa_clean[col] = df_faa_clean[col].str.strip()
    df_faa_clean[col] = df_faa_clean[col].replace([r'^\s*$', r'(?i)^<unset>$', r'(?i)^NULL$'], pd.NA, regex=True)

# Drop rows with no address info
df_faa_clean = df_faa_clean.dropna(subset=address_cols, how='all')
print(f"Total Aircraft Population after dropping rows with no address: {len(df_faa_clean)}")

# Check missing COUNTRY
missing_country = df_faa_clean[df_faa_clean['COUNTRY'].isna()]
print(f"Total Aircraft Population with empty COUNTRY: {len(missing_country)}")

# Check duplicate N-NUMBERs
unique_numbers = df_faa_clean['N-NUMBER'].nunique()
print(f"Aircraft Unique N-NUMBERs: {unique_numbers}")

# Save cleaned CSV
df_faa_clean.to_csv(faa_clean_csv, index=False, na_rep='NA')
print(f"Cleaned Aircraft Population CSV saved: {faa_clean_csv}")

# Reload cleaned dataset
df_faa_clean = pd.read_csv(faa_clean_csv, dtype=str)
print(f"FAA Total Aircraft Population: {len(df_faa_clean)}")

## World Map Aircraft Population ##
# Check invalid codes for COUNTRY
valid_iso2 = [c.alpha_2 for c in pycountry.countries]
invalid_codes_before = df_faa_clean[~df_faa_clean['COUNTRY'].isin(valid_iso2)]['COUNTRY'].unique()
print(f"Invalid COUNTRY codes before mapping: {invalid_codes_before}")

# Treat invalid codes
manual_iso_map = {'AN': 'ANT', 'RQ': 'PRI'}

def iso2_to_iso3(code):
    if code in manual_iso_map:
        return manual_iso_map[code]
    if code in valid_iso2:
        return pycountry.countries.get(alpha_2=code).alpha_3
    return None

country_counts = df_faa_clean.groupby('COUNTRY').size().reset_index(name='aircraft_count')
country_counts['iso3'] = country_counts['COUNTRY'].apply(iso2_to_iso3)
country_counts['aircraft_count'].sum()

invalid_codes_after = country_counts[country_counts['iso3'].isna()]['COUNTRY'].unique()
print(f"Invalid COUNTRY codes after mapping: {invalid_codes_after}")

country_counts = country_counts.dropna(subset=['iso3'])

# Load world shapefile
shp_files = [f for f in os.listdir(shapes_country) if f.endswith(".shp")]
if not shp_files:
    raise ValueError(f"No shapefiles found in {shapes_country}")
shapefile_path = os.path.join(shapes_country, shp_files[0])
world = gpd.read_file(shapefile_path)

shapefile_iso_col = 'ISO_A3' if 'ISO_A3' in world.columns else world.columns[0]

# Merge and fill missing
world = world.merge(country_counts, how='left', left_on=shapefile_iso_col, right_on='iso3')
world['aircraft_count'] = world['aircraft_count'].fillna(0)

# Colormap
cmap = plt.colormaps['Oranges']
norm = mcolors.Normalize(vmin=world['aircraft_count'].min(), vmax=world['aircraft_count'].max())
world['color'] = world['aircraft_count'].apply(
    lambda x: '#ffffff' if x == 0 else mcolors.to_hex(cmap(norm(x)))
)

# Plot FAA - World Registered Aircraft Map
fig, ax = plt.subplots(1, 1, figsize=(15, 8))
world.plot(color=world['color'], ax=ax, edgecolor='black')

sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.05)
cbar.set_label('Number of registered aircraft', fontsize=12)
ax.set_title('FAA - World Registered Aircraft Population', ha='center', fontsize=24)
fig.text(0.5, 0.09,
         'Counts include only aircraft registered with the U.S. FAA. Source updated: Tuesday, May 13, 2025.',
         ha='center', fontsize=10)
ax.axis('off')
plt.show()

total_mapped_aircraft = country_counts['aircraft_count'].sum()
print(f"Total aircraft represented on map: {total_mapped_aircraft}")
print(f"Total aircraft in original dataset: {len(df_faa_clean)}")

## World AEA Repair Store Map##
df_aea['country'] = df_aea['country'].str.strip()

# Map country names to ISO3
def country_name_to_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None

manual_country_map = {'Dubai': 'United Arab Emirates'}
df_aea['country'] = df_aea['country'].replace(manual_country_map)
df_aea['iso3'] = df_aea['country'].apply(country_name_to_iso3)

# Count repair stations per country
repair_counts = df_aea.dropna(subset=['iso3']).groupby('iso3').size().reset_index(name='repair_station_count')

# Merge with world shapefile
world_aea = world.merge(repair_counts, how='left', left_on=shapefile_iso_col, right_on='iso3')
world_aea['repair_station_count'] = world_aea['repair_station_count'].fillna(0)

# Colormap
cmap = plt.colormaps['Reds']
norm = mcolors.Normalize(vmin=world_aea['repair_station_count'].min(), vmax=world_aea['repair_station_count'].max())
world_aea['color'] = world_aea['repair_station_count'].apply(
    lambda x: '#ffffff' if x == 0 else mcolors.to_hex(cmap(norm(x)))
)

# Plot AEA Repair Stations map
fig, ax = plt.subplots(1, 1, figsize=(15, 8))
world_aea.plot(color=world_aea['color'], ax=ax, edgecolor='black')

sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.05)
cbar.set_label('Number of repair stations', fontsize=12)
ax.set_title('AEA Repair Station Distribution Worldwide', ha='center', fontsize=24)
fig.text(0.5, 0.09,
         'Counts include only approved maintenance organisations with AEA. Source updated: 2025-2026.',
         ha='center', fontsize=10)
ax.axis('off')
plt.show()

# Sum of all mapped countries
total_mapped_stations = repair_counts['repair_station_count'].sum()
print(f"Total repair stations represented on map: {total_mapped_stations}")
print(f"Total repair stations in original dataset: {len(df_aea)}")

missing_aea = df_aea[~df_aea['country'].apply(lambda x: country_name_to_iso3(x) is not None)]
# print(missing_aea)

## US States + Alaska and Hawaii ##
df = pd.read_csv(master_csv, dtype=str)
states = gpd.read_file(shapes_states)

# Filter and Count US
df_us = df[df['COUNTRY'].isin(['US'])]
state_counts = df_us['STATE'].value_counts().reset_index()
state_counts.columns = ['STUSPS', 'count']
print(f"Total US records: {len(df_us)}")

# Count Alaska and Hawaii
ak_count = int(df[df['STATE'] == 'AK'].shape[0])
hi_count = int(df[df['STATE'] == 'HI'].shape[0])
print(f"Total records for Alaska: {ak_count}")
print(f"Total records Hawaii: {hi_count}")

# Shapefile merging
df_main = states.merge(state_counts, on='STUSPS', how='left').fillna(0)

continental_states = [
    'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'ID', 'IL', 'IN',
    'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV',
    'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN',
    'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
]
df_plot = df_main[df_main['STUSPS'].isin(continental_states)].copy()

# Define bins and colours
max_count = int(df_plot['count'].max())
bins = [0, 500, 1000, 2000, 5000, 10000, 20000, max_count + 1]
labels = range(1, len(bins))

df_plot['category'] = pd.cut(df_plot['count'], bins=bins, labels=labels, include_lowest=True)

cmap = plt.cm.Oranges
df_plot['color'] = df_plot['category'].apply(
    lambda x: '#ffffff' if pd.isna(x) else mcolors.to_hex(cmap((int(x) - 1) / (len(labels) - 1)))
)

legend_handles = []
for i in range(1, len(bins)):
    color = mcolors.to_hex(cmap((i - 1) / (len(labels) - 1)))
    label = f"{int(bins[i - 1]) + 1:,} - {int(bins[i]) - 1:,}"
    legend_handles.append(mpatches.Patch(color=color, label=label))

# Plot US Aircraft Population
fig, ax = plt.subplots(1, 1, figsize=(17, 12))
ax.set_title('US Registered Aircraft Population', fontsize=24)
df_plot.plot(color=df_plot['color'], linewidth=0.8, ax=ax, edgecolor='0.8', legend=False)

for idx, row in df_plot.iterrows():
    plt.annotate(
        text=row['STUSPS'],
        xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
        ha='center', va='center', fontsize=8
    )

fig.text(0.5, 0.1,
    f'Alaska: {ak_count} and Hawaii: {hi_count}. Territories not '
    f'included in map.\nCounts include only aircraft registered with the U.S. FAA.',
    ha='center',
    fontsize=10
)
ax.legend(handles=legend_handles, title='Aircraft Count', loc='lower right', frameon=True)
ax.axis('off')
# plt.show()

##PLOT FOR AEA Repair Store List
# Make a copy to be safe
df_aea_clean = df_aea.copy()

# Strip country names
df_aea_clean['Country'] = df_aea_clean['Country'].str.strip()

# Optional: drop rows with empty country
df_aea_clean = df_aea_clean[df_aea_clean['Country'].notna() & (df_aea_clean['Country'] != '')]

# Convert country names to ISO3 codes
def country_name_to_iso3(name):
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None

df_aea_clean['iso3'] = df_aea_clean['Country'].apply(country_name_to_iso3)

# Check unmatched names
unmatched = df_aea_clean[df_aea_clean['iso3'].isna()]['Country'].unique()
print(f"Unmatched country names: {unmatched}")

# Count number of repair stations per country
country_counts_aea = (
    df_aea_clean
    .dropna(subset=['iso3'])
    .groupby('iso3')
    .size()
    .reset_index(name='repair_station_count')
)

# Load world shapefile
shp_files = [f for f in os.listdir(shapes_country) if f.endswith(".shp")]
if not shp_files:
    raise ValueError(f"No shapefiles found in {shapes_country}")
shapefile_path = os.path.join(shapes_country, shp_files[0])
world = gpd.read_file(shapefile_path)

shapefile_iso_col = 'ISO_A3' if 'ISO_A3' in world.columns else world.columns[0]

# Merge repair station counts into shapefile
world_aea = world.merge(country_counts_aea, how='left', left_on=shapefile_iso_col, right_on='iso3')
world_aea['repair_station_count'] = world_aea['repair_station_count'].fillna(0)

# Colormap
cmap = plt.colormaps['Blues']  # optional, different from FAA map
norm = mcolors.Normalize(vmin=world_aea['repair_station_count'].min(),
                         vmax=world_aea['repair_station_count'].max())

world_aea['color'] = world_aea['repair_station_count'].apply(
    lambda x: '#ffffff' if x == 0 else mcolors.to_hex(cmap(norm(x)))
)

# Plot AEA World Repair Stations Map
fig, ax = plt.subplots(1, 1, figsize=(15, 8))
world_aea.plot(color=world_aea['color'], ax=ax, edgecolor='black')

sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.05)
cbar.set_label('Number of AEA Repair Stations', fontsize=12)

ax.set_title('AEA - World Repair Station Distribution', ha='center', fontsize=24)
fig.text(0.5, 0.09,
         'Counts include only repair stations from the AEA 2025-2026 list.',
         ha='center', fontsize=10)
ax.axis('off')
plt.show()