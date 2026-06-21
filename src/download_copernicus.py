import cdsapi
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "raw_climate_malaria")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "era5_drc_monthly.nc")

def main():
    print("Connecting to Copernicus Climate Data Store...")
    c = cdsapi.Client()

    # DRC bounding box: North, West, South, East
    # DRC goes from roughly 5.5 N to 13.5 S, and 12.0 E to 31.5 E
    area = [5.5, 12.0, -13.5, 31.5]
    
    # We want years 2000 to 2024
    years = [str(y) for y in range(2000, 2025)]
    months = [f"{m:02d}" for m in range(1, 13)]

    request = {
        'product_type': 'monthly_averaged_reanalysis',
        'variable': [
            '2m_temperature',
            'total_precipitation',
            'volumetric_soil_water_layer_1',
            '2m_dewpoint_temperature' # For calculating humidity if needed
        ],
        'year': years,
        'month': months,
        'time': '00:00',
        'area': area,
        'format': 'netcdf',
    }

    print(f"Requesting ERA5-Land Monthly Means for DRC (2000-2024)...")
    print(f"This may take a while as the CDS processes the request in their queue.")
    
    c.retrieve(
        'reanalysis-era5-land-monthly-means',
        request,
        OUTPUT_FILE
    )
    
    print(f"\nDownload complete! File saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
