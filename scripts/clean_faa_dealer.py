import pandas as pd
import re
import os

df = pd.read_csv('data/raw/faa/Dealer.txt', delimiter=',')

df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
df['NAME'] = df['NAME'].apply(lambda x: re.sub(r'\s+', ' ', x))
df['NAME'] = df['NAME'].apply(lambda x: re.sub(r'\bIncorporated\b', 'Inc', x, flags=re.IGNORECASE))
df['NAME'] = df['NAME'].str.rstrip("., ")

output_dir = "data/processed/faa"
os.makedirs(output_dir, exist_ok=True)

csv_path = "data/processed/faa/FAA_Dealer.csv"
df.to_csv(csv_path, index=False)

print(f"DEALER.txt cleaned and saved as CSV: {csv_path}")
