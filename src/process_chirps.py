import os
import pandas as pd
import time
import climateserv.api

import json

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "raw_climate_malaria", "chirps_precip_global_full.csv")
GEOCODE_FILE = os.path.join(DATA_DIR, "geocoded_regions_full.json")


def fetch_chirps_for_coord(lat, lon, start_date, end_date):
    # Create a tiny bounding box around the coordinate (approx 1km)
    delta = 0.01
    geom = [[lon-delta, lat+delta], [lon+delta, lat+delta], 
            [lon+delta, lat-delta], [lon-delta, lat-delta], 
            [lon-delta, lat+delta]]
    
    # Dataset 0 = CHIRPS Precipitation
    try:
        # request_data(DatasetType, OperationType, EarliestDate, LatestDate, GeometryCoords, SeasonalEnsemble, SeasonalVariable, Outfile)
        data = climateserv.api.request_data(0, 'Average', start_date, end_date, geom, '', '', 'memory_object')
        
        # 'data' should be a dictionary containing the timeseries
        # The structure is usually data['data'] which is a list of dicts
        records = []
        for row in data['data']:
            # row format: {'date': '...', 'value': {'avg': ...}} or similar depending on the operation
            # Let's extract the raw values.
            # In ClimateSERV, values are usually row['value']['avg'] and date is row['date']
            val_dict = row.get('value', {})
            avg_val = val_dict.get('avg', 0)
            records.append({'date': row['date'], 'precipitation': avg_val})
            
        return pd.DataFrame(records)
    except Exception as e:
        print(f"    Error fetching from ClimateSERV: {e}")
        return pd.DataFrame()

def main():
    print("Fetching CHIRPS high-resolution precipitation data...")
    
    if not os.path.exists(GEOCODE_FILE):
        print(f"Error: {GEOCODE_FILE} not found. Run geocode_regions.py first.")
        return
        
    with open(GEOCODE_FILE, 'r') as f:
        regions = json.load(f)
        
    # Checkpointing logic
    processed_regions = set()
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)
        if 'Region' in existing_df.columns:
            processed_regions = set(existing_df['Region'].unique())
            print(f"Resuming from checkpoint: {len(processed_regions)} regions already processed.")
            
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    for idx, (province, data) in enumerate(regions.items()):
        if province in processed_regions:
            print(f"[{idx+1}/{len(regions)}] Skipping {province} (Already processed)")
            continue
            
        if data is None:
            print(f"[{idx+1}/{len(regions)}] Skipping {province} (No coordinates available)")
            continue
            
        lat = data['lat']
        lon = data['lon']
        
        print(f"[{idx+1}/{len(regions)}] Fetching CHIRPS for {province}...")
        
        try:
            # Due to 20-year limit, split into two chunks
            print(f"  -> Chunk 1 (2000-2015)")
            df1 = fetch_chirps_for_coord(lat, lon, "01/01/2000", "12/31/2015")
            time.sleep(2) # Respect rate limits
            
            print(f"  -> Chunk 2 (2016-2024)")
            df2 = fetch_chirps_for_coord(lat, lon, "01/01/2016", "12/31/2024")
            time.sleep(2)
        except Exception as e:
            print(f"  -> Error fetching data: {e}")
            continue
            
        if df1.empty and df2.empty:
            print(f"  -> WARNING: Failed to fetch any data for {province}")
            continue
            
        prov_df = pd.concat([df1, df2], ignore_index=True)
        
        if prov_df.empty:
            continue
            
        # Parse dates and group by year
        prov_df['date'] = pd.to_datetime(prov_df['date'])
        prov_df['Year'] = prov_df['date'].dt.year
        
        annual = prov_df.groupby('Year')['precipitation'].sum().reset_index()
        annual.rename(columns={'precipitation': 'CHIRPS_Precipitation'}, inplace=True)
        annual['Region'] = province
        
        # Append to CSV dynamically
        annual.to_csv(OUTPUT_FILE, mode='a', header=not os.path.exists(OUTPUT_FILE), index=False)
        print(f"  -> Saved {len(annual)} years of data for {province}")
        
    print(f"\nSuccess! CHIRPS data saved/updated to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
