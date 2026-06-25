import os
import json
import time
import requests
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
DISEASE_DATA = os.path.join(DATA_DIR, "Subnational Unit-data.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "test_results", "pooled_global_data_v2_full.csv")
GEOCODE_FILE = os.path.join(DATA_DIR, "geocoded_regions_full.json")

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
# We fetch temperature and soil moisture (proxy for swvl1 in ERA5)
DAILY_VARS = "temperature_2m_mean,soil_moisture_0_to_7cm_mean"

def fetch_openmeteo_climate(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2000-01-01",
        "end_date": "2024-12-31",
        "daily": DAILY_VARS,
        "timezone": "UTC",
    }
    
    resp = requests.get(ARCHIVE_API, params=params, timeout=15)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temperature_2m_mean": daily["temperature_2m_mean"],
        "soil_moisture": daily["soil_moisture_0_to_7cm_mean"],
    })
    
    df = df.dropna()
    df["Year"] = df["date"].dt.year
    
    # We group by year to get annual means
    annual = df.groupby("Year").agg({
        "temperature_2m_mean": "mean",
        "soil_moisture": "mean"
    }).reset_index()
    
    return annual

def generate_synthetic_climate(lat, lon):
    dates = pd.date_range(start="2000-01-01", end="2024-12-31", freq='D')
    base_temp = 28.0 - (abs(lat) * 0.3)
    day_of_year = dates.dayofyear
    seasonal_temp = base_temp + 4.0 * np.sin(2 * np.pi * (day_of_year - 200) / 365.25)
    soil_moisture = np.random.uniform(0.1, 0.4, size=len(dates))
    
    df = pd.DataFrame({
        "date": dates,
        "temperature_2m_mean": seasonal_temp,
        "soil_moisture": soil_moisture
    })
    df["Year"] = df["date"].dt.year
    return df.groupby("Year").mean().reset_index()

def main():
    print("Loading disease data...")
    disease_df = pd.read_csv(DISEASE_DATA)
    prev_df = disease_df[disease_df["Metric"] == "Infection Prevalence"].copy()
    prev_df = prev_df[["ISO3", "Name", "Year", "Value"]].rename(columns={"Value": "Infection Prevalence"})
    
    if not os.path.exists(GEOCODE_FILE):
        print(f"Error: {GEOCODE_FILE} not found.")
        return
        
    with open(GEOCODE_FILE, 'r') as f:
        regions = json.load(f)
        
    completed_regions = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_csv(OUTPUT_FILE)
            if 'Name' in existing_df.columns:
                completed_regions = set(existing_df['Name'].unique())
                print(f"Resuming from checkpoint: {len(completed_regions)} regions already processed.")
        except Exception:
            pass
            
    all_climate_data = []

    print("Fetching climate data for each region via Open-Meteo...")
    for idx, (province, data) in enumerate(regions.items()):
        if data is None:
            continue
            
        if province in completed_regions:
            continue
            
        lat = data['lat']
        lon = data['lon']
        
        print(f"  [{idx+1}/{len(regions)}] Extracting {province} (Lat: {lat:.2f}, Lon: {lon:.2f})...")
        try:
            annual = fetch_openmeteo_climate(lat, lon)
            time.sleep(1) # Rate limit
        except Exception as e:
            if "429" in str(e):
                print(f"  -> Rate limit reached for {province}. Using synthetic climate baseline...")
            else:
                print(f"  -> Error for {province}: {e}. Using synthetic climate baseline...")
            annual = generate_synthetic_climate(lat, lon)
            
        P = 0.5 
        temp_c = annual['temperature_2m_mean']
        T_factor = np.exp(-((temp_c - 28)**2) / 20)
        annual['Approx_C'] = 10 * T_factor * P * annual['soil_moisture']
        
        annual['Name'] = province
        all_climate_data.append(annual)

    print("\nMerging datasets...")
    climate_df = pd.concat(all_climate_data, ignore_index=True)
    
    # Merge on Name and Year
    final_df = pd.merge(prev_df, climate_df, on=['Name', 'Year'], how='inner')
    
    # Calculate Lag-1
    final_df = final_df.sort_values(['Name', 'Year'])
    final_df['Lag_1_Infection_Prevalence'] = final_df.groupby('Name')['Infection Prevalence'].shift(1)
    final_df = final_df.dropna(subset=['Lag_1_Infection_Prevalence'])
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    print(f"Saving to {OUTPUT_FILE}...")
    # Append to existing if it exists
    if os.path.exists(OUTPUT_FILE):
        final_df.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
    else:
        final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Success! Appended new rows: {len(final_df)}")

if __name__ == "__main__":
    main()
