import pandas as pd
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import pycountry
import matplotlib.patches as mpatches

raw_path = "data/raw/faa/MASTER.txt"
processed_dir = "data/processed"
output_file = f"{processed_dir}/faa_master.csv"
shapes_country = "data/shapes/countries"
shapes_states = "data/shapes/states_provinces"

os.makedirs(processed_dir, exist_ok=True)
master = pd.read_csv(raw_path, dtype=str)
master.to_csv(output_file, index=False)
print(f"Total records: {len(master)}")

df = pd.read_csv(output_file, dtype=str)

# Standardisation
str_cols = df.select_dtypes(include='object').columns
df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())
df.replace('', pd.NA, inplace=True)

print(f"Records missing COUNTRY: {df['COUNTRY'].isna().sum()}")
print(f"Records missing STATE: {df['STATE'].isna().sum()}")
print(f"Records missing CITY: {df['CITY'].isna().sum()}")
print(f"Records missing TYPE AIRCRAFT: {df['TYPE AIRCRAFT'].isna().sum()}")
print(f"Records missing ZIPCODE: {df['ZIP CODE'].isna().sum()}")

missing_rows_count = df[df[['COUNTRY','CITY','STATE','STREET','STREET2', 'ZIP CODE']].isna().all(axis=1)].shape[0]
print(f"Rows missing COUNTRY, CITY, STATE, STREET, STREET2, AND ZIP CODE: {missing_rows_count}")

# Drop rows missing all key fields
df = df.dropna(subset=['COUNTRY','CITY','STATE','STREET','STREET2', 'ZIP CODE'], how='all')
df.to_csv(output_file, index=False, na_rep='NA')
print(f"Total records after dropping empty location: {len(df)}")

is_unique = df['N-NUMBER'].is_unique
print(f"All N-NUMBER values unique? {is_unique}")

# Drop 7 and 8 values as type aircraft
df.drop(df[df['TYPE AIRCRAFT'].isin(['7', '8'])].index, inplace=True)
print(f"Records after dropping Weight-shift-control and Powered Parachute from Type Aircraft: {len(df)}")

us_df = df[df['COUNTRY'] == 'US'].copy()
missing_states = us_df['STATE'].isna().sum()
print(f'Missing States: {missing_states}')

# Aircraft counts by country
country_counts = df.groupby('COUNTRY').size().reset_index(name='aircraft_count')

# Manual ISO mapping for FAA-specific codes
manual_iso_map = {
    'AN': 'ANT',  # Netherlands Antilles
    'RQ': 'PRI',  # Puerto Rico
}

def iso2_to_iso3_fixed(code):
    if code in manual_iso_map:
        return manual_iso_map[code]
    try:
        return pycountry.countries.get(alpha_2=code).alpha_3
    except:
        return None

country_counts['iso3'] = country_counts['COUNTRY'].apply(iso2_to_iso3_fixed)

missing_iso = country_counts[country_counts['iso3'].isna()]
if not missing_iso.empty:
    print("Warning: Some countries could not be converted to ISO3 codes")
    print(missing_iso)

# Load shapefile
shp_files = [f for f in os.listdir(shapes_country) if f.endswith(".shp")]
if not shp_files:
    raise ValueError(f"No shapefiles found in {shapes_country}")

shapefile_path = os.path.join(shapes_country, shp_files[0])
world = gpd.read_file(shapefile_path)

# Merge aircraft counts into shapefile GeoDataFrame
shapefile_iso_col = 'ISO_A3' if 'ISO_A3' in world.columns else world.columns[0]
world = world.merge(country_counts, how='left', left_on=shapefile_iso_col, right_on='iso3')
world['aircraft_count'] = world['aircraft_count'].fillna(0)

#Define range
bins = [1, 50, 1000, world['aircraft_count'].max()+1]
labels = [1, 2, 3]

world['category'] = pd.cut(world['aircraft_count'], bins=bins, labels=labels, include_lowest=True)

