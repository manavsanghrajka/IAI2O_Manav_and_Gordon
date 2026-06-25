Write-Output "========================================"
Write-Output "Starting Global Data Pipeline"
Write-Output "========================================"

Write-Output "1. Geocoding Regions (Approx 30 mins)..."
python src\geocode_regions.py

Write-Output "`n2. Fetching WHO ITN Coverage..."
python src\process_who.py

Write-Output "`n3. Fetching Copernicus Climate Data (Approx 30 mins)..."
python src\process_copernicus.py

Write-Output "`n4. Fetching CHIRPS Precipitation (Approx 3-4 hours)..."
python src\process_chirps.py

Write-Output "`n5. Merging Final Dataset..."
python src\build_v3_dataset.py

Write-Output "`n6. Running Delta Model Validation..."
python src\pooled_delta_test.py

Write-Output "`n7. Exporting Dashboard JSON..."
python src\export_dashboard_json.py

Write-Output "`n========================================"
Write-Output "Pipeline Complete!"
Write-Output "========================================"
