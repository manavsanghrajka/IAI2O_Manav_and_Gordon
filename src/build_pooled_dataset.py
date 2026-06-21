import os
import time
import requests
import pandas as pd
from vectorial_capacity import calc_approx_yearly_C

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
COMBINED_CSV = os.path.join(DATA_DIR, "DRC combined data.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "test_results", "pooled_drc_data.csv")

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean"
BASELINE_A = 0.45
ITN_COV = 0.40

def geocode_provinces(provinces):
    print("Using hardcoded province coordinates...")
    # Approximate centroid coordinates for DRC provinces
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
    
    coords = {}
    for prov in provinces:
        if prov in drc_coords:
            coords[prov] = drc_coords[prov]
        else:
            print(f"Warning: No hardcoded coordinates for {prov}")
            
    return coords

def fetch_climate_for_coords(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2000-01-01",
        "end_date": "2024-12-31",
        "daily": DAILY_VARS,
        "timezone": "UTC",
    }
    
    resp = requests.get(ARCHIVE_API, params=params, timeout=120)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    
    df = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "temperature_2m_mean": daily["temperature_2m_mean"],
        "precipitation_sum": daily["precipitation_sum"],
        "relative_humidity_2m_mean": daily["relative_humidity_2m_mean"],
    })
    
    df = df.dropna()
    df["Year"] = df["date"].dt.year
    yearly = df.groupby("Year").agg({
        "temperature_2m_mean": "mean",
        "precipitation_sum": "sum",
        "relative_humidity_2m_mean": "mean"
    }).reset_index()
    
    # Calculate Vectorial Capacity
    yearly["Approx_C"] = yearly.apply(lambda row: calc_approx_yearly_C(
        row["temperature_2m_mean"],
        row["relative_humidity_2m_mean"],
        row["precipitation_sum"],
        BASELINE_A, ITN_COV
    ), axis=1)
    
    return yearly

def main():
    print("Loading combined disease data...")
    df = pd.read_csv(COMBINED_CSV)
    
    # Filter only for Infection Prevalence
    prev_df = df[df["Metric"] == "Infection Prevalence"].copy()
    
    # Rename 'Name' to 'Region'
    prev_df = prev_df.rename(columns={"Name": "Region", "Value": "Infection Prevalence"})
    
    # We only need Region, Year, and Infection Prevalence
    prev_df = prev_df[["Region", "Year", "Infection Prevalence"]]
    
    unique_provinces = prev_df["Region"].unique()
    print(f"Found {len(unique_provinces)} unique provinces.")
    
    coords = geocode_provinces(unique_provinces)
    
    all_climate_data = []
    
    print("\nFetching climate data for all geocoded provinces...")
    for prov, (lat, lon) in coords.items():
        print(f"  Fetching Open-Meteo data for {prov}...")
        try:
            climate_df = fetch_climate_for_coords(lat, lon)
            climate_df["Region"] = prov
            all_climate_data.append(climate_df)
        except Exception as e:
            print(f"  -> Failed to fetch climate for {prov}: {e}")
        
        time.sleep(1) # Be a good citizen

            
    if not all_climate_data:
        print("No climate data fetched. Exiting.")
        return
        
    combined_climate = pd.concat(all_climate_data, ignore_index=True)
    
    # Merge on Region and Year
    print("\nMerging dataset...")
    pooled_data = pd.merge(prev_df, combined_climate, on=["Region", "Year"], how="inner")
    
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    pooled_data.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSuccess! Pooled dataset saved to {OUTPUT_CSV}")
    print(f"Total rows: {len(pooled_data)}")
    
if __name__ == "__main__":
    main()
