import pandas as pd
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import pycountry

raw_path = "data/raw/faa/MASTER.txt"
processed_dir = "data/processed"
output_file = f"{processed_dir}/faa_master.csv"

os.makedirs(processed_dir, exist_ok=True)
master = pd.read_csv(raw_path, dtype=str)
master.to_csv(output_file, index=False)
print(f"Total records: {len(master)}")

df = pd.read_csv("data/processed/faa_master.csv", dtype=str)

#Standardising
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

# Drop rows missing all key fields - NA content
df = df.dropna(subset=['COUNTRY','CITY','STATE','STREET','STREET2', 'ZIP CODE'], how='all')

df.to_csv(output_file, index=False, na_rep='NA')
print(f"Total records after dropping empty location: {len(df)}")

is_unique = df['N-NUMBER'].is_unique
print(f"All N-NUMBER values unique? {is_unique}")

# Drop 7 and 8 values as type aircraft
df.drop(df[df['TYPE AIRCRAFT'].isin(['7', '8'])].index, inplace=True)
print(f"Records after dropping Weight-shift-control and Powered Parachute from Type Aircraft: {len(df)}")

#Counting number of aircraft per country based on the ISO2
country_counts = df['COUNTRY'].value_counts(dropna=False).reset_index()  # dropna=False to include missing values
country_counts.columns = ['iso2', 'aircraft_count']

# Converting ISO2 to ISO3 using pycountry
def iso2_to_iso3(iso2):
    try:
        return pycountry.countries.get(alpha_2=iso2).alpha_3
    except:
        return None

country_counts['iso3'] = country_counts['iso2'].apply(iso2_to_iso3)

# Load world map
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

# Merge counts into GeoDataFrame
world = world.merge(country_counts, how='left', left_on='iso_a3', right_on='iso3')
world['aircraft_count'] = world['aircraft_count'].fillna(0)

# Plot choropleth
fig, ax = plt.subplots(1, 1, figsize=(15, 8))
world.plot(column='aircraft_count', ax=ax, legend=True, cmap='OrRd', edgecolor='black')
ax.set_title('Aircraft Population by Country', fontsize=16)
ax.axis('off')

plt.show()