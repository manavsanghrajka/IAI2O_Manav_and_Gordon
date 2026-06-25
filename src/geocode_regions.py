import os
import pandas as pd
import json
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
INPUT_CSV = os.path.join(DATA_DIR, "Subnational Unit-data.csv")
OUTPUT_JSON = os.path.join(DATA_DIR, "geocoded_regions_full.json")

def main():
    print(f"Loading data from {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    
    unique_regions = df[['Name', 'National Unit']].drop_duplicates()
    print(f"Found {len(unique_regions)} unique regions to geocode.")
    
    geolocator = Nominatim(user_agent="malaria_model_geocoder_123")
    
    # Load existing cache
    geocache = {}
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r") as f:
            geocache = json.load(f)
            
    updates = 0
    
    for idx, row in unique_regions.iterrows():
        region_name = row['Name']
        country_name = row['National Unit']
        
        # Nominatim prefers detailed queries. 
        query = f"{region_name}, {country_name}"
        
        if region_name in geocache:
            continue
            
        print(f"Geocoding: {query}...")
        
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                geocache[region_name] = {
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "query": query,
                    "country": country_name
                }
                print(f"  -> Found: {location.latitude}, {location.longitude}")
            else:
                # Fallback to just country if subnational is extremely obscure
                print(f"  -> Not found. Trying country level fallback for {country_name}...")
                fallback_loc = geolocator.geocode(country_name, timeout=10)
                if fallback_loc:
                    geocache[region_name] = {
                        "lat": fallback_loc.latitude,
                        "lon": fallback_loc.longitude,
                        "query": country_name,
                        "country": country_name,
                        "fallback": True
                    }
                    print(f"  -> Fallback found: {fallback_loc.latitude}, {fallback_loc.longitude}")
                else:
                    print("  -> FAILED completely.")
                    geocache[region_name] = None
                    
            updates += 1
            time.sleep(1) # Nominatim requires 1 sec delay between requests
            
        except Exception as e:
            print(f"  -> Error: {e}")
            time.sleep(5)
            
        if updates > 0 and updates % 20 == 0:
            with open(OUTPUT_JSON, "w") as f:
                json.dump(geocache, f, indent=4)
            print(f"  -> Progress saved.")
            
    if updates > 0:
        with open(OUTPUT_JSON, "w") as f:
            json.dump(geocache, f, indent=4)
        print(f"\nSaved geocoded coordinates to {OUTPUT_JSON}")
    else:
        print("\nAll regions were already geocoded.")

if __name__ == "__main__":
    main()