color_map = {1: '#dbe9f7', 2: '#4292c6', 3: '#08306b'}
world['color'] = world['category'].map(color_map)

world['color'] = world['color'].astype(str).replace('nan', '#ffffff')

# Plot
fig, ax = plt.subplots(1, 1, figsize=(15, 8))
world.plot(color=world['color'], ax=ax, edgecolor='black')

legend_handles = [
    mpatches.Patch(color='#dbe9f7', label=f'{int(bins[0])}-{int(bins[1])}'),
    mpatches.Patch(color='#4292c6', label=f'{int(bins[1])+1}-{int(bins[2])}'),
    mpatches.Patch(color='#08306b', label=f'>{int(bins[2])}')
]

ax.legend(handles=legend_handles, title='Aircraft Count', loc='lower right', bbox_to_anchor=(1.05, 0.5))
ax.set_title('FAA - World Registered Aircraft', fontsize=16)
plt.subplots_adjust(bottom=0.01)
fig.text(0.5, 0.03,
         'Counts include only aircraft registered with the U.S. FAA. Source Last updated: Tuesday, May 13, 2025.',
         ha='center',
         fontsize=10)
ax.axis('off')
plt.show()
#------------------------------------------------------------------------------------------------------------------------------------------------------------
#Get Aircraft count per US states
# Count US aircraft by state
us_counts = df[df['COUNTRY'] == 'US'].groupby('STATE').size().reset_index(name='aircraft_count')
print("Missing US state entries:", df[(df['COUNTRY']=='US') & (df['STATE'].isna())].shape[0])

unique_states = df['STATE'].dropna().unique()
print(sorted(unique_states))

state_counts = df['STATE'].value_counts()
print(state_counts)

# Find missing or empty states
missing_states = df[df['STATE'].isna()]
print(f"Missing STATE records: {len(missing_states)}")

# Find codes that aren’t 2-letter US abbreviations
invalid_states = df[~df['STATE'].isin(states['STUSPS'])]
print(invalid_states['STATE'].unique())

# Load Natural Earth global states/provinces
# states_shp = [f for f in os.listdir(shapes_states) if f.endswith(".shp")][0]
# states_gdf = gpd.read_file(os.path.join(shapes_states, states_shp))
#
# # ---- FILTER TO UNITED STATES ONLY ----
# if "iso_a2" in states_gdf.columns:
#     states_gdf = states_gdf[states_gdf["iso_a2"] == "US"]
# elif "iso_a3" in states_gdf.columns:
#     states_gdf = states_gdf[states_gdf["iso_a3"] == "USA"]
# elif "admin" in states_gdf.columns:
#     states_gdf = states_gdf[states_gdf["admin"] == "United States of America"]
# else:
#     print(states_gdf.columns)
#     raise ValueError("Cannot find usable country column in states shapefile.")
#
# # Identify correct state abbreviation column
# if "postal" in states_gdf.columns:
#     state_col = "postal"
# elif "stusps" in states_gdf.columns:
#     state_col = "stusps"
# else:
#     print(states_gdf.columns)
#     raise ValueError("Cannot find US state abbreviation field in shapefile.")
#
# # Merge FAA state counts
# states_gdf = states_gdf.merge(us_counts, how="left", left_on=state_col, right_on="STATE")
# states_gdf['aircraft_count'] = states_gdf['aircraft_count'].fillna(0)
#
# # Plot US state choropleth
# fig, ax = plt.subplots(1, 1, figsize=(15, 8))
# states_gdf.plot(column='aircraft_count', cmap='Blues', edgecolor='black', legend=True, ax=ax)
#
# ax.set_title('FAA - Aircraft Registered by U.S. State', fontsize=16)
# ax.axis('off')
# plt.show()
#
# states = gpd.read_file(
#     "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_state_5m.zip"
# )
#
# # Drop territories (PR, GU, VI etc)
# states = states[~states['STUSPS'].isin(['PR', 'GU', 'VI', 'AS', 'MP'])]
#
# states.plot()
