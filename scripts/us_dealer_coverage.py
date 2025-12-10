import pandas as pd

aircraft_data = 'data/processed/faa/master.csv'
dealer_data = 'data/processed/aea/AEA_RepairList2025-2026.csv'

aircraft_df = pd.read_csv(aircraft_data)
dealer_df = pd.read_csv(dealer_data)

aircraft_df = aircraft_df[aircraft_df['COUNTRY'] == 'US']
dealer_df = dealer_df[dealer_df['country'] == 'United States']

aircraft_df.to_csv('data/processed/faa_aircraft_us.csv', index=False)
dealer_df.to_csv('data/processed/AEA_RepairList2025-2026_US.csv', index=False)



