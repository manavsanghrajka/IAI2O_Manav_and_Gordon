# Delta Model Validation Report

By shifting the target variable from **Absolute Prevalence** to the **Year-over-Year Delta** (change), we eliminated the model's ability to cheat via naive forecasting (i.e. just guessing whatever happened last year).

The model was forced to use CHIRPS Precipitation, WHO ITN Coverage, and Vectorial Capacity to biologically justify why the prevalence changes from year to year.

## Model Setup
- **Algorithm:** Lasso Regressor (Trained on Delta)
- **Features:** Temperature, CHIRPS Precipitation, Soil Moisture, Vectorial Capacity, WHO ITN Coverage, and One-Hot Encoded `ISO3`. (Lag-1 completely removed as a feature!)
- **Validation:** Global Temporal Holdout (Trained on 2000-2019 all regions, Tested recursively on 2020-2024 all regions)

## Global Absolute Accuracy Metrics (Holdout Test Set)
- **Mean Absolute Error (MAE):** `2.640` percentage points
- **Root Mean Squared Error (RMSE):** `5.938` percentage points
- **R^2:** `0.729`
- **Pearson r:** `0.901`

## Top Features Justifying the Delta
- **num__ITN_Coverage**: -0.3137
- **num__temperature_2m_mean**: -0.3004
- **num__soil_moisture**: 0.2082
- **num__precipitation_sum**: 0.0808
- **num__Approx_C**: -0.0000

## Graphs
![Global Accuracy Scatter](./delta_global_scatter.png)
![Barima/Waini (Region n1) Accuracy](./delta_temporal_Barima_Waini (Region n1).png)
![Cascades Accuracy](./delta_temporal_Cascades.png)
![Dayr Az Zor Accuracy](./delta_temporal_Dayr Az Zor.png)
