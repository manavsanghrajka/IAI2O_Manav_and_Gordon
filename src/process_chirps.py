import os
import pandas as pd
import time
import climateserv.api

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "raw_climate_malaria", "chirps_precip_drc.csv")

# DRC Province Coordinates (Centroids)
PROVINCE_COORDS = {
    'Mongala': (2.0000, 21.5000),
    'Nord-Ubangi': (4.0000, 21.0000),
    'Sud-Ubangi': (3.0000, 19.0000),
    'Tshuapa': (-1.0000, 22.0000),
    'Kwango': (-6.5000, 18.0000),
    'Kwilu': (-4.5000, 19.0000),
    'Mai-Ndombe': (-2.0000, 18.0000),
    'Kasai': (-4.0000, 21.0000),
    'Sankuru': (-3.0000, 23.0000),
    'Haut-Lomami': (-8.0000, 25.0000),
    'Lualaba': (-10.0000, 24.0000),
    'Tanganyka': (-6.0000, 28.0000),
    'Maniema': (-3.0000, 26.0000),
    'Nord-Kivu': (-0.5000, 29.0000),
    'Sud-Kivu': (-3.0000, 28.5000),
    'Bas-Uele': (3.5000, 25.0000),
    'Haut-Uele': (3.0000, 28.0000),
    'Ituri': (1.5000, 29.5000),
    'Tshopo': (0.5000, 25.0000),
    'Kasai Oriental': (-6.1000, 23.6000),
    'Kongo Central': (-5.5000, 14.0000),
    'Equateur': (0.0000, 19.0000),
    'Kinshasa': (-4.3224, 15.3070),
    'Haut-Katanga': (-11.0000, 27.0000),
    'Lomami': (-6.0000, 24.5000),
    'Kasai Central': (-6.0000, 22.0000)
}

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
    
    all_regions_data = []
    
    for idx, (province, (lat, lon)) in enumerate(PROVINCE_COORDS.items()):
        print(f"[{idx+1}/{len(PROVINCE_COORDS)}] Fetching CHIRPS for {province}...")
        
        # Due to 20-year limit, split into two chunks
        print(f"  -> Chunk 1 (2000-2015)")
        df1 = fetch_chirps_for_coord(lat, lon, "01/01/2000", "12/31/2015")
        time.sleep(2) # Respect rate limits
        
        print(f"  -> Chunk 2 (2016-2024)")
        df2 = fetch_chirps_for_coord(lat, lon, "01/01/2016", "12/31/2024")
        time.sleep(2)
        
        if df1.empty and df2.empty:
            print(f"  -> WARNING: Failed to fetch any data for {province}")
            continue
            
        prov_df = pd.concat([df1, df2], ignore_index=True)
        
        if prov_df.empty:
            continue
            
        # Parse dates and group by year
        prov_df['date'] = pd.to_datetime(prov_df['date'])
        prov_df['Year'] = prov_df['date'].dt.year
        
        # We need the annual sum of precipitation (since operation is 'Average' per day/month, we might need to be careful)
        # Wait, if we requested 'Average' for a bounding box, ClimateSERV returns the spatial average for each time step.
        # Then we sum those time steps over the year to get total annual precipitation.
        annual = prov_df.groupby('Year')['precipitation'].sum().reset_index()
        annual.rename(columns={'precipitation': 'CHIRPS_Precipitation'}, inplace=True)
        annual['Region'] = province
        
        all_regions_data.append(annual)
        
    if not all_regions_data:
        print("Failed to fetch any CHIRPS data!")
        return
        
    final_df = pd.concat(all_regions_data, ignore_index=True)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSuccess! CHIRPS data saved to {OUTPUT_FILE}")
    print(f"Total rows: {len(final_df)}")

if __name__ == "__main__":
    main()
