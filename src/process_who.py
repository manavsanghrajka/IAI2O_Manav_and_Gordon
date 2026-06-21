import os
import pandas as pd
from ghoclient import GHO

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "raw_climate_malaria", "who_itn_coverage_drc.csv")

def main():
    print("Connecting to WHO Global Health Observatory API...")
    gho = GHO()
    
    indicator = "MALARIA_ITN_COVERAGE"
    country_code = "COD"  # Democratic Republic of the Congo
    
    print(f"Fetching {indicator} for {country_code}...")
    try:
        data = gho.get_data(indicator)
        
        # Filter for DRC
        df = data[data['SpatialDim'] == country_code].copy()
        
        if df.empty:
            print("No data found for COD!")
            return
            
        # Extract the year and value (usually NumericValue)
        df = df[['TimeDim', 'NumericValue']].rename(columns={'TimeDim': 'Year', 'NumericValue': 'ITN_Coverage'})
        df['Year'] = pd.to_numeric(df['Year'])
        df = df.sort_values('Year').reset_index(drop=True)
        
        print("Raw Data from WHO:")
        print(df)
        
        # We need continuous data from 2000 to 2024
        full_years = pd.DataFrame({'Year': range(2000, 2025)})
        merged = pd.merge(full_years, df, on='Year', how='left')
        
        # Interpolate missing values
        print("\nInterpolating missing years...")
        # Assume ITN coverage in 2000 was effectively 0.0%
        merged.loc[merged['Year'] == 2000, 'ITN_Coverage'] = 0.0
        
        merged['ITN_Coverage'] = merged['ITN_Coverage'].interpolate(method='linear')
        
        print("Interpolated Data:")
        print(merged)
        
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        merged.to_csv(OUTPUT_FILE, index=False)
        print(f"\nSaved ITN data to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error fetching WHO data: {e}")

if __name__ == "__main__":
    main()
