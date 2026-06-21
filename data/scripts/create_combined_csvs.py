import os
import pandas as pd

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIMATE_CSV = os.path.join(DATA_DIR, "exports", "Annual_Average_Climate_Per_Region.csv")
OUTPUT_DIR = os.path.join(DATA_DIR, "combined_datasets")
RAW_DIR = os.path.join(DATA_DIR, "raw_climate_malaria")

CITY_FILES = {
    "Beni, DRC": os.path.join(RAW_DIR, "Beni.csv"),
    "Delhi, India": os.path.join(RAW_DIR, "Delhi.csv"),
    "Heilongjiang, China": os.path.join(RAW_DIR, "Heilongjiang.csv"),
    "Nairobi, Kenya": os.path.join(RAW_DIR, "Nairobi.csv"),
    "Zinder, Niger": os.path.join(RAW_DIR, "Zinder.csv"),
}

TARGET_CLIMATE_COLS = [
    "Year",
    "Region",
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "relative_humidity_2m_mean",
    "soil_temperature_mean",
]

TARGET_METRICS = [
    "Infection Prevalence",
    "Mortality Rate",
]

def main():
    print("=" * 60)
    print("Creating Combined Datasets per Region")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Load Climate Data
    print("Loading climate data...")
    climate_df = pd.read_csv(CLIMATE_CSV)
    # Filter to only the requested columns
    # Make sure all requested columns exist
    available_cols = [c for c in TARGET_CLIMATE_COLS if c in climate_df.columns]
    climate_df = climate_df[available_cols].copy()
    climate_df["Region"] = climate_df["Region"].str.strip()

    # 2. Process each region
    for region_key, filepath in CITY_FILES.items():
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found, skipping.")
            continue
            
        print(f"\nProcessing {region_key}...")
        
        # Load incidence/metric data for this city
        city_df = pd.read_csv(filepath)
        
        # Pivot the city data so we have one row per year, and metrics as columns
        # Filter to only the target metrics
        city_filtered = city_df[city_df["Metric"].isin(TARGET_METRICS)].copy()
        
        if city_filtered.empty:
            print(f"  No target metrics found for {region_key}. Skipping.")
            continue
            
        city_pivoted = city_filtered.pivot_table(
            index="Year", 
            columns="Metric", 
            values="Value", 
            aggfunc="first"
        ).reset_index()
        
        # Ensure both metric columns exist even if all NaN
        for metric in TARGET_METRICS:
            if metric not in city_pivoted.columns:
                city_pivoted[metric] = pd.NA
                
        # 3. Merge with climate data for this region
        region_climate = climate_df[climate_df["Region"] == region_key].copy()
        
        # Inner merge on Year
        merged = pd.merge(
            region_climate,
            city_pivoted,
            on="Year",
            how="inner" # use inner to only keep years where we have both climate and metrics
        )
        
        # Clean up columns: drop the Region column since the file is specific to the region
        merged = merged.drop(columns=["Region"])
        
        # Sort by Year
        merged = merged.sort_values("Year").reset_index(drop=True)
        
        # Save to CSV
        safe_region_name = region_key.split(',')[0].strip()
        output_filename = f"combined_{safe_region_name}.csv"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        merged.to_csv(output_path, index=False)
        print(f"  Saved {len(merged)} rows to: {output_path}")

    print("\n" + "=" * 60)
    print("Finished.")
    print("=" * 60)

if __name__ == "__main__":
    main()
