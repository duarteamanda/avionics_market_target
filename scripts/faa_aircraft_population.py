import os
import pandas as pd
import pycountry
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

# Load and read as CSV the FAA Master file
processed_dir = "data/processed/faa"
os.makedirs(processed_dir, exist_ok=True)

faa_raw_path = "data/raw/faa/MASTER.txt"
master_csv = f"{processed_dir}/master.csv"

shapes_country = "data/shapes/countries"
shapes_states = "data/shapes/states_provinces/cb_2018_us_state_5m.shp"

df_original = pd.read_csv(faa_raw_path, dtype=str)
df = df_original.copy()
print(f"Total records in raw file: {len(df)}")

## Clean and standardise
# Remove Type Aircraft 7 (weight-shift-control) and 8 (powered parachute)
df = df[~df['TYPE AIRCRAFT'].isin(['7', '8'])]
print(f"Total records after dropping 7 & 8 as Type Aircraft: {len(df)}")

# Remove data with no address information
address_cols = ['COUNTRY', 'STATE', 'CITY', 'STREET', 'STREET2', 'ZIP CODE']

for col in address_cols:
    df[col] = df[col].str.strip()
    df[col] = df[col].replace([r'^\s*$', r'(?i)^<unset>$', r'(?i)^NULL$'], pd.NA, regex=True)

df = df.dropna(subset=address_cols, how='all')
print(f"Total records after dropping rows with no address: {len(df)}")

missing_country = df[df['COUNTRY'].isna()]
print(f"Total records with empty COUNTRY: {len(missing_country)}")

# Check any aircraft duplicated
unique_numbers = df['N-NUMBER'].nunique()
print(f"Unique N-NUMBERs: {unique_numbers}")

# Save the cleaned CSV
df.to_csv(master_csv, index=False, na_rep='NA')
print(f"Cleaned CSV saved: {master_csv}")

df = pd.read_csv(master_csv, dtype=str)

## World Map Aircraft Population ##
# Check invalid codes for COUNTRY
valid_iso2 = [c.alpha_2 for c in pycountry.countries]
invalid_codes_before = df[~df['COUNTRY'].isin(valid_iso2)]['COUNTRY'].unique()
print(f"Invalid COUNTRY codes before mapping: {invalid_codes_before}")

# Treat invalid codes
manual_iso_map = {'AN': 'ANT', 'RQ': 'PRI'}

def iso2_to_iso3(code):
    if code in manual_iso_map:
        return manual_iso_map[code]
    if code in valid_iso2:
        return pycountry.countries.get(alpha_2=code).alpha_3
    return None

country_counts = df.groupby('COUNTRY').size().reset_index(name='aircraft_count')
country_counts['iso3'] = country_counts['COUNTRY'].apply(iso2_to_iso3)

invalid_codes_after = country_counts[country_counts['iso3'].isna()]['COUNTRY'].unique()
print(f"Invalid COUNTRY codes after manual mapping: {invalid_codes_after}")

country_counts = country_counts.dropna(subset=['iso3'])

# Load world shapefile
shp_files = [f for f in os.listdir(shapes_country) if f.endswith(".shp")]
if not shp_files:
    raise ValueError(f"No shapefiles found in {shapes_country}")
shapefile_path = os.path.join(shapes_country, shp_files[0])
world = gpd.read_file(shapefile_path)

shapefile_iso_col = 'ISO_A3' if 'ISO_A3' in world.columns else world.columns[0]

world = world.merge(country_counts, how='left', left_on=shapefile_iso_col, right_on='iso3')
world['aircraft_count'] = world['aircraft_count'].fillna(0)

# Continuous colormap
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

## US States + Alaska and Hawaii ##
df = pd.read_csv(master_csv, dtype=str)
states = gpd.read_file(shapes_states)

# Count territories and AK + HI
ak_count = int(df[df['STATE'] == 'AK'].shape[0])
hi_count = int(df[df['STATE'] == 'HI'].shape[0])
print(f"Total records for Alaska: {ak_count}")
print(f"Total records Hawaii: {hi_count}")

# Filter and Count US
df_us = df[df['COUNTRY'].isin(['US'])]
state_counts = df_us['STATE'].value_counts().reset_index()
state_counts.columns = ['STUSPS', 'count']

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

# Annotate states
for idx, row in df_plot.iterrows():
    plt.annotate(
        text=row['STUSPS'],
        xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
        ha='center', va='center', fontsize=8
    )

fig.text(
    0.5, 0.1,
    f'Alaska: {ak_count} and Hawaii: {hi_count}. Territories not included in map. '
    'Counts include only aircraft registered with the U.S. FAA.',
    ha='center',
    fontsize=10
)

ax.legend(
    handles=legend_handles,
    title='Aircraft Count',
    loc='lower right',
    frameon=True
)

ax.axis('off')
plt.show()