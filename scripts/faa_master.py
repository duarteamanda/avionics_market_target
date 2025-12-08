import os
import pandas as pd
import re
import geopandas as gpd
import matplotlib.pyplot as plt
import pycountry
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.cm as cm

# Load and read as CSV the FAA Master file
processed_dir = "data/processed"
os.makedirs(processed_dir, exist_ok=True)

raw_path = "data/raw/faa/MASTER.txt"
faa_master_csv = f"{processed_dir}/master.csv"

shapes_country = "data/shapes/countries"
shapes_states = "data/shapes/states_provinces/cb_2018_us_state_5m.shp"

df = pd.read_csv(raw_path, dtype=str)
print(f"Total records in raw file: {len(df)}")

# Cleaning and standardising - Columns that affect aircraft location
address_cols = ['COUNTRY', 'STATE', 'CITY', 'STREET', 'STREET2', 'ZIP CODE']

for col in address_cols:
    df[col] = df[col].str.strip()  # remove espaços
    df[col] = df[col].replace([r'^\s*$', r'(?i)^<unset>$', r'(?i)^NULL$'], pd.NA, regex=True)

df = df.dropna(subset=address_cols, how='all')
print(f"Empty COUNTRY total: {(df['COUNTRY'].isna() | (df['COUNTRY'] == '')).sum()}")
print(f"Total records after dropping rows with all addresses missing: {len(df)}")

unique_nnumbers = df['N-NUMBER'].nunique()
print(f"Unique N-NUMBERs: {unique_nnumbers}")

empty_state = df[(df['STATE'].isna()) | (df['STATE'] == '')]
print(f"Total records with empty STATE: {len(empty_state)}")
# Among them, filter which also have empty ZIP CODE
empty_state_no_zip = empty_state[empty_state['ZIP CODE'].isna() | (empty_state['ZIP CODE'] == '')]
print(f"Of those, records with empty ZIP CODE too: {len(empty_state_no_zip)}")

empty_state_csv = f"{processed_dir}/faa_empty_state.csv"
empty_state.to_csv(empty_state_csv, index=False, na_rep='NA')
print(f"Empty STATE records exported: {empty_state_csv}")

# Normalize COUNTRY column for reliable filtering
df['COUNTRY'] = df['COUNTRY'].str.upper().str.strip()

# Convert known variants to US
df['COUNTRY'] = df['COUNTRY'].replace({
    'UNITED STATES': 'US',
    'U.S.': 'US',
    'USA': 'US'
})

# Count NaN values in STATE for US country
missing_us_state = df[(df['COUNTRY'] == 'US') & (df['STATE'].isna())]
print("Total US records missing STATE:", len(missing_us_state))

df.to_csv(faa_master_csv, index=False, na_rep='NA')
print(f"Cleaned CSV saved: {faa_master_csv}")

## World Map Aircraft Population
country_counts = df.groupby('COUNTRY').size().reset_index(name='aircraft_count')

# Fix special ISO2 codes
manual_iso_map = {'AN': 'ANT', 'RQ': 'PRI'}  # Netherlands Antilles / Puerto Rico

def iso2_to_iso3_fixed(code):
    if code in manual_iso_map:
        return manual_iso_map[code]
    try:
        return pycountry.countries.get(alpha_2=code).alpha_3
    except:
        return None

country_counts['iso3'] = country_counts['COUNTRY'].apply(iso2_to_iso3_fixed)

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
cmap = cm.get_cmap('Reds')
norm = mcolors.Normalize(vmin=0, vmax=1)
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

ax.set_title('FAA - World Registered Aircraft Population', fontsize=18)
fig.text(0.5, 0.08,
         'Counts include only aircraft registered with the U.S. FAA. Source updated: Tuesday, May 13, 2025.',
         ha='center', fontsize=12)
ax.axis('off')
plt.show()

## US States + Territories
# # -------------------------
# states = gpd.read_file(shapes_states)
#
# # Filtra US + territórios
# df_us = df[df['COUNTRY'] == 'US']
# df_us = df[df['COUNTRY'].isin(['US','PR','VI','GU','MP','AS'])]
#
# # Contagem por estado
# state_counts = df_us['STATE'].value_counts().reset_index()
# state_counts.columns = ['STUSPS','count']
#
# # Merge com shapefile
# df_main = states.merge(state_counts, on='STUSPS', how='left').fillna(0)
#
# # Contagem AK/HI e territórios
# territories = ['PR','VI','GU','MP','AS']
# territory_counts = {t: int(df_us[df_us['STATE'] == t].shape[0]) for t in territories}
# ak_count = int(df_us[df_us['STATE'] == 'AK'].shape[0])
# hi_count = int(df_us[df_us['STATE'] == 'HI'].shape[0])
# territory_note = ", ".join([f"{t}: {v}" for t, v in territory_counts.items()])
#
# # -------------------------
# # Filtra apenas continental US
# # -------------------------
# continental_states = [
#     'AL','AZ','AR','CA','CO','CT','DE','FL','GA','ID','IL','IN',
#     'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
#     'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
#     'TX','UT','VT','VA','WA','WV','WI','WY','DC'
# ]
# df_plot = df_main[df_main['STUSPS'].isin(continental_states)].copy()
#
# # -------------------------
# # Define bins e cores
# # -------------------------
# max_count = int(df_plot['count'].max())
# # Bins fixos (0 será branco, os demais tons de azul)
# bins = [0, 500, 1000, 2000, 5000, 10000, 20000, max_count+1]
# labels = range(1, len(bins))
#
# # Categoriza
# df_plot['category'] = pd.cut(df_plot['count'], bins=bins, labels=labels, include_lowest=True)
#
# # Mapa de azul, 0 branco
# cmap = plt.cm.Blues
# df_plot['color'] = df_plot['category'].apply(
#     lambda x: '#ffffff' if pd.isna(x) else mcolors.to_hex(cmap((int(x)-1)/(len(labels)-1)))
# )
#
# # Legenda apenas valores >= 1
# legend_handles = []
# for i in range(1, len(bins)):
#     color = mcolors.to_hex(cmap((i-1)/(len(labels)-1)))
#     label = f"{int(bins[i-1])+1:,} - {int(bins[i])-1:,}"
#     legend_handles.append(mpatches.Patch(color=color, label=label))
#
# # -------------------------
# # Plot
# # -------------------------
# fig, ax = plt.subplots(1, 1, figsize=(15,10))
# df_plot.plot(color=df_plot['color'], linewidth=0.8, ax=ax, edgecolor='0.8', legend=False)
#
# # Annotate states
# for idx, row in df_plot.iterrows():
#     plt.annotate(
#         text=row['STUSPS'],
#         xy=(row['geometry'].centroid.x, row['geometry'].centroid.y),
#         ha='center', va='center', fontsize=8
#     )
#
# # Nota AK/HI e territórios
# fig.text(
#     0.5, 0.03,
#     f'Alaska (AK): {ak_count}, Hawaii (HI): {hi_count}. Territories ({territory_note}) not included in map. '
#     'Counts include only aircraft registered with the U.S. FAA.',
#     ha='center',
#     fontsize=10
# )
#
# # Legenda
# ax.legend(handles=legend_handles, title='Aircraft Count', loc='lower right', bbox_to_anchor=(1.05, 0.5))
#
# ax.axis('off')
# plt.show()
