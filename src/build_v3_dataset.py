import os
import pandas as pd

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

V2_DATA = os.path.join(DATA_DIR, "test_results", "pooled_global_data_v2_full.csv")
CHIRPS_DATA = os.path.join(DATA_DIR, "raw_climate_malaria", "chirps_precip_global_full.csv")
WHO_DATA = os.path.join(DATA_DIR, "raw_climate_malaria", "who_itn_coverage_global_full.csv")
V3_DATA = os.path.join(DATA_DIR, "test_results", "pooled_global_data_v3_full.csv")

# Baseline params
BASELINE_A = 0.3

def calc_dynamic_yearly_C(T, SM, P, a, ITN_cov_pct):
    """
    T: Temperature (Celsius)
    SM: Soil Moisture (or relative humidity analog if not available)
    P: Precipitation sum
    a: human biting rate
    ITN_cov_pct: Percentage of population with ITN (0 to 100)
    """
    ITN_cov = ITN_cov_pct / 100.0
    
    # 1. Mosquito Density (m) depends on rainfall and soil moisture
    if P < 50:
        m = 5
    elif P < 500:
        m = 10 + (P / 100.0)
    else:
        m = 15 + (SM * 10)
        
    # 2. Daily Biting Rate (a) modified by ITNs
    # ITNs physically block bites and kill mosquitoes that land on them
    a_effective = a * (1 - (0.5 * ITN_cov))
    
    # 3. Pathogen Development Time (n)
    if T <= 16:
        n = 30
    elif T >= 35:
        n = 30
    else:
        n = 111 / (T - 16)
        
    # 4. Mosquito Daily Survival (p)
    # Depends on humidity/moisture and ITN killing effect
    if SM < 0.2:
        p_base = 0.70
    elif SM < 0.5:
        p_base = 0.85
    else:
        p_base = 0.90
        
    p_effective = p_base * (1 - (0.2 * ITN_cov))
    
    # 5. Vectorial Capacity C
    try:
        C = (m * (a_effective ** 2) * (p_effective ** n)) / (-pd.np.log(p_effective) if p_effective < 1 else 0.01)
    except:
        C = 0.0
        
    return max(0, C)

def main():
    print("Loading datasets...")
    v2_df = pd.read_csv(V2_DATA)
    chirps_df = pd.read_csv(CHIRPS_DATA)
    who_df = pd.read_csv(WHO_DATA)
    
    print("Merging CHIRPS Precipitation...")
    # Drop the ERA5 precipitation if exists
    if 'precipitation_sum' in v2_df.columns:
        v2_df.drop(columns=['precipitation_sum'], inplace=True)
        
    chirps_df.rename(columns={'Region': 'Name'}, inplace=True)
    merged1 = pd.merge(v2_df, chirps_df, on=['Name', 'Year'], how='inner')
    
    print("Merging WHO ITN Coverage...")
    merged2 = pd.merge(merged1, who_df, on=['Year', 'ISO3'], how='left')
    
    print("Recalculating Vectorial Capacity with dynamic ITN & CHIRPS...")
    import numpy as np
    pd.np = np # Provide fallback for numpy in formula
    
    merged2['Approx_C'] = merged2.apply(lambda row: calc_dynamic_yearly_C(
        row['temperature_2m_mean'] - 273.15 if row['temperature_2m_mean'] > 100 else row['temperature_2m_mean'], # Handle kelvin/celsius if needed
        row['soil_moisture'],
        row['CHIRPS_Precipitation'],
        BASELINE_A,
        row['ITN_Coverage']
    ), axis=1)
    
    # Reorder columns and rename CHIRPS_Precipitation to precipitation_sum for compatibility
    merged2.rename(columns={'CHIRPS_Precipitation': 'precipitation_sum'}, inplace=True)
    
    # Drop any nulls generated during interpolation bounds
    merged2.dropna(inplace=True)
    
    os.makedirs(os.path.dirname(V3_DATA), exist_ok=True)
    merged2.to_csv(V3_DATA, index=False)
    
    print(f"\nSuccess! V3 Dataset saved to {V3_DATA}")
    print(f"Total rows: {len(merged2)}")
    print(merged2.head())

if __name__ == "__main__":
    main()
