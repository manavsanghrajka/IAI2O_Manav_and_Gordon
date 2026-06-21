# Matabeleland Spatial Holdout Accuracy Report

This report evaluates the Hybrid AI-Mechanistic pipeline's ability to predict disease burden in a completely unseen geography (Matabeleland, Zimbabwe) by training exclusively on the other 5 baseline regions.

## Model
- **Algorithm:** XGBoost Regressor
- **Features (X):** Temperature, Precipitation, Humidity, and Mechanistic Vectorial Capacity Approximation
- **Target (y):** Infection Prevalence (%)
- **Training Set:** 5 Regions (Beni, Delhi, Zinder, Nairobi, Heilongjiang)
- **Testing Set:** Matabeleland North (2000-2023)

## Standard Accuracy Metrics
- **Mean Absolute Error (MAE):** `6.083` percentage points
- **Root Mean Squared Error (RMSE):** `7.330` percentage points
- **Coefficient of Determination ($R^2$):** `-1.654`
- **Biological Correlation (Pearson $r$):** `-0.406`

## Raw Predictions vs Ground Truth
The detailed year-by-year predictions have been exported to `test_results.csv`.
