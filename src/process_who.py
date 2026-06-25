import os
import pandas as pd
from ghoclient import GHO

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
INPUT_CSV = os.path.join(DATA_DIR, "Subnational Unit-data.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "raw_climate_malaria", "who_itn_coverage_global_full.csv")

def main():
    print("Loading ISO3 codes from sample data...")
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return
        
    sample_df = pd.read_csv(INPUT_CSV)
    unique_iso3 = sample_df['ISO3'].unique()
    print(f"Found {len(unique_iso3)} unique ISO3 codes.")
    
    print("Connecting to WHO Global Health Observatory API...")
    gho = GHO()
    indicator = "MALARIA_ITN_COVERAGE"
    
    try:
        print(f"Fetching {indicator} dataset...")
        data = gho.get_data(indicator)
        
        all_country_data = []
        
        for country_code in unique_iso3:
            print(f"  -> Processing {country_code}...")
            df = data[data['SpatialDim'] == country_code].copy()
            
            if df.empty:
                print(f"     No data found for {country_code}! Generating zeros.")
                df = pd.DataFrame({'Year': range(2000, 2025), 'ITN_Coverage': 0.0, 'ISO3': country_code})
                all_country_data.append(df)
                continue
                
            # Extract the year and value
            df = df[['TimeDim', 'NumericValue']].rename(columns={'TimeDim': 'Year', 'NumericValue': 'ITN_Coverage'})
            df['Year'] = pd.to_numeric(df['Year'])
            df = df.sort_values('Year').reset_index(drop=True)
            df['ISO3'] = country_code
            
            # We need continuous data from 2000 to 2024
            full_years = pd.DataFrame({'Year': range(2000, 2025)})
            merged = pd.merge(full_years, df, on='Year', how='left')
            merged['ISO3'] = country_code
            
            # Interpolate missing values
            merged.loc[merged['Year'] == 2000, 'ITN_Coverage'] = merged.loc[merged['Year'] == 2000, 'ITN_Coverage'].fillna(0.0)
            merged['ITN_Coverage'] = merged['ITN_Coverage'].interpolate(method='linear').fillna(0.0)
            
            all_country_data.append(merged)
            
        final_df = pd.concat(all_country_data, ignore_index=True)
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved ITN data to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error fetching WHO data: {e}")

if __name__ == "__main__":
    main()
