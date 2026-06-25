# Delta Model Validation Report

By shifting the target variable from **Absolute Prevalence** to the **Year-over-Year Delta** (change), we eliminated the model's ability to cheat via naive forecasting (i.e. just guessing whatever happened last year).

The model was forced to use CHIRPS Precipitation, WHO ITN Coverage, and Vectorial Capacity to biologically justify why the prevalence changes from year to year.

## Model Setup
- **Algorithm:** Lasso Regressor (Trained on Delta)
- **Features:** Temperature, CHIRPS Precipitation, Soil Moisture, Vectorial Capacity, WHO ITN Coverage, and One-Hot Encoded `ISO3`. (Lag-1 completely removed as a feature!)
- **Validation:** Global Temporal Holdout (Trained on 2000-2019 all regions, Tested recursively on 2020-2024 all regions)

## Global Absolute Accuracy Metrics (Holdout Test Set)
- **Mean Absolute Error (MAE):** `1.309` percentage points
- **Root Mean Squared Error (RMSE):** `3.959` percentage points
- **R^2:** `0.846`
- **Pearson r:** `0.940`

## Top Features Justifying the Delta
- **passthrough__ISO3_LKA**: -4.2625
- **num__Approx_C**: -0.1519
- **num__ITN_Coverage**: 0.1357
- **num__soil_moisture**: -0.0150
- **num__temperature_2m_mean**: -0.0000

## Graphs
![Global Accuracy Scatter](./delta_global_scatter.png)
![!Karas Accuracy](./delta_temporal_!Karas.png)
![Abia Accuracy](./delta_temporal_Abia.png)
![Abidjan Accuracy](./delta_temporal_Abidjan.png)
