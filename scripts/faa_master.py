from email.contentmanager import get_and_fixup_unknown_message_content

import pandas as pd
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import pycountry
import matplotlib.patches as mpatches
faa_csv = "data/processed/faa_master.csv"

raw_path = "data/raw/faa/MASTER.txt"
processed_dir = "data/processed"
output_file = f"{processed_dir}/faa_master.csv"
shapes_country = "data/shapes/countries"
shapes_states = "data/shapes/states_provinces/cb_2018_us_state_5m.shp"
states = gpd.read_file(shapes_states)

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
         'Counts include only aircraft registered with the U.S. FAA. Source updated: Tuesday, May 13, 2025.',
         ha='center',
         fontsize=10)
ax.axis('off')
plt.show()
#------------------------------------------------------------------------------------------------------------------------------------------------------------
#Get Aircraft count per US states
# Count US aircraft by state
df_us = pd.read_csv(faa_csv, dtype=str)
df_us = df_us[df_us['COUNTRY'] == 'US']

# Padronizar a coluna STATE
df_us['STATE'] = df_us['STATE'].str.strip().str.upper()

# Contagem por estado
state_counts = df_us['STATE'].value_counts().reset_index()
state_counts.columns = ['STUSPS', 'count']

# Merge com shapefile (apenas estados existentes)
df_main = states.merge(state_counts, on='STUSPS', how='left')
df_main['count'] = df_main['count'].fillna(0)

# Separar grupos
continental_states = [
    'AL','AZ','AR','CA','CO','CT','DE','FL','GA','ID','IL','IN',
    'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
    'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
    'TX','UT','VT','VA','WA','WV','WI','WY','DC'
]
alaska_hawaii = ['AK','HI']
territories = ['PR','VI','GU','MP','AS']

# Totais corretos direto do CSV
ak_count = int(df_us[df_us['STATE'] == 'AK'].shape[0])
hi_count = int(df_us[df_us['STATE'] == 'HI'].shape[0])
pr_count = int(df_us[df_us['STATE'] == 'PR'].shape[0])
vi_count = int(df_us[df_us['STATE'] == 'VI'].shape[0])
gu_count = int(df_us[df_us['STATE'] == 'GU'].shape[0])
mp_count = int(df_us[df_us['STATE'] == 'MP'].shape[0])
as_count = int(df_us[df_us['STATE'] == 'AS'].shape[0])

# --- Plot continental US ---
df_plot = df_main[df_main['STUSPS'].isin(continental_states)]

fig, ax = plt.subplots(1, 1, figsize=(15, 10))
df_plot.plot(
    column='count',
    cmap='OrRd',
    linewidth=0.8,
    ax=ax,
    edgecolor='0.8',
    legend=True
)

# Adicionar abreviações no mapa
for idx, row in df_plot.iterrows():
    plt.annotate(
        text=row['STUSPS'],
        xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
        horizontalalignment='center',
        verticalalignment='center',
        fontsize=8,
        color='black'
    )

# Nota inferior com todos os totais corretos
territory_note = ", ".join([f"{t}: {v}" for t, v in territory_counts.items()])
fig.text(
    0.5, 0.03,
    f'Alaska (AK): {ak_count}, Hawaii (HI): {hi_count}, Territories ({territory_note}) not included in map. '
    f'Counts include only aircraft registered with the U.S. FAA. Source updated: Tuesday, May 13, 2025.',
    ha='center',
    fontsize=10
)

ax.set_title("FAA Aircraft Population per Continental US States", fontsize=16)
ax.axis('off')
plt.show()