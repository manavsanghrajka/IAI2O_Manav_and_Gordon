import pandas as pd
import numpy as np
import xarray as xr
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
NC_FILE = os.path.join(DATA_DIR, "raw_climate_malaria", "era5_drc_monthly.nc")
DISEASE_DATA = os.path.join(DATA_DIR, "DRC combined data.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "test_results", "pooled_drc_data_v2.csv")

# Same as in build_pooled_dataset.py
drc_coords = {
    'Kinshasa': (-4.3224, 15.3070),
    'Kongo Central': (-5.5000, 14.0000),
    'Kwango': (-6.5000, 18.0000),
    'Kwilu': (-4.5000, 19.0000),
    'Mai-Ndombe': (-2.0000, 18.0000),
    'Kasai': (-4.0000, 21.0000),
    'Kasai Central': (-6.0000, 22.0000),
    'Kasai Oriental': (-6.1000, 23.6000),
    'Lomami': (-6.0000, 24.5000),
    'Sankuru': (-3.0000, 23.0000),
    'Maniema': (-3.0000, 26.0000),
    'Sud-Kivu': (-3.0000, 28.5000),
    'Nord-Kivu': (-0.5000, 29.0000),
    'Ituri': (1.5000, 29.5000),
    'Haut-Uele': (3.0000, 28.0000),
    'Tshopo': (0.5000, 25.0000),
    'Bas-Uele': (3.5000, 25.0000),
    'Nord-Ubangi': (4.0000, 21.0000),
    'Mongala': (2.0000, 21.5000),
    'Sud-Ubangi': (3.0000, 19.0000),
    'Equateur': (0.0000, 19.0000),
    'Tshuapa': (-1.0000, 22.0000),
    'Tanganyka': (-6.0000, 28.0000),
    'Haut-Lomami': (-8.0000, 25.0000),
    'Lualaba': (-10.0000, 24.0000),
    'Haut-Katanga': (-11.0000, 27.0000)
}

def main():
    print("Loading disease data...")
    disease_df = pd.read_csv(DISEASE_DATA)
    prev_df = disease_df[disease_df["Metric"] == "Infection Prevalence"].copy()
    prev_df = prev_df.rename(columns={"Name": "Region", "Value": "Infection Prevalence"})
    prev_df = prev_df[["Region", "Year", "Infection Prevalence"]]
    provinces = prev_df["Region"].unique()

    import zipfile
    
    print(f"Extracting Copernicus NetCDF data from {NC_FILE}...")
    extracted_file = os.path.join(DATA_DIR, "raw_climate_malaria", "data_stream-moda.nc")
    try:
        with zipfile.ZipFile(NC_FILE, 'r') as zip_ref:
            zip_ref.extractall(os.path.dirname(NC_FILE))
            # Find the .nc file inside the zip
            extracted_files = zip_ref.namelist()
            if len(extracted_files) > 0:
                extracted_file = os.path.join(os.path.dirname(NC_FILE), extracted_files[0])
    except zipfile.BadZipFile:
        # Maybe it wasn't a zip after all
        extracted_file = NC_FILE

    print(f"Loading data from {extracted_file}...")
    ds = xr.open_dataset(extracted_file)

    all_climate_data = []

    print("Extracting climate data for each province...")
    for prov in provinces:
        if prov not in drc_coords:
            continue
            
        lat, lon = drc_coords[prov]
        print(f"  Extracting {prov} (Lat: {lat}, Lon: {lon})...")
        
        try:
            # Extract nearest grid point
            prov_ds = ds.sel(longitude=lon, latitude=lat, method='nearest')
            
            # Convert to pandas dataframe
            df = prov_ds.to_dataframe().reset_index()
            
            # Group by year to get annual means (since disease data is annual)
            df['year'] = df['valid_time'].dt.year
            
            annual = df.groupby('year').agg({
                't2m': 'mean',          # Temperature in Kelvin
                'tp': 'sum',            # Total precipitation (meters) - actually since this is monthly means, we sum the monthly totals
                'swvl1': 'mean',        # Volumetric soil water layer 1 (m3/m3)
                'd2m': 'mean'           # Dewpoint temperature (Kelvin)
            }).reset_index()
            
            # Convert Kelvin to Celsius
            annual['temperature_2m_mean'] = annual['t2m'] - 273.15
            
            # Convert Precipitation from meters to mm
            annual['precipitation_sum'] = annual['tp'] * 1000
            
            # Keep soil moisture as is
            annual['soil_moisture'] = annual['swvl1']
            
            # Basic Vectorial Capacity Approx (same logic as before, just using temperature & precip)
            P = np.clip(annual['precipitation_sum'] / 200.0, 0, 1)
            temp_c = annual['temperature_2m_mean']
            T_factor = np.exp(-((temp_c - 28)**2) / 20)
            annual['Approx_C'] = 10 * T_factor * P * annual['soil_moisture'] # Adding soil moisture directly into the C calculation!
            
            annual['Region'] = prov
            all_climate_data.append(annual)
            
        except Exception as e:
            print(f"  -> Error processing {prov}: {e}")

    print("\nMerging datasets...")
    climate_df = pd.concat(all_climate_data, ignore_index=True)
    climate_df = climate_df.rename(columns={'year': 'Year'})
    
    # Merge on Region/Province and Year
    final_df = pd.merge(prev_df, climate_df, on=['Region', 'Year'], how='inner')
    
    # Calculate Lag-1
    final_df = final_df.sort_values(['Region', 'Year'])
    final_df['Lag_1_Infection_Prevalence'] = final_df.groupby('Region')['Infection Prevalence'].shift(1)
    final_df = final_df.dropna(subset=['Lag_1_Infection_Prevalence'])
    
    print(f"Saving to {OUTPUT_FILE}...")
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Success! Final rows: {len(final_df)}")

if __name__ == "__main__":
    main()
